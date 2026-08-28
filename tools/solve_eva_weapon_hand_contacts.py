#!/usr/bin/env python3
"""Solve support-hand contact against the exact animated weapon mesh."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_eva_motion_lab_exact import ranges_from_db
from build_eva_motion_lab_3d import target_to_blender
from build_eva_cmu_motion_candidates import (
    runtime_target_pivots,
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
    parser.add_argument("--align-forward-axis", action="store_true")
    parser.add_argument("--axis-only", action="store_true")
    parser.add_argument("--right-surface-only", action="store_true",
                        help="translate the weapon socket onto the right hand")
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


def closest_point(point: Vector, obj: bpy.types.Object) -> Vector:
    return min((obj.matrix_world @ vertex.co for vertex in obj.data.vertices),
               key=lambda candidate: (candidate - point).length_squared)


def blender_to_runtime(vector: Vector) -> Vector:
    return Vector((vector.x, vector.z, -vector.y))


def blender_to_authored(quat: Quaternion) -> Quaternion:
    """Invert build_eva_motion_lab_3d.quaternion_to_blender."""
    basis = Matrix(((1.0, 0.0, 0.0),
                    (0.0, 0.0, -1.0),
                    (0.0, 1.0, 0.0)))
    runtime = basis.inverted() @ quat.to_matrix() @ basis
    euler = runtime.to_euler("XYZ")
    authored = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_quaternion()
    authored.normalize()
    return authored


def weapon_for_clip(clip_name: str) -> str | None:
    if "lance" in clip_name:
        return "lance"
    if clip_name == "prone_rifle_review":
        return "cannon"
    return None


def main() -> None:
    args = parse_args()
    document = json.loads(args.motion_db.read_text(encoding="utf-8"))
    output = copy.deepcopy(document)
    ranges = ranges_from_db(document, args.gap_frames)
    pivots = runtime_target_pivots(load_target_pivots(args.geo))
    bone_indices = {name: index for index, name in enumerate(document["bones"])}
    master_scale = float(bpy.data.objects["EVA_EXACT_ROOT"].scale.x)
    diagnostics = []
    axis_diagnostics = []
    if args.align_forward_axis:
        for clip_name, (timeline_start, _timeline_end) in ranges.items():
            weapon_name = weapon_for_clip(clip_name)
            if weapon_name is None:
                continue
            clip = output["clips"][clip_name]
            weapon_index = bone_indices[weapon_name]
            part = bpy.data.objects[f"PART::{weapon_name}"]
            for local_index, frame in enumerate(clip["frames"]):
                bpy.context.scene.frame_set(timeline_start + local_index)
                bpy.context.view_layer.update()
                current_global = part.matrix_world.to_quaternion()
                current_axis = current_global @ Vector((0.0, 0.0, -1.0))
                desired_axis = (bpy.data.objects["JOINT::root"].matrix_world
                                .to_quaternion() @ Vector((0.0, 1.0, 0.0)))
                delta = current_axis.rotation_difference(desired_axis)
                desired_global = delta @ current_global
                parent_global = (bpy.data.objects["JOINT::hand_r"].matrix_world
                                 .to_quaternion())
                desired_local = parent_global.conjugated() @ desired_global
                authored = blender_to_authored(desired_local)
                frame["rotation_wxyz"][weapon_index] = rounded_quaternion(
                    authored)
                axis_diagnostics.append({
                    "clip": clip_name,
                    "frame": local_index,
                    "initial_axis_cosine": round(
                        current_axis.normalized().dot(
                            desired_axis.normalized()), 7),
                })
        output["weapon_axis_solve"] = {
            "authority": "exact_mesh_local_axis_to_root_forward",
            "frame_count": len(axis_diagnostics),
            "minimum_initial_axis_cosine": min(
                (item["initial_axis_cosine"] for item in axis_diagnostics),
                default=1.0,
            ),
        }
        if args.axis_only:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(output, ensure_ascii=False,
                           separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            print(
                f"EVA weapon axis solve: frames={len(axis_diagnostics)} "
                f"output={args.output}"
            )
            return
    if args.right_surface_only:
        socket_diagnostics = []
        for clip_name, (timeline_start, _timeline_end) in ranges.items():
            weapon_name = weapon_for_clip(clip_name)
            if weapon_name is None:
                continue
            clip = output["clips"][clip_name]
            weapon_part = bpy.data.objects[f"PART::{weapon_name}"]
            right_hand = bpy.data.objects["PART::hand_r"]
            for local_index, frame in enumerate(clip["frames"]):
                bpy.context.scene.frame_set(timeline_start + local_index)
                bpy.context.view_layer.update()
                delta_world = closest_delta(weapon_part, right_hand)
                parent_rotation = bpy.data.objects[
                    "JOINT::hand_r"].matrix_world.to_quaternion()
                delta = (parent_rotation.conjugated() @ delta_world) / max(
                    master_scale, 1.0e-8)
                authored_delta = Vector((-delta.x, delta.z, -delta.y))
                positions = frame.setdefault("bone_position_xyz", {})
                existing = Vector(tuple(float(value) for value in
                                        positions.get(weapon_name,
                                                      (0.0, 0.0, 0.0))))
                solved = existing + authored_delta
                positions[weapon_name] = [
                    round(float(value), 7) for value in solved]
                socket_diagnostics.append({
                    "clip": clip_name,
                    "frame": local_index,
                    "delta_model_pixels": round(delta.length, 7),
                })
        output["weapon_socket_solve"] = {
            "authority": "exact_mesh_right_hand_to_weapon_surface_delta",
            "frame_count": len(socket_diagnostics),
            "maximum_delta_model_pixels": max(
                (item["delta_model_pixels"]
                 for item in socket_diagnostics), default=0.0),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(output, ensure_ascii=False,
                       separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(
            f"EVA weapon socket solve: frames={len(socket_diagnostics)} "
            f"output={args.output}"
        )
        return
    for clip_name, (timeline_start, _timeline_end) in ranges.items():
        weapon_name = weapon_for_clip(clip_name)
        if weapon_name is None:
            continue
        clip = output["clips"][clip_name]
        for local_index, frame in enumerate(clip["frames"]):
            bpy.context.scene.frame_set(timeline_start + local_index)
            bpy.context.view_layer.update()
            delta_blender = closest_delta(
                bpy.data.objects["PART::hand_l"],
                bpy.data.objects[f"PART::{weapon_name}"],
            ) / max(master_scale, 1.0e-8)
            delta_runtime = blender_to_runtime(delta_blender)
            elbow_world = bpy.data.objects[
                "JOINT::forearm_l"].matrix_world.translation
            wrist_world = bpy.data.objects[
                "JOINT::hand_l"].matrix_world.translation
            weapon_part = bpy.data.objects[f"PART::{weapon_name}"]
            if weapon_name == "lance":
                clavicle_center = bpy.data.objects[
                    "JOINT::clavicle_l"].matrix_world.translation
                clavicle_parent = bpy.data.objects[
                    "JOINT::aim_pitch"].matrix_world.to_quaternion()
                desired_world = closest_point(clavicle_center, weapon_part)
                clavicle_rest = target_to_blender(
                    pivots["arm_l"] - pivots["clavicle_l"])
                desired_clavicle = (clavicle_parent.conjugated()
                                     @ (desired_world - clavicle_center))
                clavicle_rotation = clavicle_rest.rotation_difference(
                    desired_clavicle)
                frame["rotation_wxyz"][bone_indices["clavicle_l"]] = \
                    rounded_quaternion(blender_to_authored(
                        clavicle_rotation))
                parent_rotation = clavicle_parent @ clavicle_rotation
                shoulder_world = (clavicle_center
                                  + parent_rotation @ clavicle_rest
                                  * master_scale)
            else:
                shoulder_world = bpy.data.objects[
                    "JOINT::arm_l"].matrix_world.translation
                parent_rotation = bpy.data.objects[
                    "JOINT::clavicle_l"].matrix_world.to_quaternion()
                guide_local = target_to_blender(
                    pivots[weapon_name] + Vector((0.0, -24.0, 0.0)))
                desired_world = weapon_part.matrix_world @ guide_local
            vector = (parent_rotation.conjugated()
                      @ (desired_world - shoulder_world)) / master_scale
            upper_rest = target_to_blender(
                pivots["forearm_l"] - pivots["arm_l"])
            lower_rest = target_to_blender(
                pivots["hand_l"] - pivots["forearm_l"])
            total = upper_rest.length + lower_rest.length
            direction = vector.normalized()
            reach = clamp(vector.length / total, 0.08, 0.9995)
            current_elbow = (parent_rotation.conjugated()
                             @ (elbow_world - shoulder_world)) / master_scale
            pole = current_elbow
            pole -= direction * pole.dot(direction)
            if pole.length < 1.0e-6:
                pole = Vector((0.0, 0.0, -1.0))
            pole.normalize()
            arm, forearm = solve_target_limb(
                Vector((0.0, 0.0, 0.0)), upper_rest,
                upper_rest + lower_rest, direction, reach, pole
            )
            for bone_name, rotation in (("arm_l", arm),
                                        ("forearm_l", forearm)):
                frame["rotation_wxyz"][bone_indices[bone_name]] = \
                    rounded_quaternion(blender_to_authored(rotation))
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
