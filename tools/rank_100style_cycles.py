#!/usr/bin/env python3
"""Rank 100STYLE gait cycles for symmetry, straightness, and joint stability."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--cycle-analysis", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cut-start", type=int)
    parser.add_argument("--cut-end", type=int)
    parser.add_argument("--mode", choices=("walk", "run"), required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def world_head(armature: bpy.types.Object, name: str) -> Vector:
    return armature.matrix_world @ armature.pose.bones[name].head


def unwrap(values: list[float]) -> list[float]:
    result = [values[0]]
    for value in values[1:]:
        while value - result[-1] > math.pi:
            value -= math.tau
        while value - result[-1] < -math.pi:
            value += math.tau
        result.append(value)
    return result


def percentile(values: list[float], amount: float) -> float:
    return float(np.percentile(np.asarray(values), amount)) if values else 0.0


def main() -> None:
    args = parse_args()
    analysis = json.loads(args.cycle_analysis.read_text(encoding="utf-8"))
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_anim.bvh(
        filepath=str(args.source.resolve()), target="ARMATURE",
        global_scale=0.1, frame_start=1, use_fps_scale=False,
        update_scene_fps=True, update_scene_duration=True,
        rotate_mode="NATIVE", axis_forward="-Z", axis_up="Y",
    )
    armature = next(obj for obj in bpy.context.scene.objects
                    if obj.type == "ARMATURE")
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    first = max(scene.frame_start, args.cut_start or scene.frame_start)
    last = min(scene.frame_end, args.cut_end or scene.frame_end)
    frames = list(range(first, last + 1))

    roots = []
    heads = []
    hips = {"l": [], "r": []}
    knees = {"l": [], "r": []}
    ankles = {"l": [], "r": []}
    facings = []
    seam_bones = (
        "Chest", "Chest2", "Chest3", "Chest4", "Neck", "Head",
        "LeftShoulder", "LeftElbow", "LeftWrist",
        "RightShoulder", "RightElbow", "RightWrist",
        "LeftHip", "LeftKnee", "LeftAnkle",
        "RightHip", "RightKnee", "RightAnkle",
    )
    local_rotations = {name: [] for name in seam_bones}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        root = world_head(armature, "Hips")
        head = world_head(armature, "Head")
        roots.append(root)
        heads.append(head)
        for side, label in (("l", "Left"), ("r", "Right")):
            hips[side].append(world_head(armature, f"{label}Hip"))
            knees[side].append(world_head(armature, f"{label}Knee"))
            ankles[side].append(world_head(armature, f"{label}Ankle"))
        lateral = hips["r"][-1] - hips["l"][-1]
        lateral.z = 0.0
        if lateral.length < 1.0e-8:
            lateral = Vector((1.0, 0.0, 0.0))
        lateral.normalize()
        forward = Vector((-lateral.y, lateral.x, 0.0))
        facings.append(math.atan2(forward.x, -forward.y))
        for name in seam_bones:
            rotation = armature.pose.bones[name].matrix_basis.to_quaternion()
            rotation.normalize()
            local_rotations[name].append(rotation.copy())

    height = float(np.median([
        heads[index].z - min(ankles["l"][index].z,
                             ankles["r"][index].z)
        for index in range(len(frames))
    ]))
    frame_to_index = {frame: index for index, frame in enumerate(frames)}
    ranked = []
    for cycle in analysis["cycles"]:
        if not cycle.get("stable"):
            continue
        start_frame = int(cycle["start_frame"])
        end_frame = int(cycle["end_frame"])
        if start_frame < first or end_frame > last:
            continue
        start = frame_to_index[start_frame]
        end = frame_to_index[end_frame]
        if end - start < 3:
            continue
        cycle_roots = roots[start:end + 1]
        displacement = cycle_roots[-1] - cycle_roots[0]
        displacement.z = 0.0
        if displacement.length < 1.0e-8:
            continue
        forward = displacement.normalized()
        up = Vector((0.0, 0.0, 1.0))
        right = forward.cross(up).normalized()
        path_length = sum(
            (cycle_roots[index] - cycle_roots[index - 1]).xy.length
            for index in range(1, len(cycle_roots)))
        straightness = displacement.length / max(path_length, 1.0e-8)

        lateral_lean = []
        forward_lean = []
        pelvis_height = []
        knee_angles = {"l": [], "r": []}
        knee_normals = {"l": [], "r": []}
        for index in range(start, end + 1):
            torso = heads[index] - roots[index]
            torso.normalize()
            lateral_lean.append(math.degrees(math.atan2(
                torso.dot(right), torso.dot(up))))
            forward_lean.append(math.degrees(math.atan2(
                torso.dot(forward), torso.dot(up))))
            pelvis_height.append(roots[index].z / height)
            for side in ("l", "r"):
                upper = hips[side][index] - knees[side][index]
                lower = ankles[side][index] - knees[side][index]
                knee_angles[side].append(math.degrees(upper.angle(lower)))
                normal = (knees[side][index] - hips[side][index]).cross(
                    ankles[side][index] - knees[side][index])
                if normal.length < 1.0e-8:
                    normal = right.copy()
                normal.normalize()
                if knee_normals[side] and normal.dot(
                        knee_normals[side][-1]) < 0.0:
                    normal.negate()
                knee_normals[side].append(normal)

        knee_plane_p95 = {}
        knee_acceleration_p95 = {}
        for side in ("l", "r"):
            plane_speed = [
                math.degrees(knee_normals[side][index - 1].angle(
                    knee_normals[side][index])) * fps
                for index in range(1, len(knee_normals[side]))
            ]
            angle_speed = [
                (knee_angles[side][index] - knee_angles[side][index - 1])
                * fps for index in range(1, len(knee_angles[side]))
            ]
            acceleration = [
                abs(angle_speed[index] - angle_speed[index - 1]) * fps
                for index in range(1, len(angle_speed))
            ]
            knee_plane_p95[side] = percentile(plane_speed, 95.0)
            knee_acceleration_p95[side] = percentile(acceleration, 95.0)

        yaw_values = unwrap(facings[start:end + 1])
        yaw_delta = math.degrees(yaw_values[-1] - yaw_values[0])
        lean_bias = abs(float(np.mean(lateral_lean)))
        lean_p95 = percentile([abs(value) for value in lateral_lean], 95.0)
        knee_asymmetry = abs(
            (max(knee_angles["l"]) - min(knee_angles["l"]))
            - (max(knee_angles["r"]) - min(knee_angles["r"])))
        seam_by_bone = {
            name: math.degrees(local_rotations[name][start]
                               .rotation_difference(
                                   local_rotations[name][end]).angle)
            for name in seam_bones
        }
        seam_values = list(seam_by_bone.values())
        seam_p95 = percentile(seam_values, 95.0)
        seam_maximum = max(seam_values)
        score = (
            lean_bias * 4.0
            + lean_p95 * 1.5
            + abs(yaw_delta) * 0.8
            + max(0.0, 0.985 - straightness) * 500.0
            + max(knee_plane_p95.values()) / 100.0
            + max(knee_acceleration_p95.values()) / 2000.0
            + knee_asymmetry * 0.25
            + seam_p95 * 1.5
            + seam_maximum * 0.5
        )
        ranked.append({
            "cycle_id": cycle["id"],
            "side": cycle["side"],
            "start_frame": start_frame,
            "end_frame": end_frame,
            "duration_seconds": cycle["duration_seconds"],
            "speed_mps": cycle["speed_mps"],
            "straightness": straightness,
            "yaw_delta_degrees": yaw_delta,
            "lateral_lean_mean_degrees": float(np.mean(lateral_lean)),
            "lateral_lean_p95_abs_degrees": lean_p95,
            "forward_lean_mean_degrees": float(np.mean(forward_lean)),
            "pelvis_vertical_range_h": max(pelvis_height) - min(pelvis_height),
            "knee_bend_plane_speed_p95_degrees_per_second": knee_plane_p95,
            "knee_angle_acceleration_p95_degrees_per_second2": (
                knee_acceleration_p95),
            "knee_range_asymmetry_degrees": knee_asymmetry,
            "endpoint_local_rotation_seam_by_bone_degrees": seam_by_bone,
            "endpoint_local_rotation_seam_p95_degrees": seam_p95,
            "endpoint_local_rotation_seam_maximum_degrees": seam_maximum,
            "selection_score": score,
        })
    ranked.sort(key=lambda item: item["selection_score"])
    output = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "mode": args.mode,
        "fps": fps,
        "analysis_cut": [first, last],
        "candidate_count": len(ranked),
        "ranking": ranked,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "candidate_count": len(ranked),
        "top": ranked[:10],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
