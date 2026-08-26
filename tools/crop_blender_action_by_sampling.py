#!/usr/bin/env python3
"""Bake the current review range into one rebased Blender action."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig", default="EVA_ANATOMICAL_ARMATURE")
    parser.add_argument("--action-name", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-fps", type=float)
    parser.add_argument("--target-fps", type=float)
    parser.add_argument("--source-start", type=float)
    parser.add_argument("--source-end", type=float)
    parser.add_argument("--speed", type=float, default=1.0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def iter_fcurves(action):
    if hasattr(action, "fcurves"):
        yield from action.fcurves
        return
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                yield from channelbag.fcurves


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    rig = bpy.data.objects[args.rig]
    old_action = rig.animation_data.action
    source_start = (args.source_start if args.source_start is not None
                    else scene.frame_start)
    source_end = (args.source_end if args.source_end is not None
                  else scene.frame_end)
    source_fps = args.source_fps or (
        scene.render.fps / scene.render.fps_base)
    target_fps = args.target_fps or source_fps
    if args.speed <= 0.0 or source_end <= source_start:
        raise SystemExit("invalid crop speed/range")
    duration = (source_end - source_start) / (source_fps * args.speed)
    output_count = int(round(duration * target_fps)) + 1
    samples = []
    for index in range(output_count):
        source_frame = (source_start
                        + index * source_fps * args.speed / target_fps)
        source_frame = min(source_end, source_frame)
        whole = math.floor(source_frame)
        scene.frame_set(whole, subframe=source_frame - whole)
        bpy.context.view_layer.update()
        samples.append({
            bone.name: (
                bone.location.copy(), bone.rotation_quaternion.copy(),
                bone.rotation_euler.copy(), bone.scale.copy(),
                bone.rotation_mode,
            )
            for bone in rig.pose.bones
        })

    action = bpy.data.actions.new(args.action_name)
    action.use_fake_user = True
    rig.animation_data.action = action
    for output_frame, sample in enumerate(samples, 1):
        for name, values in sample.items():
            bone = rig.pose.bones[name]
            location, quaternion, euler, scale, mode = values
            bone.location = location
            bone.scale = scale
            if mode == "QUATERNION":
                bone.rotation_mode = "QUATERNION"
                bone.rotation_quaternion = quaternion
                bone.keyframe_insert("rotation_quaternion", frame=output_frame)
            else:
                bone.rotation_mode = mode
                bone.rotation_euler = euler
                bone.keyframe_insert("rotation_euler", frame=output_frame)
            bone.keyframe_insert("location", frame=output_frame)
            bone.keyframe_insert("scale", frame=output_frame)
    for curve in iter_fcurves(action):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    action["eva_source_frame_range"] = [source_start, source_end]
    action["eva_source_action"] = old_action.name if old_action else ""
    if old_action is not None:
        old_action.use_fake_user = False
        if old_action.users == 0:
            bpy.data.actions.remove(old_action)
    scene.frame_start = 1
    scene.frame_end = len(samples)
    scene.render.fps = int(round(target_fps))
    scene.render.fps_base = scene.render.fps / target_fps
    scene.frame_set(1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print({
        "action": action.name,
        "source_frames": [source_start, source_end],
        "source_fps": source_fps,
        "target_fps": target_fps,
        "speed": args.speed,
        "output_frames": [1, len(samples)],
        "output": str(args.output),
    })


if __name__ == "__main__":
    main()
