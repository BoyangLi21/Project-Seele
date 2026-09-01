#!/usr/bin/env python3
"""Audit captured support and whole-body motion in the exact Tiger scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_eva_motion_lab_exact import joint, object_bounds, ranges_from_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gap-frames", type=int, default=12)
    parser.add_argument("--maximum-unsupported-fraction",
                        type=float, default=0.10)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def runs(values: list[bool]) -> list[tuple[int, int]]:
    output = []
    opened = None
    for index, value in enumerate(values):
        if value and opened is None:
            opened = index
        elif not value and opened is not None:
            output.append((opened, index - 1))
            opened = None
    if opened is not None:
        output.append((opened, len(values) - 1))
    return output


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    motion_hash = hashlib.sha256(args.motion_db.read_bytes()).hexdigest()
    if bpy.context.scene.get("motion_db_sha256") != motion_hash:
        raise RuntimeError("exact scene motion database hash differs")
    ranges = ranges_from_db(motion, args.gap_frames)
    scene = bpy.context.scene
    body_parts = [
        obj for obj in scene.objects
        if obj.name.startswith("PART::")
        and obj.name not in {"PART::knife", "PART::cannon", "PART::lance"}
    ]
    failures = []
    clips = {}
    for name, (start, end) in ranges.items():
        rows = []
        for frame in range(start, end + 1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            minimum, maximum = object_bounds(body_parts)
            rows.append({
                "frame": frame,
                "root": joint("root").copy(),
                "torso": joint("torso_lower").copy(),
                "hand_l": joint("hand_l").copy(),
                "hand_r": joint("hand_r").copy(),
                "ankle_l": joint("foot_l").copy(),
                "ankle_r": joint("foot_r").copy(),
                "contact_l": not bpy.data.objects[
                    "CONTACT_L_PLANTED"].hide_viewport,
                "contact_r": not bpy.data.objects[
                    "CONTACT_R_PLANTED"].hide_viewport,
                "bounds_min_z": minimum[2],
                "bounds_max_z": maximum[2],
                "knife": (joint("knife").copy()
                          if "knife" in name else None),
            })
        height = max(row["bounds_max_z"] for row in rows) - min(
            row["bounds_min_z"] for row in rows)
        clip_failures = []
        unsupported = sum(not (row["contact_l"] or row["contact_r"])
                          for row in rows) / len(rows)
        if unsupported > args.maximum_unsupported_fraction:
            clip_failures.append(
                "unsupported fraction "
                f"{unsupported:.4f} > "
                f"{args.maximum_unsupported_fraction:.4f}")
        foot_report = {}
        for side in ("l", "r"):
            contacts = [row[f"contact_{side}"] for row in rows]
            segments = []
            for first, last in runs(contacts):
                if last - first < 3:
                    continue
                origin = rows[first][f"ankle_{side}"]
                horizontal = []
                vertical = []
                for index in range(first, last + 1):
                    delta = rows[index][f"ankle_{side}"] - origin
                    horizontal.append(math.hypot(delta.x, delta.y) / height)
                    vertical.append(abs(delta.z) / height)
                segment = {
                    "frames": [first, last],
                    "maximumHorizontalDriftH": max(horizontal),
                    "maximumVerticalDriftH": max(vertical),
                }
                segments.append(segment)
                if segment["maximumHorizontalDriftH"] > 0.06:
                    clip_failures.append(
                        f"{side} planted drift "
                        f"{segment['maximumHorizontalDriftH']:.5f} H > 0.06 H")
                if segment["maximumVerticalDriftH"] > 0.04:
                    clip_failures.append(
                        f"{side} planted vertical drift "
                        f"{segment['maximumVerticalDriftH']:.5f} H > 0.04 H")
            foot_report[side] = segments
        minimum_ground = min(row["bounds_min_z"] for row in rows)
        if minimum_ground < -0.12:
            clip_failures.append(
                f"ground penetration {minimum_ground:.5f} < -0.12")
        root_origin = rows[0]["root"]
        root_range = max((row["root"] - root_origin).length
                         for row in rows) / height
        if root_range > 0.30:
            clip_failures.append(
                f"root range {root_range:.5f} H > 0.30 H")
        torso_range = max((row["torso"] - rows[0]["torso"]).length
                          for row in rows) / height
        hand_range = max(
            max((row[f"hand_{side}"] - rows[0][f"hand_{side}"]).length
                for row in rows) / height
            for side in ("l", "r")
        )
        ankle_range = max(
            max((row[f"ankle_{side}"] - rows[0][f"ankle_{side}"]).length
                for row in rows) / height
            for side in ("l", "r")
        )
        if torso_range < 0.005 or hand_range < 0.08 or ankle_range < 0.005:
            clip_failures.append(
                "whole-body dynamics missing: "
                f"torso={torso_range:.5f} hand={hand_range:.5f} "
                f"ankle={ankle_range:.5f} H")
        knife_socket_variation = None
        if "knife" in name:
            distances = [
                (row["knife"] - row["hand_r"]).length for row in rows
            ]
            knife_socket_variation = max(distances) - min(distances)
            if knife_socket_variation > 1.0e-5:
                clip_failures.append(
                    "knife grip socket changes by "
                    f"{knife_socket_variation:.8f}")
        unique = sorted(set(clip_failures))
        failures.extend(f"{name}: {failure}" for failure in unique)
        clips[name] = {
            "frameRange": [start, end],
            "frames": len(rows),
            "height": height,
            "unsupportedFraction": unsupported,
            "minimumBoundsZ": minimum_ground,
            "maximumRootRangeH": root_range,
            "requiresServerRootMotionForLive": root_range > 0.05,
            "torsoRangeH": torso_range,
            "handRangeH": hand_range,
            "ankleRangeH": ankle_range,
            "knifeSocketVariation": knife_socket_variation,
            "feet": foot_report,
            "failures": unique,
        }
    report = {
        "schema": 1,
        "authority": "exact_tiger_global_matrices_captured_full_body",
        "motionDatabaseSha256": motion_hash,
        "clipCount": len(clips),
        "failureCount": len(failures),
        "failures": failures,
        "clips": clips,
        "result": ("ELIGIBLE_FOR_HUMAN_REVIEW_ONLY"
                   if not failures else "FAIL"),
        "automaticVisualApproval": False,
        "maximumUnsupportedFraction": args.maximum_unsupported_fraction,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "clips": len(clips), "failures": len(failures),
        "result": report["result"],
    }))
    if args.strict and failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
