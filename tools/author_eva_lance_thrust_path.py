#!/usr/bin/env python3
"""Drive a two-hand lance body capture through a reviewed rear-hand path."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_cmu_motion_candidates import runtime_target_pivots
from build_eva_motion_database import (
    clamp,
    load_target_pivots,
    rounded_quaternion,
    solve_target_limb,
)
from build_eva_motion_lab_3d import target_to_blender
from solve_eva_weapon_hand_contacts import blender_to_authored


PATH_KEYS = (
    # Runtime model pixels: X right, Y up, -Z forward.  The path starts in a
    # compact guard, retracts beside the ribs, drives forward, briefly holds
    # the line, then returns without snapping back to the first frame.
    (0.00, (-16.0, 126.0, 12.0)),
    (0.22, (-19.0, 126.0, 20.0)),
    (0.62, (-10.0, 127.0, -8.0)),
    (0.76, (-8.0, 127.0, -12.0)),
    (1.00, (-15.0, 126.0, 0.0)),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--clip", default="lance_thrust_review")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def smoothstep(value: float) -> float:
    value = clamp(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def sample_path(phase: float) -> Vector:
    for (left_time, left), (right_time, right) in zip(
            PATH_KEYS, PATH_KEYS[1:]):
        if phase <= right_time:
            amount = smoothstep(
                (phase - left_time) / max(1.0e-8, right_time - left_time))
            return Vector(tuple(
                a + (b - a) * amount for a, b in zip(left, right)))
    return Vector(PATH_KEYS[-1][1])


def main() -> None:
    args = parse_args()
    document = json.loads(args.motion_db.read_text(encoding="utf-8"))
    output = copy.deepcopy(document)
    clip = output["clips"][args.clip]
    frames = clip["frames"]
    bone_indices = {name: index for index, name in enumerate(output["bones"])}
    pivots = runtime_target_pivots(load_target_pivots(args.geo))
    upper_rest = target_to_blender(pivots["forearm_r"] - pivots["arm_r"])
    lower_rest = target_to_blender(pivots["hand_r"] - pivots["forearm_r"])
    total = upper_rest.length + lower_rest.length
    master_scale = float(bpy.data.objects["EVA_EXACT_ROOT"].scale.x)
    diagnostics = []

    for index, frame in enumerate(frames):
        bpy.context.scene.frame_set(1 + index)
        bpy.context.view_layer.update()
        phase = index / max(1, len(frames) - 1)
        root = bpy.data.objects["JOINT::root"]
        target_local = target_to_blender(sample_path(phase))
        desired_world = (
            root.matrix_world.translation
            + root.matrix_world.to_quaternion() @ target_local * master_scale
        )
        shoulder_world = bpy.data.objects[
            "JOINT::arm_r"].matrix_world.translation
        elbow_world = bpy.data.objects[
            "JOINT::forearm_r"].matrix_world.translation
        parent_rotation = bpy.data.objects[
            "JOINT::clavicle_r"].matrix_world.to_quaternion()
        vector = (parent_rotation.conjugated()
                  @ (desired_world - shoulder_world)) / master_scale
        distance = vector.length
        direction = vector.normalized()
        reach = clamp(distance / total, 0.08, 0.995)
        current_elbow = (parent_rotation.conjugated()
                         @ (elbow_world - shoulder_world)) / master_scale
        pole = current_elbow - direction * current_elbow.dot(direction)
        if pole.length < 1.0e-6:
            pole = Vector((-1.0, 0.0, -1.0))
        arm, forearm = solve_target_limb(
            Vector((0.0, 0.0, 0.0)), upper_rest,
            upper_rest + lower_rest, direction, reach, pole,
        )
        frame["rotation_wxyz"][bone_indices["arm_r"]] = \
            rounded_quaternion(blender_to_authored(arm))
        frame["rotation_wxyz"][bone_indices["forearm_r"]] = \
            rounded_quaternion(blender_to_authored(forearm))
        for name in ("wrist_r", "hand_r"):
            frame["rotation_wxyz"][bone_indices[name]] = [1.0, 0.0, 0.0, 0.0]
        diagnostics.append({
            "frame": index,
            "phase": round(phase, 6),
            "rear_hand_target_model_pixels": [
                round(float(value), 5) for value in sample_path(phase)],
            "reach_fraction": round(reach, 6),
        })

    output["lance_path_authoring"] = {
        "authority": "captured_staff_body_plus_reviewed_rear_hand_path",
        "path_keys_model_pixels": [
            [time, list(position)] for time, position in PATH_KEYS],
        "frames": diagnostics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA lance path: clip={args.clip} frames={len(frames)} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
