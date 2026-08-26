#!/usr/bin/env python3
"""Audit one ACCAD punch after retargeting onto the real EVA rig."""

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
    parser.add_argument("--source-object", required=True)
    parser.add_argument("--strike-side", choices=("left", "right"), required=True)
    parser.add_argument("--contact-frame", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def point(rig, name, tail=False):
    bone = rig.pose.bones[name]
    return rig.matrix_world @ (bone.tail if tail else bone.head)


def angle(a, b, c):
    first = a - b
    second = c - b
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return 0.0
    return math.degrees(first.angle(second))


def direction_error(first, second):
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return 180.0
    return math.degrees(first.normalized().angle(second.normalized()))


def percentile(values, fraction):
    values = sorted(values)
    position = fraction * (len(values) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return values[low]
    blend = position - low
    return values[low] * (1.0 - blend) + values[high] * blend


def yaw_from_lateral(left, right):
    lateral = right - left
    lateral.z = 0.0
    if lateral.length < 1.0e-8:
        return 0.0
    lateral.normalize()
    forward = Vector((-lateral.y, lateral.x, 0.0))
    return math.atan2(forward.x, forward.y)


def unwrap_delta(value):
    while value > math.pi:
        value -= math.tau
    while value < -math.pi:
        value += math.tau
    return value


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    source = bpy.data.objects[args.source_object]
    target = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    if args.contact_frame not in frames:
        raise SystemExit(f"contact outside review range: {args.contact_frame}")

    mappings = (
        ("LeftArm", "LeftForeArm", "arm_l", "forearm_l"),
        ("LeftForeArm", "LeftHand", "forearm_l", "hand_l"),
        ("RightArm", "RightForeArm", "arm_r", "forearm_r"),
        ("RightForeArm", "RightHand", "forearm_r", "hand_r"),
        ("LeftUpLeg", "LeftLeg", "leg_l", "shin_l"),
        ("LeftLeg", "LeftFoot", "shin_l", "foot_l"),
        ("RightUpLeg", "RightLeg", "leg_r", "shin_r"),
        ("RightLeg", "RightFoot", "shin_r", "foot_r"),
    )
    errors = {f"{ta}/{tb}": [] for _, _, ta, tb in mappings}
    rotation_bones = (
        "root", "torso_lower", "torso_upper", "arm_l", "forearm_l",
        "hand_l", "arm_r", "forearm_r", "hand_r", "leg_l", "shin_l",
        "leg_r", "shin_r",
    )
    rotations = {name: [] for name in rotation_bones}
    rows = []
    strike = "l" if args.strike_side == "left" else "r"
    guard = "r" if strike == "l" else "l"
    source_strike = "Left" if strike == "l" else "Right"
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for sa, sb, ta, tb in mappings:
            errors[f"{ta}/{tb}"].append(direction_error(
                point(source, sb) - point(source, sa),
                point(target, tb) - point(target, ta)))
        for name in rotation_bones:
            value = target.pose.bones[name].matrix_basis.to_quaternion()
            value.normalize()
            if rotations[name] and rotations[name][-1].dot(value) < 0.0:
                value.negate()
            rotations[name].append(value)
        rows.append({
            "frame": frame,
            "root": point(target, "world_root") if "world_root" in target.pose.bones
                    else point(target, "root"),
            "strike_fist": point(target, f"hand_{strike}", tail=True),
            "guard_fist": point(target, f"hand_{guard}", tail=True),
            "head": point(target, "head", tail=True),
            "chest": point(target, "torso_upper"),
            "left_foot": point(target, "foot_l"),
            "right_foot": point(target, "foot_r"),
            "pelvis_yaw": yaw_from_lateral(point(target, "leg_l"),
                                             point(target, "leg_r")),
            "chest_yaw": yaw_from_lateral(point(target, "arm_l"),
                                            point(target, "arm_r")),
            "strike_elbow": angle(point(target, f"arm_{strike}"),
                                    point(target, f"forearm_{strike}"),
                                    point(target, f"hand_{strike}")),
            "guard_elbow": angle(point(target, f"arm_{guard}"),
                                   point(target, f"forearm_{guard}"),
                                   point(target, f"hand_{guard}")),
            "left_knee": angle(point(target, "leg_l"),
                                 point(target, "shin_l"),
                                 point(target, "foot_l")),
            "right_knee": angle(point(target, "leg_r"),
                                  point(target, "shin_r"),
                                  point(target, "foot_r")),
        })

    height = max(point(target, "head", tail=True).z for _ in (0,)) - min(
        rows[0]["left_foot"].z, rows[0]["right_foot"].z)
    height = max(height, 1.0e-6)
    contact = rows[args.contact_frame - frames[0]]
    root_steps = [(rows[index]["root"] - rows[index - 1]["root"]).length
                  for index in range(1, len(rows))]
    foot_travel = {
        side: max((row[f"{side}_foot"] - rows[0][f"{side}_foot"]).length
                  for row in rows) / height
        for side in ("left", "right")
    }
    scene.frame_set(frames[0])
    bpy.context.view_layer.update()
    ready_lateral = point(target, "leg_r") - point(target, "leg_l")
    ready_lateral.z = 0.0
    ready_lateral.normalize()
    ready_stance_signed = ((rows[0]["right_foot"] - rows[0]["left_foot"])
                           .dot(ready_lateral) / height)
    knee_plane_ratios = {"left": [], "right": []}
    for row in rows:
        scene.frame_set(row["frame"])
        bpy.context.view_layer.update()
        lateral = Vector((math.cos(row["pelvis_yaw"]),
                          -math.sin(row["pelvis_yaw"]), 0.0))
        forward = Vector((math.sin(row["pelvis_yaw"]),
                          math.cos(row["pelvis_yaw"]), 0.0))
        for side in ("left", "right"):
            hip = point(target, "leg_l" if side == "left" else "leg_r")
            knee = point(target, "shin_l" if side == "left" else "shin_r")
            ankle = row[f"{side}_foot"]
            axis = ankle - hip
            projection = hip + axis * ((knee - hip).dot(axis)
                                       / max(axis.length_squared, 1.0e-9))
            bend = knee - projection
            knee_plane_ratios[side].append(
                abs(bend.dot(lateral)) / max(1.0e-6,
                                              abs(bend.dot(forward))))
    heading = math.degrees(unwrap_delta(rows[0]["pelvis_yaw"]))
    strike_delta = contact["strike_fist"] - rows[0]["strike_fist"]
    strike_delta.z = 0.0
    strike_path_yaw = math.degrees(math.atan2(
        strike_delta.x, strike_delta.y)) if strike_delta.length > 1.0e-8 else 180.0
    strike_direction_error = (direction_error(
        strike_delta, Vector((0.0, 1.0, 0.0)))
        if strike_delta.length > 1.0e-8 else 180.0)
    pelvis_turn = math.degrees(unwrap_delta(
        contact["pelvis_yaw"] - rows[0]["pelvis_yaw"]))
    chest_turn = math.degrees(unwrap_delta(
        contact["chest_yaw"] - rows[0]["chest_yaw"]))
    guard_to_head = (contact["guard_fist"] - contact["head"]).length / height
    guard_to_chest = (contact["guard_fist"] - contact["chest"]).length / height
    chain_summary = {
        name: {
            "median_degrees": percentile(values, 0.50),
            "p95_degrees": percentile(values, 0.95),
            "maximum_degrees": max(values),
        }
        for name, values in errors.items()
    }
    angular_steps = []
    for name, values in rotations.items():
        for index in range(1, len(values)):
            amount = math.degrees(values[index - 1].rotation_difference(
                values[index]).angle)
            angular_steps.append({"bone": name, "frame": frames[index],
                                  "degrees": amount})
    maximum_angular_step = max(angular_steps,
                               key=lambda row: row["degrees"])
    strike_bones = {f"arm_{strike}", f"forearm_{strike}", f"hand_{strike}"}
    structural_steps = [row for row in angular_steps
                        if row["bone"] not in strike_bones]
    maximum_structural_step = max(structural_steps,
                                  key=lambda row: row["degrees"])
    maximum_chain_error = max(value["maximum_degrees"]
                              for name, value in chain_summary.items()
                              if not name.startswith(("leg_", "shin_")))
    failures = []
    # A boxing pelvis is intentionally oblique; attack travel, not hip yaw,
    # owns target direction.
    if abs(heading) > 15.0:
        failures.append("ready_heading_not_forward")
    if strike_direction_error > 12.0:
        failures.append("strike_path_not_forward")
    if maximum_chain_error > 8.0:
        failures.append("source_target_chain_error")
    if not 45.0 <= contact["strike_elbow"] <= 172.0:
        failures.append("strike_elbow_outside_45_172")
    if not 35.0 <= contact["guard_elbow"] <= 155.0:
        failures.append("guard_elbow_outside_35_155")
    if guard_to_head > 0.34:
        failures.append("guard_hand_too_low_or_far")
    if max(foot_travel.values()) > 0.08:
        failures.append("foot_travel_over_0_08H")
    if ready_stance_signed < 0.16:
        failures.append("stance_too_narrow_or_crossed")
    if max(root_steps, default=0.0) / height > 0.025:
        failures.append("root_step_over_0_025H")
    if min(row["left_knee"] for row in rows) < 35.0 or min(
            row["right_knee"] for row in rows) < 35.0:
        failures.append("knee_collapse")
    if maximum_structural_step["degrees"] > 35.0:
        failures.append("non_strike_joint_angular_step_over_35")
    if maximum_angular_step["bone"] in strike_bones and (
            maximum_angular_step["degrees"] > 80.0):
        failures.append("strike_joint_angular_step_over_80")

    report = {
        "schema": 1,
        "source_object": source.name,
        "target_action": target.animation_data.action.name,
        "review_frames": [frames[0], frames[-1]],
        "contact_frame": args.contact_frame,
        "body_height_blender_units": height,
        "ready_heading_degrees": heading,
        "strike_direction_error_degrees": strike_direction_error,
        "strike_path_yaw_degrees": strike_path_yaw,
        "contact": {
            "strike_elbow_degrees": contact["strike_elbow"],
            "guard_elbow_degrees": contact["guard_elbow"],
            "guard_to_head_body_heights": guard_to_head,
            "guard_to_chest_body_heights": guard_to_chest,
            "pelvis_turn_degrees": pelvis_turn,
            "chest_turn_degrees": chest_turn,
        },
        "foot_travel_body_heights": foot_travel,
        "ready_stance_width_body_heights": ready_stance_signed,
        "knee_lateral_to_sagittal_ratio_p95": {
            side: percentile(values, 0.95)
            for side, values in knee_plane_ratios.items()
        },
        "knee_angle_degrees": {
            side: {
                "minimum": min(row[f"{side}_knee"] for row in rows),
                "maximum": max(row[f"{side}_knee"] for row in rows),
            }
            for side in ("left", "right")
        },
        "root_step_p95_body_heights": percentile(root_steps, 0.95) / height,
        "root_step_max_body_heights": max(root_steps, default=0.0) / height,
        "chain_direction_error": chain_summary,
        "maximum_chain_direction_error_degrees": maximum_chain_error,
        "joint_angular_step": {
            "p95_degrees": percentile(
                [row["degrees"] for row in angular_steps], 0.95),
            "maximum": maximum_angular_step,
            "maximum_non_strike": maximum_structural_step,
        },
        "failures": failures,
        "passed": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
