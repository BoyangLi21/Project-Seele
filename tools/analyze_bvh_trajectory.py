#!/usr/bin/env python3
"""Measure and crop a locomotion/turn/stop BVH trajectory in full 3D."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_bvh_locomotion import actor_height, world_point


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-blend", type=Path)
    parser.add_argument("--padding-seconds", type=float, default=0.25)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def unwrap(values: list[float]) -> list[float]:
    output = [values[0]]
    for value in values[1:]:
        while value - output[-1] > math.pi:
            value -= math.tau
        while value - output[-1] < -math.pi:
            value += math.tau
        output.append(value)
    return output


def main() -> None:
    args = parse_args()
    if not args.source.is_file():
        raise SystemExit(f"missing BVH: {args.source}")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_anim.bvh(
        filepath=str(args.source.resolve()), target="ARMATURE",
        global_scale=0.1, frame_start=1, use_fps_scale=False,
        update_scene_fps=True, update_scene_duration=True,
        rotate_mode="NATIVE", axis_forward="-Z", axis_up="Y",
    )
    armatures = [obj for obj in bpy.context.scene.objects
                 if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise SystemExit(f"expected one armature, found {len(armatures)}")
    armature = armatures[0]
    armature.name = "CMU_TRAJECTORY_SOURCE"
    armature.show_in_front = True
    armature.data.display_type = "STICK"
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start, end = scene.frame_start, scene.frame_end
    scene.frame_set(start)
    bpy.context.view_layer.update()
    scale = 1.75 / max(actor_height(armature), 1.0e-6)
    positions = []
    raw_yaw = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        positions.append(world_point(armature, "root") * scale)
        # Derive facing from the physical hip line.  The CMU root bone has a
        # format/import rest-axis rotation which can flip Euler yaw thousands
        # of degrees per second despite a smooth performer trajectory.
        left_hip = world_point(armature, "lfemur")
        right_hip = world_point(armature, "rfemur")
        lateral = right_hip - left_hip
        lateral.z = 0.0
        lateral.normalize()
        forward = Vector((-lateral.y, lateral.x, 0.0))
        raw_yaw.append(math.atan2(forward.x, -forward.y))
    yaw = unwrap(raw_yaw)
    active = []
    speeds = [0.0]
    yaw_speeds = [0.0]
    for index in range(1, len(positions)):
        delta = positions[index] - positions[index - 1]
        speed = math.hypot(delta.x, delta.y) * fps
        yaw_speed = abs(yaw[index] - yaw[index - 1]) * fps
        speeds.append(speed)
        yaw_speeds.append(yaw_speed)
    active = [speed >= 0.22 or yaw_speed >= math.radians(12.0)
              for speed, yaw_speed in zip(speeds, yaw_speeds)]
    active_indices = [index for index, value in enumerate(active) if value]
    if active_indices:
        padding = int(round(args.padding_seconds * fps))
        first = max(0, min(active_indices) - padding)
        last = min(len(positions) - 1, max(active_indices) + padding)
    else:
        first, last = 0, len(positions) - 1
    delta = positions[last] - positions[first]
    segment = {
        "id": "motion_01",
        "start_frame": start + first,
        "end_frame": start + last,
        "duration_seconds": round((last - first) / fps, 6),
        "root_displacement_meters": [
            round(float(delta.x), 7), round(float(delta.z), 7),
            round(float(-delta.y), 7),
        ],
        "horizontal_distance_meters": round(
            math.hypot(delta.x, delta.y), 7
        ),
        "yaw_delta_degrees": round(
            math.degrees(yaw[last] - yaw[first]), 5
        ),
        "peak_speed_mps": round(max(speeds[first:last + 1]), 6),
        "peak_yaw_speed_degrees_per_second": round(
            math.degrees(max(yaw_speeds[first:last + 1])), 6
        ),
    }
    scene.timeline_markers.new("MOTION_START", frame=segment["start_frame"])
    scene.timeline_markers.new("MOTION_END", frame=segment["end_frame"])
    report = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "fps": fps,
        "frame_range": [start, end],
        "source_to_meters": scale,
        "segments": [segment],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.output_blend is not None:
        scene.world.color = (0.008, 0.012, 0.02)
        scene.frame_set(segment["start_frame"])
        text = bpy.data.texts.new("README_CMU_TRAJECTORY_REVIEW")
        text.write(
            "CMU Graphics Lab Motion Capture Database\n"
            "Markers delimit velocity/yaw-derived active trajectory.\n"
        )
        args.output_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    print(
        f"BVH trajectory analysis: frames={end - start + 1} "
        f"distance={segment['horizontal_distance_meters']:.3f}m "
        f"yaw={segment['yaw_delta_degrees']:.2f}deg output={args.output_json}"
    )


if __name__ == "__main__":
    main()
