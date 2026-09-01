#!/usr/bin/env python3
"""Report the exact Tiger part that defines kick ground clearance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_eva_motion_lab_exact import joint, ranges_from_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gap-frames", type=int, default=12)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    digest = hashlib.sha256(args.motion_db.read_bytes()).hexdigest()
    if bpy.context.scene.get("motion_db_sha256") != digest:
        raise RuntimeError("exact scene motion database hash differs")
    ranges = ranges_from_db(motion, args.gap_frames)
    parts = [
        obj for obj in bpy.context.scene.objects
        if obj.name.startswith("PART::")
        and obj.name not in {"PART::knife", "PART::cannon", "PART::lance"}
    ]
    reports = {}
    scene = bpy.context.scene
    for clip_name, (start, end) in ranges.items():
        rows = []
        clip_frames = motion["clips"][clip_name]["frames"]
        for local, timeline in enumerate(range(start, end + 1)):
            scene.frame_set(timeline)
            bpy.context.view_layer.update()
            minimum = None
            minimum_part = None
            for part in parts:
                part_minimum = min(
                    (part.matrix_world @ vertex.co).z
                    for vertex in part.data.vertices
                )
                if minimum is None or part_minimum < minimum:
                    minimum = part_minimum
                    minimum_part = part.name.removeprefix("PART::")
            contacts = clip_frames[local]["foot_contact"]
            support_side = "l" if contacts[0] else "r" if contacts[1] else None
            support_z = (joint(f"foot_{support_side}").z
                         if support_side is not None else None)
            rows.append({
                "localFrame": local,
                "timelineFrame": timeline,
                "minimumMeshZ": minimum,
                "minimumPart": minimum_part,
                "supportSide": support_side,
                "supportAnkleZ": support_z,
                "minimumRelativeToSupportAnkle": (
                    minimum - support_z if support_z is not None else None
                ),
            })
        contact_rows = [row for row in rows if row["supportSide"] is not None]
        worst = min(rows, key=lambda row: row["minimumMeshZ"])
        reports[clip_name] = {
            "worst": worst,
            "minimumPartsByFrequency": {
                part: sum(row["minimumPart"] == part for row in rows)
                for part in sorted({row["minimumPart"] for row in rows})
            },
            "supportAnkleZRange": (
                [min(row["supportAnkleZ"] for row in contact_rows),
                 max(row["supportAnkleZ"] for row in contact_rows)]
                if contact_rows else None
            ),
            "minimumMeshRelativeToSupportAnkle": (
                min(row["minimumRelativeToSupportAnkle"]
                    for row in contact_rows)
                if contact_rows else None
            ),
            "fiveLowestFrames": sorted(
                rows, key=lambda row: row["minimumMeshZ"]
            )[:5],
            "frames": rows,
        }
    output = {
        "schema": 1,
        "authority": "exact_tiger_kick_ground_clearance_diagnostic",
        "motionDatabaseSha256": digest,
        "clips": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        name: {
            "minimumMeshZ": report["worst"]["minimumMeshZ"],
            "minimumPart": report["worst"]["minimumPart"],
            "supportAnkleZRange": report["supportAnkleZRange"],
        }
        for name, report in reports.items()
    }))


if __name__ == "__main__":
    main()
