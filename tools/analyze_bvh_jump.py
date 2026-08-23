#!/usr/bin/env python3
"""Extract take-off/apex/landing intervals from a BVH in 3D."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_bvh_locomotion import (
    actor_height,
    quantile,
    smooth_boolean,
    world_point,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-blend", type=Path)
    parser.add_argument("--pre-roll-seconds", type=float, default=0.28)
    parser.add_argument("--post-roll-seconds", type=float, default=0.34)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


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
    armature.name = "CMU_JUMP_SOURCE"
    armature.show_in_front = True
    armature.data.display_type = "STICK"
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start, end = scene.frame_start, scene.frame_end
    scene.frame_set(start)
    bpy.context.view_layer.update()
    source_to_meters = 1.75 / max(actor_height(armature), 1.0e-6)
    samples = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples.append({
            "frame": frame,
            "root_z": world_point(armature, "root").z,
            "left": min(world_point(armature, "lfoot").z,
                        world_point(armature, "ltoes").z),
            "right": min(world_point(armature, "rfoot").z,
                         world_point(armature, "rtoes").z),
        })
    floor = quantile(
        [sample[side] for sample in samples for side in ("left", "right")],
        0.015,
    )
    limit = floor + 0.07 / source_to_meters
    contacts = {"left": [], "right": []}
    for index, sample in enumerate(samples):
        for side in ("left", "right"):
            speed = 0.0 if index == 0 else abs(
                sample[side] - samples[index - 1][side]
            ) * fps * source_to_meters
            contacts[side].append(sample[side] <= limit and speed <= 0.48)
    radius = max(1, int(round(fps * 0.025)))
    contacts = {side: smooth_boolean(values, radius)
                for side, values in contacts.items()}
    airborne = [not contacts["left"][index]
                and not contacts["right"][index]
                for index in range(len(samples))]
    intervals = []
    opened = None
    for index, active in enumerate(airborne):
        if active and opened is None:
            opened = index
        elif not active and opened is not None:
            intervals.append((opened, index - 1))
            opened = None
    if opened is not None:
        intervals.append((opened, len(samples) - 1))
    minimum = int(round(fps * 0.16))
    pre = int(round(fps * args.pre_roll_seconds))
    post = int(round(fps * args.post_roll_seconds))
    jumps = []
    for first, last in intervals:
        if last - first + 1 < minimum:
            continue
        apex_index = max(range(first, last + 1),
                         key=lambda index: samples[index]["root_z"])
        segment_start = max(0, first - pre)
        segment_end = min(len(samples) - 1, last + post)
        base_root = min(samples[first]["root_z"], samples[last]["root_z"])
        apex_height = ((samples[apex_index]["root_z"] - base_root)
                       * source_to_meters)
        if apex_height < 0.10:
            continue
        jump = {
            "id": f"jump_{len(jumps) + 1:02d}",
            "start_frame": samples[segment_start]["frame"],
            "takeoff_frame": samples[first]["frame"],
            "apex_frame": samples[apex_index]["frame"],
            "landing_frame": samples[last]["frame"],
            "end_frame": samples[segment_end]["frame"],
            "airborne_seconds": round((last - first) / fps, 6),
            "apex_height_meters": round(apex_height, 6),
        }
        jumps.append(jump)
        for label in ("start", "takeoff", "apex", "landing", "end"):
            scene.timeline_markers.new(
                f"{jump['id'].upper()}_{label.upper()}",
                frame=jump[f"{label}_frame"],
            )
    report = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "fps": fps,
        "frame_range": [start, end],
        "source_to_meters": source_to_meters,
        "floor_source_units": floor,
        "jumps": jumps,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.output_blend is not None:
        scene.world.color = (0.008, 0.012, 0.02)
        scene.frame_set(start)
        text = bpy.data.texts.new("README_CMU_JUMP_REVIEW")
        text.write(
            "CMU Graphics Lab Motion Capture Database\n"
            "Markers identify measured take-off, apex and landing frames.\n"
        )
        args.output_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    print(
        f"BVH jump analysis: frames={end - start + 1} jumps={len(jumps)} "
        f"output={args.output_json}"
    )


if __name__ == "__main__":
    main()
