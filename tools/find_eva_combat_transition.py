#!/usr/bin/env python3
"""Find a pose/velocity-compatible branch between two EVA combat actions."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


BONES = (
    "root", "torso_lower", "torso_upper", "aim_pitch", "head",
    "arm_l", "forearm_l", "hand_l", "arm_r", "forearm_r", "hand_r",
    "leg_l", "shin_l", "foot_l", "leg_r", "shin_r", "foot_r",
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--source-min", type=int, required=True)
    parser.add_argument("--source-max", type=int, required=True)
    parser.add_argument("--target-min", type=int, default=1)
    parser.add_argument("--target-max", type=int, default=8)
    parser.add_argument("--fps", type=float, default=60.0)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def load_action(path):
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (source, loaded):
        matches = [name for name in source.actions
                   if "ANATOMICAL_FISTS" in name.upper()]
        if not matches:
            matches = [name for name in source.actions
                       if name.upper().startswith("EVA_")]
        loaded.actions = matches
    actions = [action for action in loaded.actions if action is not None]
    return max(actions, key=lambda action: action.frame_range[1]
               - action.frame_range[0])


def sample(rig, action, frame):
    rig.animation_data.action = action
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {name: rig.pose.bones[name].matrix_basis.to_quaternion().normalized()
            for name in BONES}


def angle(first, second):
    return math.degrees(first.rotation_difference(second).angle)


def velocity(previous, current, fps):
    return previous.rotation_difference(current).to_exponential_map() * fps


def main():
    args = parse_args()
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    source_action = rig.animation_data.action
    target_action = load_action(args.target)
    rows = []
    for source_frame in range(args.source_min, args.source_max + 1):
        source_previous = sample(rig, source_action, source_frame - 1)
        source_current = sample(rig, source_action, source_frame)
        for target_frame in range(args.target_min, args.target_max + 1):
            target_current = sample(rig, target_action, target_frame)
            target_next = sample(rig, target_action, target_frame + 1)
            pose_errors = [angle(source_current[name], target_current[name])
                           for name in BONES]
            velocity_errors = []
            for name in BONES:
                first = velocity(source_previous[name], source_current[name],
                                 args.fps)
                second = velocity(target_current[name], target_next[name],
                                  args.fps)
                velocity_errors.append(math.degrees((first - second).length))
            mean_pose = sum(pose_errors) / len(pose_errors)
            mean_velocity = sum(velocity_errors) / len(velocity_errors)
            score = mean_pose + 0.015 * mean_velocity + 0.25 * max(pose_errors)
            rows.append({
                "source_frame": source_frame,
                "target_frame": target_frame,
                "mean_pose_degrees": mean_pose,
                "maximum_pose_degrees": max(pose_errors),
                "mean_velocity_error_degrees_per_second": mean_velocity,
                "score": score,
            })
    rows.sort(key=lambda row: row["score"])
    report = {
        "schema": 1,
        "source_action": source_action.name,
        "target_action": target_action.name,
        "search": {
            "source": [args.source_min, args.source_max],
            "target": [args.target_min, args.target_max],
        },
        "best": rows[0],
        "top": rows[:20],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
