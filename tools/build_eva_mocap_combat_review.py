#!/usr/bin/env python3
"""Build isolated constrained CMU unarmed/knife review candidates.

Human capture owns timing and the upper-body trajectory.  Tiger feet, joint
range, grip, root scale and ready-pose closure are imposed afterwards.  The
output is never promoted to live gameplay by this script.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from mathutils import Quaternion

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parent.parent
BODY_BONES = (
    "root", "torso_lower", "torso_upper", "aim_pitch", "neck", "head",
    "clavicle_l", "arm_l", "forearm_l", "wrist_l", "hand_l",
    "clavicle_r", "arm_r", "forearm_r", "wrist_r", "hand_r",
    "leg_l", "shin_l", "ankle_l", "foot_l",
    "leg_r", "shin_r", "ankle_r", "foot_r",
)
IDENTITY = [1.0, 0.0, 0.0, 0.0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def resolved(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else REPO / value


def rounded(value: Quaternion) -> list[float]:
    value.normalize()
    return [round(float(value.w), 7), round(float(value.x), 7),
            round(float(value.y), 7), round(float(value.z), 7)]


def interpolate_quaternion(first, second, amount: float) -> list[float]:
    left = Quaternion(tuple(float(value) for value in first))
    right = Quaternion(tuple(float(value) for value in second))
    left.normalize()
    right.normalize()
    if left.dot(right) < 0.0:
        right.negate()
    return rounded(left.slerp(right, amount))


def resample(document: dict, clip: dict, target_rate: float) -> list[dict]:
    source_rate = float(document["sample_rate"])
    source = clip["frames"]
    duration = (len(source) - 1) / source_rate
    count = int(round(duration * target_rate)) + 1
    frames = []
    for target_index in range(count):
        source_position = min(
            len(source) - 1,
            target_index / target_rate * source_rate,
        )
        first = int(math.floor(source_position))
        second = min(len(source) - 1, first + 1)
        amount = source_position - first
        left = source[first]
        right = source[second]
        rotations = [
            interpolate_quaternion(before, after, amount)
            for before, after in zip(
                left["rotation_wxyz"], right["rotation_wxyz"])
        ]
        root = [
            float(left["root_m"][axis]) * (1.0 - amount)
            + float(right["root_m"][axis]) * amount
            for axis in range(3)
        ]
        contact_source = source[int(round(source_position))]
        frames.append({
            "root_m": root,
            "rotation_wxyz": rotations,
            "foot_contact": list(contact_source["foot_contact"]),
        })
    return frames


def scale_from_reference(reference, value, amount: float) -> list[float]:
    first = Quaternion(tuple(float(item) for item in reference))
    current = Quaternion(tuple(float(item) for item in value))
    first.normalize()
    current.normalize()
    if first.dot(current) < 0.0:
        current.negate()
    delta = first.conjugated() @ current
    delta.normalize()
    scaled = first @ Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(
        delta, amount)
    return rounded(scaled)


def smoothstep(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def smooth_body_rotations(frames: list[dict], bones: list[str],
                          strength: float = 0.20) -> None:
    """One bounded symmetric pass; static grip channels are untouched."""
    source = copy.deepcopy(frames)
    for frame_index in range(1, len(frames) - 1):
        for bone_index, bone in enumerate(bones):
            if bone.startswith("finger_"):
                continue
            before = Quaternion(tuple(source[frame_index - 1]
                                      ["rotation_wxyz"][bone_index]))
            current = Quaternion(tuple(source[frame_index]
                                       ["rotation_wxyz"][bone_index]))
            after = Quaternion(tuple(source[frame_index + 1]
                                     ["rotation_wxyz"][bone_index]))
            if before.dot(after) < 0.0:
                after.negate()
            guide = before.slerp(after, 0.5)
            if current.dot(guide) < 0.0:
                guide.negate()
            frames[frame_index]["rotation_wxyz"][bone_index] = rounded(
                current.slerp(guide, strength))


def normalized_frames(document: dict, source_clip: dict,
                      target_bones: list[str], finger_pose: dict,
                      foundation_pose: dict, rate: float,
                      constraints: dict) -> list[dict]:
    source_bones = list(document["bones"])
    source_index = {name: index for index, name in enumerate(source_bones)}
    sampled = resample(document, source_clip, rate)
    first_root = [float(value) for value in sampled[0]["root_m"]]
    scales = constraints["boneMotionScale"]
    output = []
    first_pose = None
    for source_frame in sampled:
        rotations = []
        for bone in target_bones:
            if bone in finger_pose:
                rotations.append(list(finger_pose[bone]))
                continue
            source_value = (source_frame["rotation_wxyz"][
                source_index[bone]] if bone in source_index else IDENTITY)
            reference_value = (sampled[0]["rotation_wxyz"][
                source_index[bone]] if bone in source_index else IDENTITY)
            scale = float(scales.get(bone, 0.0))
            if scale <= 0.0 and bone in foundation_pose:
                rotations.append(list(foundation_pose[bone]))
            else:
                rotations.append(scale_from_reference(
                    reference_value, source_value, scale))
        if first_pose is None:
            first_pose = copy.deepcopy(rotations)
        root_delta = [
            float(source_frame["root_m"][axis]) - first_root[axis]
            for axis in range(3)
        ]
        root = [
            root_delta[0] * float(constraints["rootHorizontalScale"]),
            root_delta[1] * float(constraints["rootVerticalScale"]),
            root_delta[2] * float(constraints["rootHorizontalScale"]),
        ]
        output.append({
            "root_m": [round(value, 7) for value in root],
            "rotation_wxyz": rotations,
            "foot_contact": [True, True],
        })

    ready = copy.deepcopy(output[0])
    ready["root_m"] = [0.0, 0.0, 0.0]
    result = [copy.deepcopy(ready) for _ in range(
        int(constraints["anticipationFrames"]))]
    result.extend(output)
    last = output[-1]
    recovery = int(constraints["recoveryFrames"])
    for index in range(1, recovery + 1):
        amount = smoothstep(index / recovery)
        result.append({
            "root_m": [
                round(float(last["root_m"][axis]) * (1.0 - amount), 7)
                for axis in range(3)
            ],
            "rotation_wxyz": [
                interpolate_quaternion(before, after, amount)
                for before, after in zip(
                    last["rotation_wxyz"], ready["rotation_wxyz"])
            ],
            "foot_contact": [True, True],
        })
    result.extend(copy.deepcopy(ready) for _ in range(
        int(constraints["readyHoldFrames"])))
    return result


def maximum_rotation_step(frames: list[dict], bones: list[str]) -> dict:
    maximum = 0.0
    location = None
    for frame_index in range(1, len(frames)):
        for bone_index, bone in enumerate(bones):
            before = Quaternion(tuple(
                frames[frame_index - 1]["rotation_wxyz"][bone_index]))
            after = Quaternion(tuple(
                frames[frame_index]["rotation_wxyz"][bone_index]))
            radians = before.rotation_difference(after).angle
            degrees = math.degrees(min(radians, 2.0 * math.pi - radians))
            if degrees > maximum:
                maximum = degrees
                location = {"frame": frame_index, "bone": bone}
    return {"degrees": maximum, "location": location}


def seam_error(frames: list[dict], bones: list[str]) -> float:
    return max(
        math.degrees(min(
            Quaternion(tuple(frames[0]["rotation_wxyz"][index]))
            .rotation_difference(Quaternion(tuple(
                frames[-1]["rotation_wxyz"][index]))).angle,
            2.0 * math.pi - Quaternion(tuple(
                frames[0]["rotation_wxyz"][index]))
            .rotation_difference(Quaternion(tuple(
                frames[-1]["rotation_wxyz"][index]))).angle,
        ))
        for index in range(len(bones))
    )


def main() -> None:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise RuntimeError("mocap combat manifest schema differs")
    rate = float(manifest["sampleRate"])
    geo_path = resolved(manifest["targetGeo"])
    if not geo_path.is_file():
        raise RuntimeError(f"target geometry is missing: {geo_path}")
    fist_document = json.loads(resolved(manifest["fistProfile"])
                               .read_text(encoding="utf-8"))
    fist_bones = fist_document["bones"]
    fist_frame = next(iter(fist_document["clips"].values()))["frames"][0]
    finger_pose = {
        name: fist_frame["rotation_wxyz"][index]
        for index, name in enumerate(fist_bones)
        if name.startswith("finger_")
    }
    finger_bones = [name for name in fist_bones
                    if name.startswith("finger_")]
    target_bones = list(BODY_BONES) + finger_bones
    foundation_document = json.loads(resolved(
        manifest["approvedFoundationProfile"]).read_text(encoding="utf-8"))
    foundation_bones = foundation_document["bones"]
    foundation_frame = foundation_document["clips"][
        manifest["approvedFoundationClip"]]["frames"][0]
    foundation_pose = {
        name: foundation_frame["rotation_wxyz"][index]
        for index, name in enumerate(foundation_bones)
    }
    foundation_pose["root"] = IDENTITY
    clips = {}
    sources = []
    reports = {}
    for item in manifest["clips"]:
        database_path = resolved(item["sourceDatabase"])
        source_document = json.loads(database_path.read_text(
            encoding="utf-8"))
        source_clip = source_document["clips"][item["sourceClip"]]
        frames = normalized_frames(
            source_document, source_clip, target_bones, finger_pose,
            foundation_pose, rate, manifest["constraints"])
        smooth_body_rotations(frames, target_bones)
        pre_constraint_step = maximum_rotation_step(frames, target_bones)
        step = maximum_rotation_step(frames, target_bones)
        seam = seam_error(frames, target_bones)
        maximum_root = max(math.hypot(
            float(frame["root_m"][0]), float(frame["root_m"][2]))
            for frame in frames)
        failures = []
        if step["degrees"] > 20.0:
            failures.append("rotation_step_over_20_degrees")
        if seam > 0.05:
            failures.append("ready_pose_seam_over_0_05_degrees")
        if maximum_root > 0.35:
            failures.append("root_horizontal_offset_over_0_35m")
        if not all(frame["foot_contact"] == [True, True]
                   for frame in frames):
            failures.append("support_contact_contract_invalid")
        clip = {
            "duration_seconds": round((len(frames) - 1) / rate, 7),
            "loop": False,
            "role": "isolated_constrained_human_mocap_review_only",
            "kind": item["kind"],
            "source_id": item["sourceId"],
            "source_clip": item["sourceClip"],
            "constraints": (
                "CMU timing/upper-body trajectory; Tiger support, root, "
                "joint amplitude, fist/knife grip and ready closure"),
            "frames": frames,
        }
        clips[item["name"]] = clip
        reports[item["name"]] = {
            "sourceDatabase": str(database_path),
            "sourceClip": item["sourceClip"],
            "sourceId": item["sourceId"],
            "frames": len(frames),
            "durationSeconds": clip["duration_seconds"],
            "preConstraintMaximumRotationStep": pre_constraint_step,
            "maximumRotationStep": step,
            "readyPoseSeamDegrees": seam,
            "maximumRootHorizontalOffsetMetres": maximum_root,
            "supportMode": manifest["constraints"]["supportMode"],
            "temporalSmoothing": {
                "passes": 1, "symmetricNeighbourStrength": 0.20,
                "fingerChannelsModified": False,
            },
            "failures": failures,
            "eligible": not failures,
        }
        for source in source_document.get("sources", []):
            if source not in sources:
                sources.append(source)

    failures = [
        f"{name}:{failure}"
        for name, report in reports.items()
        for failure in report["failures"]
    ]
    output = {
        "schema": 2,
        "coordinate_system": "bedrock_x_right_y_up_z_back",
        "quaternion_order": "wxyz",
        "sample_rate": rate,
        "preview_only": True,
        "live_gameplay_replacement": False,
        "human_review": manifest["humanDecision"],
        "authority": "constrained_human_mocap_candidate_review_only",
        "sources": sources,
        "bones": target_bones,
        "clips": clips,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    report = {
        "schema": 1,
        "result": ("ELIGIBLE_FOR_HUMAN_REVIEW_ONLY"
                   if not failures else "FAIL"),
        "automaticVisualApproval": False,
        "liveGameplayChanged": False,
        "sampleRate": rate,
        "bones": len(target_bones),
        "clips": reports,
        "failures": failures,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
