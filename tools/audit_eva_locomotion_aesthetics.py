#!/usr/bin/env python3
"""Measure EVA locomotion symmetry, knee stability, and load response in 3D."""

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
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fps", type=float, default=60.0)
    parser.add_argument("--source-profile", choices=("100style", "accad"),
                        default="100style")
    parser.add_argument("--source-object")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def quantile(values: list[float], amount: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), amount * 100.0))


def world_head(obj: bpy.types.Object, name: str) -> Vector:
    return obj.matrix_world @ obj.pose.bones[name].head


def joint_angle(a: Vector, b: Vector, c: Vector) -> float:
    first = a - b
    second = c - b
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return 0.0
    return math.degrees(first.angle(second))


def contact_mask(points: np.ndarray, heights: np.ndarray,
                 height: float, fps: float) -> np.ndarray:
    floor = float(np.percentile(heights, 2.0))
    low = heights <= floor + 0.03 * height
    speed = np.zeros(len(points), dtype=float)
    if len(points) > 1:
        steps = np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1) * fps
        speed[1:] = steps
        speed[:-1] = np.minimum(
            np.where(speed[:-1] == 0.0, np.inf, speed[:-1]), steps)
        speed[np.isinf(speed)] = 0.0
    result = low & (speed <= 0.25 * height)
    for index in range(1, len(result) - 1):
        if not result[index] and result[index - 1] and result[index + 1]:
            result[index] = True
    return result


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    source = (bpy.data.objects[args.source_object]
              if args.source_object else next(
                  obj for obj in bpy.data.objects
                  if obj.type == "ARMATURE" and obj != rig))
    source_names = ({
        "head": "Head", "left_foot": "LeftAnkle",
        "left_toe": "LeftToe", "right_foot": "RightAnkle",
        "right_toe": "RightToe",
    } if args.source_profile == "100style" else {
        "head": "Head", "left_foot": "LeftFoot",
        "left_toe": "LeftToeBase", "right_foot": "RightFoot",
        "right_toe": "RightToeBase",
    })
    authority_root = ("world_root" if "world_root" in rig.pose.bones
                      else "root")
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    samples = []
    source_feet = {"l": [], "r": []}
    source_foot_heights = {"l": [], "r": []}
    source_heights = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        bones = {
            name: world_head(rig, name) for name in (
                authority_root, "root", "torso_upper", "head",
                "leg_l", "shin_l", "foot_l",
                "leg_r", "shin_r", "foot_r",
                "arm_l", "forearm_l", "hand_l",
                "arm_r", "forearm_r", "hand_r",
            )
        }
        samples.append(bones)
        floor_values = []
        for side, label in (("l", "left"), ("r", "right")):
            ankle = world_head(source, source_names[f"{label}_foot"])
            toe = world_head(source, source_names[f"{label}_toe"])
            source_feet[side].append(np.asarray(ankle, dtype=float))
            source_foot_heights[side].append(min(ankle.z, toe.z))
            floor_values.append(min(ankle.z, toe.z))
        source_heights.append(
            world_head(source, source_names["head"]).z - min(floor_values))

    root_path = [sample[authority_root] for sample in samples]
    displacement = root_path[-1] - root_path[0]
    displacement.z = 0.0
    if displacement.length < 1.0e-7:
        forward = Vector((0.0, -1.0, 0.0))
    else:
        forward = displacement.normalized()
    up = Vector((0.0, 0.0, 1.0))
    right = forward.cross(up).normalized()
    heights = [
        sample["head"].z
        - min(sample["foot_l"].z, sample["foot_r"].z)
        for sample in samples
    ]
    height = float(np.median(heights))
    source_height = float(np.median(source_heights))
    contacts = {
        side: contact_mask(
            np.asarray(source_feet[side]),
            np.asarray(source_foot_heights[side]),
            source_height, args.fps,
        ) for side in ("l", "r")
    }

    lateral_lean = []
    forward_lean = []
    pelvis_lateral = []
    knee_angles = {"l": [], "r": []}
    knee_normals = {"l": [], "r": []}
    shoulder_roll = []
    pelvis_heights = []
    for sample in samples:
        torso_up = sample["head"] - sample["root"]
        torso_up.normalize()
        lateral_lean.append(math.degrees(math.atan2(
            torso_up.dot(right), torso_up.dot(up))))
        forward_lean.append(math.degrees(math.atan2(
            torso_up.dot(forward), torso_up.dot(up))))
        pelvis_lateral.append(
            (sample["root"] - sample[authority_root]).dot(right) / height)
        pelvis_heights.append(sample["root"].z / height)
        shoulder = sample["arm_r"] - sample["arm_l"]
        shoulder_roll.append(math.degrees(math.atan2(
            shoulder.dot(up), max(1.0e-8, abs(shoulder.dot(right))))))
        for side in ("l", "r"):
            hip = sample[f"leg_{side}"]
            knee = sample[f"shin_{side}"]
            ankle = sample[f"foot_{side}"]
            knee_angles[side].append(joint_angle(hip, knee, ankle))
            normal = (knee - hip).cross(ankle - knee)
            if normal.length < 1.0e-8:
                normal = right.copy()
            normal.normalize()
            if knee_normals[side] and normal.dot(knee_normals[side][-1]) < 0.0:
                normal.negate()
            knee_normals[side].append(normal)

    arm_forward = {
        side: np.asarray([
            (sample[f"hand_{side}"] - sample["root"]).dot(forward)
            for sample in samples])
        for side in ("l", "r")
    }
    arm_swing_range_h = {
        side: float(np.ptp(values) / height)
        for side, values in arm_forward.items()
    }
    shoulder_yaw = []
    hip_yaw = []
    elbow_angles = {"l": [], "r": []}
    for sample in samples:
        shoulder_axis = sample["arm_r"] - sample["arm_l"]
        hip_axis = sample["leg_r"] - sample["leg_l"]
        shoulder_axis.z = 0.0
        hip_axis.z = 0.0
        shoulder_axis.normalize()
        hip_axis.normalize()
        shoulder_yaw.append(math.atan2(
            shoulder_axis.dot(forward), shoulder_axis.dot(right)))
        hip_yaw.append(math.atan2(
            hip_axis.dot(forward), hip_axis.dot(right)))
        for side in ("l", "r"):
            elbow_angles[side].append(joint_angle(
                sample[f"arm_{side}"], sample[f"forearm_{side}"],
                sample[f"hand_{side}"]))
    counter_yaw = np.degrees(
        np.unwrap(np.asarray(shoulder_yaw))
        - np.unwrap(np.asarray(hip_yaw)))
    target_floor = min(min(sample["foot_l"].z, sample["foot_r"].z)
                       for sample in samples)
    flight_fraction = float(np.mean([
        sample["foot_l"].z > target_floor + 0.02 * height
        and sample["foot_r"].z > target_floor + 0.02 * height
        for sample in samples
    ]))

    knee_reports = {}
    for side in ("l", "r"):
        normal_speed = [
            math.degrees(knee_normals[side][index - 1].angle(
                knee_normals[side][index])) * args.fps
            for index in range(1, len(frames))
        ]
        angle_speed = [
            (knee_angles[side][index] - knee_angles[side][index - 1])
            * args.fps
            for index in range(1, len(frames))
        ]
        angle_acceleration = [
            (angle_speed[index] - angle_speed[index - 1]) * args.fps
            for index in range(1, len(angle_speed))
        ]
        knee_reports[side] = {
            "angle_min_deg": min(knee_angles[side]),
            "angle_max_deg": max(knee_angles[side]),
            "angle_min_frame": frames[int(np.argmin(knee_angles[side]))],
            "angle_max_frame": frames[int(np.argmax(knee_angles[side]))],
            "bend_plane_speed_p95_deg_s": quantile(normal_speed, 0.95),
            "bend_plane_speed_max_deg_s": max(normal_speed, default=0.0),
            "bend_plane_speed_max_frame": (
                frames[normal_speed.index(max(normal_speed)) + 1]
                if normal_speed else None),
            "angle_speed_p95_abs_deg_s": quantile(
                [abs(value) for value in angle_speed], 0.95),
            "angle_acceleration_p95_abs_deg_s2": quantile(
                [abs(value) for value in angle_acceleration], 0.95),
            "angle_acceleration_max_abs_deg_s2": max(
                [abs(value) for value in angle_acceleration], default=0.0),
            "angle_acceleration_max_frame": (
                frames[[abs(value) for value in angle_acceleration].index(
                    max(abs(value) for value in angle_acceleration)) + 2]
                if angle_acceleration else None),
        }

    strikes = []
    load_window = max(2, int(round(args.fps * 0.18)))
    for side in ("l", "r"):
        for index in range(len(frames)):
            previous = contacts[side][index - 1] if index > 0 else contacts[side][-1]
            if contacts[side][index] and not previous:
                end = min(len(frames), index + load_window + 1)
                local = pelvis_heights[index:end]
                if not local:
                    continue
                minimum = min(local)
                strikes.append({
                    "side": side,
                    "frame": frames[index],
                    "compression_h": pelvis_heights[index] - minimum,
                    "frames_to_max_compression": local.index(minimum),
                })

    report = {
        "schema": 1,
        "authority": "external_3d_locomotion_aesthetic_metrics",
        "frames": [frames[0], frames[-1]],
        "fps": args.fps,
        "height_units": height,
        "travel_h": displacement.length / height,
        "lateral_lean_deg": {
            "mean": float(np.mean(lateral_lean)),
            "median": float(np.median(lateral_lean)),
            "p95_abs": quantile([abs(value) for value in lateral_lean], 0.95),
            "minimum": min(lateral_lean),
            "maximum": max(lateral_lean),
        },
        "forward_lean_deg": {
            "mean": float(np.mean(forward_lean)),
            "median": float(np.median(forward_lean)),
            "minimum": min(forward_lean),
            "maximum": max(forward_lean),
        },
        "pelvis_lateral_h": {
            "mean": float(np.mean(pelvis_lateral)),
            "p95_abs": quantile([abs(value) for value in pelvis_lateral], 0.95),
        },
        "shoulder_roll_deg": {
            "mean": float(np.mean(shoulder_roll)),
            "p95_abs": quantile([abs(value) for value in shoulder_roll], 0.95),
        },
        "pelvis_vertical_range_h": max(pelvis_heights) - min(pelvis_heights),
        "locomotion_semantics": {
            "arm_swing_range_h": arm_swing_range_h,
            "minimum_arm_swing_range_h": min(
                arm_swing_range_h.values()),
            "thorax_pelvis_counter_yaw_range_degrees": float(
                np.ptp(counter_yaw)),
            "thorax_pelvis_yaw_correlation": (
                float(np.corrcoef(shoulder_yaw, hip_yaw)[0, 1])
                if (np.std(shoulder_yaw) > 1.0e-8
                    and np.std(hip_yaw) > 1.0e-8) else 0.0),
            "flight_fraction_from_ankle_landmarks": flight_fraction,
            "elbow_mean_degrees": {
                side: float(np.mean(values))
                for side, values in elbow_angles.items()
            },
        },
        "knee": knee_reports,
        "foot_strike_load_response": strikes,
        "median_load_compression_h": (
            float(np.median([strike["compression_h"] for strike in strikes]))
            if strikes else None),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "lateral_lean": report["lateral_lean_deg"],
        "locomotion_semantics": report["locomotion_semantics"],
        "knee": report["knee"],
        "median_load_compression_h": report["median_load_compression_h"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
