#!/usr/bin/env python3
"""Classify EVA knife grip from blade-tip and forearm geometry.

Forward/reverse is measured from the final exact matrices.  A blade pointing
with the elbow-to-wrist vector is forward grip; a blade pointing back toward
the elbow is reverse grip.  This avoids treating an authored Euler label as
visual evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_eva_motion_lab_3d import (
    load_geo,
    runtime_pivot,
    target_to_blender,
)
from build_eva_motion_lab_armature import (
    deformation_matrices,
    geometry_bind_rotations,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--knife-mesh", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict-reverse", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    bones, pivots, parents = load_geo(args.geo)
    bone_order = [bone["name"] for bone in bones]
    bind_rotations = geometry_bind_rotations(bones)
    mesh = json.loads(args.knife_mesh.read_text(encoding="utf-8"))
    part = mesh["parts"]["knife"]
    stride = int(mesh["stride"])
    pivot = runtime_pivot(part["pivot"])
    values = [float(value) for value in part["vertices"]]
    vertices = [
        target_to_blender(pivot + Vector((
            -values[offset], values[offset + 1], values[offset + 2]
        )))
        for offset in range(0, len(values), stride)
    ]
    grip_bind = target_to_blender(pivots["knife"])
    ordered = sorted(vertices, key=lambda value: (value - grip_bind).length,
                     reverse=True)
    tip_bind = sum(
        ordered[:max(3, len(ordered) // 200)],
        Vector((0.0, 0.0, 0.0)),
    ) / max(3, len(ordered) // 200)

    clips = {}
    failures = []
    candidate_search = {}
    knife_index = motion["bones"].index("knife")
    for clip_name, clip in motion["clips"].items():
        if "knife" not in clip_name:
            continue
        rows = []
        for frame_index, frame in enumerate(clip["frames"]):
            matrices = deformation_matrices(
                frame, motion["bones"], bone_order, pivots, parents,
                bind_rotations,
            )
            grip = matrices["knife"] @ grip_bind
            tip = matrices["knife"] @ tip_bind
            elbow = matrices["forearm_r"] @ target_to_blender(
                pivots["forearm_r"]
            )
            wrist = matrices["hand_r"] @ target_to_blender(
                pivots["hand_r"]
            )
            blade = (tip - grip).normalized()
            forearm = (wrist - elbow).normalized()
            rows.append({
                "frame": frame_index,
                "bladeForearmDot": blade.dot(forearm),
                "gripToWristModelUnits": (grip - wrist).length,
            })
        dots = [row["bladeForearmDot"] for row in rows]
        distances = [row["gripToWristModelUnits"] for row in rows]
        median = statistics.median(dots)
        classification = (
            "REVERSE" if median <= -0.25
            else "FORWARD" if median >= 0.25
            else "CROSSWISE"
        )
        if (args.strict_reverse and "reverse" in clip_name
                and classification != "REVERSE"):
            failures.append(
                f"{clip_name}: median blade/forearm dot {median:.6f} "
                f"is {classification}, not REVERSE"
            )
        clips[clip_name] = {
            "classification": classification,
            "minimumBladeForearmDot": min(dots),
            "medianBladeForearmDot": median,
            "maximumBladeForearmDot": max(dots),
            "maximumGripToWristModelUnits": max(distances),
        }
        half_turns = {
            "post_x": Quaternion((1.0, 0.0, 0.0), math.pi),
            "post_y": Quaternion((0.0, 1.0, 0.0), math.pi),
            "post_z": Quaternion((0.0, 0.0, 1.0), math.pi),
        }
        candidates = {"current": None}
        candidates.update(half_turns)
        candidates.update({
            name.replace("post_", "pre_"): value
            for name, value in half_turns.items()
        })
        candidate_rows = []
        for candidate_name, half_turn in candidates.items():
            candidate_dots = []
            candidate_quaternion = None
            for frame in clip["frames"]:
                source_quaternion = Quaternion(tuple(
                    float(value)
                    for value in frame["rotation_wxyz"][knife_index]
                ))
                source_quaternion.normalize()
                if half_turn is None:
                    tested = source_quaternion
                elif candidate_name.startswith("post_"):
                    tested = source_quaternion @ half_turn
                else:
                    tested = half_turn @ source_quaternion
                tested.normalize()
                candidate_quaternion = tested
                rotations = list(frame["rotation_wxyz"])
                rotations[knife_index] = [
                    float(tested.w), float(tested.x),
                    float(tested.y), float(tested.z),
                ]
                test_frame = dict(frame)
                test_frame["rotation_wxyz"] = rotations
                matrices = deformation_matrices(
                    test_frame, motion["bones"], bone_order, pivots,
                    parents, bind_rotations,
                )
                grip = matrices["knife"] @ grip_bind
                tip = matrices["knife"] @ tip_bind
                elbow = matrices["forearm_r"] @ target_to_blender(
                    pivots["forearm_r"]
                )
                wrist = matrices["hand_r"] @ target_to_blender(
                    pivots["hand_r"]
                )
                candidate_dots.append(
                    (tip - grip).normalized().dot(
                        (wrist - elbow).normalized())
                )
            candidate_rows.append({
                "variant": candidate_name,
                "authoredQuaternionWxyz": [
                    float(candidate_quaternion.w),
                    float(candidate_quaternion.x),
                    float(candidate_quaternion.y),
                    float(candidate_quaternion.z),
                ],
                "minimumBladeForearmDot": min(candidate_dots),
                "medianBladeForearmDot": statistics.median(candidate_dots),
                "maximumBladeForearmDot": max(candidate_dots),
            })
        candidate_rows.sort(key=lambda row: row["medianBladeForearmDot"])
        candidate_search[clip_name] = candidate_rows
    report = {
        "schema": 1,
        "authority": "exact_blade_tip_vs_elbow_to_wrist_geometry",
        "clipCount": len(clips),
        "clips": clips,
        "halfTurnCandidateSearch": candidate_search,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "automaticVisualApproval": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
