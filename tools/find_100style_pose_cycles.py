#!/usr/bin/env python3
"""Find periodic humanoid gait windows with full-body semantic metrics."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--profile", choices=("100style", "accad"),
                        default="100style")
    parser.add_argument("--mode", choices=("walk", "run"), required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cut-start", required=True, type=int)
    parser.add_argument("--cut-end", required=True, type=int)
    parser.add_argument("--minimum-frames", required=True, type=int)
    parser.add_argument("--maximum-frames", required=True, type=int)
    parser.add_argument("--minimum-speed", required=True, type=float)
    parser.add_argument("--maximum-speed", required=True, type=float)
    parser.add_argument("--limit", type=int, default=500)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def world_head(armature, name: str) -> np.ndarray:
    return np.asarray(armature.matrix_world
                      @ armature.pose.bones[name].head, dtype=float)


def main() -> None:
    args = parse_args()
    names = ({
        "root": "Hips", "head": "Head",
        "left_shoulder": "LeftShoulder", "left_elbow": "LeftElbow",
        "left_wrist": "LeftWrist", "right_shoulder": "RightShoulder",
        "right_elbow": "RightElbow", "right_wrist": "RightWrist",
        "left_hip": "LeftHip", "left_knee": "LeftKnee",
        "left_foot": "LeftAnkle", "left_toe": "LeftToe",
        "right_hip": "RightHip", "right_knee": "RightKnee",
        "right_foot": "RightAnkle", "right_toe": "RightToe",
        "seam_bones": (
            "Chest", "Chest2", "Chest3", "Chest4", "Neck", "Head",
            "LeftShoulder", "LeftElbow", "LeftWrist",
            "RightShoulder", "RightElbow", "RightWrist",
            "LeftHip", "LeftKnee", "LeftAnkle",
            "RightHip", "RightKnee", "RightAnkle",
        ),
    } if args.profile == "100style" else {
        "root": "Hips", "head": "Head",
        "left_shoulder": "LeftArm", "left_elbow": "LeftForeArm",
        "left_wrist": "LeftHand", "right_shoulder": "RightArm",
        "right_elbow": "RightForeArm", "right_wrist": "RightHand",
        "left_hip": "LeftUpLeg", "left_knee": "LeftLeg",
        "left_foot": "LeftFoot", "left_toe": "LeftToeBase",
        "right_hip": "RightUpLeg", "right_knee": "RightLeg",
        "right_foot": "RightFoot", "right_toe": "RightToeBase",
        "seam_bones": (
            "ToSpine", "Spine", "Spine1", "Neck", "Head",
            "LeftArm", "LeftForeArm", "LeftHand",
            "RightArm", "RightForeArm", "RightHand",
            "LeftUpLeg", "LeftLeg", "LeftFoot",
            "RightUpLeg", "RightLeg", "RightFoot",
        ),
    })
    seam_bones = names["seam_bones"]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_anim.bvh(
        filepath=str(args.source.resolve()), target="ARMATURE",
        global_scale=0.1, frame_start=1, use_fps_scale=False,
        update_scene_fps=True, update_scene_duration=True,
        rotate_mode="NATIVE", axis_forward="-Z", axis_up="Y",
    )
    rig = next(obj for obj in bpy.context.scene.objects
               if obj.type == "ARMATURE")
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    first = max(scene.frame_start, args.cut_start)
    last = min(scene.frame_end, args.cut_end)
    frames = np.arange(first, last + 1, dtype=int)
    rotations = np.empty((len(frames), len(seam_bones), 4), dtype=float)
    roots = np.empty((len(frames), 3), dtype=float)
    heads = np.empty((len(frames), 3), dtype=float)
    hips_l = np.empty((len(frames), 3), dtype=float)
    hips_r = np.empty((len(frames), 3), dtype=float)
    shoulders_l = np.empty((len(frames), 3), dtype=float)
    shoulders_r = np.empty((len(frames), 3), dtype=float)
    elbows_l = np.empty((len(frames), 3), dtype=float)
    elbows_r = np.empty((len(frames), 3), dtype=float)
    wrists_l = np.empty((len(frames), 3), dtype=float)
    wrists_r = np.empty((len(frames), 3), dtype=float)
    feet_l = np.empty((len(frames), 3), dtype=float)
    feet_r = np.empty((len(frames), 3), dtype=float)
    toes_l = np.empty((len(frames), 3), dtype=float)
    toes_r = np.empty((len(frames), 3), dtype=float)
    for index, frame in enumerate(frames):
        scene.frame_set(int(frame))
        bpy.context.view_layer.update()
        roots[index] = world_head(rig, names["root"])
        heads[index] = world_head(rig, names["head"])
        hips_l[index] = world_head(rig, names["left_hip"])
        hips_r[index] = world_head(rig, names["right_hip"])
        shoulders_l[index] = world_head(rig, names["left_shoulder"])
        shoulders_r[index] = world_head(rig, names["right_shoulder"])
        elbows_l[index] = world_head(rig, names["left_elbow"])
        elbows_r[index] = world_head(rig, names["right_elbow"])
        wrists_l[index] = world_head(rig, names["left_wrist"])
        wrists_r[index] = world_head(rig, names["right_wrist"])
        feet_l[index] = world_head(rig, names["left_foot"])
        feet_r[index] = world_head(rig, names["right_foot"])
        toes_l[index] = world_head(rig, names["left_toe"])
        toes_r[index] = world_head(rig, names["right_toe"])
        for bone_index, name in enumerate(seam_bones):
            quaternion = rig.pose.bones[name].matrix_basis.to_quaternion()
            quaternion.normalize()
            rotations[index, bone_index] = (
                quaternion.w, quaternion.x, quaternion.y, quaternion.z)

    actor_height = float(np.median(
        heads[:, 2] - np.minimum.reduce((feet_l[:, 2], feet_r[:, 2],
                                         toes_l[:, 2], toes_r[:, 2]))))
    if args.analysis is not None:
        source_report = json.loads(args.analysis.read_text(encoding="utf-8"))
        source_to_meters = float(source_report["source_to_meters"])
    else:
        source_to_meters = 1.75 / max(actor_height, 1.0e-8)
    floor = float(np.percentile(np.concatenate((
        feet_l[:, 2], feet_r[:, 2], toes_l[:, 2], toes_r[:, 2])), 2.0))

    horizontal_steps = np.linalg.norm(
        np.diff(roots[:, :2], axis=0), axis=1)
    cumulative_path = np.concatenate(([0.0], np.cumsum(horizontal_steps)))
    up = np.asarray((0.0, 0.0, 1.0), dtype=float)
    candidates = []
    for duration_frames in range(args.minimum_frames,
                                 args.maximum_frames + 1):
        count = len(frames) - duration_frames
        if count <= 0:
            continue
        dots = np.abs(np.sum(
            rotations[:count] * rotations[duration_frames:], axis=2))
        dots = np.clip(dots, -1.0, 1.0)
        seam = np.degrees(2.0 * np.arccos(dots))
        seam_p95 = np.percentile(seam, 95.0, axis=1)
        seam_maximum = np.max(seam, axis=1)
        displacement = (roots[duration_frames:, :2]
                        - roots[:count, :2])
        distance = np.linalg.norm(displacement, axis=1)
        speed = (distance * source_to_meters * fps
                 / duration_frames)
        path = cumulative_path[duration_frames:] - cumulative_path[:count]
        straightness = distance / np.maximum(path, 1.0e-8)
        plausible = ((speed >= args.minimum_speed)
                     & (speed <= args.maximum_speed)
                     & (straightness >= 0.975)
                     & (seam_maximum <= 18.0))
        for start_index in np.flatnonzero(plausible):
            end_index = start_index + duration_frames
            forward = np.asarray((displacement[start_index, 0],
                                  displacement[start_index, 1], 0.0))
            forward /= max(np.linalg.norm(forward), 1.0e-8)
            right = np.cross(forward, up)
            torso = heads[start_index:end_index + 1] - roots[
                start_index:end_index + 1]
            torso /= np.maximum(np.linalg.norm(torso, axis=1)[:, None],
                                1.0e-8)
            lateral = np.degrees(np.arctan2(torso @ right, torso @ up))
            forward_lean = np.degrees(np.arctan2(
                torso @ forward, torso @ up))
            hip_axis_start = hips_r[start_index] - hips_l[start_index]
            hip_axis_end = hips_r[end_index] - hips_l[end_index]
            hip_axis_start[2] = 0.0
            hip_axis_end[2] = 0.0
            hip_axis_start /= max(np.linalg.norm(hip_axis_start), 1.0e-8)
            hip_axis_end /= max(np.linalg.norm(hip_axis_end), 1.0e-8)
            yaw_seam = math.degrees(math.acos(float(np.clip(
                np.dot(hip_axis_start, hip_axis_end), -1.0, 1.0))))
            window = slice(start_index, end_index + 1)
            left_arm = (wrists_l[window] - roots[window]) @ forward
            right_arm = (wrists_r[window] - roots[window]) @ forward
            left_arm_swing = float(np.ptp(left_arm) / actor_height)
            right_arm_swing = float(np.ptp(right_arm) / actor_height)

            shoulder_axes = shoulders_r[window] - shoulders_l[window]
            hip_axes = hips_r[window] - hips_l[window]
            shoulder_axes[:, 2] = 0.0
            hip_axes[:, 2] = 0.0
            shoulder_axes /= np.maximum(
                np.linalg.norm(shoulder_axes, axis=1)[:, None], 1.0e-8)
            hip_axes /= np.maximum(
                np.linalg.norm(hip_axes, axis=1)[:, None], 1.0e-8)
            shoulder_yaw = np.unwrap(np.arctan2(
                shoulder_axes @ forward, shoulder_axes @ right))
            hip_yaw = np.unwrap(np.arctan2(
                hip_axes @ forward, hip_axes @ right))
            counter_yaw = np.degrees(shoulder_yaw - hip_yaw)
            counter_yaw_range = float(np.ptp(counter_yaw))
            yaw_correlation = (
                float(np.corrcoef(shoulder_yaw, hip_yaw)[0, 1])
                if (len(shoulder_yaw) > 2
                    and np.std(shoulder_yaw) > 1.0e-8
                    and np.std(hip_yaw) > 1.0e-8)
                else 0.0)

            left_ground = np.minimum(feet_l[window, 2], toes_l[window, 2])
            right_ground = np.minimum(feet_r[window, 2], toes_r[window, 2])
            flight_fraction = float(np.mean(
                (left_ground > floor + 0.02 * actor_height)
                & (right_ground > floor + 0.02 * actor_height)))

            def joint_angle(first_points, middle_points, last_points):
                first_vector = first_points - middle_points
                second_vector = last_points - middle_points
                cosine = np.sum(first_vector * second_vector, axis=1) / (
                    np.maximum(np.linalg.norm(first_vector, axis=1), 1.0e-8)
                    * np.maximum(np.linalg.norm(second_vector, axis=1),
                                 1.0e-8))
                return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

            left_elbow = joint_angle(shoulders_l[window], elbows_l[window],
                                     wrists_l[window])
            right_elbow = joint_angle(shoulders_r[window], elbows_r[window],
                                      wrists_r[window])
            arm_swing_minimum = min(left_arm_swing, right_arm_swing)
            arm_target = 0.10 if args.mode == "walk" else 0.16
            counter_target = 3.0 if args.mode == "walk" else 5.0
            semantic_penalty = (
                max(0.0, arm_target - arm_swing_minimum) * 180.0
                + max(0.0, counter_target - counter_yaw_range) * 2.0)
            if args.mode == "run":
                semantic_penalty += max(0.0, 0.06 - flight_fraction) * 180.0
                semantic_penalty += max(
                    0.0, (float(np.mean(left_elbow + right_elbow)) * 0.5
                          - 155.0)) * 0.3
            else:
                semantic_penalty += max(0.0, flight_fraction - 0.03) * 180.0
            score = (
                float(seam_p95[start_index]) * 4.0
                + float(seam_maximum[start_index]) * 2.0
                + abs(float(np.mean(lateral))) * 3.0
                + float(np.percentile(np.abs(lateral), 95.0))
                + max(0.0, 0.99 - float(straightness[start_index])) * 500.0
                + yaw_seam
                + semantic_penalty
            )
            candidates.append({
                "start_frame": int(frames[start_index]),
                "end_frame": int(frames[end_index]),
                "duration_frames": duration_frames,
                "duration_seconds": duration_frames / fps,
                "speed_mps": float(speed[start_index]),
                "straightness": float(straightness[start_index]),
                "endpoint_local_rotation_seam_p95_degrees": float(
                    seam_p95[start_index]),
                "endpoint_local_rotation_seam_maximum_degrees": float(
                    seam_maximum[start_index]),
                "endpoint_yaw_seam_degrees": yaw_seam,
                "lateral_lean_mean_degrees": float(np.mean(lateral)),
                "lateral_lean_p95_abs_degrees": float(
                    np.percentile(np.abs(lateral), 95.0)),
                "forward_lean_mean_degrees": float(np.mean(forward_lean)),
                "left_arm_swing_range_h": left_arm_swing,
                "right_arm_swing_range_h": right_arm_swing,
                "minimum_arm_swing_range_h": arm_swing_minimum,
                "thorax_pelvis_counter_yaw_range_degrees":
                    counter_yaw_range,
                "thorax_pelvis_yaw_correlation": yaw_correlation,
                "flight_fraction": flight_fraction,
                "left_elbow_mean_degrees": float(np.mean(left_elbow)),
                "right_elbow_mean_degrees": float(np.mean(right_elbow)),
                "semantic_penalty": semantic_penalty,
                "selection_score": score,
            })
    candidates.sort(key=lambda row: row["selection_score"])
    output = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "profile": args.profile,
        "mode": args.mode,
        "fps": fps,
        "actor_height_source_units": actor_height,
        "source_to_meters": source_to_meters,
        "analysis_cut": [first, last],
        "window_frames": [args.minimum_frames, args.maximum_frames],
        "speed_mps": [args.minimum_speed, args.maximum_speed],
        "candidate_count": len(candidates),
        "ranking": candidates[:args.limit],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "candidate_count": len(candidates),
        "top": candidates[:10],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
