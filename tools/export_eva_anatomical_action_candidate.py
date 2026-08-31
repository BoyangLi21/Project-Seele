#!/usr/bin/env python3
"""Export one anatomical EVA Blender action as a Tiger review motion clip.

The source action must already be retargeted onto ``EVA_ANATOMICAL_ARMATURE``.
This bridge solves the actual rigid Tiger part transforms rather than copying
source Euler channels.  The resulting database remains review-only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_eva_motion_lab_3d import runtime_pivot, target_to_blender


MODEL_UNITS_PER_SOURCE_METRE = 112.0
SOURCE_BONES = (
    "root", "torso_lower", "torso_upper", "aim_pitch", "head",
    "arm_l", "forearm_l", "hand_l",
    "arm_r", "forearm_r", "hand_r",
    "leg_l", "shin_l", "foot_l",
    "leg_r", "shin_r", "foot_r",
)
BLENDER_RUNTIME_BASIS = Matrix((
    (1.0, 0.0, 0.0),
    (0.0, 0.0, -1.0),
    (0.0, 1.0, 0.0),
))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--contacts", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--rig", default="EVA_ANATOMICAL_ARMATURE")
    parser.add_argument("--rigid-mesh", default="EVA_ANATOMICAL_RIGID_MESH")
    parser.add_argument("--display-scale", type=float, default=0.05)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def rounded_quaternion(value: Quaternion) -> list[float]:
    value.normalize()
    return [round(float(value.w), 7), round(float(value.x), 7),
            round(float(value.y), 7), round(float(value.z), 7)]


def blender_to_authored(value: Quaternion) -> Quaternion:
    value.normalize()
    runtime = (BLENDER_RUNTIME_BASIS.inverted()
               @ value.to_matrix()
               @ BLENDER_RUNTIME_BASIS)
    euler = runtime.to_euler("XYZ")
    authored = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_quaternion()
    authored.normalize()
    return authored


def rigid_fit(source_points, target_points) -> tuple[Matrix, float, float]:
    source = np.asarray(source_points, dtype=np.float64)
    target = np.asarray(target_points, dtype=np.float64)
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    covariance = (source - source_center).T @ (target - target_center)
    left, _, right = np.linalg.svd(covariance)
    rotation = right.T @ left.T
    if np.linalg.det(rotation) < 0.0:
        right[-1, :] *= -1.0
        rotation = right.T @ left.T
    translation = target_center - rotation @ source_center
    matrix = Matrix.Identity(4)
    for row in range(3):
        for column in range(3):
            matrix[row][column] = float(rotation[row, column])
        matrix[row][3] = float(translation[row])
    fitted = (rotation @ source.T).T + translation
    errors = np.linalg.norm(fitted - target, axis=1)
    return (matrix, float(np.sqrt(np.mean(errors * errors))),
            float(errors.max()))


def nearest_rigid_fit(source_points, target_points) -> tuple[
        Matrix, float, float]:
    """Rigid ICP fallback for a mesh part whose semantic face count changed."""
    source = np.asarray(source_points, dtype=np.float64)
    target = np.asarray(target_points, dtype=np.float64)
    transform = Matrix.Identity(4)
    for _ in range(8):
        rotation = np.asarray([
            list(transform[row][:3]) for row in range(3)
        ], dtype=np.float64)
        translation = np.asarray(transform.translation, dtype=np.float64)
        moved = (rotation @ source.T).T + translation
        distances = np.linalg.norm(
            moved[:, None, :] - target[None, :, :], axis=2)
        matched = target[np.argmin(distances, axis=1)]
        transform, _, _ = rigid_fit(source, matched)
    rotation = np.asarray([
        list(transform[row][:3]) for row in range(3)
    ], dtype=np.float64)
    translation = np.asarray(transform.translation, dtype=np.float64)
    moved = (rotation @ source.T).T + translation
    errors = np.min(np.linalg.norm(
        moved[:, None, :] - target[None, :, :], axis=2), axis=1)
    return (transform, float(np.sqrt(np.mean(errors * errors))),
            float(errors.max()))


def main() -> None:
    args = parse_args()
    rig = bpy.data.objects.get(args.rig)
    target_mesh = bpy.data.objects.get(args.rigid_mesh)
    if rig is None or rig.type != "ARMATURE" or target_mesh is None:
        raise RuntimeError("anatomical EVA rig or rigid mesh is missing")
    if rig.animation_data is None or rig.animation_data.action is None:
        raise RuntimeError("anatomical EVA rig has no active action")
    missing = set(SOURCE_BONES) - set(rig.pose.bones.keys())
    if missing:
        raise RuntimeError("anatomical action is missing bones: "
                           + ", ".join(sorted(missing)))

    geometry = json.loads(args.geo.read_text(
        encoding="utf-8"))["minecraft:geometry"][0]["bones"]
    parents = {row["name"]: row.get("parent") for row in geometry}
    pivots = {
        row["name"]: runtime_pivot(row.get("pivot", (0.0, 0.0, 0.0)))
        for row in geometry
    }
    mesh = json.loads(args.mesh.read_text(encoding="utf-8"))
    stride = int(mesh.get("stride", 0))
    if stride != 8:
        raise RuntimeError("expected stride-8 Tiger mesh")
    pretransforms = {}
    rest_fit = {}
    target_groups = {
        group.name: group.index for group in target_mesh.vertex_groups
    }
    for bone_name, part in mesh["parts"].items():
        pivot = runtime_pivot(part["pivot"])
        values = [float(value) for value in part["vertices"]]
        source_points = []
        for offset in range(0, len(values), stride):
            local = Vector((-values[offset], values[offset + 1],
                            values[offset + 2]))
            source_points.append(tuple(target_to_blender(
                pivot + local) * args.display_scale))
        if bone_name not in target_groups:
            continue
        group_index = target_groups[bone_name]
        target_points = [
            tuple(vertex.co) for vertex in target_mesh.data.vertices
            if any(link.group == group_index and link.weight > 0.5
                   for link in vertex.groups)
        ]
        if not target_points:
            raise RuntimeError(f"empty anatomical vertex group {bone_name}")
        if len(source_points) == len(target_points):
            transform, rms, maximum = rigid_fit(
                source_points, target_points)
            fit_method = "ordered"
        else:
            transform, rms, maximum = nearest_rigid_fit(
                source_points, target_points)
            fit_method = "nearest_icp"
        pretransforms[bone_name] = transform
        rest_fit[bone_name] = {
            "vertices": len(source_points), "rms": rms,
            "maximum": maximum, "method": fit_method,
            "targetVertices": len(target_points),
        }
    mesh_vertex_count = sum(
        len(part["vertices"]) // stride for part in mesh["parts"].values())
    if mesh_vertex_count != len(target_mesh.data.vertices):
        raise RuntimeError(
            f"Tiger/anatomical vertex mismatch: {mesh_vertex_count} != "
            f"{len(target_mesh.data.vertices)}")

    def exported_parent(name: str) -> str | None:
        parent = parents.get(name)
        while parent is not None and parent not in SOURCE_BONES:
            parent = parents.get(parent)
        return parent

    action = rig.animation_data.action
    first, last = (int(round(value)) for value in action.frame_range)
    scene = bpy.context.scene
    contact_rows = None
    if args.contacts is not None:
        source = np.load(args.contacts)
        contact_rows = np.asarray(source["foot_contact"], dtype=np.bool_)

    frames = []
    previous = None
    maximum_step = 0.0
    maximum_step_location = None
    first_root_residual = None
    for frame in range(first, last + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        desired_global = {}
        desired_rotation = {}
        rotations = []
        for bone_name in SOURCE_BONES:
            target_deformation = (
                rig.pose.bones[bone_name].matrix
                @ rig.data.bones[bone_name].matrix_local.inverted())
            desired = (target_deformation
                       @ pretransforms.get(bone_name, Matrix.Identity(4)))
            desired_global[bone_name] = desired
            global_rotation = desired.to_quaternion()
            global_rotation.normalize()
            desired_rotation[bone_name] = global_rotation
            parent = exported_parent(bone_name)
            parent_rotation = desired_rotation.get(
                parent, Quaternion((1.0, 0.0, 0.0, 0.0)))
            local = parent_rotation.inverted() @ global_rotation
            local.normalize()
            authored = blender_to_authored(local)
            if previous is not None:
                prior = Quaternion(tuple(previous[len(rotations)]))
                if prior.dot(authored) < 0.0:
                    authored.negate()
            rotations.append(rounded_quaternion(authored))

        root_rotation = desired_global["root"].to_quaternion()
        root_rotation.normalize()
        root_pivot = target_to_blender(pivots["root"]) * args.display_scale
        rotation_translation = root_pivot - root_rotation @ root_pivot
        residual = desired_global["root"].translation - rotation_translation
        if first_root_residual is None:
            first_root_residual = residual.copy()
        residual -= first_root_residual
        root_m = [
            round(float(-residual.x)
                  / (args.display_scale * MODEL_UNITS_PER_SOURCE_METRE), 7),
            round(float(residual.z)
                  / (args.display_scale * MODEL_UNITS_PER_SOURCE_METRE), 7),
            round(float(-residual.y)
                  / (args.display_scale * MODEL_UNITS_PER_SOURCE_METRE), 7),
        ]
        if contact_rows is None:
            contacts = [True, True]
        else:
            phase = (frame - first) / max(1, last - first)
            index = int(round(phase * (len(contact_rows) - 1)))
            contacts = [bool(value) for value in contact_rows[index]]
        frames.append({
            "root_m": root_m,
            "rotation_wxyz": rotations,
            "foot_contact": contacts,
        })

        if previous is not None:
            for bone_name, before, after in zip(
                    SOURCE_BONES, previous, rotations):
                radians = Quaternion(tuple(before)).rotation_difference(
                    Quaternion(tuple(after))).angle
                step = math.degrees(min(radians, 2.0 * math.pi - radians))
                if step > maximum_step:
                    maximum_step = step
                    maximum_step_location = {
                        "frame": frame, "bone": bone_name,
                    }
        previous = rotations

    fps = scene.render.fps / scene.render.fps_base
    document = {
        "schema": 2,
        "coordinate_system": "bedrock_x_right_y_up_z_back",
        "quaternion_order": "wxyz",
        "sample_rate": fps,
        "preview_only": True,
        "authority": "anatomical_eva_rigid_part_solve_review_only",
        "sources": [{
            "id": args.source_id,
            "name": args.source_name,
            "url": args.source_url,
            "license": args.license,
        }],
        "bones": list(SOURCE_BONES),
        "clips": {
            args.clip: {
                "duration_seconds": round((len(frames) - 1) / fps, 7),
                "loop": False,
                "role": "raw_mocap_anatomical_retarget_review_only",
                "source_id": args.source_id,
                "frames": frames,
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    report = {
        "schema": 1,
        "sourceAction": action.name,
        "sourceFrames": [first, last],
        "fps": fps,
        "frames": len(frames),
        "meshVertices": mesh_vertex_count,
        "restFitRmsMaximum": max(row["rms"] for row in rest_fit.values()),
        "restFitMaximum": max(
            row["maximum"] for row in rest_fit.values()),
        "maximumRotationStepDegrees": maximum_step,
        "maximumRotationStepLocation": maximum_step_location,
        "status": "raw_review_candidate_not_live",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
