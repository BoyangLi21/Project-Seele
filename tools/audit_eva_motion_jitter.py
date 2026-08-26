#!/usr/bin/env python3
"""Measure high-frequency positional and angular jitter in an EVA action."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fps", required=True, type=float)
    parser.add_argument("--smoothing-seconds", type=float, default=0.10)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def percentile(values, amount: float) -> float:
    return float(np.percentile(np.asarray(values), amount))


def main() -> None:
    args = parse_args()
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    scene = bpy.context.scene
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    authority = "world_root" if "world_root" in rig.pose.bones else "root"
    names = (authority, "root", "torso_lower", "torso_upper", "head",
             "hand_l", "hand_r", "foot_l", "foot_r")
    positions = {name: [] for name in names}
    rotations = {name: [] for name in names if name != authority}
    heights = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name in names:
            bone = rig.pose.bones[name]
            positions[name].append(np.asarray(
                rig.matrix_world @ bone.head, dtype=float))
            if name in rotations:
                q = (rig.matrix_world @ bone.matrix).to_quaternion()
                q.normalize()
                rotations[name].append(np.asarray(
                    (q.w, q.x, q.y, q.z), dtype=float))
        heights.append(positions["head"][-1][2] - min(
            positions["foot_l"][-1][2], positions["foot_r"][-1][2]))
    height = float(np.median(heights))
    dt = 1.0 / args.fps
    radius = max(1, int(round(args.smoothing_seconds * args.fps)))
    offsets = np.arange(-radius, radius + 1)
    sigma = max(1.0, radius * 0.45)
    kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
    kernel /= np.sum(kernel)
    position_reports = {}
    for name, raw in positions.items():
        values = np.asarray(raw)
        velocity = np.diff(values, axis=0) / dt
        acceleration = np.diff(velocity, axis=0) / dt
        padded = np.pad(values, ((radius, radius), (0, 0)), mode="wrap")
        smooth = np.stack([
            np.convolve(padded[:, axis], kernel, mode="valid")
            for axis in range(3)], axis=1)
        residual = np.linalg.norm(values - smooth, axis=1) / height
        speed = np.linalg.norm(velocity, axis=1) / height
        accel = np.linalg.norm(acceleration, axis=1) / height
        position_reports[name] = {
            "speed_p95_h_per_s": percentile(speed, 95.0),
            "speed_max_h_per_s": float(np.max(speed)),
            "acceleration_p95_h_per_s2": percentile(accel, 95.0),
            "acceleration_max_h_per_s2": float(np.max(accel)),
            "high_frequency_residual_p95_h": percentile(residual, 95.0),
            "high_frequency_residual_max_h": float(np.max(residual)),
        }
    rotation_reports = {}
    for name, raw in rotations.items():
        values = np.asarray(raw)
        dots = np.abs(np.sum(values[1:] * values[:-1], axis=1))
        steps = np.degrees(2.0 * np.arccos(np.clip(dots, -1.0, 1.0)))
        speed = steps / dt
        acceleration = np.abs(np.diff(speed)) / dt
        rotation_reports[name] = {
            "angular_speed_p95_deg_s": percentile(speed, 95.0),
            "angular_speed_max_deg_s": float(np.max(speed)),
            "angular_acceleration_p95_deg_s2": percentile(
                acceleration, 95.0) if len(acceleration) else 0.0,
            "angular_acceleration_max_deg_s2": float(
                np.max(acceleration)) if len(acceleration) else 0.0,
            "loop_rotation_seam_degrees": float(np.degrees(
                2.0 * np.arccos(np.clip(abs(np.dot(
                    values[0], values[-1])), -1.0, 1.0)))),
        }
    authority_values = np.asarray(positions[authority])
    position_seams = {}
    for name, raw in positions.items():
        if name == authority:
            continue
        values = np.asarray(raw) - authority_values
        position_seams[name] = float(
            np.linalg.norm(values[-1] - values[0]) / height)
    report = {
        "schema": 1,
        "action": rig.animation_data.action.name,
        "frames": [frames[0], frames[-1]],
        "fps": args.fps,
        "height_units": height,
        "smoothing_seconds": args.smoothing_seconds,
        "positions": position_reports,
        "rotations": rotation_reports,
        "root_relative_position_loop_seams_h": position_seams,
        "maximum_root_relative_position_loop_seam_h": max(
            position_seams.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "action": report["action"],
        "authority_root": position_reports[authority],
        "root_rotation": rotation_reports["root"],
        "torso_upper_rotation": rotation_reports["torso_upper"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
