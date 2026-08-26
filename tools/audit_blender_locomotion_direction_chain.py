#!/usr/bin/env python3
"""Locate locomotion direction and knee-plane corruption inside a review blend."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def args_from_blender():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-object", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def point(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].head


def percentile(values, amount):
    return float(np.percentile(np.asarray(values, dtype=float), amount))


def principal_axis(points_by_side):
    centered = []
    for points in points_by_side.values():
        values = np.asarray([[point.x, point.y] for point in points])
        centered.append(values - np.mean(values, axis=0, keepdims=True))
    values = np.concatenate(centered, axis=0)
    covariance = values.T @ values / len(values)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    axis = Vector((*eigenvectors[:, int(np.argmax(eigenvalues))], 0.0))
    axis.normalize()
    return axis, covariance.tolist()


def acute_angle(first, second):
    return math.degrees(math.acos(max(-1.0, min(1.0,
        abs(first.normalized().dot(second.normalized()))))))


def analyse(rig, names, frames, canonical_forward=None):
    roots = []
    feet = {"l": [], "r": []}
    knee_ratios = {"l": [], "r": []}
    hip_lines = []
    leg_points = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        root = point(rig, names["root"])
        roots.append(root)
        left_foot = point(rig, names["foot_l"])
        right_foot = point(rig, names["foot_r"])
        feet["l"].append(left_foot - root)
        feet["r"].append(right_foot - root)
        hip_lines.append(point(rig, names["hip_r"])
                         - point(rig, names["hip_l"]))
        leg_points.append({
            side: (point(rig, names[f"hip_{side}"]),
                   point(rig, names[f"knee_{side}"]),
                   point(rig, names[f"foot_{side}"]))
            for side in ("l", "r")
        })
    travel = roots[-1] - roots[0]
    travel.z = 0.0
    travel.normalize()
    right = Vector((travel.y, -travel.x, 0.0))
    swing, covariance = principal_axis(feet)
    facing_errors = []
    order_values = []
    for hip_line, legs in zip(hip_lines, leg_points):
        lateral = hip_line.copy()
        lateral.z = 0.0
        lateral.normalize()
        facing = Vector((-lateral.y, lateral.x, 0.0))
        if facing.dot(travel) < 0.0:
            facing.negate()
        facing_errors.append(acute_angle(facing, travel))
        left_foot = legs["l"][2]
        right_foot = legs["r"][2]
        order_values.append((left_foot - right_foot).dot(right))
        for side in ("l", "r"):
            hip, knee, ankle = legs[side]
            line = ankle - hip
            projection = (knee - hip).dot(line) / max(1.0e-9,
                                                       line.length_squared)
            bend = knee - (hip + line * projection)
            knee_ratios[side].append(
                abs(bend.dot(right)) / max(1.0e-6,
                                           abs(bend.dot(travel))))
    expected_order_sign = 1.0 if float(np.median(order_values)) >= 0.0 else -1.0
    result = {
        "travel_xy": [float(travel.x), float(travel.y)],
        "facing_to_travel_degrees": {
            "median": percentile(facing_errors, 50),
            "p95": percentile(facing_errors, 95),
        },
        "foot_swing_to_travel_degrees": acute_angle(swing, travel),
        "foot_swing_axis_xy": [float(swing.x), float(swing.y)],
        "foot_swing_covariance": covariance,
        "foot_left_right_order_failure_fraction": sum(
            value * expected_order_sign < 0.0 for value in order_values
        ) / len(order_values),
        "knee_lateral_to_sagittal_bend_ratio": {
            side: {"median": percentile(values, 50),
                   "p95": percentile(values, 95),
                   "maximum": max(values)}
            for side, values in knee_ratios.items()
        },
    }
    if canonical_forward is not None:
        result["travel_to_canonical_forward_degrees"] = acute_angle(
            travel, canonical_forward)
        result["foot_swing_to_canonical_forward_degrees"] = acute_angle(
            swing, canonical_forward)
    return result


def main():
    args = args_from_blender()
    target = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    source = bpy.data.objects[args.source_object]
    start = int(round(target.animation_data.action.frame_range[0]))
    end = int(round(target.animation_data.action.frame_range[1]))
    frames = list(range(start, end + 1))
    report = {
        "schema": 1,
        "frames": [start, end],
        "source": analyse(source, {
            "root": "Hips", "hip_l": "LeftUpLeg", "knee_l": "LeftLeg",
            "foot_l": "LeftFoot", "hip_r": "RightUpLeg",
            "knee_r": "RightLeg", "foot_r": "RightFoot",
        }, frames),
        "target": analyse(target, {
            "root": "world_root", "hip_l": "leg_l", "knee_l": "shin_l",
            "foot_l": "foot_l", "hip_r": "leg_r", "knee_r": "shin_r",
            "foot_r": "foot_r",
        }, frames, Vector((0.0, 1.0, 0.0))),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
