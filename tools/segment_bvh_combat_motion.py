#!/usr/bin/env python3
"""Segment long BVH combat captures by 3D wrist-velocity energy."""

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
    parser.add_argument("--merge-gap-seconds", type=float, default=0.42)
    parser.add_argument("--expand-seconds", type=float, default=0.22)
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


def merge_intervals(intervals: list[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    merged = []
    for start, end in intervals:
        if merged and start - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


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
    armature.name = "CMU_COMBAT_SOURCE"
    armature.show_in_front = True
    armature.data.display_type = "STICK"
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start = scene.frame_start
    end = scene.frame_end
    previous = None
    raw_energy = []
    trajectories = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        left = armature.pose.bones["lwrist"].matrix.translation.copy()
        right = armature.pose.bones["rwrist"].matrix.translation.copy()
        root = armature.pose.bones["root"].matrix.translation.copy()
        trajectories.append({
            "frame": frame,
            "left_wrist": [round(float(value), 6) for value in left],
            "right_wrist": [round(float(value), 6) for value in right],
            "root": [round(float(value), 6) for value in root],
        })
        if previous is None:
            raw_energy.append(0.0)
        else:
            left_speed = (left - previous[0]).length * fps
            right_speed = (right - previous[1]).length * fps
            root_speed = (root - previous[2]).length * fps
            raw_energy.append(max(left_speed, right_speed) + root_speed * 0.18)
        previous = (left, right, root)
    smoothed = moving_average(raw_energy, max(2, int(round(fps * 0.055))))
    median = statistics.median(smoothed)
    p85 = quantile(smoothed, 0.85)
    p96 = quantile(smoothed, 0.96)
    threshold = median + (p85 - median) * 0.72
    # Avoid a near-zero threshold in long static lead-ins.
    threshold = max(threshold, p96 * 0.20)
    active = [value >= threshold for value in smoothed]
    intervals = []
    open_start = None
    for index, enabled in enumerate(active):
        frame = start + index
        if enabled and open_start is None:
            open_start = frame
        elif not enabled and open_start is not None:
            intervals.append((open_start, frame - 1))
            open_start = None
    if open_start is not None:
        intervals.append((open_start, end))
    intervals = merge_intervals(
        intervals, int(round(args.merge_gap_seconds * fps))
    )
    expand = int(round(args.expand_seconds * fps))
    intervals = [(max(start, left - expand), min(end, right + expand))
                 for left, right in intervals]
    intervals = [item for item in intervals
                 if item[1] - item[0] >= int(round(fps * 0.24))]

    segments = []
    for index, (left, right) in enumerate(intervals, start=1):
        local = smoothed[left - start:right - start + 1]
        peak_offset = max(range(len(local)), key=local.__getitem__)
        peak_frame = left + peak_offset
        segments.append({
            "id": f"strike_{index:02d}",
            "start_frame": left,
            "peak_frame": peak_frame,
            "end_frame": right,
            "duration_seconds": round((right - left) / fps, 4),
            "peak_energy": round(local[peak_offset], 6),
        })
        scene.timeline_markers.new(f"STRIKE_{index:02d}_START", frame=left)
        scene.timeline_markers.new(f"STRIKE_{index:02d}_PEAK", frame=peak_frame)
        scene.timeline_markers.new(f"STRIKE_{index:02d}_END", frame=right)

    report = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "fps": fps,
        "frame_range": [start, end],
        "energy": {
            "median": median,
            "p85": p85,
            "p96": p96,
            "threshold": threshold,
        },
        "segments": segments,
        "trajectory_samples": trajectories,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.output_blend is not None:
        scene.world.color = (0.008, 0.012, 0.02)
        scene.frame_set(start)
        text = bpy.data.texts.new("README_CMU_COMBAT_REVIEW")
        text.write(
            "CMU Graphics Lab Motion Capture Database\n"
            "Source: mocap.cs.cmu.edu\n"
            "Timeline markers are velocity-derived candidate strikes;\n"
            "review them in 3D before any retarget is accepted.\n"
        )
        args.output_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    print(
        f"BVH combat segmentation: frames={end - start + 1} "
        f"segments={len(segments)} threshold={threshold:.4f} "
        f"output={args.output_json}"
    )


if __name__ == "__main__":
    main()
