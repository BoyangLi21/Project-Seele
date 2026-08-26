#!/usr/bin/env python3
"""Find the meaningful motion window inside a padded Blender action."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig", default="EVA_ANATOMICAL_ARMATURE")
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--angular-threshold", type=float, default=30.0,
                        help="degrees/second")
    parser.add_argument("--padding-seconds", type=float, default=0.12)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def main():
    args = parse_args()
    scene = bpy.context.scene
    rig = bpy.data.objects[args.rig]
    bones = (
        "root", "torso_lower", "torso_upper", "aim_pitch", "head",
        "arm_l", "forearm_l", "hand_l", "arm_r", "forearm_r", "hand_r",
        "leg_l", "shin_l", "foot_l", "leg_r", "shin_r", "foot_r",
    )
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    samples = []
    previous = {}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        current = {}
        for name in bones:
            value = rig.pose.bones[name].matrix_basis.to_quaternion()
            value.normalize()
            if name in previous and previous[name].dot(value) < 0.0:
                value.negate()
            current[name] = value
        samples.append(current)
        previous = {name: value.copy() for name, value in current.items()}

    rows = []
    for index in range(1, len(samples)):
        changes = {
            name: math.degrees(samples[index - 1][name]
                               .rotation_difference(samples[index][name]).angle)
            * args.fps
            for name in bones
        }
        bone = max(changes, key=changes.get)
        rows.append({"frame": frames[index], "bone": bone,
                     "degrees_per_second": changes[bone]})
    active = [row["degrees_per_second"] >= args.angular_threshold
              for row in rows]
    # Fill short holes inside one purposeful transition.
    gap = max(1, int(round(args.fps * 0.12)))
    for size in range(1, gap + 1):
        for index in range(size, len(active) - size):
            if not active[index] and active[index - size] and active[index + size]:
                active[index] = True
    active_indices = [index for index, value in enumerate(active) if value]
    if not active_indices:
        suggested = [frames[0], frames[-1]]
    else:
        padding = int(round(args.padding_seconds * args.fps))
        suggested = [
            max(frames[0], rows[active_indices[0]]["frame"] - padding - 1),
            min(frames[-1], rows[active_indices[-1]]["frame"] + padding),
        ]
    report = {
        "schema": 1,
        "action": rig.animation_data.action.name,
        "fps": args.fps,
        "source_range": [frames[0], frames[-1]],
        "threshold_degrees_per_second": args.angular_threshold,
        "suggested_active_range": suggested,
        "suggested_duration_seconds": (suggested[1] - suggested[0]) / args.fps,
        "peak": max(rows, key=lambda row: row["degrees_per_second"]),
        "activity": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key != "activity"}, indent=2))


if __name__ == "__main__":
    main()
