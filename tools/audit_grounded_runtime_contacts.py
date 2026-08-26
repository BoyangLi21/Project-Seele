#!/usr/bin/env python3
"""Audit exact runtime rigid-foot contact after Blender-to-DB export."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_motion_lab_3d import load_geo, runtime_pivot, target_to_blender
from build_eva_motion_lab_armature import deformation_matrices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--mesh", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def raw_part_vertices(part: dict, stride: int) -> np.ndarray:
    pivot = runtime_pivot(part["pivot"])
    values = [float(value) for value in part["vertices"]]
    points = []
    for offset in range(0, len(values), stride):
        local = Vector((-values[offset], values[offset + 1],
                        values[offset + 2]))
        points.append(tuple(target_to_blender(pivot + local)))
    return np.asarray(points, dtype=float)


def transform_points(matrix, points: np.ndarray,
                     translation: Vector) -> np.ndarray:
    rotation = np.asarray(matrix.to_3x3(), dtype=float)
    offset = np.asarray(matrix.translation + translation, dtype=float)
    return (rotation @ points.T).T + offset


def percentile(values: list[float], amount: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), amount))


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    mesh = json.loads(args.mesh.read_text(encoding="utf-8"))
    stride = int(mesh.get("stride", 0))
    if stride != 8:
        raise RuntimeError(f"expected stride-8 mesh, got {stride}")
    bones, pivots, parents = load_geo(args.geo)
    bone_order = [bone["name"] for bone in bones]
    db_bones = list(motion["bones"])
    part_points = {
        name: raw_part_vertices(part, stride)
        for name, part in mesh["parts"].items()
    }
    fps = float(motion.get("sample_rate", 60.0))
    reports = {}
    failures = []
    for clip_name in ("grounded_walk", "grounded_run"):
        clip = motion["clips"][clip_name]
        frames = clip["frames"]
        travel_m = Vector(tuple(float(value) for value in
                                clip.get("root_travel_m", (0, 0, 0))))
        evaluated = {"l": [], "r": []}
        height_points = []
        for index, frame in enumerate(frames):
            phase = index / max(1, len(frames) - 1)
            matrices = deformation_matrices(
                frame, db_bones, bone_order, pivots, parents)
            runtime_travel = Vector((-travel_m.x, travel_m.y,
                                     travel_m.z)) * (112.0 * phase)
            world_travel = target_to_blender(runtime_travel)
            for side in ("l", "r"):
                name = f"foot_{side}"
                evaluated[side].append(transform_points(
                    matrices[name], part_points[name], world_travel))
            if index == 0:
                for name, points in part_points.items():
                    driver = ({"finger_thumb_l": "hand_l",
                               "finger_thumb_r": "hand_r"}.get(name, name))
                    if driver in matrices:
                        height_points.extend(transform_points(
                            matrices[driver], points, world_travel)[:, 2])
        character_height = (float(np.percentile(height_points, 99.5)
                                  - np.percentile(height_points, 0.5)))
        side_reports = {}
        for side_index, side in enumerate(("l", "r")):
            all_z = np.concatenate([points[:, 2]
                                    for points in evaluated[side]])
            floor = float(np.percentile(all_z, 0.5))
            limit = floor + 0.01 * character_height
            speeds = []
            pair_reports = []
            missing_pairs = 0
            for index in range(len(frames) - 1):
                if not (frames[index]["foot_contact"][side_index]
                        and frames[index + 1]["foot_contact"][side_index]):
                    continue
                first = evaluated[side][index]
                second = evaluated[side][index + 1]
                common = ((first[:, 2] <= limit)
                          & (second[:, 2] <= limit))
                if not np.any(common):
                    missing_pairs += 1
                    continue
                velocity = np.linalg.norm(
                    second[common, :2] - first[common, :2], axis=1) * fps
                normalized = velocity / character_height
                speeds.extend(normalized.tolist())
                pair_reports.append({
                    "frame_indices": [index, index + 1],
                    "samples": int(np.count_nonzero(common)),
                    "median_h_per_s": float(np.median(normalized)),
                    "p95_h_per_s": float(np.percentile(normalized, 95.0)),
                    "maximum_h_per_s": float(np.max(normalized)),
                })
            worst = (max(pair_reports,
                         key=lambda row: row["p95_h_per_s"])
                     if pair_reports else None)
            side_reports[side] = {
                "floor_model_units": floor,
                "contact_limit_model_units": limit,
                "contact_pairs": len(pair_reports),
                "missing_contact_pairs": missing_pairs,
                "contact_vertex_samples": len(speeds),
                "median_slide_h_per_s": percentile(speeds, 50.0),
                "p95_slide_h_per_s": percentile(speeds, 95.0),
                "maximum_slide_h_per_s": max(speeds) if speeds else None,
                "worst_pair": worst,
            }
        gates = {
            "both_feet_have_contact_samples": all(
                side_reports[side]["contact_vertex_samples"] > 0
                for side in ("l", "r")),
            "no_missing_contact_pairs": all(
                side_reports[side]["missing_contact_pairs"] == 0
                for side in ("l", "r")),
            "left_worst_pair_p95_le_0p02Hps": (
                side_reports["l"]["worst_pair"] is not None
                and side_reports["l"]["worst_pair"]["p95_h_per_s"]
                <= 0.02),
            "right_worst_pair_p95_le_0p02Hps": (
                side_reports["r"]["worst_pair"] is not None
                and side_reports["r"]["worst_pair"]["p95_h_per_s"]
                <= 0.02),
        }
        passed = all(gates.values())
        if not passed:
            failures.append(clip_name)
        reports[clip_name] = {
            "frames": len(frames),
            "fps": fps,
            "character_height_model_units": character_height,
            "left_foot": side_reports["l"],
            "right_foot": side_reports["r"],
            "gates": gates,
            "passed": passed,
        }
    report = {
        "schema": 1,
        "authority": "exported_runtime_rigid_foot_vertices",
        "motion_db": str(args.motion_db.resolve()),
        "failures": failures,
        "clips": reports,
        "passed": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "passed": report["passed"],
        "failures": failures,
        "output": str(args.output),
    }, indent=2))
    if args.strict and failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
