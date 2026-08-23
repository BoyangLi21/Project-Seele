#!/usr/bin/env python3
"""Extract crawl and floor-transition intervals from a long BVH capture."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_bvh_locomotion import actor_height, quantile, world_point


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--mode", choices=("crawl", "getup", "laydown"),
                        required=True)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-blend", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def moving_average(values: list[float], radius: int) -> list[float]:
    prefix = [0.0]
    for value in values:
        prefix.append(prefix[-1] + value)
    output = []
    for index in range(len(values)):
        left = max(0, index - radius)
        right = min(len(values), index + radius + 1)
        output.append((prefix[right] - prefix[left]) / (right - left))
    return output


def main() -> None:
    args = parse_args()
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
    armature.name = "CMU_POSTURE_SOURCE"
    armature.show_in_front = True
    armature.data.display_type = "STICK"
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    first_frame, last_frame = scene.frame_start, scene.frame_end
    scene.frame_set(first_frame)
    bpy.context.view_layer.update()
    scale = 1.75 / max(actor_height(armature), 1.0e-6)
    roots = []
    heights = []
    for frame in range(first_frame, last_frame + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        root = world_point(armature, "root") * scale
        roots.append(root)
        heights.append(root.z)
    smoothed = moving_average(heights, max(2, int(round(fps * 0.08))))
    low = quantile(smoothed, 0.15)
    high = quantile(smoothed, 0.85)
    if args.mode == "crawl":
        window = min(len(roots), int(round(fps * 3.2)))
        best = None
        for start in range(0, len(roots) - window + 1,
                           max(1, int(round(fps * 0.10)))):
            end = start + window - 1
            median_height = statistics.median(smoothed[start:end + 1])
            distance = (roots[end] - roots[start]).length
            score = distance - max(0.0, median_height - low) * 2.0
            if best is None or score > best[0]:
                best = (score, start, end)
        _, start, end = best
    else:
        derivatives = [0.0] + [smoothed[index] - smoothed[index - 1]
                               for index in range(1, len(smoothed))]
        peak = (max(range(len(derivatives)), key=derivatives.__getitem__)
                if args.mode == "getup" else
                min(range(len(derivatives)), key=derivatives.__getitem__))
        span = max(1.0e-5, high - low)
        low_limit = low + span * 0.18
        high_limit = high - span * 0.12
        if args.mode == "getup":
            before = [index for index in range(0, peak + 1)
                      if smoothed[index] <= low_limit]
            after = [index for index in range(peak, len(smoothed))
                     if smoothed[index] >= high_limit]
        else:
            before = [index for index in range(0, peak + 1)
                      if smoothed[index] >= high_limit]
            after = [index for index in range(peak, len(smoothed))
                     if smoothed[index] <= low_limit]
        pad = int(round(fps * 0.40))
        start = max(0, (before[-1] if before else peak) - pad)
        end = min(len(smoothed) - 1, (after[0] if after else peak) + pad)
    segment = {
        "id": f"{args.mode}_01",
        "start_frame": first_frame + start,
        "end_frame": first_frame + end,
        "duration_seconds": round((end - start) / fps, 6),
        "pelvis_height_start_meters": round(smoothed[start], 6),
        "pelvis_height_end_meters": round(smoothed[end], 6),
        "root_displacement_meters": round((roots[end] - roots[start]).length, 6),
    }
    scene.timeline_markers.new("POSTURE_START", frame=segment["start_frame"])
    scene.timeline_markers.new("POSTURE_END", frame=segment["end_frame"])
    report = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "mode": args.mode,
        "fps": fps,
        "frame_range": [first_frame, last_frame],
        "source_to_meters": scale,
        "pelvis_height_quantiles_meters": {"low": low, "high": high},
        "segments": [segment],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.output_blend is not None:
        text = bpy.data.texts.new("README_CMU_POSTURE_REVIEW")
        text.write(
            "CMU Graphics Lab Motion Capture Database\n"
            f"Selected posture mode: {args.mode}\n"
        )
        scene.world.color = (0.008, 0.012, 0.02)
        scene.frame_set(segment["start_frame"])
        args.output_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    print(
        f"BVH posture analysis: mode={args.mode} "
        f"frames={end - start + 1} output={args.output_json}"
    )


if __name__ == "__main__":
    main()
