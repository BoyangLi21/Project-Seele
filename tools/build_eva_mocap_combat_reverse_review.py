#!/usr/bin/env python3
"""Build isolated non-boxing and reverse-grip knife review candidates."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from mathutils import Euler, Quaternion

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


def rounded(value: Quaternion) -> list[float]:
    value.normalize()
    return [round(float(value.w), 7), round(float(value.x), 7),
            round(float(value.y), 7), round(float(value.z), 7)]


def knife_rotation_variant(value: list[float], variant: str) -> list[float]:
    rotation = Quaternion(tuple(float(item) for item in value))
    rotation.normalize()
    variants = {
        "BASE": None,
        "POST_X_180": Quaternion((1.0, 0.0, 0.0), math.pi),
        "POST_Y_180": Quaternion((0.0, 1.0, 0.0), math.pi),
        "POST_Z_180": Quaternion((0.0, 0.0, 1.0), math.pi),
    }
    if variant not in variants:
        raise RuntimeError(f"unsupported knife rotation variant: {variant}")
    half_turn = variants[variant]
    if half_turn is not None:
        rotation = rotation @ half_turn
        rotation.normalize()
    return rounded(rotation)


def partial_fist(value, amount: float) -> list[float]:
    target = Quaternion(tuple(float(item) for item in value))
    target.normalize()
    return rounded(Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(
        target, amount))


def finger_profile(kind: str, finger_bones: list[str],
                   full_fist: dict, constraints: dict) -> dict:
    if kind == "palm_left":
        amount = {
            "l": float(constraints["palmStrikingHandFistFraction"]),
            "r": float(constraints["guardHandFistFraction"]),
        }
    elif kind == "palm_right":
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["palmStrikingHandFistFraction"]),
        }
    elif kind == "claw_left":
        amount = {
            "l": float(constraints["clawStrikingHandFistFraction"]),
            "r": float(constraints["guardHandFistFraction"]),
        }
    elif kind == "claw_right":
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["clawStrikingHandFistFraction"]),
        }
    elif kind == "maul_lunge":
        amount = {
            "l": float(constraints["maulHandFistFraction"]),
            "r": float(constraints["maulHandFistFraction"]),
        }
    elif kind == "anime_body_drive":
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["bodyDriveHandFistFraction"]),
        }
    elif kind == "forearm_lariat":
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["forearmStrikingHandFistFraction"]),
        }
    elif kind == "forearm_backhand_right":
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["forearmStrikingHandFistFraction"]),
        }
    elif kind == "forearm_backhand_left":
        amount = {
            "l": float(constraints["forearmStrikingHandFistFraction"]),
            "r": float(constraints["guardHandFistFraction"]),
        }
    elif kind == "contact_clamp_actor":
        amount = {
            "l": float(constraints["clampHandFistFraction"]),
            "r": float(constraints["clampHandFistFraction"]),
        }
    elif kind == "contact_target_actor":
        amount = {
            "l": float(constraints["targetBraceHandFistFraction"]),
            "r": float(constraints["targetBraceHandFistFraction"]),
        }
    elif kind in {"overhand_right", "overhand_right_heavy"}:
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["overhandStrikingHandFistFraction"]),
        }
    elif kind == "overhand_left":
        amount = {
            "l": float(constraints["overhandStrikingHandFistFraction"]),
            "r": float(constraints["guardHandFistFraction"]),
        }
    elif kind == "target_hit_reaction":
        amount = {
            "l": float(constraints["targetBraceHandFistFraction"]),
            "r": float(constraints["targetBraceHandFistFraction"]),
        }
    elif kind in {"g1_attack_right_down", "g1_attack_right_drive"}:
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["combatStrikingHandFistFraction"]),
        }
    elif kind == "g1_attack_left_sweep":
        amount = {
            "l": float(constraints["combatStrikingHandFistFraction"]),
            "r": float(constraints["guardHandFistFraction"]),
        }
    elif kind.startswith("g1_kick_"):
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["guardHandFistFraction"]),
        }
    else:
        amount = {
            "l": float(constraints["guardHandFistFraction"]),
            "r": float(constraints["reverseGripRightHandFistFraction"]),
        }
    return {
        bone: partial_fist(full_fist[bone], amount[bone[-1]])
        for bone in finger_bones
    }


def build_frames(document: dict, clip: dict, target_bones: list[str],
                 profile: dict, kind: str, knife_rotation: list[float],
                 knife_position: list[float], rate: float,
                 time_scale: float, root_scale: float,
                 constraints: dict) -> list[dict]:
    source_bones = list(document["bones"])
    source_index = {name: index for index, name in enumerate(source_bones)}
    sampled = resample(document, clip, rate * time_scale)
    frames = []
    reverse = kind == "reverse_knife"
    uses_knife = kind in {"forward_knife", "reverse_knife"}
    for source_frame_index, source_frame in enumerate(sampled):
        rotations = []
        for bone in target_bones:
            if bone in profile:
                rotations.append(list(profile[bone]))
            elif bone == "knife":
                rotations.append(list(knife_rotation))
            elif bone in source_index:
                rotations.append(list(source_frame["rotation_wxyz"][
                    source_index[bone]]))
            else:
                rotations.append(list(IDENTITY))
        frame = {
            "root_m": [round(float(value) * root_scale, 7)
                       for value in source_frame["root_m"]],
            "rotation_wxyz": rotations,
            "foot_contact": list(source_frame["foot_contact"]),
        }
        if kind.startswith("g1_kick_"):
            # The striking foot is airborne by definition. Markerless source
            # contact classifiers often keep both feet flagged through the
            # chamber and extension, which makes two incompatible foot locks
            # fight over the root. Preserve the captured joint curves and
            # declare only the non-striking support foot as contact authority.
            phases = constraints.get("kickContactPhases")
            if phases:
                frame["foot_contact"] = [False, False]
                for phase in phases:
                    if (int(phase["firstFrame"]) <= source_frame_index
                            <= int(phase["lastFrame"])):
                        support_index = 0 if phase["supportFoot"] == "l" else 1
                        frame["foot_contact"][support_index] = True
            else:
                striking_left = kind.endswith("_left")
                frame["foot_contact"] = [not striking_left, striking_left]
                edge_release = int(constraints.get(
                    "kickContactEdgeReleaseFrames", 4))
                if (source_frame_index < edge_release
                        or source_frame_index >= len(sampled) - edge_release):
                    frame["foot_contact"] = [False, False]
        if uses_knife:
            frame["bone_position_xyz"] = {"knife": list(knife_position)}
        frames.append(frame)

    ready = copy.deepcopy(frames[0])
    ready["root_m"] = [0.0, 0.0, 0.0]
    output = [copy.deepcopy(ready) for _ in range(
        int(constraints["anticipationFrames"]))]
    output.extend(frames)
    last = frames[-1]
    recovery = int(constraints["recoveryFrames"])
    recovery_mode = constraints.get("recoveryMode", "RETURN_TO_READY")
    if recovery_mode == "PRESERVE_CAPTURED_FOLLOW_THROUGH":
        output.extend(copy.deepcopy(last) for _ in range(
            recovery + int(constraints["readyHoldFrames"])))
    elif recovery_mode == "RETURN_TO_READY":
        for index in range(1, recovery + 1):
            amount = smoothstep(index / recovery)
            frame = {
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
            }
            if uses_knife:
                frame["bone_position_xyz"] = {"knife": list(knife_position)}
            output.append(frame)
        output.extend(copy.deepcopy(ready) for _ in range(
            int(constraints["readyHoldFrames"])))
    else:
        raise RuntimeError(f"unsupported recovery mode: {recovery_mode}")
    for _ in range(int(constraints["temporalSmoothingPasses"])):
        smooth_body_rotations(
            output, target_bones,
            float(constraints["temporalSmoothingStrength"]))
    return output


def main() -> None:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest["constraints"]["supportMode"] != "CAPTURED_FULL_BODY":
        raise RuntimeError("captured full body authority is missing")
    fist_document = json.loads(resolved(
        manifest["fistProfile"]).read_text(encoding="utf-8"))
    fist_bones = fist_document["bones"]
    fist_frame = next(iter(fist_document["clips"].values()))["frames"][0]
    full_fist = {
        name: fist_frame["rotation_wxyz"][index]
        for index, name in enumerate(fist_bones)
        if name.startswith("finger_")
    }
    finger_bones = list(full_fist)
    target_bones = list(BODY_BONES) + finger_bones + ["knife"]
    knife_config = manifest.get("knifeTransform", manifest.get(
        "reverseGrip"))
    if knife_config is None:
        raise RuntimeError("knife transform is missing")
    raw_euler = knife_config["knifeAuthoredEulerDegrees"]
    knife_rotation = rounded(Euler(tuple(
        math.radians(float(value)) for value in raw_euler),
        "XYZ").to_quaternion())
    knife_position = [float(value) for value in
                      knife_config["knifePositionXYZ"]]
    rate = float(manifest["sampleRate"])
    clips = {}
    reports = {}
    sources = []
    failures = []
    lower_names = (
        "torso_lower", "leg_l", "shin_l", "foot_l",
        "leg_r", "shin_r", "foot_r")
    lower_indices = [target_bones.index(name) for name in lower_names]
    for item in manifest["clips"]:
        document_path = resolved(item["sourceDatabase"])
        document = json.loads(document_path.read_text(encoding="utf-8"))
        source_clip = document["clips"][item["sourceClip"]]
        profile = finger_profile(
            item["kind"], finger_bones, full_fist,
            manifest["constraints"])
        clip_constraints = dict(manifest["constraints"])
        for key in ("temporalSmoothingPasses",
                    "temporalSmoothingStrength"):
            if key in item:
                clip_constraints[key] = item[key]
        if "contactPhases" in item:
            clip_constraints["kickContactPhases"] = item["contactPhases"]
        frames = build_frames(
            document, source_clip, target_bones, profile, item["kind"],
            knife_rotation_variant(
                knife_rotation, item.get("knifeRotationVariant", "BASE")
            ), knife_position, rate, float(item["timeScale"]),
            float(item["rootTranslationScale"]), clip_constraints)
        step = maximum_rotation_step(frames, target_bones)
        seam = seam_error(frames, target_bones)
        unsupported = sum(not any(frame["foot_contact"])
                          for frame in frames) / len(frames)
        lower_step = maximum_rotation_step([
            {"rotation_wxyz": [frame["rotation_wxyz"][index]
                                for index in lower_indices]}
            for frame in frames
        ], list(lower_names))["degrees"]
        clip_failures = []
        if step["degrees"] > float(
                manifest["constraints"]["maximumRotationStepDegrees"]):
            clip_failures.append("rotation_step_over_limit")
        recovery_mode = clip_constraints.get(
            "recoveryMode", "RETURN_TO_READY")
        if recovery_mode == "RETURN_TO_READY" and seam > 0.05:
            clip_failures.append("ready_pose_seam_over_0_05_degrees")
        if unsupported > float(
                manifest["constraints"]["maximumUnsupportedFraction"]):
            clip_failures.append("unsupported_fraction_over_limit")
        if lower_step < 0.5:
            clip_failures.append("lower_body_motion_missing")
        reverse = item["kind"] == "reverse_knife"
        uses_knife = item["kind"] in {"forward_knife", "reverse_knife"}
        if uses_knife and not all(
                frame.get("bone_position_xyz", {}).get("knife")
                == knife_position for frame in frames):
            clip_failures.append("knife_grip_position_not_constant")
        grip = (
            "REVERSE_RIGHT" if reverse
            else "FORWARD_RIGHT" if uses_knife
            else "CLAW" if item["kind"].startswith("claw_")
            else "CURLED_HAND_BODY_DRIVE" if item["kind"] == "anime_body_drive"
            else "CURLED_HAND_FOREARM_CONTACT" if item["kind"] == "forearm_lariat"
            else "CURLED_RIGHT_BACKHAND" if item["kind"] == "forearm_backhand_right"
            else "CURLED_LEFT_BACKHAND" if item["kind"] == "forearm_backhand_left"
            else "TWO_HAND_CONTACT_CLAMP" if item["kind"] == "contact_clamp_actor"
            else "TARGET_BRACE_HANDS" if item["kind"] == "contact_target_actor"
            else "CURLED_RIGHT_OVERHAND" if item["kind"] == "overhand_right"
            else "CURLED_LEFT_OVERHAND" if item["kind"] == "overhand_left"
            else "CURLED_RIGHT_OVERHAND_HEAVY" if item["kind"] == "overhand_right_heavy"
            else "TARGET_HIT_REACTION_HANDS" if item["kind"] == "target_hit_reaction"
            else "CURLED_RIGHT_DOWNWARD_ATTACK" if item["kind"] == "g1_attack_right_down"
            else "CURLED_LEFT_SWEEP_ATTACK" if item["kind"] == "g1_attack_left_sweep"
            else "CURLED_RIGHT_DRIVE_ATTACK" if item["kind"] == "g1_attack_right_drive"
            else "GUARDED_FISTS" if item["kind"].startswith("g1_kick_")
            else "OPEN_PALM"
        )
        role = (
            "isolated_kick_attack_review_only"
            if item["kind"].startswith("g1_kick_")
            else "isolated_ordinary_attack_review_only"
            if item["kind"] in {
                "anime_body_drive", "forearm_lariat",
                "forearm_backhand_right", "forearm_backhand_left",
                "contact_clamp_actor", "contact_target_actor",
                "overhand_right", "overhand_left", "overhand_right_heavy",
                "target_hit_reaction",
                "g1_attack_right_down", "g1_attack_left_sweep",
                "g1_attack_right_drive",
            }
            else "isolated_nonboxing_reverse_grip_review_only"
        )
        clips[item["name"]] = {
            "duration_seconds": round((len(frames) - 1) / rate, 7),
            "loop": False,
            "role": role,
            "kind": item["kind"],
            "source_id": item["sourceId"],
            "source_clip": item["sourceClip"],
            "support_mode": "CAPTURED_FULL_BODY",
            "contact_authority": (
                "NON_STRIKING_SUPPORT_FOOT"
                if item["kind"].startswith("g1_kick_")
                else "CAPTURED_FOOT_CONTACTS"
            ),
            "grip": grip,
            "knife_rotation_variant": item.get(
                "knifeRotationVariant", "BASE"),
            "frames": frames,
        }
        reports[item["name"]] = {
            "sourceDatabase": str(document_path),
            "sourceId": item["sourceId"],
            "timeScale": float(item["timeScale"]),
            "rootTranslationScale": float(item["rootTranslationScale"]),
            "frames": len(frames),
            "durationSeconds": clips[item["name"]]["duration_seconds"],
            "maximumRotationStep": step,
            "readyPoseSeamDegrees": seam,
            "endingPosePolicy": recovery_mode,
            "unsupportedFraction": unsupported,
            "maximumLowerBodyStepDegrees": lower_step,
            "grip": grip,
            "knifeRotationVariant": item.get(
                "knifeRotationVariant", "BASE"),
            "temporalSmoothingPasses": int(
                clip_constraints["temporalSmoothingPasses"]),
            "temporalSmoothingStrength": float(
                clip_constraints["temporalSmoothingStrength"]),
            "failures": clip_failures,
            "eligible": not clip_failures,
        }
        failures.extend(f"{item['name']}:{failure}"
                        for failure in clip_failures)
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
            "status": manifest.get(
                "status", "CANDIDATE_REQUIRES_HUMAN_REVIEW")
        },
        "root_authority": manifest["rootAuthority"],
        "knife_base_transform": {
            "knifeAuthoredEulerDegrees": raw_euler,
            "knifeAuthoredQuaternionWxyz": knife_rotation,
            "knifePositionXYZ": knife_position,
            "description": knife_config["description"],
        },
        "authority": manifest.get(
            "authority", "nonboxing_full_body_reverse_grip_review"),
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
        "supportMode": "CAPTURED_FULL_BODY",
        "unarmedVocabulary": manifest.get(
            "unarmedVocabulary", "NON_BOXING_UPPER_BODY"),
        "knifeGrip": manifest.get("knifeGrip", "REVERSE_RIGHT"),
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
