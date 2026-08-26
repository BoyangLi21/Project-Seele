#!/usr/bin/env python3
"""Close a reviewed EVA pose cycle without touching world-root travel."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def qangle(first: Quaternion, second: Quaternion) -> float:
    return math.degrees(first.rotation_difference(second).angle)


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    action = rig.animation_data.action
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    bones = [bone.name for bone in rig.pose.bones
             if bone.name != "world_root"]
    samples = {name: [] for name in bones}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name in bones:
            basis = rig.pose.bones[name].matrix_basis.copy()
            rotation = basis.to_quaternion()
            rotation.normalize()
            samples[name].append((basis.translation.copy(), rotation,
                                  basis.to_scale()))
    pre_rotation = {
        name: qangle(samples[name][0][1], samples[name][-1][1])
        for name in bones}
    pre_location = {
        name: (samples[name][-1][0] - samples[name][0][0]).length
        for name in bones}
    identity = Quaternion((1.0, 0.0, 0.0, 0.0))
    last_index = len(frames) - 1
    for name in bones:
        bone = rig.pose.bones[name]
        bone.rotation_mode = "QUATERNION"
        first_location = samples[name][0][0]
        last_location = samples[name][-1][0]
        location_delta = first_location - last_location
        first_rotation = samples[name][0][1]
        last_rotation = samples[name][-1][1]
        rotation_correction = last_rotation.conjugated() @ first_rotation
        rotation_correction.normalize()
        for index, frame in enumerate(frames):
            amount = index / max(1, last_index)
            location, rotation, scale = samples[name][index]
            corrected_rotation = rotation @ identity.slerp(
                rotation_correction, amount)
            corrected_rotation.normalize()
            bone.location = location + location_delta * amount
            bone.rotation_quaternion = corrected_rotation
            bone.scale = scale
            bone.keyframe_insert("location", frame=frame)
            bone.keyframe_insert("rotation_quaternion", frame=frame)
            bone.keyframe_insert("scale", frame=frame)
    for curve in action.fcurves:
        if 'pose.bones["world_root"]' in curve.data_path:
            continue
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
    post_rotation = {}
    post_location = {}
    for frame in (frames[0], frames[-1]):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name in bones:
            basis = rig.pose.bones[name].matrix_basis.copy()
            rotation = basis.to_quaternion()
            rotation.normalize()
            post_rotation.setdefault(name, []).append(rotation)
            post_location.setdefault(name, []).append(
                basis.translation.copy())
    report = {
        "schema": 1,
        "action": action.name,
        "frames": [frames[0], frames[-1]],
        "world_root_modified": False,
        "maximum_pre_rotation_seam_degrees": max(pre_rotation.values()),
        "maximum_post_rotation_seam_degrees": max(
            qangle(values[0], values[1])
            for values in post_rotation.values()),
        "maximum_pre_local_position_seam": max(pre_location.values()),
        "maximum_post_local_position_seam": max(
            (values[1] - values[0]).length
            for values in post_location.values()),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
