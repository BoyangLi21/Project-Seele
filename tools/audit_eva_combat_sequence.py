#!/usr/bin/env python3
"""Audit support-foot continuity across a composed EVA combat sequence."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_range(value):
    label, first, last = value.split(":")
    return label, int(first), int(last)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--range", action="append", required=True,
                        help="LABEL:START:END")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fps", type=float, default=60.0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def point(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].head


def percentile(values, fraction):
    values = sorted(values)
    position = fraction * (len(values) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return values[low]
    blend = position - low
    return values[low] * (1.0 - blend) + values[high] * blend


def main():
    args = parse_args()
    scene = bpy.context.scene
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    samples = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples.append({
            "frame": frame,
            "root": point(rig, "world_root") if "world_root" in rig.pose.bones
                    else point(rig, "root"),
            "head": point(rig, "head"),
            "left": point(rig, "foot_l"),
            "right": point(rig, "foot_r"),
        })
    height = percentile([
        row["head"].z - min(row["left"].z, row["right"].z)
        for row in samples
    ], 0.50)
    by_frame = {row["frame"]: row for row in samples}
    reports = []
    failures = []
    for label, first, last in map(parse_range, args.range):
        rows = [by_frame[frame] for frame in range(first, last + 1)]
        foot_report = {}
        for side in ("left", "right"):
            origin = rows[0][side]
            travel = max((row[side] - origin).length for row in rows) / height
            speeds = []
            for previous, current in zip(rows, rows[1:]):
                delta = current[side] - previous[side]
                delta.z = 0.0
                speeds.append(delta.length * args.fps / height)
            base_height = rows[0][side].z
            lift = max(row[side].z - base_height for row in rows) / height
            foot_report[side] = {
                "travel_body_heights": travel,
                "horizontal_speed_p95_body_heights_per_second": (
                    percentile(speeds, 0.95) if speeds else 0.0),
                "maximum_lift_body_heights": lift,
            }
        support = min(foot_report, key=lambda side:
                      foot_report[side]["travel_body_heights"])
        moving = "right" if support == "left" else "left"
        support_travel = foot_report[support]["travel_body_heights"]
        moving_travel = foot_report[moving]["travel_body_heights"]
        moving_lift = foot_report[moving]["maximum_lift_body_heights"]
        row_failures = []
        if support_travel > 0.015:
            row_failures.append("no_planted_support_foot")
        if moving_travel > 0.04 and moving_lift < 0.008:
            row_failures.append("moving_foot_slides_without_lift")
        root_steps = [
            (current["root"] - previous["root"]).length / height
            for previous, current in zip(rows, rows[1:])
        ]
        if max(root_steps, default=0.0) > 0.025:
            row_failures.append("root_step_over_0_025H")
        reports.append({
            "label": label, "frames": [first, last],
            "feet": foot_report, "support_foot": support,
            "root_step_max_body_heights": max(root_steps, default=0.0),
            "failures": row_failures,
        })
        failures.extend(f"{label}:{failure}" for failure in row_failures)
    report = {
        "schema": 1,
        "action": rig.animation_data.action.name,
        "fps": args.fps,
        "body_height_units": height,
        "ranges": reports,
        "failures": failures,
        "passed": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
