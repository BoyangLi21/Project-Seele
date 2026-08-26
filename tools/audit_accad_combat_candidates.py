#!/usr/bin/env python3
"""Rank ACCAD Male-2 punch captures before any EVA retargeting.

Run through Blender.  The report deliberately measures the original performer
first: whole-body timing, elbow extension, guard position, planted feet and
pelvis/chest contribution.  A bad source clip is never repaired into a target.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector


PUNCH_RE = re.compile(
    r"Male2_E(?P<number>\d+)_(?P<label>Jab|Cross|Hook|Uppercut|BodyHook|"
    r"Backfist|BodyCross|BodyJab)(?P<side>Left|Right)\.bvh$",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for action in tuple(bpy.data.actions):
        bpy.data.actions.remove(action)
    for armature in tuple(bpy.data.armatures):
        bpy.data.armatures.remove(armature)


def point(rig: bpy.types.Object, name: str, tail: bool = False) -> Vector:
    bone = rig.pose.bones[name]
    return rig.matrix_world @ (bone.tail if tail else bone.head)


def angle(a: Vector, b: Vector, c: Vector) -> float:
    first = a - b
    second = c - b
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return 0.0
    return math.degrees(first.angle(second))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = fraction * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    blend = position - lower
    return ordered[lower] * (1.0 - blend) + ordered[upper] * blend


def unwrap(values: list[float]) -> list[float]:
    result = [values[0]]
    for value in values[1:]:
        while value - result[-1] > math.pi:
            value -= math.tau
        while value - result[-1] < -math.pi:
            value += math.tau
        result.append(value)
    return result


def planar_yaw(left: Vector, right: Vector) -> float:
    lateral = right - left
    lateral.z = 0.0
    if lateral.length < 1.0e-8:
        return 0.0
    lateral.normalize()
    forward = Vector((-lateral.y, lateral.x, 0.0))
    return math.atan2(forward.x, forward.y)


def analyse(path: Path, label: str, side: str) -> dict:
    clean_scene()
    bpy.ops.import_anim.bvh(
        filepath=str(path.resolve()), target="ARMATURE", global_scale=0.01,
        frame_start=1, use_fps_scale=False, update_scene_fps=True,
        update_scene_duration=True, rotate_mode="NATIVE",
        axis_forward="-Z", axis_up="Y",
    )
    rig = next(obj for obj in bpy.context.scene.objects
               if obj.type == "ARMATURE")
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    action = rig.animation_data.action
    action_start = int(math.ceil(action.frame_range[0]))
    action_end = int(math.floor(action.frame_range[1]))
    frames = list(range(action_start, action_end + 1))
    dt = 1.0 / fps

    strike_prefix = "Left" if side == "left" else "Right"
    guard_prefix = "Right" if side == "left" else "Left"
    samples = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        hips = point(rig, "Hips")
        head = point(rig, "Head", tail=True)
        left_hip = point(rig, "LeftUpLeg")
        right_hip = point(rig, "RightUpLeg")
        left_shoulder = point(rig, "LeftArm")
        right_shoulder = point(rig, "RightArm")
        chest = (left_shoulder + right_shoulder) * 0.5
        shoulder = point(rig, f"{strike_prefix}Arm")
        elbow = point(rig, f"{strike_prefix}ForeArm")
        wrist = point(rig, f"{strike_prefix}Hand")
        fist = point(rig, f"{strike_prefix}Hand", tail=True)
        guard_shoulder = point(rig, f"{guard_prefix}Arm")
        guard_elbow = point(rig, f"{guard_prefix}ForeArm")
        guard_wrist = point(rig, f"{guard_prefix}Hand")
        guard_fist = point(rig, f"{guard_prefix}Hand", tail=True)
        left_knee = point(rig, "LeftLeg")
        right_knee = point(rig, "RightLeg")
        left_ankle = point(rig, "LeftFoot")
        right_ankle = point(rig, "RightFoot")
        samples.append({
            "hips": hips, "head": head, "chest": chest,
            "left_hip": left_hip, "right_hip": right_hip,
            "left_shoulder": left_shoulder, "right_shoulder": right_shoulder,
            "shoulder": shoulder, "elbow": elbow, "wrist": wrist,
            "fist": fist, "guard_shoulder": guard_shoulder,
            "guard_elbow": guard_elbow, "guard_wrist": guard_wrist,
            "guard_fist": guard_fist, "left_knee": left_knee,
            "right_knee": right_knee, "left_ankle": left_ankle,
            "right_ankle": right_ankle,
        })

    heights = [sample["head"].z
               - min(sample["left_ankle"].z, sample["right_ankle"].z)
               for sample in samples]
    body_height = percentile(heights, 0.50)
    scale = 1.75 / max(body_height, 1.0e-6)
    for sample in samples:
        for key, value in sample.items():
            sample[key] = value * scale

    pelvis_yaw = unwrap([planar_yaw(sample["left_hip"], sample["right_hip"])
                         for sample in samples])
    chest_yaw = unwrap([planar_yaw(sample["left_shoulder"],
                                   sample["right_shoulder"])
                        for sample in samples])
    start_forward = Vector((math.sin(pelvis_yaw[0]),
                            math.cos(pelvis_yaw[0]), 0.0))
    start_lateral = Vector((start_forward.y, -start_forward.x, 0.0))

    relative_fists = [sample["fist"] - sample["hips"] for sample in samples]
    forward_reach = [value.dot(start_forward) for value in relative_fists]
    arm_extension = [(sample["fist"] - sample["shoulder"]).length
                     for sample in samples]
    # Full extension is a better contact proxy than peak velocity; the latter
    # occurs before impact in every properly decelerated punch.
    contact = max(range(len(samples)), key=arm_extension.__getitem__)
    windup = min(range(contact + 1), key=forward_reach.__getitem__)

    fist_speeds = []
    foot_speeds = {"left": [], "right": []}
    for index in range(len(samples)):
        before = max(0, index - 1)
        after = min(len(samples) - 1, index + 1)
        duration = max(dt, (after - before) * dt)
        fist_speeds.append((relative_fists[after]
                            - relative_fists[before]).length / duration)
        for foot in ("left", "right"):
            delta = (samples[after][f"{foot}_ankle"]
                     - samples[before][f"{foot}_ankle"])
            foot_speeds[foot].append(delta.length / duration)

    peak_radius = max(2, int(round(fps * 0.12)))
    prominence_radius = max(peak_radius + 1, int(round(fps * 0.55)))
    peak_indices = []
    for index in range(peak_radius, len(samples) - peak_radius):
        local = arm_extension[index - peak_radius:index + peak_radius + 1]
        if arm_extension[index] < max(local) - 1.0e-7:
            continue
        before = arm_extension[max(0, index - prominence_radius):index + 1]
        after = arm_extension[index:min(len(samples),
                                        index + prominence_radius + 1)]
        prominence = min(arm_extension[index] - min(before),
                         arm_extension[index] - min(after))
        approach_speed = max(fist_speeds[max(0, index - peak_radius * 2):
                                         index + 1])
        if prominence < 0.10 or approach_speed < 1.0:
            continue
        if peak_indices and index - peak_indices[-1] < int(round(fps * 0.55)):
            if arm_extension[index] > arm_extension[peak_indices[-1]]:
                peak_indices[-1] = index
            continue
        peak_indices.append(index)
    strike_events = []
    lead = int(round(fps * 0.60))
    trail = int(round(fps * 0.72))
    for event_index, peak in enumerate(peak_indices, 1):
        start = max(0, peak - lead)
        end = min(len(samples) - 1, peak + trail)
        strike_events.append({
            "id": f"take_{event_index:02d}",
            "source_window": [frames[start], frames[end]],
            "contact_frame": frames[peak],
            "duration_seconds": (end - start) / fps,
            "extension_meters": arm_extension[peak],
            "approach_peak_speed_mps": max(fist_speeds[start:peak + 1]),
            "return_error_meters": (samples[end]["fist"]
                                    - samples[start]["fist"]).length,
        })

    contact_sample = samples[contact]
    strike_elbow = angle(contact_sample["shoulder"],
                         contact_sample["elbow"], contact_sample["wrist"])
    guard_elbow = angle(contact_sample["guard_shoulder"],
                        contact_sample["guard_elbow"],
                        contact_sample["guard_wrist"])
    guard_to_head = (contact_sample["guard_fist"]
                     - contact_sample["head"]).length
    guard_to_chest = (contact_sample["guard_fist"]
                      - contact_sample["chest"]).length

    root_displacement = (samples[-1]["hips"] - samples[0]["hips"]).length
    lateral_displacement = abs((samples[contact]["hips"]
                                - samples[0]["hips"]).dot(start_lateral))
    pelvis_turn = math.degrees(pelvis_yaw[contact] - pelvis_yaw[0])
    chest_turn = math.degrees(chest_yaw[contact] - chest_yaw[0])
    return_error = (samples[-1]["fist"] - samples[0]["fist"]).length
    foot_travel = {
        foot: (samples[-1][f"{foot}_ankle"]
               - samples[0][f"{foot}_ankle"]).length
        for foot in ("left", "right")
    }
    contact_knees = {
        "left": angle(contact_sample["left_hip"],
                      contact_sample["left_knee"],
                      contact_sample["left_ankle"]),
        "right": angle(contact_sample["right_hip"],
                       contact_sample["right_knee"],
                       contact_sample["right_ankle"]),
    }

    failures = []
    if not 45.0 <= strike_elbow <= 172.0:
        failures.append("strike_elbow_outside_45_172")
    if not 35.0 <= guard_elbow <= 155.0:
        failures.append("guard_elbow_outside_35_155")
    if guard_to_head > 0.62:
        failures.append("guard_hand_too_far_from_head")
    if max(foot_travel.values()) > 0.22:
        failures.append("excessive_foot_translation")
    if max(foot_speeds["left"] + foot_speeds["right"]) > 3.5:
        failures.append("foot_velocity_spike")
    if lateral_displacement > 0.18:
        failures.append("excessive_lateral_root_shift")
    if contact == 0 or contact == len(samples) - 1:
        failures.append("contact_at_clip_boundary")

    style = label.lower()
    ordinary_bonus = 1.0 if style in {"jab", "cross"} else 0.0
    guard_score = max(0.0, 1.0 - guard_to_head / 0.62)
    whole_body = min(1.0, (abs(pelvis_turn) + abs(chest_turn)) / 35.0)
    extension_score = max(0.0, 1.0 - abs(strike_elbow - 158.0) / 70.0)
    return_score = max(0.0, 1.0 - return_error / 0.85)
    score = (2.0 * ordinary_bonus + 1.4 * guard_score
             + 1.2 * whole_body + 1.1 * extension_score
             + 0.8 * return_score - 1.5 * len(failures))

    return {
        "source": str(path.resolve()),
        "clip": path.stem,
        "kind": label.lower(),
        "strike_side": side,
        "fps": fps,
        "frames": [frames[0], frames[-1]],
        "duration_seconds": (len(frames) - 1) / fps,
        "phase_frames": {
            "ready": frames[0], "windup": frames[windup],
            "contact": frames[contact], "recovery": frames[-1],
        },
        "strike_events": strike_events,
        "contact": {
            "strike_elbow_degrees": strike_elbow,
            "guard_elbow_degrees": guard_elbow,
            "guard_to_head_meters": guard_to_head,
            "guard_to_chest_meters": guard_to_chest,
            "pelvis_turn_degrees": pelvis_turn,
            "chest_turn_degrees": chest_turn,
            "knee_degrees": contact_knees,
        },
        "motion": {
            "peak_fist_speed_mps": max(fist_speeds),
            "fist_path_meters": sum(
                (relative_fists[index] - relative_fists[index - 1]).length
                for index in range(1, len(relative_fists))),
            "root_displacement_meters": root_displacement,
            "contact_lateral_root_shift_meters": lateral_displacement,
            "foot_travel_meters": foot_travel,
            "foot_speed_p95_mps": {
                foot: percentile(values, 0.95)
                for foot, values in foot_speeds.items()
            },
            "fist_return_error_meters": return_error,
        },
        "source_body_yaw_degrees": math.degrees(pelvis_yaw[0]),
        "failures": failures,
        "score": score,
    }


def main() -> None:
    args = parse_args()
    rows = []
    for path in sorted(args.source_dir.glob("Male2_E*.bvh")):
        match = PUNCH_RE.match(path.name)
        if match is None:
            continue
        rows.append(analyse(path, match.group("label"),
                            match.group("side").lower()))
    rows.sort(key=lambda row: (len(row["failures"]), -row["score"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank

    report = {
        "schema": 1,
        "authority": "ACCAD Male-2 original BVH before EVA retarget",
        "source_page": "https://accad.osu.edu/research/motion-lab/mocap-system-and-data",
        "license": "CC BY 3.0",
        "candidate_count": len(rows),
        "candidates": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n",
                                encoding="utf-8")

    lines = [
        "# ACCAD EVA ordinary-attack source audit R01", "",
        "Original performer measurements; no EVA retarget has been applied.",
        "", "| Rank | Clip | Side | Contact | Elbow | Guard-head | "
        "Pelvis/chest turn | Peak fist | Failures |", "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        contact = row["phase_frames"]["contact"]
        values = row["contact"]
        motion = row["motion"]
        lines.append(
            f"| {row['rank']} | {row['clip']} | {row['strike_side']} | "
            f"{contact} | {values['strike_elbow_degrees']:.1f}° | "
            f"{values['guard_to_head_meters']:.3f} m | "
            f"{values['pelvis_turn_degrees']:.1f}°/"
            f"{values['chest_turn_degrees']:.1f}° | "
            f"{motion['peak_fist_speed_mps']:.2f} m/s | "
            f"{', '.join(row['failures']) or 'none'} |"
        )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidates": len(rows),
        "passing": sum(not row["failures"] for row in rows),
        "top": [row["clip"] for row in rows[:6]],
        "output": str(args.output_json),
    }, indent=2))


if __name__ == "__main__":
    main()
