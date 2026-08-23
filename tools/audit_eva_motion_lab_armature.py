#!/usr/bin/env python3
"""Audit the Blender EVA armature lab in 3D, without rendering screenshots."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def world_head(armature: bpy.types.Object, bone: str) -> Vector:
    return armature.matrix_world @ armature.pose.bones[bone].head


def joint_angle(a: Vector, b: Vector, c: Vector) -> float:
    first = a - b
    second = c - b
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return float("nan")
    return math.degrees(first.angle(second))


def evaluated_bounds(obj: bpy.types.Object) -> tuple[list[float], list[float]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        minimum = [min(point[axis] for point in points) for axis in range(3)]
        maximum = [max(point[axis] for point in points) for axis in range(3)]
        return minimum, maximum
    finally:
        evaluated.to_mesh_clear()


def sample_frame(scene: bpy.types.Scene, armature: bpy.types.Object,
                 mesh: bpy.types.Object, frame: int) -> dict:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    minimum, maximum = evaluated_bounds(mesh)
    left_hip = world_head(armature, "leg_l")
    left_knee = world_head(armature, "shin_l")
    left_ankle = world_head(armature, "foot_l")
    right_hip = world_head(armature, "leg_r")
    right_knee = world_head(armature, "shin_r")
    right_ankle = world_head(armature, "foot_r")
    left_shoulder = world_head(armature, "arm_l")
    left_elbow = world_head(armature, "forearm_l")
    left_wrist = world_head(armature, "hand_l")
    right_shoulder = world_head(armature, "arm_r")
    right_elbow = world_head(armature, "forearm_r")
    right_wrist = world_head(armature, "hand_r")
    return {
        "frame": frame,
        "bounds_min": [round(value, 6) for value in minimum],
        "bounds_max": [round(value, 6) for value in maximum],
        "span": [round(maximum[axis] - minimum[axis], 6)
                 for axis in range(3)],
        "left_knee_degrees": round(joint_angle(
            left_hip, left_knee, left_ankle), 4),
        "right_knee_degrees": round(joint_angle(
            right_hip, right_knee, right_ankle), 4),
        "left_elbow_degrees": round(joint_angle(
            left_shoulder, left_elbow, left_wrist), 4),
        "right_elbow_degrees": round(joint_angle(
            right_shoulder, right_elbow, right_wrist), 4),
        "left_ankle_z": round(left_ankle.z, 6),
        "right_ankle_z": round(right_ankle.z, 6),
        "left_contact": float(armature.pose.bones["foot_l"].get(
            "contact", 0.0)) >= 0.5,
        "right_contact": float(armature.pose.bones["foot_r"].get(
            "contact", 0.0)) >= 0.5,
    }


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    armature = bpy.data.objects["EVA_RUNTIME_ARMATURE"]
    mesh = bpy.data.objects["EVA_RUNTIME_SKINNED_MESH"]
    track = armature.animation_data.nla_tracks["EVA REVIEW SEQUENCE"]
    idle_strip = next(strip for strip in track.strips if strip.name.endswith("idle"))
    scene.frame_set(int(idle_strip.frame_start))
    idle_min, idle_max = evaluated_bounds(mesh)
    baseline_height = idle_max[2] - idle_min[2]
    baseline_ankle = {
        "l": world_head(armature, "foot_l").z,
        "r": world_head(armature, "foot_r").z,
    }

    failures = []
    clips = {}
    for strip in track.strips:
        start = int(round(strip.frame_start))
        end = int(round(strip.frame_end))
        count = max(1, end - start)
        frames = sorted({start, end,
                         start + count // 4,
                         start + count // 2,
                         start + count * 3 // 4})
        samples = [sample_frame(scene, armature, mesh, frame)
                   for frame in frames]
        clip_name = strip.name.removeprefix("EVA::")
        clip_failures = []
        for sample in samples:
            height = sample["span"][2]
            width = sample["span"][0]
            depth = sample["span"][1]
            if not all(math.isfinite(value) for value in (
                    height, width, depth,
                    sample["left_knee_degrees"],
                    sample["right_knee_degrees"])):
                clip_failures.append(
                    f"frame {sample['frame']}: non-finite 3D state")
            if not clip_name.startswith("slide") and height < baseline_height * 0.42:
                clip_failures.append(
                    f"frame {sample['frame']}: collapsed height {height:.3f}")
            if not clip_name.startswith("slide") and max(width, depth) > height * 1.8:
                clip_failures.append(
                    f"frame {sample['frame']}: horizontal explosion "
                    f"span=({width:.3f},{depth:.3f},{height:.3f})")
            if sample["bounds_min"][2] < -0.28:
                clip_failures.append(
                    f"frame {sample['frame']}: ground penetration "
                    f"{sample['bounds_min'][2]:.3f}")
            for side in ("left", "right"):
                if sample[f"{side}_contact"]:
                    key = "l" if side == "left" else "r"
                    drift = abs(sample[f"{side}_ankle_z"]
                                - baseline_ankle[key])
                    if drift > 0.85:
                        clip_failures.append(
                            f"frame {sample['frame']}: planted {side} ankle "
                            f"vertical drift {drift:.3f}")
        clips[clip_name] = {
            "frame_range": [start, end],
            "samples": samples,
            "failures": sorted(set(clip_failures)),
        }
        failures.extend(f"{clip_name}: {failure}"
                        for failure in sorted(set(clip_failures)))

    report = {
        "schema": 1,
        "blend": bpy.data.filepath,
        "baseline_height": round(baseline_height, 6),
        "baseline_ankle_z": {key: round(value, 6)
                             for key, value in baseline_ankle.items()},
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
        f"EVA armature 3D audit: clips={len(clips)} failures={len(failures)} "
        f"output={args.output}"
    )
    if args.strict and failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
