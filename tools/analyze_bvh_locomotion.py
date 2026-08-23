#!/usr/bin/env python3
"""Extract stable gait cycles from a BVH in Blender's full 3D scene.

The analyser never renders screenshots.  It measures the actual armature in
world space, derives a scale-independent floor/contact signal, and writes
cycle boundaries that can be consumed by the EVA retarget pipeline.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-blend", type=Path)
    parser.add_argument("--minimum-cycle-seconds", type=float, default=0.42)
    parser.add_argument("--maximum-cycle-seconds", type=float, default=1.8)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def quantile(values: list[float], amount: float) -> float:
    ordered = sorted(values)
    position = amount * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    alpha = position - low
    return ordered[low] * (1.0 - alpha) + ordered[high] * alpha


def world_point(armature: bpy.types.Object, bone_name: str) -> Vector:
    return armature.matrix_world @ armature.pose.bones[bone_name].matrix.translation


def actor_height(armature: bpy.types.Object) -> float:
    points = [world_point(armature, name) for name in (
        "head", "lfoot", "ltoes", "rfoot", "rtoes"
    )]
    return max(point.z for point in points) - min(point.z for point in points)


def smooth_boolean(values: list[bool], radius: int) -> list[bool]:
    output = []
    for index in range(len(values)):
        left = max(0, index - radius)
        right = min(len(values), index + radius + 1)
        window = values[left:right]
        output.append(sum(window) * 2 >= len(window))
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
    armature.name = "CMU_LOCOMOTION_SOURCE"
    armature.show_in_front = True
    armature.data.display_type = "STICK"
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start = scene.frame_start
    end = scene.frame_end

    scene.frame_set(start)
    bpy.context.view_layer.update()
    height = actor_height(armature)
    source_to_meters = 1.75 / max(height, 1.0e-6)
    samples: list[dict] = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        root = world_point(armature, "root")
        left_foot = world_point(armature, "lfoot")
        left_toe = world_point(armature, "ltoes")
        right_foot = world_point(armature, "rfoot")
        right_toe = world_point(armature, "rtoes")
        samples.append({
            "frame": frame,
            "root": root,
            "left": min(left_foot.z, left_toe.z),
            "right": min(right_foot.z, right_toe.z),
        })
    floor = quantile(
        [sample[side] for sample in samples for side in ("left", "right")],
        0.015,
    )
    height_limit = floor + 0.07 / source_to_meters
    speed_limit = 0.42
    raw_contacts: dict[str, list[bool]] = {"left": [], "right": []}
    for index, sample in enumerate(samples):
        for side in ("left", "right"):
            if index == 0:
                vertical_speed = 0.0
            else:
                vertical_speed = abs(sample[side] - samples[index - 1][side]) \
                    * fps * source_to_meters
            raw_contacts[side].append(
                sample[side] <= height_limit and vertical_speed <= speed_limit
            )
    radius = max(1, int(round(fps * 0.025)))
    contacts = {
        side: smooth_boolean(raw_contacts[side], radius)
        for side in ("left", "right")
    }

    strikes: dict[str, list[int]] = {"left": [], "right": []}
    minimum_gap = int(round(args.minimum_cycle_seconds * fps * 0.62))
    for side in ("left", "right"):
        last = -10_000
        for index in range(1, len(samples)):
            if contacts[side][index] and not contacts[side][index - 1]:
                frame = start + index
                if frame - last >= minimum_gap:
                    strikes[side].append(frame)
                    last = frame

    cycles = []
    minimum = int(round(args.minimum_cycle_seconds * fps))
    maximum = int(round(args.maximum_cycle_seconds * fps))
    for side in ("left", "right"):
        for first, second in zip(strikes[side], strikes[side][1:]):
            duration_frames = second - first
            if not minimum <= duration_frames <= maximum:
                continue
            a = samples[first - start]["root"]
            b = samples[second - start]["root"]
            delta = (b - a) * source_to_meters
            horizontal = math.hypot(delta.x, delta.y)
            duration = duration_frames / fps
            cycles.append({
                "id": f"{side}_cycle_{len(cycles) + 1:02d}",
                "side": side,
                "start_frame": first,
                "end_frame": second,
                "duration_seconds": round(duration, 6),
                "stride_meters": round(horizontal, 6),
                "speed_mps": round(horizontal / max(duration, 1.0e-6), 6),
                "vertical_root_delta_m": round(delta.z, 6),
            })
    speeds = [cycle["speed_mps"] for cycle in cycles]
    median_speed = statistics.median(speeds) if speeds else 0.0
    for cycle in cycles:
        cycle["stable"] = (
            abs(cycle["speed_mps"] - median_speed) <= max(0.35, median_speed * 0.35)
            and abs(cycle["vertical_root_delta_m"]) <= 0.12
        )
        scene.timeline_markers.new(
            f"{cycle['id'].upper()}_START", frame=cycle["start_frame"]
        )
        scene.timeline_markers.new(
            f"{cycle['id'].upper()}_END", frame=cycle["end_frame"]
        )

    report = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "fps": fps,
        "frame_range": [start, end],
        "actor_height_source_units": height,
        "source_to_meters": source_to_meters,
        "floor_source_units": floor,
        "contact_height_limit_source_units": height_limit,
        "contact_vertical_speed_limit_mps": speed_limit,
        "heel_strikes": strikes,
        "cycles": cycles,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.output_blend is not None:
        scene.world.color = (0.008, 0.012, 0.02)
        scene.frame_set(start)
        text = bpy.data.texts.new("README_CMU_LOCOMOTION_REVIEW")
        text.write(
            "CMU Graphics Lab Motion Capture Database\n"
            "Timeline markers delimit measured same-foot gait cycles.\n"
            "Stable cycles are selected by speed and vertical-root continuity.\n"
        )
        args.output_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    print(
        f"BVH locomotion analysis: frames={end - start + 1} "
        f"cycles={len(cycles)} stable={sum(c['stable'] for c in cycles)} "
        f"output={args.output_json}"
    )


if __name__ == "__main__":
    main()
