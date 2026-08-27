#!/usr/bin/env python3
"""Detect locomotion, turn, jump, and foot-contact events in a BVH."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_bvh_locomotion import actor_height, quantile, world_point


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--profile", choices=("100style", "accad", "cmu"),
                        default="100style")
    parser.add_argument("--cut-start", type=int)
    parser.add_argument("--cut-end", type=int)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


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


def unwrap(values: list[float]) -> list[float]:
    output = [values[0]]
    for value in values[1:]:
        while value - output[-1] > math.pi:
            value -= math.tau
        while value - output[-1] < -math.pi:
            value += math.tau
        output.append(value)
    return output


def boolean_segments(values: list[bool], minimum: int,
                     fill_gap: int = 1) -> list[tuple[int, int]]:
    values = list(values)
    for gap in range(1, fill_gap + 1):
        for index in range(gap, len(values) - gap):
            if values[index]:
                continue
            if values[index - gap] and values[index + gap]:
                values[index] = True
    segments = []
    start = None
    for index, value in enumerate(values):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(values) - 1):
            end = index if value and index == len(values) - 1 else index - 1
            if end - start + 1 >= minimum:
                segments.append((start, end))
            start = None
    return segments


def sustained(values: list[float], start: int, count: int,
              predicate) -> bool:
    end = min(len(values), start + count)
    return end - start == count and all(predicate(value)
                                        for value in values[start:end])


def main() -> None:
    args = parse_args()
    if not args.source.is_file():
        raise SystemExit(f"missing BVH: {args.source}")

    names = ({
        "root": "Hips", "head": "Head",
        "left_hip": "LeftHip", "right_hip": "RightHip",
        "left_foot": "LeftAnkle", "left_toe": "LeftToe",
        "right_foot": "RightAnkle", "right_toe": "RightToe",
    } if args.profile == "100style" else ({
        "root": "Hips", "head": "Head",
        "left_hip": "LeftUpLeg", "right_hip": "RightUpLeg",
        "left_foot": "LeftFoot", "left_toe": "LeftToeBase",
        "right_foot": "RightFoot", "right_toe": "RightToeBase",
    } if args.profile in {"accad", "cmu"} else {
        "root": "root", "head": "head",
        "left_hip": "lfemur", "right_hip": "rfemur",
        "left_foot": "lfoot", "left_toe": "ltoes",
        "right_foot": "rfoot", "right_toe": "rtoes",
    }))

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
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    first = max(scene.frame_start, args.cut_start or scene.frame_start)
    last = min(scene.frame_end, args.cut_end or scene.frame_end)
    if first >= last:
        raise SystemExit(f"invalid cut: {first}-{last}")

    scene.frame_set(first)
    bpy.context.view_layer.update()
    scale = 1.75 / max(actor_height(armature, names), 1.0e-6)
    frames = list(range(first, last + 1))
    roots = []
    raw_yaw = []
    feet = {"l": [], "r": []}
    foot_heights = {"l": [], "r": []}
    root_heights = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        root = world_point(armature, names["root"]) * scale
        roots.append(root)
        root_heights.append(root.z)

        left_hip = world_point(armature, names["left_hip"])
        right_hip = world_point(armature, names["right_hip"])
        lateral = right_hip - left_hip
        lateral.z = 0.0
        if lateral.length < 1.0e-7:
            lateral = Vector((1.0, 0.0, 0.0))
        lateral.normalize()
        forward = Vector((-lateral.y, lateral.x, 0.0))
        raw_yaw.append(math.atan2(forward.x, -forward.y))

        for side, label in (("l", "left"), ("r", "right")):
            ankle = world_point(armature, names[f"{label}_foot"]) * scale
            toe = world_point(armature, names[f"{label}_toe"]) * scale
            feet[side].append(ankle)
            foot_heights[side].append(min(ankle.z, toe.z))

    dt = 1.0 / fps
    yaw = unwrap(raw_yaw)
    speeds = []
    velocity_x = []
    velocity_y = []
    vertical_speeds = []
    yaw_speeds = []
    for index in range(len(frames)):
        before = max(0, index - 1)
        after = min(len(frames) - 1, index + 1)
        duration = max(dt, (after - before) * dt)
        delta = roots[after] - roots[before]
        velocity_x.append(delta.x / duration)
        velocity_y.append(delta.y / duration)
        speeds.append(math.hypot(delta.x, delta.y) / duration)
        vertical_speeds.append(delta.z / duration)
        yaw_speeds.append((yaw[after] - yaw[before]) / duration)
    radius = max(1, int(round(fps * 0.05)))
    speeds = moving_average(speeds, radius)
    velocity_x = moving_average(velocity_x, radius)
    velocity_y = moving_average(velocity_y, radius)
    vertical_speeds = moving_average(vertical_speeds, radius)
    yaw_speeds = moving_average(yaw_speeds, radius)
    raw_path_yaw = []
    previous_path_yaw = yaw[0]
    for speed, x_value, y_value in zip(speeds, velocity_x, velocity_y):
        if speed >= 0.15:
            previous_path_yaw = math.atan2(x_value, -y_value)
        raw_path_yaw.append(previous_path_yaw)
    path_yaw = unwrap(raw_path_yaw)
    facing_velocity_dots = []
    for speed, body_yaw, path_heading in zip(speeds, yaw, path_yaw):
        if speed >= 0.20:
            facing_velocity_dots.append(math.cos(body_yaw - path_heading))

    contacts = {}
    contact_segments = {}
    for side in ("l", "r"):
        floor = quantile(foot_heights[side], 0.02)
        horizontal_speeds = []
        for index in range(len(frames)):
            before = max(0, index - 1)
            after = min(len(frames) - 1, index + 1)
            duration = max(dt, (after - before) * dt)
            delta = feet[side][after] - feet[side][before]
            horizontal_speeds.append(math.hypot(delta.x, delta.y)
                                     / duration)
        contacts[side] = [
            height <= floor + 0.03 * 1.75 and speed <= 0.25 * 1.75
            for height, speed in zip(foot_heights[side], horizontal_speeds)
        ]
        contact_segments[side] = boolean_segments(
            contacts[side], minimum=max(2, int(round(fps * 0.04))),
            fill_gap=max(1, int(round(fps * 0.02))),
        )
        contacts[side] = [False] * len(frames)
        for start, end in contact_segments[side]:
            for index in range(start, end + 1):
                contacts[side][index] = True

    events = []
    still_limit = 0.08
    moving_limit = 0.35
    sustain_count = max(3, int(round(fps * 0.10)))
    state = "still" if sustained(
        speeds, 0, sustain_count, lambda value: value <= still_limit
    ) else "moving"
    index = sustain_count
    while index < len(frames) - sustain_count:
        if state == "still" and sustained(
                speeds, index, sustain_count,
                lambda value: value >= moving_limit):
            begin = max(0, index - int(round(fps * 0.30)))
            end = min(len(frames) - 1, index + int(round(fps * 0.65)))
            events.append({
                "type": "LOCOMOTION_START",
                "frame": frames[index],
                "segment": [frames[begin], frames[end]],
                "peak_speed_mps": max(speeds[begin:end + 1]),
            })
            state = "moving"
            index += sustain_count
            continue
        if state == "moving" and sustained(
                speeds, index, sustain_count,
                lambda value: value <= still_limit):
            begin = max(0, index - int(round(fps * 0.65)))
            end = min(len(frames) - 1, index + int(round(fps * 0.35)))
            events.append({
                "type": "LOCOMOTION_STOP",
                "frame": frames[index],
                "segment": [frames[begin], frames[end]],
                "entry_speed_mps": max(speeds[begin:index + 1]),
            })
            state = "still"
            index += sustain_count
            continue
        index += 1

    turning = [abs(value) >= math.radians(25.0) for value in yaw_speeds]
    for start, end in boolean_segments(
            turning, minimum=max(3, int(round(fps * 0.10))),
            fill_gap=max(1, int(round(fps * 0.05)))):
        padding = int(round(fps * 0.10))
        begin = max(0, start - padding)
        finish = min(len(frames) - 1, end + padding)
        delta_degrees = math.degrees(yaw[finish] - yaw[begin])
        if abs(delta_degrees) < 30.0:
            continue
        median_speed = statistics.median(speeds[begin:finish + 1])
        path_delta_degrees = math.degrees(
            path_yaw[finish] - path_yaw[begin])
        in_place = median_speed < 0.15
        if not in_place:
            if abs(path_delta_degrees) < 25.0:
                continue
            if delta_degrees * path_delta_degrees <= 0.0:
                continue
        nearest = min((45, 90, 135, 180),
                      key=lambda value: abs(abs(delta_degrees) - value))
        events.append({
            "type": "TURN",
            "segment": [frames[begin], frames[finish]],
            "direction": "left" if delta_degrees > 0.0 else "right",
            "yaw_delta_degrees": delta_degrees,
            "path_yaw_delta_degrees": path_delta_degrees,
            "nominal_angle_degrees": nearest,
            "median_speed_mps": median_speed,
            "mode": "in_place" if in_place else "moving",
        })

    airborne = [not contacts["l"][index] and not contacts["r"][index]
                for index in range(len(frames))]
    for start, end in boolean_segments(
            airborne, minimum=max(3, int(round(fps * 0.08))), fill_gap=1):
        if start == 0 or end == len(frames) - 1:
            continue
        apex = max(range(start, end + 1), key=root_heights.__getitem__)
        airborne_seconds = (end - start + 1) / fps
        root_rise = root_heights[apex] - root_heights[start]
        takeoff_speed = max(vertical_speeds[
            max(0, start - 2):min(len(frames), start + 3)])
        if (airborne_seconds < 0.18 or root_rise < 0.08
                or takeoff_speed < 0.40):
            continue
        events.append({
            "type": "JUMP",
            "takeoff_frame": frames[start],
            "apex_frame": frames[apex],
            "land_frame": frames[end + 1],
            "airborne_seconds": airborne_seconds,
            "root_rise_meters": root_rise,
            "takeoff_vertical_speed_mps": takeoff_speed,
        })

    for side in ("l", "r"):
        label = "L" if side == "l" else "R"
        for start, end in contact_segments[side]:
            events.append({
                "type": f"{label}_FOOT_CONTACT",
                "strike_frame": frames[start],
                "release_frame": frames[end],
                "duration_seconds": (end - start + 1) / fps,
            })

    boundary_indices = {0, len(frames) - 1}
    for side in ("l", "r"):
        for start, end in contact_segments[side]:
            boundary_indices.add(start)
            boundary_indices.add(end)
    boundary_indices = sorted(boundary_indices)
    turn_candidates = []
    minimum_turn_frames = max(3, int(round(fps * 0.25)))
    maximum_turn_frames = max(minimum_turn_frames,
                              int(round(fps * 3.0)))
    for start in boundary_indices:
        for end in boundary_indices:
            duration_frames = end - start
            if duration_frames < minimum_turn_frames:
                continue
            if duration_frames > maximum_turn_frames:
                break
            delta_degrees = math.degrees(yaw[end] - yaw[start])
            if abs(delta_degrees) < 30.0:
                continue
            root_delta = roots[end] - roots[start]
            root_displacement = math.hypot(root_delta.x, root_delta.y)
            if root_displacement > 0.20 * 1.75:
                continue
            target_angle = min((45, 90, 135, 180),
                               key=lambda value: abs(abs(delta_degrees)
                                                     - value))
            angle_error = abs(abs(delta_degrees) - target_angle)
            if angle_error > max(12.0, target_angle * 0.12):
                continue
            start_mask = [contacts["l"][start], contacts["r"][start]]
            end_mask = [contacts["l"][end], contacts["r"][end]]
            endpoint_penalty = (0.0 if any(start_mask) and any(end_mask)
                                else 1.0)
            score = (angle_error / target_angle
                     + root_displacement / (0.20 * 1.75)
                     + endpoint_penalty)
            turn_candidates.append({
                "segment": [frames[start], frames[end]],
                "direction": "left" if delta_degrees > 0.0 else "right",
                "nominal_angle_degrees": target_angle,
                "yaw_delta_degrees": delta_degrees,
                "angle_error_degrees": angle_error,
                "duration_seconds": duration_frames / fps,
                "root_displacement_meters": root_displacement,
                "start_contact": start_mask,
                "end_contact": end_mask,
                "score": score,
            })
    selected_turn_candidates = []
    for direction in ("left", "right"):
        for target_angle in (45, 90, 135, 180):
            matches = [
                candidate for candidate in turn_candidates
                if candidate["direction"] == direction
                and candidate["nominal_angle_degrees"] == target_angle
            ]
            matches.sort(key=lambda candidate: candidate["score"])
            selected_turn_candidates.extend(matches[:3])

    def event_frame(event: dict) -> int:
        for key in ("frame", "takeoff_frame", "strike_frame"):
            if key in event:
                return int(event[key])
        return int(event.get("segment", [0])[0])

    events.sort(key=event_frame)
    report = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "profile": args.profile,
        "fps": fps,
        "source_frame_range": [scene.frame_start, scene.frame_end],
        "analysis_cut": [first, last],
        "source_to_meters": scale,
        "thresholds": {
            "stationary_mps": still_limit,
            "moving_mps": moving_limit,
            "turn_degrees_per_second": 25.0,
            "foot_height_body_heights": 0.03,
            "foot_speed_body_heights_per_second": 0.25,
            "jump_min_airborne_seconds": 0.18,
            "jump_min_root_rise_meters": 0.08,
            "jump_min_takeoff_vertical_speed_mps": 0.40,
        },
        "root_speed_mps": {
            "minimum": min(speeds),
            "median": statistics.median(speeds),
            "p95": quantile(speeds, 0.95),
            "maximum": max(speeds),
        },
        "facing_velocity_dot": {
            "sample_count": len(facing_velocity_dots),
            "median": (statistics.median(facing_velocity_dots)
                       if facing_velocity_dots else None),
            "p05": (quantile(facing_velocity_dots, 0.05)
                    if facing_velocity_dots else None),
        },
        "event_count": len(events),
        "events": events,
        "turn_candidates": selected_turn_candidates,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    counts = {}
    for event in events:
        counts[event["type"]] = counts.get(event["type"], 0) + 1
    print(json.dumps({"source": args.source.name, "counts": counts,
                      "output": str(args.output_json)}, indent=2))


if __name__ == "__main__":
    main()
