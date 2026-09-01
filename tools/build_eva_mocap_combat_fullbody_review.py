#!/usr/bin/env python3
"""Build Phase-H full-body Bandai combat candidates for Tiger review."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_eva_mocap_combat_review import (
    BODY_BONES,
    IDENTITY,
    interpolate_quaternion,
    maximum_rotation_step,
    resample,
    seam_error,
    smooth_body_rotations,
    smoothstep,
)


REPO = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def resolved(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def source_frames(document: dict, clip: dict, target_bones: list[str],
                  finger_pose: dict, rate: float,
                  time_scale: float, constraints: dict) -> list[dict]:
    source_bones = list(document["bones"])
    source_index = {name: index for index, name in enumerate(source_bones)}
    sampled = resample(document, clip, rate * time_scale)
    frames = []
    for source_frame in sampled:
        rotations = []
        for bone in target_bones:
            if bone in finger_pose:
                rotations.append(list(finger_pose[bone]))
            elif bone in source_index:
                rotations.append(list(source_frame["rotation_wxyz"][
                    source_index[bone]]))
            else:
                rotations.append(list(IDENTITY))
        frames.append({
            "root_m": [round(float(value), 7)
                       for value in source_frame["root_m"]],
            "rotation_wxyz": rotations,
            "foot_contact": list(source_frame["foot_contact"]),
        })

    ready = copy.deepcopy(frames[0])
    ready["root_m"] = [0.0, 0.0, 0.0]
    output = [copy.deepcopy(ready) for _ in range(
        int(constraints["anticipationFrames"]))]
    output.extend(frames)
    last = frames[-1]
    recovery = int(constraints["recoveryFrames"])
    for index in range(1, recovery + 1):
        amount = smoothstep(index / recovery)
        output.append({
            "root_m": [
                round(float(last["root_m"][axis]) * (1.0 - amount), 7)
                for axis in range(3)
            ],
            "rotation_wxyz": [
                interpolate_quaternion(before, after, amount)
                for before, after in zip(
                    last["rotation_wxyz"], ready["rotation_wxyz"])
            ],
            "foot_contact": (list(last["foot_contact"])
                             if index <= recovery // 2
                             else list(ready["foot_contact"])),
        })
    output.extend(copy.deepcopy(ready) for _ in range(
        int(constraints["readyHoldFrames"])))
    for _ in range(int(constraints["temporalSmoothingPasses"])):
        smooth_body_rotations(
            output, target_bones,
            float(constraints["temporalSmoothingStrength"]))
    return output


def main() -> None:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise RuntimeError("Phase-H manifest schema differs")
    if manifest["constraints"]["supportMode"] != "CAPTURED_FULL_BODY":
        raise RuntimeError("Phase-H lower body is not capture-authoritative")
    rate = float(manifest["sampleRate"])
    fist_document = json.loads(resolved(
        manifest["fistProfile"]).read_text(encoding="utf-8"))
    fist_bones = fist_document["bones"]
    fist_frame = next(iter(fist_document["clips"].values()))["frames"][0]
    finger_pose = {
        name: fist_frame["rotation_wxyz"][index]
        for index, name in enumerate(fist_bones)
        if name.startswith("finger_")
    }
    target_bones = list(BODY_BONES) + list(finger_pose)
    clips = {}
    sources = []
    reports = {}
    all_failures = []
    lower_indices = [target_bones.index(name) for name in (
        "torso_lower", "leg_l", "shin_l", "foot_l",
        "leg_r", "shin_r", "foot_r")]
    for item in manifest["clips"]:
        database_path = resolved(item["sourceDatabase"])
        document = json.loads(database_path.read_text(encoding="utf-8"))
        source_clip = document["clips"][item["sourceClip"]]
        frames = source_frames(
            document, source_clip, target_bones, finger_pose, rate,
            float(item["timeScale"]), manifest["constraints"])
        step = maximum_rotation_step(frames, target_bones)
        seam = seam_error(frames, target_bones)
        unsupported = sum(not any(frame["foot_contact"])
                          for frame in frames) / len(frames)
        lower_motion = max(
            maximum_rotation_step([
                {"rotation_wxyz": [frame["rotation_wxyz"][index]
                                    for index in lower_indices]}
                for frame in frames
            ], [target_bones[index] for index in lower_indices])["degrees"],
            0.0,
        )
        root_range = max(
            (sum(float(value) ** 2 for value in frame["root_m"])) ** 0.5
            for frame in frames)
        failures = []
        if step["degrees"] > float(
                manifest["constraints"]["maximumRotationStepDegrees"]):
            failures.append("rotation_step_over_limit")
        if seam > 0.05:
            failures.append("ready_pose_seam_over_0_05_degrees")
        if unsupported > float(
                manifest["constraints"]["maximumUnsupportedFraction"]):
            failures.append("unsupported_fraction_over_limit")
        if lower_motion < 0.5:
            failures.append("lower_body_motion_missing")
        clips[item["name"]] = {
            "duration_seconds": round((len(frames) - 1) / rate, 7),
            "loop": False,
            "role": "isolated_full_body_human_mocap_review_only",
            "kind": item["kind"],
            "source_id": item["sourceId"],
            "source_clip": item["sourceClip"],
            "support_mode": "CAPTURED_FULL_BODY",
            "frames": frames,
        }
        reports[item["name"]] = {
            "sourceDatabase": str(database_path),
            "sourceId": item["sourceId"],
            "timeScale": float(item["timeScale"]),
            "frames": len(frames),
            "durationSeconds": clips[item["name"]]["duration_seconds"],
            "maximumRotationStep": step,
            "readyPoseSeamDegrees": seam,
            "unsupportedFraction": unsupported,
            "maximumLowerBodyStepDegrees": lower_motion,
            "maximumRootOffsetMetres": root_range,
            "failures": failures,
            "eligible": not failures,
        }
        all_failures.extend(f"{item['name']}:{failure}"
                            for failure in failures)
        for source in document.get("sources", []):
            if source not in sources:
                sources.append(source)
    output = {
        "schema": 2,
        "coordinate_system": "bedrock_x_right_y_up_z_back",
        "quaternion_order": "wxyz",
        "sample_rate": rate,
        "preview_only": True,
        "live_gameplay_replacement": False,
        "human_review": {
            **manifest["humanDecision"],
        },
        "root_authority": manifest["rootAuthority"],
        "authority": "captured_full_body_bandai_mocap_review_only",
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
                   if not all_failures else "FAIL"),
        "automaticVisualApproval": False,
        "liveGameplayChanged": False,
        "supportMode": "CAPTURED_FULL_BODY",
        "sampleRate": rate,
        "bones": len(target_bones),
        "clips": reports,
        "failures": all_failures,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if all_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
