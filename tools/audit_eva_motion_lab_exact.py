#!/usr/bin/env python3
"""3D biomechanical audit for EVA_MOTION_LAB_V4_EXACT.blend."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_motion_lab_3d import CORE_SEQUENCE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gap-frames", type=int, default=12)
    parser.add_argument("--profile", choices=("all", "runtime-core"),
                        default="all")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def object_bounds(objects: list[bpy.types.Object]) -> tuple[list[float], list[float]]:
    points = []
    for obj in objects:
        matrix = obj.matrix_world
        points.extend(matrix @ vertex.co for vertex in obj.data.vertices)
    return (
        [min(point[axis] for point in points) for axis in range(3)],
        [max(point[axis] for point in points) for axis in range(3)],
    )


def joint(name: str) -> Vector:
    return bpy.data.objects[f"JOINT::{name}"].matrix_world.translation


def angle(a: Vector, b: Vector, c: Vector) -> float:
    first = a - b
    second = c - b
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return float("nan")
    return math.degrees(first.angle(second))


def sample(scene: bpy.types.Scene, parts: list[bpy.types.Object],
           frame: int) -> dict:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    minimum, maximum = object_bounds(parts)
    left_hip, left_knee, left_ankle = (
        joint("leg_l"), joint("shin_l"), joint("foot_l")
    )
    right_hip, right_knee, right_ankle = (
        joint("leg_r"), joint("shin_r"), joint("foot_r")
    )
    left_shoulder, left_elbow, left_wrist = (
        joint("arm_l"), joint("forearm_l"), joint("hand_l")
    )
    right_shoulder, right_elbow, right_wrist = (
        joint("arm_r"), joint("forearm_r"), joint("hand_r")
    )
    root_matrix = bpy.data.objects["JOINT::root"].matrix_world
    root_origin = root_matrix.translation
    root_rotation = root_matrix.to_quaternion()
    root_forward = root_rotation @ Vector((0.0, 1.0, 0.0))
    root_right = root_rotation @ Vector((1.0, 0.0, 0.0))
    return {
        "frame": frame,
        "bounds_min": [round(value, 6) for value in minimum],
        "bounds_max": [round(value, 6) for value in maximum],
        "span": [round(maximum[axis] - minimum[axis], 6)
                 for axis in range(3)],
        "left_knee_degrees": round(angle(
            left_hip, left_knee, left_ankle), 4),
        "right_knee_degrees": round(angle(
            right_hip, right_knee, right_ankle), 4),
        "left_elbow_degrees": round(angle(
            left_shoulder, left_elbow, left_wrist), 4),
        "right_elbow_degrees": round(angle(
            right_shoulder, right_elbow, right_wrist), 4),
        "left_hand_forward": round(
            (left_wrist - root_origin).dot(root_forward), 6),
        "right_hand_forward": round(
            (right_wrist - root_origin).dot(root_forward), 6),
        "left_ankle_lateral": round(
            (left_ankle - root_origin).dot(root_right), 6),
        "right_ankle_lateral": round(
            (right_ankle - root_origin).dot(root_right), 6),
        "left_ankle_z": round(left_ankle.z, 6),
        "right_ankle_z": round(right_ankle.z, 6),
        "left_contact": not bpy.data.objects[
            "CONTACT_L_PLANTED"].hide_viewport,
        "right_contact": not bpy.data.objects[
            "CONTACT_R_PLANTED"].hide_viewport,
    }


def ranges_from_db(motion: dict, gap: int) -> dict[str, tuple[int, int]]:
    sequence = [name for name in CORE_SEQUENCE if name in motion["clips"]]
    sequence.extend(sorted(set(motion["clips"]) - set(sequence)))
    cursor = 1
    ranges = {}
    for name in sequence:
        end = cursor + len(motion["clips"][name]["frames"]) - 1
        ranges[name] = (cursor, end)
        cursor = end + gap + 1
    return ranges


def directional_alignment(scene: bpy.types.Scene, start: int, end: int,
                          role: str) -> dict | None:
    if role not in {
            "candidate_locomotion", "candidate_trajectory",
            "locomotion", "trajectory", "gait"}:
        return None
    alignments = []
    previous = None
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        root = joint("root").copy()
        if previous is not None:
            velocity = root - previous
            velocity.z = 0.0
            # One Blender unit in this lab is about 0.1786 m at display scale;
            # ignore sub-0.1 m/s pelvis/contact-lock corrections and audit the
            # actual locomotion trajectory instead of root micro-jitter.
            if velocity.length > 0.02:
                velocity.normalize()
                torso = bpy.data.objects["JOINT::torso_lower"]
                facing = (torso.matrix_world.to_quaternion()
                          @ Vector((0.0, 1.0, 0.0)))
                facing.z = 0.0
                if facing.length > 1.0e-8:
                    facing.normalize()
                    alignments.append(velocity.dot(facing))
        previous = root.copy()
    if not alignments:
        return {
            "sample_count": 0,
            "median_facing_velocity_dot": None,
            "minimum_facing_velocity_dot": None,
            "negative_fraction": None,
        }
    return {
        "sample_count": len(alignments),
        "median_facing_velocity_dot": statistics.median(alignments),
        "minimum_facing_velocity_dot": min(alignments),
        "negative_fraction": (sum(value < 0.0 for value in alignments)
                              / len(alignments)),
    }


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    motion_hash = hashlib.sha256(args.motion_db.read_bytes()).hexdigest()
    embedded_hash = bpy.context.scene.get("motion_db_sha256")
    if embedded_hash != motion_hash:
        raise SystemExit(
            "exact Blender lab was built from a different motion database: "
            f"embedded={embedded_hash} current={motion_hash}"
        )
    ranges = ranges_from_db(motion, args.gap_frames)
    if args.profile == "runtime-core":
        runtime_core = {
            "idle", "walk", "formal_walk", "jog", "sprint",
            "jump_start", "jump_loop", "jump_land",
            "jump_takeoff_v2", "jump_airborne_v2", "jump_landing_v2",
        }
        ranges = {name: value for name, value in ranges.items()
                  if name in runtime_core}
    scene = bpy.context.scene
    parts = [obj for obj in scene.objects
             if obj.name.startswith("PART::")
             and obj.name not in {"PART::knife", "PART::cannon", "PART::lance"}]
    if len(parts) != 43:
        raise SystemExit(f"expected 43 exact mesh parts, found {len(parts)}")
    baseline_name = "idle" if "idle" in ranges else next(iter(ranges))
    idle = sample(scene, parts, ranges[baseline_name][0])
    baseline_height = idle["span"][2]
    baseline_ankle = {
        "left": idle["left_ankle_z"],
        "right": idle["right_ankle_z"],
    }
    failures = []
    clips = {}
    for name, (start, end) in ranges.items():
        role = motion["clips"][name].get("role", "unknown")
        low_profile = role in {
            "candidate_prone", "candidate_posture_transition", "crouch"
        } or name.startswith("prone_") or "_to_prone" in name \
            or name.startswith("crawl")
        length = max(1, end - start)
        frames = sorted({start, end, start + length // 4,
                         start + length // 2, start + length * 3 // 4})
        samples = [sample(scene, parts, frame) for frame in frames]
        clip_failures = []
        direction = directional_alignment(scene, start, end, role)
        if direction is not None and direction["sample_count"] >= 3:
            if direction["median_facing_velocity_dot"] < 0.35:
                clip_failures.append(
                    "backwards exact mesh: median facing/velocity dot "
                    f"{direction['median_facing_velocity_dot']:.3f} < 0.350"
                )
            if direction["negative_fraction"] > 0.20:
                clip_failures.append(
                    "backwards exact mesh: negative facing/velocity samples "
                    f"{direction['negative_fraction']:.1%} > 20.0%"
                )
        for value in samples:
            width, depth, height = value["span"]
            finite = (width, depth, height, value["left_knee_degrees"],
                      value["right_knee_degrees"],
                      value["left_elbow_degrees"],
                      value["right_elbow_degrees"])
            if not all(math.isfinite(number) for number in finite):
                clip_failures.append(
                    f"frame {value['frame']}: non-finite 3D state")
            if (not name.startswith("slide") and not low_profile
                    and height < baseline_height * 0.42):
                clip_failures.append(
                    f"frame {value['frame']}: collapsed height {height:.3f}")
            if (not name.startswith("slide") and not low_profile
                    and max(width, depth) > height * 1.8):
                clip_failures.append(
                    f"frame {value['frame']}: horizontal explosion "
                    f"span=({width:.3f},{depth:.3f},{height:.3f})")
            if value["bounds_min"][2] < -0.12:
                clip_failures.append(
                    f"frame {value['frame']}: ground penetration "
                    f"{value['bounds_min'][2]:.3f}")
            if role == "crouch":
                if min(value["left_hand_forward"],
                       value["right_hand_forward"]) < 0.20:
                    clip_failures.append(
                        f"frame {value['frame']}: crouch hand behind root "
                        f"left={value['left_hand_forward']:.3f} "
                        f"right={value['right_hand_forward']:.3f}")
                if (value["left_ankle_lateral"] >= -0.20
                        or value["right_ankle_lateral"] <= 0.20):
                    clip_failures.append(
                        f"frame {value['frame']}: crouch ankles crossed "
                        f"left={value['left_ankle_lateral']:.3f} "
                        f"right={value['right_ankle_lateral']:.3f}")
            for side in ("left", "right"):
                if value[f"{side}_contact"] and not low_profile:
                    drift = abs(value[f"{side}_ankle_z"]
                                - baseline_ankle[side])
                    if drift > 0.65:
                        clip_failures.append(
                            f"frame {value['frame']}: planted {side} ankle "
                            f"vertical drift {drift:.3f}")
        unique = sorted(set(clip_failures))
        clips[name] = {
            "frame_range": [start, end],
            "samples": samples,
            "directional_alignment": direction,
            "failures": unique,
        }
        failures.extend(f"{name}: {failure}" for failure in unique)
    report = {
        "schema": 1,
        "authority": "exact_gecko_global_matrices_in_blender_3d",
        "profile": args.profile,
        "blend": bpy.data.filepath,
        "motion_db_sha256": motion_hash,
        "baseline_clip": baseline_name,
        "baseline_height": baseline_height,
        "baseline_ankle_z": baseline_ankle,
        "clip_count": len(clips),
        "failure_count": len(failures),
        "failures": failures,
        "clips": clips,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA exact 3D audit: clips={len(clips)} failures={len(failures)} "
        f"output={args.output}"
    )
    if args.strict and failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
