#!/usr/bin/env python3
"""Export solved weapon contact curves as a hash-chained animation patch."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

from mathutils import Quaternion

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eva_animation_geometry_repairs import semantic_sha256


BASE_MAPPINGS = {
    "animation.eva_unit01.lance_ready": (
        "lance_ready_review", ("clavicle_l", "arm_l", "forearm_l", "lance")),
    "animation.eva_unit01.lance_carry": (
        "lance_ready_review", ("clavicle_l", "arm_l", "forearm_l", "lance")),
    "animation.eva_unit01.lance_thrust": (
        "lance_thrust_review", ("clavicle_l", "arm_l", "forearm_l", "lance")),
    "animation.eva_unit01.prone_lance_ready": (
        "prone_lance_review", ("clavicle_l", "arm_l", "forearm_l", "lance")),
    "animation.eva_unit01.prone_lance_thrust": (
        "prone_lance_thrust_review", ("clavicle_l", "arm_l", "forearm_l", "lance")),
    "animation.eva_unit01.crouch_lance_thrust": (
        "crouch_lance_thrust_review", ("clavicle_l", "arm_l", "forearm_l", "lance")),
    "animation.eva_unit01.prone_rifle_aim": (
        "prone_rifle_review", ("arm_l", "forearm_l", "cannon")),
}

VISUAL_MAPPINGS = {
    "animation.eva_unit01.visual_lance_ready": ("lance_ready_review", 0.0),
    "animation.eva_unit01.visual_lance_windup": ("lance_thrust_review", 0.30),
    "animation.eva_unit01.visual_lance_contact": ("lance_thrust_review", 0.63),
    "animation.eva_unit01.visual_lance_recovery": ("lance_thrust_review", 1.10),
    "animation.eva_unit01.visual_prone_lance_contact": (
        "prone_lance_thrust_review", 0.63),
    "animation.eva_unit01.visual_crouch_lance_contact": (
        "crouch_lance_thrust_review", 0.63),
    "animation.eva_unit01.visual_prone_rifle": (
        "prone_rifle_review", 0.0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--animation", required=True, type=Path)
    parser.add_argument("--solved-motion-db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--maximum-error-degrees", type=float, default=0.35)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def angular_error(actual: Quaternion, predicted: Quaternion) -> float:
    return math.degrees(actual.rotation_difference(predicted).angle)


def reduce_curve(quaternions: list[Quaternion], maximum_error: float) -> list[int]:
    keep = {0, len(quaternions) - 1}

    def split(first: int, last: int) -> None:
        if last - first <= 1:
            return
        worst_index = None
        worst_error = -1.0
        for index in range(first + 1, last):
            amount = (index - first) / (last - first)
            predicted = quaternions[first].slerp(quaternions[last], amount)
            error = angular_error(quaternions[index], predicted)
            if error > worst_error:
                worst_error = error
                worst_index = index
        if worst_error > maximum_error:
            keep.add(worst_index)
            split(first, worst_index)
            split(worst_index, last)

    split(0, len(quaternions) - 1)
    return sorted(keep)


def euler_degrees(quat: Quaternion) -> list[float]:
    euler = quat.to_euler("XYZ")
    return [round(math.degrees(float(value)), 5) for value in euler]


def clip_quaternions(motion: dict, clip_name: str,
                     bone_name: str, maximum_time: float | None = None):
    bone_index = motion["bones"].index(bone_name)
    frames = motion["clips"][clip_name]["frames"]
    if maximum_time is not None:
        frames = frames[:min(len(frames), int(round(maximum_time * 30.0)) + 1)]
    output = []
    previous = None
    for frame in frames:
        quat = Quaternion(tuple(frame["rotation_wxyz"][bone_index]))
        if previous is not None and previous.dot(quat) < 0.0:
            quat = Quaternion((-quat.w, -quat.x, -quat.y, -quat.z))
        output.append(quat)
        previous = quat
    return output


def rotation_channel(motion: dict, clip_name: str, bone_name: str,
                     duration: float, maximum_error: float) -> dict:
    quaternions = clip_quaternions(motion, clip_name, bone_name, duration)
    indices = reduce_curve(quaternions, maximum_error)
    return {
        str(round(index / 30.0, 6)): euler_degrees(quaternions[index])
        for index in indices
    }


def sampled_rotation(motion: dict, clip_name: str,
                     bone_name: str, seconds: float) -> list[float]:
    quaternions = clip_quaternions(motion, clip_name, bone_name)
    index = min(len(quaternions) - 1, int(round(seconds * 30.0)))
    return euler_degrees(quaternions[index])


def main() -> None:
    args = parse_args()
    source = json.loads(args.animation.read_text(encoding="utf-8"))
    target = copy.deepcopy(source)
    motion = json.loads(args.solved_motion_db.read_text(encoding="utf-8"))
    replacements = {}
    for animation_name, (clip_name, bone_names) in BASE_MAPPINGS.items():
        replacement = copy.deepcopy(target["animations"][animation_name])
        duration = float(replacement.get("animation_length",
                                         motion["clips"][clip_name]["duration_seconds"]))
        for bone_name in bone_names:
            rotation = rotation_channel(
                motion, clip_name, bone_name, duration,
                args.maximum_error_degrees,
            )
            if replacement.get("loop") and len(rotation) > 1:
                keys = sorted(rotation, key=float)
                rotation[keys[-1]] = list(rotation[keys[0]])
            replacement.setdefault("bones", {}).setdefault(bone_name, {})[
                "rotation"
            ] = rotation
        target["animations"][animation_name] = replacement
        replacements[animation_name] = replacement
    for animation_name, (clip_name, seconds) in VISUAL_MAPPINGS.items():
        replacement = copy.deepcopy(target["animations"][animation_name])
        bone_names = ("arm_l", "forearm_l", "cannon") \
            if "rifle" in animation_name else \
            ("clavicle_l", "arm_l", "forearm_l", "lance")
        for bone_name in bone_names:
            replacement.setdefault("bones", {}).setdefault(bone_name, {})[
                "rotation"
            ] = {"0.0": sampled_rotation(
                motion, clip_name, bone_name, seconds
            )}
        target["animations"][animation_name] = replacement
        replacements[animation_name] = replacement
    patch = {
        "format_version": 1,
        "source_animation_semantic_sha256": semantic_sha256(source["animations"]),
        "target_animation_semantic_sha256": semantic_sha256(target["animations"]),
        "maximum_quaternion_error_degrees": args.maximum_error_degrees,
        "source_solved_motion_db": args.solved_motion_db.as_posix(),
        "source_solved_motion_db_sha256": hashlib.sha256(
            args.solved_motion_db.read_bytes()).hexdigest(),
        "replace_animations": replacements,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(patch, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    key_count = sum(
        len(animation.get("bones", {}).get(bone, {}).get("rotation", {}))
        for animation in replacements.values()
        for bone in animation.get("bones", {})
    )
    print(
        f"EVA weapon contact patch: animations={len(replacements)} "
        f"rotation-keys={key_count} output={args.output}"
    )


if __name__ == "__main__":
    main()
