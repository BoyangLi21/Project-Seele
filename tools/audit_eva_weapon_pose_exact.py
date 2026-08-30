#!/usr/bin/env python3
"""Measure exact two-hand grip and forward-axis constraints in Blender."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_motion_lab_3d import load_geo, target_to_blender
from audit_eva_motion_lab_exact import ranges_from_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gap-frames", type=int, default=16)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def joint(name: str) -> Vector:
    return bpy.data.objects[f"JOINT::{name}"].matrix_world.translation


def transformed_point(part: bpy.types.Object, point: Vector) -> Vector:
    return part.matrix_world @ point


def cosine(first: Vector, second: Vector) -> float:
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return -1.0
    return first.normalized().dot(second.normalized())


def surface_distance(first: bpy.types.Object,
                     second: bpy.types.Object) -> float:
    tree = KDTree(len(second.data.vertices))
    for index, vertex in enumerate(second.data.vertices):
        tree.insert(second.matrix_world @ vertex.co, index)
    tree.balance()
    return min(tree.find(first.matrix_world @ vertex.co)[2]
               for vertex in first.data.vertices)


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    motion_hash = hashlib.sha256(args.motion_db.read_bytes()).hexdigest()
    if bpy.context.scene.get("motion_db_sha256") != motion_hash:
        raise SystemExit("weapon lab motion database hash mismatch")
    _bones, pivots, _parents = load_geo(args.geo)
    ranges = ranges_from_db(motion, args.gap_frames)
    failures = []
    reports = {}
    for clip_name, (start, end) in ranges.items():
        weapon_name = ("knife" if "knife" in clip_name
                       else "cannon" if ("rifle" in clip_name
                                          or "cannon" in clip_name)
                       else "lance" if "lance" in clip_name else None)
        if weapon_name is None:
            continue
        part = bpy.data.objects[f"PART::{weapon_name}"]
        pivot = target_to_blender(pivots[weapon_name])
        guide_offset = (-24.0 if weapon_name == "cannon"
                        else -34.0 if weapon_name == "lance" else 0.0)
        guide = target_to_blender(
            pivots[weapon_name] + Vector((0.0, guide_offset, 0.0))
        )
        # Both current weapon meshes are authored muzzle/fork-forward on local
        # -Y, which is Blender rest -Z after coordinate conversion.
        muzzle = min(part.data.vertices, key=lambda vertex: vertex.co.z).co
        length = max(1, end - start)
        sample_frames = sorted({start, end, start + length // 4,
                                start + length // 2,
                                start + length * 3 // 4})
        samples = []
        clip_failures = []
        for frame in sample_frames:
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            rear = transformed_point(part, pivot)
            forward_grip = transformed_point(part, guide)
            muzzle_world = transformed_point(part, muzzle)
            right_distance = (joint("hand_r") - rear).length
            left_distance = (joint("hand_l") - forward_grip).length
            left_local = part.matrix_world.inverted() @ joint("hand_l")
            axis_offset = left_local.z - pivot.z
            axis_point = pivot + Vector((0.0, 0.0, axis_offset))
            axis_radial_distance = (left_local - axis_point).length
            weapon_axis = muzzle_world - rear
            root_forward = (bpy.data.objects["JOINT::root"].matrix_world
                            .to_3x3() @ Vector((0.0, 1.0, 0.0)))
            alignment = cosine(weapon_axis, root_forward)
            right_surface = surface_distance(
                bpy.data.objects["PART::hand_r"], part
            )
            left_surface = surface_distance(
                bpy.data.objects["PART::hand_l"], part
            )
            samples.append({
                "frame": frame,
                "right_rear_grip_distance": right_distance,
                "left_forward_grip_distance": left_distance,
                "left_axis_offset_model_pixels": axis_offset,
                "left_axis_radial_distance": axis_radial_distance,
                "forward_axis_cosine": alignment,
                "right_hand_surface_distance": right_surface,
                "left_hand_surface_distance": left_surface,
            })
            # Display scale is 0.05, so 0.30 Blender units equals six model
            # pixels. The final solver will target a stricter two-pixel gate.
            if right_surface > 0.12:
                clip_failures.append(
                    f"frame {frame}: right surface distance {right_surface:.3f}"
                )
            if weapon_name != "knife" and left_surface > 0.12:
                clip_failures.append(
                    f"frame {frame}: left surface distance {left_surface:.3f}"
                )
            if (weapon_name != "knife"
                    and alignment < math.cos(math.radians(18.0))):
                clip_failures.append(
                    f"frame {frame}: weapon axis cosine {alignment:.4f}"
                )
        clip_failures = sorted(set(clip_failures))
        reports[clip_name] = {
            "weapon": weapon_name,
            "sample_frames": samples,
            "failures": clip_failures,
        }
        failures.extend(f"{clip_name}: {failure}"
                        for failure in clip_failures)
    report = {
        "schema": 1,
        "authority": "exact_blender_weapon_mesh_and_hand_joints",
        "motion_db_sha256": motion_hash,
        "clip_count": len(reports),
        "failure_count": len(failures),
        "failures": failures,
        "clips": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA weapon pose audit: clips={len(reports)} "
        f"failures={len(failures)} output={args.output}"
    )
    if args.strict and failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
