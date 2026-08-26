#!/usr/bin/env python3
"""Repair gait contacts through world-root translation, never leg IK."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--source-profile", choices=("100style", "accad"),
                        required=True)
    parser.add_argument("--source-object", required=True)
    parser.add_argument("--source-fps", required=True, type=float)
    parser.add_argument("--foot-blend-frames", type=int, default=4)
    parser.add_argument("--floor-z", type=float, default=0.0)
    parser.add_argument("--flatten-feet", action="store_true")
    parser.add_argument("--vertical-repair", action="store_true")
    parser.add_argument("--close-root-seam", action="store_true")
    parser.add_argument("--root-smoothing-frames", type=int, default=0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def world_head(obj, name: str) -> Vector:
    return obj.matrix_world @ obj.pose.bones[name].head


def contact_segments(values: np.ndarray) -> list[tuple[int, int]]:
    values = values.copy()
    for index in range(1, len(values) - 1):
        if not values[index] and values[index - 1] and values[index + 1]:
            values[index] = True
    segments = []
    first = None
    for index, value in enumerate(values):
        if value and first is None:
            first = index
        if first is not None and (not value or index == len(values) - 1):
            last = index if value and index == len(values) - 1 else index - 1
            if last - first + 1 >= 2:
                segments.append((first, last))
            first = None
    return segments


def fitted_up_normal(points: list[Vector]) -> Vector:
    values = np.asarray(points, dtype=float)
    centered = values - np.mean(values, axis=0)
    _, _, right = np.linalg.svd(centered, full_matrices=False)
    normal = Vector(tuple(right[-1]))
    if normal.z < 0.0:
        normal.negate()
    return normal.normalized()


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    mesh = bpy.data.objects["EVA_ANATOMICAL_RIGID_MESH"]
    source = bpy.data.objects[args.source_object]
    action = rig.animation_data.action
    if "world_root" not in rig.pose.bones:
        raise RuntimeError("world_root is required for root-only repair")
    source_names = ({
        "head": "Head", "left_foot": "LeftAnkle",
        "left_toe": "LeftToe", "right_foot": "RightAnkle",
        "right_toe": "RightToe",
    } if args.source_profile == "100style" else {
        "head": "Head", "left_foot": "LeftFoot",
        "left_toe": "LeftToeBase", "right_foot": "RightFoot",
        "right_toe": "RightToeBase",
    })
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    source_points = {"l": [], "r": []}
    source_heights = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        floor_points = []
        for side, label in (("l", "left"), ("r", "right")):
            ankle = world_head(source, source_names[f"{label}_foot"])
            toe = world_head(source, source_names[f"{label}_toe"])
            source_points[side].append(np.asarray(ankle, dtype=float))
            floor_points.append(min(ankle.z, toe.z))
        source_heights.append(
            world_head(source, source_names["head"]).z
            - min(floor_points))
    source_height = float(np.median(source_heights))
    dt = 1.0 / args.source_fps
    contacts = {}
    segments = {}
    for side in ("l", "r"):
        points = np.asarray(source_points[side])
        floor = float(np.percentile(points[:, 2], 2.0))
        low = points[:, 2] <= floor + 0.03 * source_height
        speed = np.zeros(len(points), dtype=float)
        if len(points) > 1:
            steps = np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1)
            speed[1:] = steps / dt
            speed[:-1] = np.minimum(
                np.where(speed[:-1] == 0.0, np.inf, speed[:-1]),
                steps / dt)
            speed[np.isinf(speed)] = 0.0
        contacts[side] = low & (speed <= 0.25 * source_height)
        segments[side] = contact_segments(contacts[side])
        contacts[side][:] = False
        for first, last in segments[side]:
            contacts[side][first:last + 1] = True

    world_root = rig.pose.bones["world_root"]
    root_matrices = []
    ankle_positions = {"l": [], "r": []}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        root_matrices.append(world_root.matrix.copy())
        for side in ("l", "r"):
            ankle_positions[side].append(world_head(rig, f"foot_{side}"))

    planar_samples: list[list[Vector]] = [[] for _ in frames]
    for side in ("l", "r"):
        for first, last in segments[side]:
            anchor = ankle_positions[side][first].copy()
            for index in range(first, last + 1):
                correction = anchor - ankle_positions[side][index]
                correction.z = 0.0
                planar_samples[index].append(correction)
    known = np.asarray([bool(values) for values in planar_samples])
    planar = np.zeros((len(frames), 2), dtype=float)
    for index, values in enumerate(planar_samples):
        if values:
            average = sum(values, Vector((0.0, 0.0, 0.0))) / len(values)
            planar[index] = (average.x, average.y)
    known_indices = np.flatnonzero(known)
    if known_indices.size == 0:
        raise RuntimeError("source action contains no contact frames")
    all_indices = np.arange(len(frames))
    for axis in range(2):
        planar[:, axis] = np.interp(
            all_indices, known_indices, planar[known_indices, axis])
    if args.close_root_seam:
        seam_delta = planar[-1] - planar[0]
        phase = np.linspace(0.0, 1.0, len(frames))[:, None]
        planar -= phase * seam_delta
    smoothing_radius = max(0, args.root_smoothing_frames)
    if smoothing_radius > 0:
        offsets = np.arange(-smoothing_radius, smoothing_radius + 1)
        sigma = max(1.0, smoothing_radius * 0.45)
        kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
        kernel /= np.sum(kernel)
        for axis in range(2):
            padded = np.pad(planar[:, axis], smoothing_radius, mode="wrap")
            planar[:, axis] = np.convolve(
                padded, kernel, mode="valid")
        if args.close_root_seam:
            planar[-1] = planar[0]

    world_root.rotation_mode = "QUATERNION"
    corrected_root = []
    for index, frame in enumerate(frames):
        scene.frame_set(frame)
        matrix = root_matrices[index].copy()
        matrix.translation += Vector((planar[index, 0],
                                      planar[index, 1], 0.0))
        world_root.matrix = matrix
        world_root.keyframe_insert("location", frame=frame)
        world_root.keyframe_insert("rotation_quaternion", frame=frame)
        world_root.keyframe_insert("scale", frame=frame)
        corrected_root.append(matrix.copy())

    foot_indices = {}
    sole_indices = {}
    for side in ("l", "r"):
        group = mesh.vertex_groups[f"foot_{side}"].index
        foot_indices[side] = [
            vertex.index for vertex in mesh.data.vertices
            if any(item.group == group for item in vertex.groups)]
        sole_indices[side] = sorted(
            foot_indices[side],
            key=lambda index: mesh.data.vertices[index].co.z)[:36]

    blend = max(0, args.foot_blend_frames)
    weights = {"l": np.asarray(contacts["l"], dtype=float),
               "r": np.asarray(contacts["r"], dtype=float)}
    if not args.flatten_feet:
        weights = {"l": np.zeros(len(frames), dtype=float),
                   "r": np.zeros(len(frames), dtype=float)}
    for side in ("l", "r"):
        for first, last in segments[side]:
            for offset in range(1, blend + 1):
                weight = smoothstep(1.0 - offset / (blend + 1.0))
                if first - offset >= 0:
                    weights[side][first - offset] = max(
                        weights[side][first - offset], weight)
                if last + offset < len(frames):
                    weights[side][last + offset] = max(
                        weights[side][last + offset], weight)

    for side in ("l", "r"):
        foot = rig.pose.bones[f"foot_{side}"]
        original_matrices = []
        normals = []
        for frame in frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            original_matrices.append(foot.matrix.copy())
            evaluated = mesh.evaluated_get(
                bpy.context.evaluated_depsgraph_get())
            points = [evaluated.matrix_world
                      @ evaluated.data.vertices[index].co
                      for index in sole_indices[side]]
            normals.append(fitted_up_normal(points))
        foot.rotation_mode = "QUATERNION"
        for index, frame in enumerate(frames):
            scene.frame_set(frame)
            matrix = original_matrices[index].copy()
            current = matrix.to_quaternion()
            flat = normals[index].rotation_difference(
                Vector((0.0, 0.0, 1.0))) @ current
            desired = current.slerp(flat, float(weights[side][index]))
            desired.normalize()
            result = desired.to_matrix().to_4x4()
            result.translation = matrix.translation
            foot.matrix = result
            foot.keyframe_insert("location", frame=frame)
            foot.keyframe_insert("rotation_quaternion", frame=frame)
            foot.keyframe_insert("scale", frame=frame)

    vertical = np.zeros(len(frames), dtype=float)
    if args.vertical_repair:
        vertical_samples: list[list[float]] = [[] for _ in frames]
        for index, frame in enumerate(frames):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            evaluated = mesh.evaluated_get(
                bpy.context.evaluated_depsgraph_get())
            for side in ("l", "r"):
                if not contacts[side][index]:
                    continue
                sole_z = min((evaluated.matrix_world
                              @ evaluated.data.vertices[vertex].co).z
                             for vertex in sole_indices[side])
                vertical_samples[index].append(args.floor_z - sole_z)
        vertical_known = np.asarray(
            [bool(values) for values in vertical_samples])
        for index, values in enumerate(vertical_samples):
            if values:
                vertical[index] = float(np.mean(values))
        vertical_indices = np.flatnonzero(vertical_known)
        vertical[:] = np.interp(
            all_indices, vertical_indices, vertical[vertical_indices])
        if args.close_root_seam:
            vertical -= np.linspace(0.0, 1.0, len(frames)) * (
                vertical[-1] - vertical[0])
    for index, frame in enumerate(frames):
        scene.frame_set(frame)
        matrix = corrected_root[index].copy()
        matrix.translation.z += vertical[index]
        world_root.matrix = matrix
        world_root.keyframe_insert("location", frame=frame)
        world_root.keyframe_insert("rotation_quaternion", frame=frame)
        world_root.keyframe_insert("scale", frame=frame)

    for curve in action.fcurves:
        if ('pose.bones["world_root"]' not in curve.data_path
                and 'pose.bones["foot_' not in curve.data_path):
            continue
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"

    height = float(mesh.dimensions.z)
    correction_lengths = np.linalg.norm(planar, axis=1)
    report = {
        "schema": 1,
        "authority": "world_root_translation_plus_foot_roll_only",
        "source_profile": args.source_profile,
        "source_object": source.name,
        "frames": [frames[0], frames[-1]],
        "source_fps": args.source_fps,
        "contact_segments": {
            side: [[frames[first], frames[last]]
                   for first, last in segments[side]]
            for side in ("l", "r")},
        "maximum_planar_root_correction_h": float(
            np.max(correction_lengths) / height),
        "root_correction_seam_h": float(
            np.linalg.norm(planar[-1] - planar[0]) / height),
        "maximum_vertical_root_correction_h": float(
            np.max(np.abs(vertical)) / height),
        "joint_rotations_modified": (
            ["foot_l", "foot_r"] if args.flatten_feet else []),
        "flatten_feet": args.flatten_feet,
        "vertical_repair": args.vertical_repair,
        "close_root_seam": args.close_root_seam,
        "root_smoothing_frames": smoothing_radius,
        "leg_ik_used": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
