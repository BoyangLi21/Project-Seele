#!/usr/bin/env python3
"""Remove fixed lateral body bias without changing gait-relative motion."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--target-lateral-p95-degrees", type=float,
                        default=3.0)
    parser.add_argument("--correction-bone",
                        choices=("root", "torso_upper"),
                        default="torso_upper")
    parser.add_argument("--preserve-leg-directions", action="store_true")
    parser.add_argument("--preserve-leg-transforms", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def world_head(rig, name: str) -> Vector:
    return rig.matrix_world @ rig.pose.bones[name].head


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    action = rig.animation_data.action
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    authority = "world_root" if "world_root" in rig.pose.bones else "root"
    scene.frame_set(frames[0])
    bpy.context.view_layer.update()
    start = world_head(rig, authority)
    scene.frame_set(frames[-1])
    bpy.context.view_layer.update()
    travel = world_head(rig, authority) - start
    travel.z = 0.0
    if travel.length < 1.0e-7:
        raise RuntimeError("locomotion action has no planar travel")
    forward_world = travel.normalized()
    up = Vector((0.0, 0.0, 1.0))
    right = forward_world.cross(up).normalized()
    lateral = []
    correction_matrices = []
    leg_rotations = {"l": [], "r": []}
    leg_matrices = {"l": [], "r": []}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        correction_matrices.append(
            rig.pose.bones[args.correction_bone].matrix.copy())
        for side in ("l", "r"):
            leg_rotations[side].append(
                rig.pose.bones[f"leg_{side}"].matrix.to_quaternion())
            leg_matrices[side].append(
                rig.pose.bones[f"leg_{side}"].matrix.copy())
        torso_up = world_head(rig, "head") - world_head(rig, "root")
        torso_up.normalize()
        lateral.append(math.atan2(torso_up.dot(right), torso_up.dot(up)))
    lateral_values = np.asarray(lateral, dtype=float)
    lateral_mean = float(np.mean(lateral_values))
    centered = lateral_values - lateral_mean
    current_p95 = float(np.percentile(np.abs(centered), 95.0))
    target_p95 = math.radians(max(
        0.0, args.target_lateral_p95_degrees))
    lateral_gain = (min(1.0, target_p95 / current_p95)
                    if current_p95 > 1.0e-8 else 1.0)
    corrections = -lateral_mean + centered * (lateral_gain - 1.0)
    forward_armature = (rig.matrix_world.to_3x3().inverted()
                        @ forward_world).normalized()
    correction_bone = rig.pose.bones[args.correction_bone]
    correction_bone.rotation_mode = "QUATERNION"
    pivot = correction_bone.head.copy()
    for index, (frame, original, correction_angle) in enumerate(zip(
            frames, correction_matrices, corrections)):
        scene.frame_set(frame)
        correction = Matrix.Rotation(
            float(correction_angle), 4, forward_armature)
        correction_bone.matrix = (Matrix.Translation(pivot) @ correction
                                  @ Matrix.Translation(-pivot) @ original)
        correction_bone.keyframe_insert("location", frame=frame)
        correction_bone.keyframe_insert("rotation_quaternion", frame=frame)
        correction_bone.keyframe_insert("scale", frame=frame)
        if args.preserve_leg_directions or args.preserve_leg_transforms:
            bpy.context.view_layer.update()
            for side in ("l", "r"):
                leg = rig.pose.bones[f"leg_{side}"]
                if args.preserve_leg_transforms:
                    matrix = leg_matrices[side][index].copy()
                else:
                    translation = leg.matrix.translation.copy()
                    matrix = leg_rotations[side][index].to_matrix().to_4x4()
                    matrix.translation = translation
                leg.matrix = matrix
                leg.rotation_mode = "QUATERNION"
                leg.keyframe_insert("location", frame=frame)
                leg.keyframe_insert("rotation_quaternion", frame=frame)
                leg.keyframe_insert("scale", frame=frame)
    for curve in action.fcurves:
        relevant = (f'pose.bones["{args.correction_bone}"]'
                    in curve.data_path)
        if args.preserve_leg_directions or args.preserve_leg_transforms:
            relevant = relevant or any(
                f'pose.bones["leg_{side}"]' in curve.data_path
                for side in ("l", "r"))
        if not relevant:
            continue
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"

    corrected = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        torso_up = world_head(rig, "head") - world_head(rig, "root")
        torso_up.normalize()
        corrected.append(math.degrees(math.atan2(
            torso_up.dot(right), torso_up.dot(up))))
    report = {
        "schema": 1,
        "action": action.name,
        "correction_bone": args.correction_bone,
        "preserve_leg_directions": args.preserve_leg_directions,
        "preserve_leg_transforms": args.preserve_leg_transforms,
        "frames": [frames[0], frames[-1]],
        "mean_correction_degrees": math.degrees(-lateral_mean),
        "lateral_amplitude_gain": lateral_gain,
        "before_lateral_mean_degrees": math.degrees(lateral_mean),
        "before_lateral_p95_abs_centered_degrees": math.degrees(current_p95),
        "after_lateral_mean_degrees": float(np.mean(corrected)),
        "after_lateral_p95_abs_degrees": float(np.percentile(
            np.abs(corrected), 95.0)),
        "world_root_modified": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
