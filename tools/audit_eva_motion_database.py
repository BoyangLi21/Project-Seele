#!/usr/bin/env python3
"""Audit an EVA quaternion motion DB without rendering or opening Minecraft."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from mathutils import Euler, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_motion_lab_3d import load_geo, target_to_blender
from build_eva_motion_lab_armature import deformation_matrices
from build_eva_motion_database import target_ankle_position


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--profile", choices=("all", "runtime-core"),
                        default="all")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def point(matrices, pivots, name: str) -> Vector:
    return matrices[name] @ target_to_blender(pivots[name])


def angle(a: Vector, b: Vector, c: Vector) -> float:
    first = a - b
    second = c - b
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return float("nan")
    return math.degrees(first.angle(second))


def quaternion_angle(a: list[float], b: list[float]) -> float:
    first = Quaternion(tuple(a))
    second = Quaternion(tuple(b))
    dot = min(1.0, max(-1.0, abs(first.dot(second))))
    return math.degrees(2.0 * math.acos(dot))


def runtime_quaternion(wxyz: list[float]) -> Quaternion:
    authored = Quaternion(tuple(wxyz))
    euler = authored.to_euler("XYZ")
    result = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_quaternion()
    result.normalize()
    return result


def sample_frame(frame, db_bones, bone_order, pivots, parents) -> dict:
    matrices = deformation_matrices(frame, db_bones, bone_order, pivots, parents)
    joints = {name: point(matrices, pivots, name) for name in (
        "arm_l", "forearm_l", "hand_l", "arm_r", "forearm_r", "hand_r",
        "leg_l", "shin_l", "foot_l", "leg_r", "shin_r", "foot_r",
        "torso_lower", "torso_upper", "head",
    )}
    return {
        "matrices": matrices,
        "joints": joints,
        "left_elbow": angle(joints["arm_l"], joints["forearm_l"],
                            joints["hand_l"]),
        "right_elbow": angle(joints["arm_r"], joints["forearm_r"],
                             joints["hand_r"]),
        "left_knee": angle(joints["leg_l"], joints["shin_l"],
                           joints["foot_l"]),
        "right_knee": angle(joints["leg_r"], joints["shin_r"],
                            joints["foot_r"]),
    }


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    bones, pivots, parents = load_geo(args.geo)
    bone_order = [bone["name"] for bone in bones]
    db_bones = list(motion["bones"])
    fps = float(motion.get("sample_rate", 30.0))
    idle_frame = motion["clips"]["idle"]["frames"][0]
    idle = sample_frame(idle_frame, db_bones, bone_order, pivots, parents)
    baseline_ankles = {
        side: idle["joints"][f"foot_{side}"].z for side in ("l", "r")
    }
    all_failures = []
    reports = {}
    runtime_core = {
        "idle", "walk", "formal_walk", "jog", "sprint",
        "jump_start", "jump_loop", "jump_land",
        "jump_takeoff_v2", "jump_airborne_v2", "jump_landing_v2",
    }
    selected_clips = {
        name: clip for name, clip in motion["clips"].items()
        if args.profile == "all" or name in runtime_core
    }
    for clip_name, clip in selected_clips.items():
        frames = clip["frames"]
        samples = [
            sample_frame(frame, db_bones, bone_order, pivots, parents)
            for frame in frames
        ]
        failures = []
        extrema = {
            "left_elbow": [float("inf"), float("-inf")],
            "right_elbow": [float("inf"), float("-inf")],
            "left_knee": [float("inf"), float("-inf")],
            "right_knee": [float("inf"), float("-inf")],
        }
        maximum_joint_speed = 0.0
        maximum_joint_accel = 0.0
        maximum_root_yaw_speed = 0.0
        previous_velocity: dict[str, Vector] = {}
        maximum_contact_drift = {"l": 0.0, "r": 0.0}
        maximum_contact_drift_frame = {"l": None, "r": None}
        maximum_contact_speed = {"l": 0.0, "r": 0.0}
        maximum_contact_speed_frame = {"l": None, "r": None}
        previous_world_feet: dict[str, Vector] = {}
        previous_contacts = [False, False]
        travel = clip.get("root_travel_m", [0.0, 0.0, 0.0])
        for index, (frame, sample) in enumerate(zip(frames, samples)):
            phase = index / max(1, len(frames) - 1)
            virtual_root = Vector((
                -float(travel[0]), -float(travel[2]), 0.0
            )) * (112.0 * phase)
            runtime_rotations = {
                name: runtime_quaternion(frame["rotation_wxyz"][bone_index])
                for bone_index, name in enumerate(db_bones)
            }
            for joint_name in extrema:
                value = sample[joint_name]
                extrema[joint_name][0] = min(extrema[joint_name][0], value)
                extrema[joint_name][1] = max(extrema[joint_name][1], value)
                if not math.isfinite(value) or not 1.0 <= value <= 179.99:
                    failures.append(
                        f"frame {index}: implausible {joint_name}={value:.3f}deg"
                    )
            for side, planted in zip(("l", "r"), frame["foot_contact"]):
                world_foot = sample["joints"][f"foot_{side}"] + virtual_root
                if planted:
                    drift = abs(sample["joints"][f"foot_{side}"].z
                                - baseline_ankles[side])
                    if drift > maximum_contact_drift[side]:
                        maximum_contact_drift[side] = drift
                        maximum_contact_drift_frame[side] = {
                            "frame_index": index,
                            "ankle_z": sample["joints"][f"foot_{side}"].z,
                            "baseline_z": baseline_ankles[side],
                            "root_m": frame["root_m"],
                            "contacts": frame["foot_contact"],
                            "analytic_ankle_z": target_ankle_position(
                                runtime_rotations, pivots, side
                            ).y + float(frame["root_m"][1]) * 112.0,
                        }
                side_index = 0 if side == "l" else 1
                if planted and previous_contacts[side_index] and index > 0:
                    speed = ((world_foot - previous_world_feet[side]).length
                             / 112.0 * fps)
                    if speed > maximum_contact_speed[side]:
                        maximum_contact_speed[side] = speed
                        maximum_contact_speed_frame[side] = index
                previous_world_feet[side] = world_foot
            previous_contacts = list(frame["foot_contact"])
            if index == 0:
                continue
            yaw_delta = (float(frame.get("root_yaw_radians", 0.0))
                         - float(frames[index - 1].get(
                             "root_yaw_radians", 0.0)))
            while yaw_delta > math.pi:
                yaw_delta -= math.tau
            while yaw_delta < -math.pi:
                yaw_delta += math.tau
            maximum_root_yaw_speed = max(
                maximum_root_yaw_speed, abs(math.degrees(yaw_delta) * fps)
            )
            for joint_name, current in sample["joints"].items():
                velocity = (current - samples[index - 1]["joints"][joint_name]) * fps
                maximum_joint_speed = max(maximum_joint_speed, velocity.length)
                old_velocity = previous_velocity.get(joint_name)
                if old_velocity is not None:
                    acceleration = (velocity - old_velocity) * fps
                    maximum_joint_accel = max(
                        maximum_joint_accel, acceleration.length
                    )
                previous_velocity[joint_name] = velocity
        for side in ("l", "r"):
            if maximum_contact_drift[side] > 4.0:
                failures.append(
                    f"planted {side} ankle drift "
                    f"{maximum_contact_drift[side]:.3f} model units"
                )
        if maximum_root_yaw_speed > 720.0:
            failures.append(
                f"root yaw spike {maximum_root_yaw_speed:.3f}deg/s"
            )
            if maximum_contact_speed[side] > 0.35:
                failures.append(
                    f"planted {side} foot speed "
                    f"{maximum_contact_speed[side]:.3f}m/s at frame "
                    f"{maximum_contact_speed_frame[side]}"
                )

        seam = None
        if clip.get("loop") and len(frames) > 1:
            seam_by_bone = {
                db_bones[index]: quaternion_angle(
                    frames[0]["rotation_wxyz"][index],
                    frames[-1]["rotation_wxyz"][index],
                )
                for index in range(len(db_bones))
                if not db_bones[index].startswith("finger_")
            }
            seam_angles = list(seam_by_bone.values())
            worst_bone = max(seam_by_bone, key=seam_by_bone.get)
            seam = {
                "max_bone_angle_degrees": max(seam_angles),
                "max_bone": worst_bone,
                "largest_bone_angles_degrees": dict(sorted(
                    seam_by_bone.items(), key=lambda item: item[1],
                    reverse=True
                )[:5]),
                "root_height_meters": abs(
                    float(frames[0]["root_m"][1])
                    - float(frames[-1]["root_m"][1])
                ),
                "contact_match": frames[0]["foot_contact"]
                                 == frames[-1]["foot_contact"],
                "root_yaw_degrees": abs(math.degrees(
                    float(frames[0].get("root_yaw_radians", 0.0))
                    - float(frames[-1].get("root_yaw_radians", 0.0))
                )),
            }
            if seam["max_bone_angle_degrees"] > 28.0:
                failures.append(
                    f"loop seam angle {seam['max_bone_angle_degrees']:.3f}deg"
                )
            if seam["root_height_meters"] > 0.08:
                failures.append(
                    f"loop root-height seam {seam['root_height_meters']:.4f}m"
                )
            if seam["root_yaw_degrees"] > 2.0:
                failures.append(
                    f"loop root-yaw seam {seam['root_yaw_degrees']:.3f}deg"
                )

        failures = sorted(set(failures))
        reports[clip_name] = {
            "role": clip.get("role", "unknown"),
            "frames": len(frames),
            "duration_seconds": clip["duration_seconds"],
            "joint_angle_extrema_degrees": extrema,
            "maximum_joint_speed_model_units_per_second": maximum_joint_speed,
            "maximum_joint_acceleration_model_units_per_second2": maximum_joint_accel,
            "maximum_root_yaw_speed_degrees_per_second": maximum_root_yaw_speed,
            "maximum_planted_ankle_drift_model_units": maximum_contact_drift,
            "maximum_planted_ankle_drift_frame": maximum_contact_drift_frame,
            "maximum_planted_foot_speed_mps": maximum_contact_speed,
            "maximum_planted_foot_speed_frame": maximum_contact_speed_frame,
            "loop_seam": seam,
            "failures": failures,
        }
        all_failures.extend(f"{clip_name}: {failure}" for failure in failures)
    report = {
        "schema": 1,
        "authority": "eva_quaternion_database_exact_skeleton_kinematics",
        "profile": args.profile,
        "motion_db": str(args.motion_db.resolve()),
        "motion_db_sha256": hashlib.sha256(
            args.motion_db.read_bytes()
        ).hexdigest(),
        "baseline_ankle_z": baseline_ankles,
        "clip_count": len(reports),
        "failure_count": len(all_failures),
        "failures": all_failures,
        "clips": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA motion DB audit: clips={len(reports)} "
        f"failures={len(all_failures)} output={args.output}"
    )
    if args.strict and all_failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
