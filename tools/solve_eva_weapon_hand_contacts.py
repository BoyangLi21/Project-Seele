#!/usr/bin/env python3
"""Solve support-hand contact against the exact animated weapon mesh."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_eva_motion_lab_exact import ranges_from_db
from build_eva_cmu_motion_candidates import (
    authored_to_runtime_quaternion,
    runtime_to_authored_quaternion,
    runtime_target_pivots,
    target_hand_position,
)
from build_eva_motion_database import (
    clamp,
    load_target_pivots,
    rounded_quaternion,
    solve_target_limb,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gap-frames", type=int, default=16)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def closest_delta(first: bpy.types.Object,
                  second: bpy.types.Object) -> Vector:
    tree = KDTree(len(second.data.vertices))
    for index, vertex in enumerate(second.data.vertices):
        tree.insert(second.matrix_world @ vertex.co, index)
    tree.balance()
    best_distance = float("inf")
    best_delta = Vector((0.0, 0.0, 0.0))
    for vertex in first.data.vertices:
        point = first.matrix_world @ vertex.co
        nearest, _index, distance = tree.find(point)
        if distance < best_distance:
            best_distance = distance
            best_delta = nearest - point
    return best_delta


def blender_to_runtime(vector: Vector) -> Vector:
    return Vector((vector.x, vector.z, -vector.y))


def main() -> None:
    args = parse_args()
    document = json.loads(args.motion_db.read_text(encoding="utf-8"))
    output = copy.deepcopy(document)
    ranges = ranges_from_db(document, args.gap_frames)
    pivots = runtime_target_pivots(load_target_pivots(args.geo))
    bone_indices = {name: index for index, name in enumerate(document["bones"])}
    master_scale = float(bpy.data.objects["EVA_EXACT_ROOT"].scale.x)
    diagnostics = []
    for clip_name, (timeline_start, _timeline_end) in ranges.items():
        if "lance" not in clip_name:
            continue
        clip = output["clips"][clip_name]
        for local_index, frame in enumerate(clip["frames"]):
            bpy.context.scene.frame_set(timeline_start + local_index)
            bpy.context.view_layer.update()
            delta_blender = closest_delta(
                bpy.data.objects["PART::hand_l"],
                bpy.data.objects["PART::lance"],
            ) / max(master_scale, 1.0e-8)
            delta_runtime = blender_to_runtime(delta_blender)
            rotations = {
                name: authored_to_runtime_quaternion(Quaternion(tuple(
                    frame["rotation_wxyz"][index]
                )))
                for name, index in bone_indices.items()
            }
            yaw = float(frame.get("root_yaw_radians", 0.0))
            root_rotation = Quaternion((math.cos(yaw * 0.5), 0.0,
                                        math.sin(yaw * 0.5), 0.0))
            current = target_hand_position(rotations, pivots, "l")
            desired_world = root_rotation @ current + delta_runtime
            body_target = root_rotation.conjugated() @ desired_world
            lower_pivot = pivots["torso_lower"]
            body_target = lower_pivot + rotations["torso_lower"].conjugated() @ (
                body_target - lower_pivot
            )
            upper_pivot = pivots["torso_upper"]
            local_target = upper_pivot + rotations["torso_upper"].conjugated() @ (
                body_target - upper_pivot
            )
            shoulder = pivots["arm_l"]
            elbow = pivots["forearm_l"]
            wrist = pivots["hand_l"]
            vector = local_target - shoulder
            total = (elbow - shoulder).length + (wrist - elbow).length
            direction = vector.normalized()
            reach = clamp(vector.length / total, 0.08, 0.9995)
            current_elbow = shoulder + rotations["arm_l"] @ (elbow - shoulder)
            pole = current_elbow - shoulder
            pole -= direction * pole.dot(direction)
            if pole.length < 1.0e-6:
                pole = Vector((0.0, 0.0, -1.0))
            pole.normalize()
            arm, forearm = solve_target_limb(
                shoulder, elbow, wrist, direction, reach, pole
            )
            for bone_name, rotation in (("arm_l", arm),
                                        ("forearm_l", forearm)):
                frame["rotation_wxyz"][bone_indices[bone_name]] = \
                    rounded_quaternion(runtime_to_authored_quaternion(rotation))
            diagnostics.append({
                "clip": clip_name,
                "frame": local_index,
                "surface_delta_model_pixels": round(delta_runtime.length, 6),
            })
    output["weapon_contact_solve"] = {
        "authority": "exact_mesh_closest_surface_delta_plus_two_bone_ik",
        "frame_count": len(diagnostics),
        "maximum_initial_surface_delta_model_pixels": max(
            (item["surface_delta_model_pixels"] for item in diagnostics),
            default=0.0,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA weapon hand solve: frames={len(diagnostics)} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
