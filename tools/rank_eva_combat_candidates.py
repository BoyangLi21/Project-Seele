#!/usr/bin/env python3
"""Rank EVA combat candidates from exact 3D hand/blade trajectories."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_motion_lab_3d import (
    load_geo,
    runtime_pivot,
    target_to_blender,
)
from build_eva_motion_lab_armature import deformation_matrices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--knife-mesh", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--shortlist-output", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def quaternion_angle(first, second) -> float:
    a = Quaternion(tuple(first))
    b = Quaternion(tuple(second))
    dot = min(1.0, max(-1.0, abs(a.dot(b))))
    return math.degrees(2.0 * math.acos(dot))


def knife_tip(path: Path) -> Vector:
    payload = json.loads(path.read_text(encoding="utf-8"))
    part = payload["parts"]["knife"]
    stride = int(payload["stride"])
    pivot = runtime_pivot(part["pivot"])
    points = []
    values = [float(value) for value in part["vertices"]]
    for offset in range(0, len(values), stride):
        local = Vector((-values[offset], values[offset + 1],
                        values[offset + 2]))
        points.append(target_to_blender(pivot + local))
    hand = target_to_blender(pivot)
    return max(points, key=lambda point: (point - hand).length)


def path_metrics(points: list[Vector], fps: float) -> dict:
    distances = [(points[index] - points[index - 1]).length / 112.0
                 for index in range(1, len(points))]
    speeds = [distance * fps for distance in distances]
    accelerations = [abs(speeds[index] - speeds[index - 1]) * fps
                     for index in range(1, len(speeds))]
    return {
        "path_length_meters": sum(distances),
        "peak_speed_mps": max(speeds, default=0.0),
        "mean_speed_mps": sum(speeds) / max(1, len(speeds)),
        "peak_tangential_acceleration_mps2": max(accelerations, default=0.0),
        "displacement_meters": (points[-1] - points[0]).length / 112.0,
    }


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    bones, pivots, parents = load_geo(args.geo)
    bone_order = [bone["name"] for bone in bones]
    db_bones = list(motion["bones"])
    fps = float(motion.get("sample_rate", 30.0))
    tip = knife_tip(args.knife_mesh)
    reports = []
    for name, clip in motion["clips"].items():
        if clip.get("role") != "candidate_combat":
            continue
        matrices = [deformation_matrices(
            frame, db_bones, bone_order, pivots, parents
        ) for frame in clip["frames"]]
        left_hand = [matrix["hand_l"] @ target_to_blender(pivots["hand_l"])
                     for matrix in matrices]
        right_hand = [matrix["hand_r"] @ target_to_blender(pivots["hand_r"])
                      for matrix in matrices]
        knife_points = [matrix["knife"] @ tip for matrix in matrices]
        left = path_metrics(left_hand, fps)
        right = path_metrics(right_hand, fps)
        blade = path_metrics(knife_points, fps)
        start = clip["frames"][0]["rotation_wxyz"]
        end = clip["frames"][-1]["rotation_wxyz"]
        pose_return = [
            quaternion_angle(start[index], end[index])
            for index, bone in enumerate(db_bones)
            if not bone.startswith("finger_")
        ]
        root_start = Vector(tuple(clip["frames"][0]["root_m"]))
        root_end = Vector(tuple(clip["frames"][-1]["root_m"]))
        root_displacement = (root_end - root_start).length
        is_sword = name.startswith("cmu_sword_")
        primary = blade if is_sword else (
            left if left["peak_speed_mps"] >= right["peak_speed_mps"] else right
        )
        recovery = sum(pose_return) / max(1, len(pose_return))
        # Rank forceful, readable paths while preferring clips that recover
        # toward a chainable pose and do not translate the whole EVA wildly.
        score = (primary["peak_speed_mps"] * 0.52
                 + primary["path_length_meters"] * 0.90
                 - recovery * 0.022
                 - root_displacement * 0.35)
        reports.append({
            "clip": name,
            "kind": "sword" if is_sword else "punch",
            "duration_seconds": clip["duration_seconds"],
            "primary_hand": ("blade" if is_sword else
                             "left" if primary is left else "right"),
            "left_hand": left,
            "right_hand": right,
            "blade_tip": blade,
            "mean_pose_return_error_degrees": recovery,
            "root_displacement_meters": root_displacement,
            "score": score,
        })
    for kind in ("punch", "sword"):
        group = sorted((item for item in reports if item["kind"] == kind),
                       key=lambda item: item["score"], reverse=True)
        for rank, item in enumerate(group, start=1):
            item["rank_within_kind"] = rank
    reports.sort(key=lambda item: (item["kind"], item["rank_within_kind"]))
    output = {
        "schema": 1,
        "authority": "exact_eva_joint_and_progressive_knife_trajectory",
        "motion_db": str(args.motion_db.resolve()),
        "candidates": reports,
        "shortlist": {
            kind: [item["clip"] for item in reports
                   if item["kind"] == kind and item["rank_within_kind"] <= 3]
            for kind in ("punch", "sword")
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.shortlist_output is not None:
        selected = {"idle"}
        selected.update(output["shortlist"]["punch"])
        selected.update(output["shortlist"]["sword"])
        shortlist = copy.deepcopy(motion)
        shortlist["clips"] = {
            name: clip for name, clip in shortlist["clips"].items()
            if name in selected
        }
        shortlist["shortlist_source"] = str(args.output.resolve())
        args.shortlist_output.parent.mkdir(parents=True, exist_ok=True)
        args.shortlist_output.write_text(
            json.dumps(shortlist, ensure_ascii=False,
                       separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    print(
        f"EVA combat ranking: candidates={len(reports)} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
