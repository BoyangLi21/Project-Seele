#!/usr/bin/env python3
"""Export reviewed Blender locomotion into the V2 lab-only motion schema."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_eva_motion_lab_3d import runtime_pivot, target_to_blender


SAMPLE_RATE = 60.0
MODEL_UNITS_PER_SOURCE_METRE = 112.0
BONES = (
    "root", "torso_lower", "torso_upper", "head", "aim_pitch",
    "arm_l", "forearm_l", "hand_l",
    "arm_r", "forearm_r", "hand_r",
    "leg_l", "shin_l", "foot_l",
    "leg_r", "shin_r", "foot_r",
)
THUMB_DRIVER = {"finger_thumb_l": "hand_l", "finger_thumb_r": "hand_r"}
BLENDER_RUNTIME_BASIS = Matrix(((1.0, 0.0, 0.0),
                                (0.0, 0.0, -1.0),
                                (0.0, 1.0, 0.0)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--walk-action", required=True)
    parser.add_argument("--run-blend", required=True, type=Path)
    parser.add_argument("--run-action", required=True)
    parser.add_argument("--walk-report", required=True, type=Path)
    parser.add_argument("--run-report", required=True, type=Path)
    parser.add_argument("--mesh", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=0.05)
    parser.add_argument("--skip-loop-closure", action="store_true")
    parser.add_argument("--subtract-gecko-bind", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def load_action(path: Path, action_name: str, unique_name: str):
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (
            available, loaded):
        if action_name not in available.actions:
            raise RuntimeError(f"{action_name} missing from {path}")
        loaded.actions = [action_name]
    action = loaded.actions[0]
    action.name = unique_name
    return action


def rigid_fit(source_points, target_points):
    source = np.asarray(source_points, dtype=float)
    target = np.asarray(target_points, dtype=float)
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
    return matrix, float(np.sqrt(np.mean(errors * errors))), float(errors.max())


def rounded_quaternion(value: Quaternion) -> list[float]:
    value.normalize()
    return [round(float(value.w), 7), round(float(value.x), 7),
            round(float(value.y), 7), round(float(value.z), 7)]


def blender_to_authored(value: Quaternion) -> Quaternion:
    """Invert build_eva_motion_lab_3d.quaternion_to_blender exactly."""
    value.normalize()
    runtime = (BLENDER_RUNTIME_BASIS.inverted()
               @ value.to_matrix()
               @ BLENDER_RUNTIME_BASIS)
    euler = runtime.to_euler("XYZ")
    authored = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_quaternion()
    authored.normalize()
    return authored


def close_loop(frames: list[dict]) -> None:
    if len(frames) < 3:
        return
    last_index = len(frames) - 1
    identity = Quaternion((1.0, 0.0, 0.0, 0.0))
    for bone_index in range(len(frames[0]["rotation_wxyz"])):
        first = Quaternion(tuple(frames[0]["rotation_wxyz"][bone_index]))
        last = Quaternion(tuple(frames[-1]["rotation_wxyz"][bone_index]))
        correction = last.conjugated() @ first
        correction.normalize()
        for frame_index, frame in enumerate(frames):
            amount = frame_index / last_index
            partial = identity.slerp(correction, amount)
            current = Quaternion(tuple(frame["rotation_wxyz"][bone_index]))
            closed = current @ partial
            closed.normalize()
            frame["rotation_wxyz"][bone_index] = rounded_quaternion(closed)
    root_delta = [
        float(frames[-1]["root_m"][axis])
        - float(frames[0]["root_m"][axis])
        for axis in range(3)
    ]
    for frame_index, frame in enumerate(frames):
        amount = frame_index / last_index
        frame["root_m"] = [
            round(float(frame["root_m"][axis])
                  - root_delta[axis] * amount, 7)
            for axis in range(3)
        ]
    frames[-1]["foot_contact"] = list(frames[0]["foot_contact"])


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    target = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    target_mesh = bpy.data.objects["EVA_ANATOMICAL_RIGID_MESH"]
    walk_action = bpy.data.actions.get(args.walk_action)
    if walk_action is None:
        raise RuntimeError(f"missing walk action {args.walk_action}")
    run_action = load_action(args.run_blend, args.run_action,
                             "EXPORT_GROUNDED_RUN")
    reports = {
        "grounded_walk": json.loads(args.walk_report.read_text(
            encoding="utf-8")),
        "grounded_run": json.loads(args.run_report.read_text(
            encoding="utf-8")),
    }

    geometry = json.loads(args.geo.read_text(
        encoding="utf-8"))["minecraft:geometry"][0]["bones"]
    by_name = {row["name"]: row for row in geometry}
    parents = {row["name"]: row.get("parent") for row in geometry}

    mesh_payload = json.loads(args.mesh.read_text(encoding="utf-8"))
    if int(mesh_payload.get("stride", 0)) != 8:
        raise RuntimeError("expected stride-8 rigid mesh")
    cursor = 0
    pretransforms = {}
    rest_fit = {}
    for bone_name, part in mesh_payload["parts"].items():
        pivot = runtime_pivot(part["pivot"])
        values = [float(value) for value in part["vertices"]]
        source_points = []
        target_points = []
        for offset in range(0, len(values), 8):
            local = Vector((-values[offset], values[offset + 1],
                            values[offset + 2]))
            source_points.append(tuple(target_to_blender(
                pivot + local) * args.scale))
            target_points.append(tuple(target_mesh.data.vertices[cursor].co))
            cursor += 1
        transform, rms, maximum = rigid_fit(source_points, target_points)
        pretransforms[bone_name] = transform
        rest_fit[bone_name] = {"rms": rms, "maximum": maximum,
                               "vertices": len(source_points)}
    if cursor != len(target_mesh.data.vertices):
        raise RuntimeError(
            f"mesh revision mismatch: json={cursor} blend="
            f"{len(target_mesh.data.vertices)}")

    def exported_parent(name: str) -> str | None:
        parent = parents.get(name)
        while parent is not None and parent not in BONES:
            parent = parents.get(parent)
        return parent

    def solve_authored_rotations(heading_matrix: Matrix) -> tuple[
            list[list[float]], dict, Matrix]:
        """Solve local runtime rotations from actual rigid-part transforms.

        ``pretransforms`` maps each authored runtime part into the anatomical
        rest mesh.  The target pose deformation then maps that anatomical rest
        part into its evaluated frame position.  Their product is therefore
        the complete desired global deformation of the original runtime part.
        Extracting local rotations from those global transforms avoids the
        temporary-armature basis/roll ambiguity that mirrored and folded the
        first exporter revision.
        """
        desired_global: dict[str, Matrix] = {}
        desired_rotation: dict[str, Quaternion] = {}
        local_residuals = {}
        rotations = []
        for name in BONES:
            driver = THUMB_DRIVER.get(name, name)
            if driver not in target.pose.bones:
                raise RuntimeError(f"target action has no driver for {name}")
            target_deformation = (
                target.pose.bones[driver].matrix
                @ target.data.bones[driver].matrix_local.inverted())
            desired = heading_matrix @ target_deformation @ pretransforms.get(
                name, Matrix.Identity(4))
            desired_global[name] = desired
            global_rotation = desired.to_quaternion()
            global_rotation.normalize()
            desired_rotation[name] = global_rotation

            parent = exported_parent(name)
            parent_rotation = desired_rotation.get(
                parent, Quaternion((1.0, 0.0, 0.0, 0.0)))
            local_blender = parent_rotation.inverted() @ global_rotation
            local_blender.normalize()
            rotations.append(rounded_quaternion(
                blender_to_authored(local_blender)))

            pivot = target_to_blender(runtime_pivot(
                by_name[name].get("pivot", [0, 0, 0]))) * args.scale
            local = (desired if parent not in desired_global
                     else desired_global[parent].inverted() @ desired)
            expected_translation = pivot - local.to_quaternion() @ pivot
            local_residuals[name] = (0.0 if name == "root" else float(
                (local.translation - expected_translation).length))
        return rotations, local_residuals, desired_global["root"]

    def contact_array(report: dict, frame: int) -> list[bool]:
        output = []
        segments = report["contact_segments"]
        for side in ("l", "r"):
            output.append(any(int(first) <= frame <= int(last)
                              for first, last in segments[side]))
        return output

    def sample_clip(name: str, action, report: dict) -> tuple[dict, dict]:
        target.animation_data.action = action
        start, end = (int(round(value)) for value in action.frame_range)
        authority = ("world_root" if "world_root" in target.pose.bones
                     else "root")
        scene.frame_set(start)
        bpy.context.view_layer.update()
        world_start = target.pose.bones[authority].matrix.translation.copy()
        scene.frame_set(end)
        bpy.context.view_layer.update()
        world_end = target.pose.bones[authority].matrix.translation.copy()
        travel = world_end - world_start
        horizontal_travel = Vector((travel.x, travel.y, 0.0))
        if horizontal_travel.length < 1.0e-8:
            heading_rotation = Quaternion((1.0, 0.0, 0.0, 0.0))
        else:
            heading_rotation = (
                horizontal_travel.normalized().rotation_difference(
                    Vector((0.0, 1.0, 0.0))))
            heading_rotation.normalize()
        heading_matrix = heading_rotation.to_matrix().to_4x4()
        travel = heading_rotation @ travel
        heading_degrees = math.degrees(
            heading_rotation.to_euler("XYZ").z)
        root_travel_m = [
            round(float(-travel.x)
                  / (args.scale * MODEL_UNITS_PER_SOURCE_METRE), 7),
            0.0,
            round(float(-travel.y)
                  / (args.scale * MODEL_UNITS_PER_SOURCE_METRE), 7),
        ]
        frames = []
        local_translation_residuals = {bone: [] for bone in BONES}
        for frame in range(start, end + 1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            rotations, residuals, desired_root = solve_authored_rotations(
                heading_matrix)
            for bone_name, value in residuals.items():
                local_translation_residuals[bone_name].append(value)
            phase = (frame - start) / max(1, end - start)
            root_rotation = desired_root.to_quaternion()
            root_rotation.normalize()
            root_pivot = target_to_blender(runtime_pivot(
                by_name["root"].get("pivot", [0, 0, 0]))) * args.scale
            rotation_translation = (
                root_pivot - root_rotation @ root_pivot)
            residual = (desired_root.translation
                        - travel * phase - rotation_translation)
            root_m = [
                round(float(-residual.x)
                      / (args.scale * MODEL_UNITS_PER_SOURCE_METRE), 7),
                round(float(residual.z)
                      / (args.scale * MODEL_UNITS_PER_SOURCE_METRE), 7),
                round(float(-residual.y)
                      / (args.scale * MODEL_UNITS_PER_SOURCE_METRE), 7),
            ]
            frames.append({
                "root_m": root_m,
                "rotation_wxyz": rotations,
                "foot_contact": contact_array(report, frame),
            })
        before_seam = []
        before_seam_by_bone = {}
        interframe_steps = []
        for bone_index in range(len(BONES)):
            first = Quaternion(tuple(frames[0]["rotation_wxyz"][bone_index]))
            last = Quaternion(tuple(frames[-1]["rotation_wxyz"][bone_index]))
            seam = math.degrees(first.rotation_difference(last).angle)
            before_seam.append(seam)
            before_seam_by_bone[BONES[bone_index]] = seam
            for current_index in range(1, len(frames)):
                previous = Quaternion(tuple(
                    frames[current_index - 1]["rotation_wxyz"][bone_index]))
                current = Quaternion(tuple(
                    frames[current_index]["rotation_wxyz"][bone_index]))
                interframe_steps.append(math.degrees(
                    previous.rotation_difference(current).angle))
        if not args.skip_loop_closure:
            close_loop(frames)
        duration = (len(frames) - 1) / SAMPLE_RATE
        clip = {
            "duration_seconds": round(duration, 7),
            "loop": True,
            "closed_endpoint": not args.skip_loop_closure,
            "heading_normalization_blender_degrees": round(
                heading_degrees, 7),
            "root_travel_m": root_travel_m,
            "frames": frames,
        }
        audit = {
            "action": action.name,
            "source_frames": [start, end],
            "frame_count": len(frames),
            "duration_seconds": duration,
            "root_travel_m": root_travel_m,
            "heading_normalization_blender_degrees": heading_degrees,
            "preclosure_rotation_seam_max_degrees": max(before_seam),
            "preclosure_rotation_seam_by_bone_degrees":
                before_seam_by_bone,
            "interframe_rotation_step_p95_degrees": float(
                np.percentile(interframe_steps, 95.0)),
            "interframe_rotation_step_maximum_degrees": max(
                interframe_steps),
            "postclosure_rotation_seam_max_degrees": max(
                math.degrees(Quaternion(tuple(
                    frames[0]["rotation_wxyz"][index])).rotation_difference(
                        Quaternion(tuple(frames[-1]["rotation_wxyz"][index]))).angle)
                for index in range(len(BONES))),
            "local_translation_residual_maximum": max(
                max(values) for values in local_translation_residuals.values()),
            "local_translation_residual_by_bone": {
                bone: max(values)
                for bone, values in local_translation_residuals.items()
            },
        }
        return clip, audit

    clips = {}
    audits = {}
    for semantic, action in (("grounded_walk", walk_action),
                             ("grounded_run", run_action)):
        clips[semantic], audits[semantic] = sample_clip(
            semantic, action, reports[semantic])
    idle_frame = copy.deepcopy(clips["grounded_walk"]["frames"][0])
    idle_frame["root_m"] = [0.0, 0.0, 0.0]
    idle_frame["foot_contact"] = [True, True]
    clips["idle"] = {
        "duration_seconds": round(1.0 / SAMPLE_RATE, 7),
        "loop": True,
        "closed_endpoint": True,
        "root_travel_m": [0.0, 0.0, 0.0],
        "frames": [copy.deepcopy(idle_frame), copy.deepcopy(idle_frame)],
    }
    payload = {
        "schema": 2,
        "coordinate_system": "bedrock_x_right_y_up_z_back",
        "quaternion_order": "wxyz",
        "sample_rate": SAMPLE_RATE,
        "sources": [{
            "name": "100STYLE strict allowlist (BentKnees)",
            "url": "https://www.ianxmason.com/100style/",
            "license": "CC-BY-4.0",
            "modifications": [
                "official frame cut", "cycle selection", "EVA retarget",
                "contact IK", "pelvis load response", "swing clearance",
                "runtime rigid-part solve",
            ],
        }],
        "bones": list(BONES),
        "clips": clips,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False,
                                      separators=(",", ":")) + "\n",
                           encoding="utf-8")
    audit_payload = {
        "schema": 1,
        "mesh_vertices": cursor,
        "rest_fit_maximum": max(
            row["maximum"] for row in rest_fit.values()),
        "rest_fit_rms_maximum": max(row["rms"] for row in rest_fit.values()),
        "actions": audits,
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit_payload, indent=2) + "\n",
                          encoding="utf-8")
    print(json.dumps(audit_payload, indent=2))


if __name__ == "__main__":
    main()
