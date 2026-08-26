#!/usr/bin/env python3
"""Compare exported runtime bone directions against the source review rig."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_motion_lab_3d import load_geo, target_to_blender
from build_eva_motion_lab_armature import deformation_matrices


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--motion-db", required=True, type=Path)
parser.add_argument("--clip", required=True)
parser.add_argument("--action", required=True)
parser.add_argument("--geo", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--scale", type=float, default=0.05)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
clip = motion["clips"][args.clip]
heading_matrix = Matrix.Rotation(math.radians(float(clip.get(
    "heading_normalization_blender_degrees", 0.0))), 4, "Z")
target = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
action = bpy.data.actions.get(args.action)
if action is None:
    raise RuntimeError(f"missing action {args.action}")
target.animation_data.action = action
bones, pivots, parents = load_geo(args.geo)
bone_order = [row["name"] for row in bones]
chains = (
    ("arm_l", "forearm_l"), ("forearm_l", "hand_l"),
    ("arm_r", "forearm_r"), ("forearm_r", "hand_r"),
    ("leg_l", "shin_l"), ("shin_l", "foot_l"),
    ("leg_r", "shin_r"), ("shin_r", "foot_r"),
)


def angle(first: Vector, second: Vector) -> float:
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return 0.0
    return math.degrees(first.angle(second))


errors = []
position_errors = []
samples = []
start = int(round(action.frame_range[0]))
for index, frame_data in enumerate(clip["frames"]):
    frame = min(int(round(action.frame_range[1])), start + index)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    matrices = deformation_matrices(
        frame_data, motion["bones"], bone_order, pivots, parents)
    frame_errors = {}
    frame_position_errors = {}
    # The anatomical lab's synthetic root sits at the pelvis while the
    # authored Bedrock root pivot is near model origin.  Torso-lower is their
    # first shared physical landmark, so compare all joints relative to it.
    runtime_anchor = (matrices["torso_lower"]
                      @ target_to_blender(pivots["torso_lower"]))
    target_anchor = (heading_matrix @ (target.matrix_world
                     @ target.pose.bones["torso_lower"].head)) / args.scale
    for bone_name in motion["bones"]:
        if (bone_name == "root" or bone_name not in matrices
                or bone_name not in target.pose.bones):
            continue
        runtime_point = (matrices[bone_name]
                         @ target_to_blender(pivots[bone_name]))
        target_point = (heading_matrix @ (target.matrix_world
                        @ target.pose.bones[bone_name].head)) / args.scale
        value = float(((runtime_point - runtime_anchor)
                       - (target_point - target_anchor)).length)
        frame_position_errors[bone_name] = value
        position_errors.append(value)
    for first_name, second_name in chains:
        runtime_first = matrices[first_name] @ target_to_blender(
            pivots[first_name])
        runtime_second = matrices[second_name] @ target_to_blender(
            pivots[second_name])
        target_first = (heading_matrix @ (target.matrix_world
                        @ target.pose.bones[first_name].head)) / args.scale
        target_second = (heading_matrix @ (target.matrix_world
                         @ target.pose.bones[second_name].head)) / args.scale
        value = angle(runtime_second - runtime_first,
                      target_second - target_first)
        frame_errors[f"{first_name}/{second_name}"] = value
        errors.append(value)
    samples.append({"frame": frame, "errors_degrees": frame_errors,
                    "root_relative_position_errors_model_units":
                        frame_position_errors})

report = {
    "schema": 1,
    "clip": args.clip,
    "action": action.name,
    "sample_count": len(samples),
    "median_chain_direction_error_degrees": float(__import__(
        "numpy").median(errors)),
    "p95_chain_direction_error_degrees": float(__import__(
        "numpy").percentile(errors, 95.0)),
    "maximum_chain_direction_error_degrees": max(errors),
    "median_root_relative_position_error_model_units": float(__import__(
        "numpy").median(position_errors)),
    "p95_root_relative_position_error_model_units": float(__import__(
        "numpy").percentile(position_errors, 95.0)),
    "maximum_root_relative_position_error_model_units": max(position_errors),
    "samples": samples,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n",
                       encoding="utf-8")
print(json.dumps({key: value for key, value in report.items()
                  if key != "samples"}, indent=2))
