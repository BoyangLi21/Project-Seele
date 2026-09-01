#!/usr/bin/env python3
"""Segment BVH kick captures by 3D striking-foot velocity."""

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
    parser.add_argument("--minimum-separation-seconds", type=float, default=0.7)
    parser.add_argument("--lead-seconds", type=float, default=0.58)
    parser.add_argument("--follow-seconds", type=float, default=0.58)
    parser.add_argument("--maximum-events", type=int, default=16)
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


def bone_end(armature: bpy.types.Object, name: str) -> Vector:
    pose_bone = armature.pose.bones[name]
    return armature.matrix_world @ pose_bone.tail


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
    armatures = [
        obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"
    ]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature, found {len(armatures)}")
    armature = armatures[0]
    armature.name = "G1_KICK_SOURCE"
    armature.show_in_front = True
    armature.data.display_type = "STICK"
    available = set(armature.pose.bones.keys())
    if {"LeftFoot", "RightFoot", "Hips"}.issubset(available):
        names = {"left": "LeftFoot", "right": "RightFoot", "root": "Hips"}
    elif {"LFoot", "RFoot", "Hip"}.issubset(available):
        names = {"left": "LFoot", "right": "RFoot", "root": "Hip"}
    else:
        raise RuntimeError(
            "unsupported BVH foot/root names: " + ", ".join(sorted(available))
        )

    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start = scene.frame_start
    end = scene.frame_end
    samples: list[dict[str, object]] = []
    previous: dict[str, Vector] | None = None
    speeds = {"left": [], "right": []}
    root_speeds: list[float] = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        points = {
            "left": bone_end(armature, names["left"]),
            "right": bone_end(armature, names["right"]),
            "root": armature.matrix_world
            @ armature.pose.bones[names["root"]].matrix.translation,
        }
        if previous is None:
            speeds["left"].append(0.0)
            speeds["right"].append(0.0)
            root_speeds.append(0.0)
        else:
            for side in ("left", "right"):
                speeds[side].append((points[side] - previous[side]).length * fps)
            root_speeds.append((points["root"] - previous["root"]).length * fps)
        samples.append({
            "frame": frame,
            "left_foot": [round(float(value), 6) for value in points["left"]],
            "right_foot": [round(float(value), 6) for value in points["right"]],
            "root": [round(float(value), 6) for value in points["root"]],
        })
        previous = points

    radius = max(1, int(round(fps * 0.035)))
    smooth = {
        side: moving_average(values, radius) for side, values in speeds.items()
    }
    combined = [max(smooth["left"][index], smooth["right"][index])
                + root_speeds[index] * 0.08
                for index in range(len(samples))]
    threshold = max(
        quantile(combined, 0.78),
        statistics.median(combined)
        + (quantile(combined, 0.92) - statistics.median(combined)) * 0.42,
    )
    local_peaks = []
    for index in range(1, len(combined) - 1):
        if (combined[index] >= threshold
                and combined[index] >= combined[index - 1]
                and combined[index] >= combined[index + 1]):
            side = "left" if smooth["left"][index] > smooth["right"][index] \
                else "right"
            local_peaks.append((combined[index], index, side))

    separation = max(1, int(round(args.minimum_separation_seconds * fps)))
    selected: list[tuple[float, int, str]] = []
    for candidate in sorted(local_peaks, reverse=True):
        if any(abs(candidate[1] - other[1]) < separation
               for other in selected):
            continue
        selected.append(candidate)
        if len(selected) >= args.maximum_events:
            break
    selected.sort(key=lambda value: value[1])

    lead = int(round(args.lead_seconds * fps))
    follow = int(round(args.follow_seconds * fps))
    segments = []
    for number, (energy, index, side) in enumerate(selected, start=1):
        other = "right" if side == "left" else "left"
        peak_frame = start + index
        left = max(start, peak_frame - lead)
        right = min(end, peak_frame + follow)
        striking_height = float(samples[index][f"{side}_foot"][1])
        support_height = float(samples[index][f"{other}_foot"][1])
        support_speed = float(smooth[other][index])
        segments.append({
            "id": f"kick_{number:02d}",
            "start_frame": left,
            "peak_frame": peak_frame,
            "end_frame": right,
            "duration_seconds": round((right - left) / fps, 5),
            "striking_side": side,
            "peak_energy": round(float(energy), 6),
            "striking_foot_speed": round(float(smooth[side][index]), 6),
            "other_foot_speed": round(support_speed, 6),
            "striking_foot_height": round(striking_height, 6),
            "support_foot_height": round(support_height, 6),
        })
        scene.timeline_markers.new(
            f"KICK_{number:02d}_PEAK_{side.upper()}", frame=peak_frame
        )

    report = {
        "schema": 1,
        "authority": "striking_foot_velocity_source_segmentation",
        "automatic_visual_approval": False,
        "source": str(args.source.resolve()),
        "fps": fps,
        "frame_range": [start, end],
        "threshold": threshold,
        "segments": segments,
        "trajectory_samples": samples,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.output_blend is not None:
        args.output_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    print(
        f"BVH kick segmentation: frames={end - start + 1} "
        f"segments={len(segments)} threshold={threshold:.5f} "
        f"output={args.output_json}"
    )


if __name__ == "__main__":
    main()
