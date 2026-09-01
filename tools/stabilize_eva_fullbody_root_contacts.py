#!/usr/bin/env python3
"""Apply bounded root-only contact stabilization to a review motion DB."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_eva_motion_lab_3d import (
    load_geo,
    target_to_blender,
)
from build_eva_motion_lab_armature import (
    deformation_matrices,
    geometry_bind_rotations,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--maximum-correction-height-fraction",
                        type=float, default=0.06)
    parser.add_argument("--edge-fade-frames", type=int, default=6)
    parser.add_argument("--strength", type=float, default=0.85)
    parser.add_argument("--maximum-contact-horizontal-drift-height-fraction",
                        type=float, default=0.06)
    parser.add_argument("--maximum-contact-vertical-drift-height-fraction",
                        type=float, default=0.04)
    parser.add_argument("--maximum-redundant-contact-run-frames",
                        type=int, default=45)
    parser.add_argument("--allow-split-airborne", action="store_true")
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


def median_vector(values: list[Vector]) -> Vector:
    ordered = [sorted(float(value[axis]) for value in values)
               for axis in range(3)]
    middle = len(values) // 2
    return Vector(tuple(values_axis[middle] for values_axis in ordered))


def root_delta_from_blender(value: Vector) -> Vector:
    runtime = Vector((value.x, value.z, -value.y))
    return Vector((-runtime.x, runtime.y, runtime.z)) / 112.0


def main() -> None:
    args = parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    bones, pivots, parents = load_geo(args.geo)
    bone_order = [bone["name"] for bone in bones]
    bind_rotations = geometry_bind_rotations(bones)
    height = max(point.y for point in pivots.values()) - min(
        point.y for point in pivots.values())
    maximum = args.maximum_correction_height_fraction * height
    reports = {}
    for clip_name, clip in document["clips"].items():
        frames = clip["frames"]
        evaluated = [
            deformation_matrices(
                frame, document["bones"], bone_order, pivots, parents,
                bind_rotations)
            for frame in frames
        ]
        feet = {
            side: [matrix[f"foot_{side}"] @ target_to_blender(
                pivots[f"foot_{side}"]) for matrix in evaluated]
            for side in ("l", "r")
        }
        requests: list[list[Vector]] = [[] for _ in frames]
        original_contacts = {
            side: [bool(frame["foot_contact"][side_index])
                   for frame in frames]
            for side_index, side in enumerate(("l", "r"))
        }
        refined_contacts = {
            side: list(values) for side, values in original_contacts.items()
        }
        rejected_contact_runs = []
        for side in ("l", "r"):
            for first, last in runs(original_contacts[side]):
                if last - first < 3:
                    continue
                origin = feet[side][first]
                cleared = []
                maximum_horizontal = 0.0
                maximum_vertical = 0.0
                for index in range(first + 1, last + 1):
                    delta = feet[side][index] - origin
                    horizontal = math.hypot(delta.x, delta.y) / height
                    vertical = abs(delta.z) / height
                    maximum_horizontal = max(maximum_horizontal, horizontal)
                    maximum_vertical = max(maximum_vertical, vertical)
                    if (horizontal
                            > args.maximum_contact_horizontal_drift_height_fraction
                            or vertical
                            > args.maximum_contact_vertical_drift_height_fraction):
                        refined_contacts[side][index] = False
                        cleared.append(index)
                        if index < last:
                            origin = feet[side][index + 1]
                if cleared:
                    rejected_contact_runs.append({
                        "side": side,
                        "frames": [first, last],
                        "horizontalDriftHeightFraction": maximum_horizontal,
                        "verticalDriftHeightFraction": maximum_vertical,
                        "splitFrames": cleared,
                    })
        # Contact-run splitting must not invent an airborne phase that was
        # absent from the source capture.  If a split cleared the only active
        # foot, restore the slower of the originally planted feet for that
        # frame; true source airborne frames remain untouched.
        if not args.allow_split_airborne:
            for index in range(len(frames)):
                if (refined_contacts["l"][index]
                        or refined_contacts["r"][index]):
                    continue
                candidates = [
                    side for side in ("l", "r")
                    if original_contacts[side][index]
                ]
                if not candidates:
                    continue
                before = max(0, index - 1)
                chosen = min(
                    candidates,
                    key=lambda side: (feet[side][index]
                                      - feet[side][before]).length,
                )
                refined_contacts[chosen][index] = True
        for index, frame in enumerate(frames):
            frame["foot_contact"] = [
                refined_contacts["l"][index],
                refined_contacts["r"][index],
            ]

        contact_runs = {}
        for side_index, side in enumerate(("l", "r")):
            active = refined_contacts[side]
            contact_runs[side] = runs(active)
            for first, last in contact_runs[side]:
                if last - first < 3:
                    continue
                lock = median_vector(feet[side][first:last + 1])
                for index in range(first, last + 1):
                    requests[index].append(lock - feet[side][index])
        raw = []
        for values in requests:
            if not values:
                raw.append(Vector((0.0, 0.0, 0.0)))
            else:
                raw.append(sum(values, Vector((0.0, 0.0, 0.0)))
                           / len(values))
        smoothed = []
        for index in range(len(raw)):
            first = max(0, index - 2)
            last = min(len(raw), index + 3)
            value = sum(raw[first:last], Vector((0.0, 0.0, 0.0))) \
                / (last - first)
            edge = min(index, len(raw) - 1 - index)
            fade = min(1.0, edge / max(1, args.edge_fade_frames))
            value *= args.strength * fade
            if value.length > maximum:
                value.normalize()
                value *= maximum
            smoothed.append(value)
        for frame, correction in zip(frames, smoothed):
            delta = root_delta_from_blender(correction)
            frame["root_m"] = [
                round(float(frame["root_m"][axis]) + delta[axis], 7)
                for axis in range(3)
            ]
        reports[clip_name] = {
            "contactRuns": contact_runs,
            "rejectedContactRuns": rejected_contact_runs,
            "maximumCorrectionModelUnits": max(
                value.length for value in smoothed),
            "maximumCorrectionHeightFraction": max(
                value.length for value in smoothed) / height,
            "meanCorrectionHeightFraction": sum(
                value.length for value in smoothed) / len(smoothed) / height,
        }
    document["root_contact_stabilization"] = {
        "method": "bounded_root_only_median_contact_lock_with_edge_fade",
        "maximumCorrectionHeightFraction": (
            args.maximum_correction_height_fraction),
        "edgeFadeFrames": args.edge_fade_frames,
        "strength": args.strength,
        "writesJointRotations": False,
        "writesWorldEntityRoot": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    report = {
        "schema": 1,
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "heightModelUnits": height,
        "clips": reports,
        "status": "bounded_root_only_review_stabilization_not_live",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "clips": len(reports),
        "maximumCorrectionHeightFraction": max(
            value["maximumCorrectionHeightFraction"]
            for value in reports.values()),
    }))


if __name__ == "__main__":
    main()
