#!/usr/bin/env python3
"""Measure whole-body lean in the exact Gecko/Bedrock runtime matrix path."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from render_unit01_rig_preview import (
    bone_matrix,
    load_skeleton,
    select_animation,
    transform,
)


def angle(horizontal: float, vertical: float) -> float:
    return math.degrees(math.atan2(horizontal, vertical))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = min(len(ordered) - 1, lower + 1)
    alpha = position - lower
    return ordered[lower] * (1.0 - alpha) + ordered[upper] * alpha


def pivot_world(name, matrices, pivots):
    return transform(matrices[name], pivots[name])


def subtract(left, right):
    return [left[index] - right[index] for index in range(3)]


def dot(left, right):
    return sum(left[index] * right[index] for index in range(3))


def scale(vector, amount):
    return [value * amount for value in vector]


def length(vector):
    return math.sqrt(dot(vector, vector))


def gait_axis_degrees(points_by_side):
    centered = []
    for points in points_by_side.values():
        mean_x = sum(point[0] for point in points) / len(points)
        mean_z = sum(point[2] for point in points) / len(points)
        centered.extend((point[0] - mean_x, point[2] - mean_z)
                        for point in points)
    cxx = sum(x * x for x, _ in centered) / len(centered)
    cxz = sum(x * z for x, z in centered) / len(centered)
    czz = sum(z * z for _, z in centered) / len(centered)
    # Principal horizontal foot-swing axis, measured from canonical local Z.
    angle_from_z = 0.5 * math.atan2(2.0 * cxz, czz - cxx)
    degrees = abs(math.degrees(angle_from_z)) % 180.0
    return min(degrees, 180.0 - degrees), {
        "xx": cxx, "xz": cxz, "zz": czz,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("animation", type=Path)
    parser.add_argument("geo", type=Path)
    parser.add_argument("mesh", type=Path)
    parser.add_argument("--clips", nargs="+", default=("walk", "run"))
    parser.add_argument("--samples", type=int, default=240)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    mesh = json.loads(args.mesh.read_text(encoding="utf-8"))
    pivots, parents, base_rotations = load_skeleton(mesh, args.geo)
    animation_data = json.loads(args.animation.read_text(encoding="utf-8"))
    available = animation_data.get("animations", {})
    report = {"schema": 1, "authority": "exact_gecko_runtime_matrices",
              "clips": {}}
    for clip in args.clips:
        full_name = (clip if clip.startswith("animation.")
                     else f"animation.eva_unit01.{clip}")
        length = float(available[full_name]["animation_length"])
        samples = []
        relative_feet = {"l": [], "r": []}
        knee_lateral_ratios = {"l": [], "r": []}
        foot_order_failures = 0
        bind_foot_order = pivots["foot_l"][0] - pivots["foot_r"][0]
        for index in range(args.samples):
            time = length * index / args.samples
            _, _, rotations, positions = select_animation(
                args.animation, full_name, time)
            cache = {}
            matrices = {
                name: bone_matrix(name, pivots, parents, rotations, positions,
                                  base_rotations, cache)
                for name in pivots
            }
            root = pivot_world("root", matrices, pivots)
            head = pivot_world("head", matrices, pivots)
            left_foot = pivot_world("foot_l", matrices, pivots)
            right_foot = pivot_world("foot_r", matrices, pivots)
            relative_feet["l"].append(subtract(left_foot, root))
            relative_feet["r"].append(subtract(right_foot, root))
            if ((left_foot[0] - right_foot[0]) * bind_foot_order < 0.0):
                foot_order_failures += 1
            for side in ("l", "r"):
                hip = pivot_world(f"leg_{side}", matrices, pivots)
                knee = pivot_world(f"shin_{side}", matrices, pivots)
                ankle = pivot_world(f"foot_{side}", matrices, pivots)
                hip_to_ankle = subtract(ankle, hip)
                denominator = max(1.0e-9, dot(hip_to_ankle, hip_to_ankle))
                projection = dot(subtract(knee, hip), hip_to_ankle) / denominator
                bend = subtract(knee, [hip[axis] + projection
                                       * hip_to_ankle[axis]
                                       for axis in range(3)])
                knee_lateral_ratios[side].append(
                    abs(bend[0]) / max(1.0e-6, abs(bend[2])))
            feet = [(left_foot[axis] + right_foot[axis]) * 0.5
                    for axis in range(3)]
            spine = [head[axis] - root[axis] for axis in range(3)]
            whole = [head[axis] - feet[axis] for axis in range(3)]
            root_matrix = matrices["root"]
            root_origin = transform(root_matrix, pivots["root"])
            root_up_point = transform(root_matrix, (
                pivots["root"][0], pivots["root"][1] + 1.0,
                pivots["root"][2]))
            root_up = [root_up_point[axis] - root_origin[axis]
                       for axis in range(3)]
            samples.append({
                "time": time,
                "root_lateral_degrees": angle(root_up[0], root_up[1]),
                "root_forward_degrees": angle(root_up[2], root_up[1]),
                "spine_lateral_degrees": angle(spine[0], spine[1]),
                "spine_forward_degrees": angle(spine[2], spine[1]),
                "whole_lateral_degrees": angle(whole[0], whole[1]),
                "whole_forward_degrees": angle(whole[2], whole[1]),
            })
        summary = {}
        for key in samples[0]:
            if key == "time":
                continue
            values = [sample[key] for sample in samples]
            mean = sum(values) / len(values)
            centered = [abs(value - mean) for value in values]
            summary[key] = {
                "mean": mean,
                "minimum": min(values),
                "maximum": max(values),
                "p95_abs_centered": percentile(centered, 0.95),
            }
        report["clips"][clip] = {"length": length,
                                  "summary": summary,
                                  "direction": {},
                                  "samples": samples}
        gait_angle, covariance = gait_axis_degrees(relative_feet)
        report["clips"][clip]["direction"] = {
            "foot_swing_axis_error_from_forward_degrees": gait_angle,
            "foot_swing_horizontal_covariance": covariance,
            "foot_left_right_order_failure_fraction":
                foot_order_failures / args.samples,
            "foot_relative_ranges": {
                side: {
                    "lateral": max(point[0] for point in points)
                        - min(point[0] for point in points),
                    "forward": max(point[2] for point in points)
                        - min(point[2] for point in points),
                    "vertical": max(point[1] for point in points)
                        - min(point[1] for point in points),
                }
                for side, points in relative_feet.items()
            },
            "knee_lateral_to_sagittal_bend_ratio": {
                side: {
                    "median": percentile(values, 0.5),
                    "p95": percentile(values, 0.95),
                    "maximum": max(values),
                }
                for side, values in knee_lateral_ratios.items()
            },
        }

    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps({name: {"summary": value["summary"],
                             "direction": value["direction"]}
                      for name, value in report["clips"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
