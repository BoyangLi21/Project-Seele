#!/usr/bin/env python3
"""Lock the declared non-striking kick support foot with root translation only."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_eva_motion_lab_3d import load_geo, target_to_blender
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
    parser.add_argument(
        "--maximum-correction-height-fraction", type=float, default=0.30
    )
    parser.add_argument("--clip", action="append",
                        help="limit support locking to named clips")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def median_vector(values: list[Vector]) -> Vector:
    ordered = [sorted(float(value[axis]) for value in values)
               for axis in range(3)]
    middle = len(values) // 2
    return Vector(tuple(axis[middle] for axis in ordered))


def root_delta_from_blender(value: Vector) -> Vector:
    runtime = Vector((value.x, value.z, -value.y))
    return Vector((-runtime.x, runtime.y, runtime.z)) / 112.0


def evaluate(document: dict, clip: dict, bone_order: list[str],
             pivots: dict[str, Vector], parents: dict[str, str | None],
             bind_rotations: dict) -> dict[str, list[Vector]]:
    matrices = [
        deformation_matrices(
            frame, document["bones"], bone_order, pivots, parents,
            bind_rotations,
        )
        for frame in clip["frames"]
    ]
    return {
        side: [matrix[f"foot_{side}"] @ target_to_blender(
            pivots[f"foot_{side}"])
            for matrix in matrices]
        for side in ("l", "r")
    }


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


def contact_runs(frames: list[dict]) -> list[tuple[int, int, str]]:
    if any(sum(bool(value) for value in frame["foot_contact"]) > 1
           for frame in frames):
        raise RuntimeError("kick root lock accepts one support foot per frame")
    output = []
    for side_index, side in enumerate(("l", "r")):
        active = [bool(frame["foot_contact"][side_index]) for frame in frames]
        output.extend((first, last, side) for first, last in runs(active))
    output.sort()
    if not output:
        raise RuntimeError("kick clip has no support contact run")
    return output


def main() -> None:
    args = parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    output = copy.deepcopy(document)
    bones, pivots, parents = load_geo(args.geo)
    bone_order = [bone["name"] for bone in bones]
    bind_rotations = geometry_bind_rotations(bones)
    height = max(point.y for point in pivots.values()) - min(
        point.y for point in pivots.values()
    )
    maximum_allowed = args.maximum_correction_height_fraction * height
    reports = {}
    failures = []
    canonical_support_z = None

    for name, clip in output["clips"].items():
        if args.clip and name not in args.clip:
            continue
        frames = clip["frames"]
        declared_runs = contact_runs(frames)
        feet = evaluate(
            output, clip, bone_order, pivots, parents, bind_rotations
        )
        corrections = [Vector((0.0, 0.0, 0.0)) for _ in frames]
        run_reports = []
        for run_index, (first, last, support) in enumerate(declared_runs):
            lock = median_vector(feet[support][first:last + 1])
            if canonical_support_z is None:
                canonical_support_z = lock.z
            lock.z = canonical_support_z
            if run_index > 0:
                previous_last = declared_runs[run_index - 1][1]
                if first <= previous_last + 1:
                    continuous = feet[support][first] \
                        + corrections[previous_last]
                    lock.x = continuous.x
                    lock.y = continuous.y
            for index in range(first, last + 1):
                corrections[index] = lock - feet[support][index]
            run_reports.append({
                "supportFoot": support,
                "contactFrames": [first, last],
                "lock": [float(value) for value in lock],
            })
        first = declared_runs[0][0]
        if first > 0:
            for index in range(first):
                corrections[index] = corrections[first] * (index / first)
        for left_run, right_run in zip(declared_runs, declared_runs[1:]):
            left = left_run[1]
            right = right_run[0]
            gap = right - left
            for index in range(left + 1, right):
                amount = (index - left) / gap
                corrections[index] = Vector(corrections[left]).lerp(
                    corrections[right], amount
                )
        last = declared_runs[-1][1]
        tail = len(frames) - 1 - last
        if tail > 0:
            for index in range(last + 1, len(frames)):
                remaining = (len(frames) - 1 - index) / tail
                corrections[index] = corrections[last] * remaining
        maximum = max(value.length for value in corrections)
        if maximum > maximum_allowed:
            failures.append(
                f"{name}: support correction {maximum / height:.5f} H "
                f"> {args.maximum_correction_height_fraction:.5f} H"
            )
        for frame, correction in zip(frames, corrections):
            delta = root_delta_from_blender(correction)
            frame["root_m"] = [
                round(float(frame["root_m"][axis]) + delta[axis], 7)
                for axis in range(3)
            ]
        corrected = evaluate(
            output, clip, bone_order, pivots, parents, bind_rotations
        )
        maximum_horizontal_drift = 0.0
        maximum_vertical_drift = 0.0
        for run_report, (first, last, support) in zip(
                run_reports, declared_runs):
            origin = corrected[support][first]
            horizontal_drift = max(
                math.hypot((point - origin).x, (point - origin).y)
                for point in corrected[support][first:last + 1]
            )
            vertical_drift = max(
                abs((point - origin).z)
                for point in corrected[support][first:last + 1]
            )
            maximum_horizontal_drift = max(
                maximum_horizontal_drift, horizontal_drift
            )
            maximum_vertical_drift = max(
                maximum_vertical_drift, vertical_drift
            )
            run_report["maximumHorizontalDriftHeightFraction"] = (
                horizontal_drift / height
            )
            run_report["maximumVerticalDriftHeightFraction"] = (
                vertical_drift / height
            )
        reports[name] = {
            "contactRuns": run_reports,
            "maximumCorrectionHeightFraction": maximum / height,
            "maximumSupportHorizontalDriftHeightFraction": (
                maximum_horizontal_drift / height
            ),
            "maximumSupportVerticalDriftHeightFraction": (
                maximum_vertical_drift / height
            ),
            "writesJointRotations": False,
            "writesRootVertical": True,
        }
        if maximum_horizontal_drift / height > 0.06:
            failures.append(
                f"{name}: corrected support drift "
                f"{maximum_horizontal_drift / height:.5f} H > 0.06 H"
            )
        if maximum_vertical_drift / height > 0.04:
            failures.append(
                f"{name}: corrected support vertical drift "
                f"{maximum_vertical_drift / height:.5f} H > 0.04 H"
            )

    output["root_contact_stabilization"] = {
        "method": "single_support_kick_exact_root_lock",
        "maximumCorrectionHeightFraction": (
            args.maximum_correction_height_fraction
        ),
        "writesJointRotations": False,
        "writesRootVertical": True,
        "writesWorldEntityRoot": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": 1,
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "heightModelUnits": height,
        "clips": reports,
        "failures": failures,
        "status": "FAIL" if failures else "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "automaticVisualApproval": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "clips": len(reports), "failures": len(failures),
        "maximumCorrectionHeightFraction": max(
            row["maximumCorrectionHeightFraction"]
            for row in reports.values()
        ),
        "maximumSupportDriftHeightFraction": max(
            row["maximumSupportHorizontalDriftHeightFraction"]
            for row in reports.values()
        ),
    }))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
