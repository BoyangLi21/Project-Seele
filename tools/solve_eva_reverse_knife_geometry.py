#!/usr/bin/env python3
"""Solve a reverse knife so its blade points from wrist toward elbow."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from mathutils import Euler, Matrix, Quaternion, Vector

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


BLENDER_RUNTIME_BASIS = Matrix((
    (1.0, 0.0, 0.0),
    (0.0, 0.0, -1.0),
    (0.0, 1.0, 0.0),
))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--knife-mesh", required=True, type=Path)
    parser.add_argument("--clip", default="free_reverse_knife_combo")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def blender_to_authored(value: Quaternion) -> Quaternion:
    value.normalize()
    runtime = (BLENDER_RUNTIME_BASIS.inverted()
               @ value.to_matrix()
               @ BLENDER_RUNTIME_BASIS)
    euler = runtime.to_euler("XYZ")
    authored = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_quaternion()
    authored.normalize()
    return authored


def rounded(value: Quaternion) -> list[float]:
    value.normalize()
    return [round(float(value.w), 7), round(float(value.x), 7),
            round(float(value.y), 7), round(float(value.z), 7)]


def main() -> None:
    args = parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    clip = document["clips"].get(args.clip)
    if clip is None:
        raise SystemExit(f"missing reverse clip: {args.clip}")
    knife_index = document["bones"].index("knife")
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
    tip_count = max(3, len(ordered) // 200)
    tip_bind = sum(ordered[:tip_count], Vector((0.0, 0.0, 0.0))) \
        / tip_count
    blade_bind = (tip_bind - grip_bind).normalized()
    half_turn = Quaternion((0.0, 1.0, 0.0), math.pi)

    previous = None
    solved = []
    for frame in clip["frames"]:
        base = Quaternion(tuple(float(value)
                                for value in frame["rotation_wxyz"][
                                    knife_index]))
        base.normalize()
        seed = half_turn @ base
        seed.normalize()
        seed_rotations = list(frame["rotation_wxyz"])
        seed_rotations[knife_index] = rounded(seed)
        seed_frame = dict(frame)
        seed_frame["rotation_wxyz"] = seed_rotations
        matrices = deformation_matrices(
            seed_frame, document["bones"], bone_order, pivots, parents,
            bind_rotations,
        )
        elbow = matrices["forearm_r"] @ target_to_blender(
            pivots["forearm_r"]
        )
        wrist = matrices["hand_r"] @ target_to_blender(pivots["hand_r"])
        desired_blade = (elbow - wrist).normalized()
        knife_global = matrices["knife"].to_quaternion()
        knife_global.normalize()
        current_blade = knife_global @ blade_bind
        correction = current_blade.rotation_difference(desired_blade)
        target_global = correction @ knife_global
        parent_global = matrices["hand_r"].to_quaternion()
        parent_global.normalize()
        target_local_blender = parent_global.conjugated() @ target_global
        authored = blender_to_authored(target_local_blender)
        if previous is not None and previous.dot(authored) < 0.0:
            authored.negate()
        previous = authored.copy()
        frame["rotation_wxyz"][knife_index] = rounded(authored)
        solved.append(authored.copy())

    dots = []
    grip_distances = []
    steps = []
    for index, frame in enumerate(clip["frames"]):
        matrices = deformation_matrices(
            frame, document["bones"], bone_order, pivots, parents,
            bind_rotations,
        )
        grip = matrices["knife"] @ grip_bind
        tip = matrices["knife"] @ tip_bind
        elbow = matrices["forearm_r"] @ target_to_blender(
            pivots["forearm_r"]
        )
        wrist = matrices["hand_r"] @ target_to_blender(pivots["hand_r"])
        dots.append((tip - grip).normalized().dot(
            (wrist - elbow).normalized()))
        grip_distances.append((grip - wrist).length)
        if index:
            radians = solved[index - 1].rotation_difference(solved[index]).angle
            steps.append(math.degrees(min(radians, math.tau - radians)))
    if max(dots) > -0.995:
        raise RuntimeError(
            f"reverse blade constraint failed: maximum dot {max(dots)}"
        )
    clip["grip"] = "REVERSE_RIGHT_GEOMETRY_SOLVED"
    document["reverse_grip_contract"] = {
        "method": "exact_blade_tip_aligned_wrist_to_elbow_each_frame",
        "seedHalfTurn": "PRE_Y_180",
        "bladeForearmDotMeaning": (
            "-1 points from wrist toward elbow; +1 points away from elbow"),
        "minimumBladeForearmDot": min(dots),
        "maximumBladeForearmDot": max(dots),
        "writesBodyJointRotations": False,
        "writesKnifeGripPosition": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    report = {
        "schema": 1,
        "clip": args.clip,
        "frames": len(clip["frames"]),
        "minimumBladeForearmDot": min(dots),
        "maximumBladeForearmDot": max(dots),
        "maximumGripToWristModelUnits": max(grip_distances),
        "maximumKnifeRotationStepDegrees": max(steps, default=0.0),
        "bodyJointRotationsModified": False,
        "knifePositionModified": False,
        "result": "PASS",
        "automaticVisualApproval": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
