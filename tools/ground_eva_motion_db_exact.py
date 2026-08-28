#!/usr/bin/env python3
"""Lift only the EVA root enough to keep the exact animated mesh grounded."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_eva_motion_lab_exact import ranges_from_db


MODEL_UNITS_PER_METRE = 112.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gap-frames", type=int, default=12)
    parser.add_argument("--minimum-blender-z", type=float, default=-0.10)
    parser.add_argument("--window", type=int, default=2,
                        help="symmetric maximum-filter radius")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def minimum_mesh_z(parts: list[bpy.types.Object]) -> float:
    return min(
        (part.matrix_world @ vertex.co).z
        for part in parts
        for vertex in part.data.vertices
    )


def main() -> None:
    args = parse_args()
    document = json.loads(args.motion_db.read_text(encoding="utf-8"))
    digest = hashlib.sha256(args.motion_db.read_bytes()).hexdigest()
    if bpy.context.scene.get("motion_db_sha256") != digest:
        raise SystemExit("exact scene and motion database hashes differ")
    output = copy.deepcopy(document)
    ranges = ranges_from_db(document, args.gap_frames)
    master_scale = float(bpy.data.objects["EVA_EXACT_ROOT"].scale.x)
    if master_scale <= 0.0:
        raise RuntimeError("EVA exact root scale must be positive")
    parts = [
        obj for obj in bpy.context.scene.objects
        if obj.name.startswith("PART::")
        and obj.name not in {"PART::knife", "PART::cannon", "PART::lance"}
    ]
    if not parts:
        raise RuntimeError("exact EVA body parts are missing")

    maximum_lift_m = 0.0
    lifted_frames = 0
    per_clip = {}
    scene = bpy.context.scene
    for clip_name, (start, end) in ranges.items():
        required = []
        for timeline_frame in range(start, end + 1):
            scene.frame_set(timeline_frame)
            bpy.context.view_layer.update()
            deficit = max(0.0, args.minimum_blender_z - minimum_mesh_z(parts))
            required.append(
                deficit / (master_scale * MODEL_UNITS_PER_METRE))
        radius = max(0, args.window)
        filtered = [
            max(required[max(0, index - radius):
                         min(len(required), index + radius + 1)])
            for index in range(len(required))
        ]
        frames = output["clips"][clip_name]["frames"]
        for frame, lift_m in zip(frames, filtered):
            if lift_m > 1.0e-9:
                frame["root_m"][1] = round(
                    float(frame["root_m"][1]) + lift_m, 7)
                lifted_frames += 1
                maximum_lift_m = max(maximum_lift_m, lift_m)
        per_clip[clip_name] = {
            "frames": len(frames),
            "lifted_frames": sum(value > 1.0e-9 for value in filtered),
            "maximum_lift_m": round(max(filtered, default=0.0), 7),
        }

    output["exact_grounding"] = {
        "authority": "exact_body_mesh_root_only_minimum_clearance",
        "minimum_blender_z": args.minimum_blender_z,
        "maximum_filter_radius": args.window,
        "maximum_lift_m": round(maximum_lift_m, 7),
        "lifted_frames": lifted_frames,
        "clips": per_clip,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    print(json.dumps(output["exact_grounding"], ensure_ascii=False))


if __name__ == "__main__":
    main()
