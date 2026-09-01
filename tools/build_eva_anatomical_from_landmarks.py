#!/usr/bin/env python3
"""Retarget normalized full-body landmarks onto the anatomical EVA rig.

This stage preserves the captured pelvis, legs and support timing.  It does not
copy source Euler channels and does not lock the lower body to a stock pose.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector


SOURCE_TO_TARGET = Matrix((
    (0.0, -1.0, 0.0),
    (1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
))
CHAINS = {
    "torso_lower": ("pelvis", "abdomen"),
    "torso_upper": ("abdomen", "thorax"),
    "aim_pitch": ("thorax", "neck"),
    "head": ("neck", "head"),
    "arm_l": ("shoulder_l", "elbow_l"),
    "forearm_l": ("elbow_l", "wrist_l"),
    "hand_l": ("wrist_l", "hand_l"),
    "arm_r": ("shoulder_r", "elbow_r"),
    "forearm_r": ("elbow_r", "wrist_r"),
    "hand_r": ("wrist_r", "hand_r"),
    "leg_l": ("hip_l", "knee_l"),
    "shin_l": ("knee_l", "ankle_l"),
    "foot_l": ("ankle_l", "toe_l"),
    "leg_r": ("hip_r", "knee_r"),
    "shin_r": ("knee_r", "ankle_r"),
    "foot_r": ("ankle_r", "toe_r"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--landmarks", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--action-name", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--root-horizontal-scale", type=float, default=1.0)
    parser.add_argument("--root-vertical-scale", type=float, default=1.0)
    parser.add_argument("--rig", default="EVA_ANATOMICAL_ARMATURE")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def normalized(value: Vector) -> Vector:
    if value.length < 1.0e-8:
        raise RuntimeError("zero-length source direction")
    return value.normalized()


def pose_head(rig: bpy.types.Object, name: str) -> Vector:
    return rig.matrix_world @ rig.pose.bones[name].head


def rest_head(rig: bpy.types.Object, name: str) -> Vector:
    return rig.matrix_world @ rig.data.bones[name].head_local


def pose_direction(rig: bpy.types.Object, name: str) -> Vector:
    bone = rig.pose.bones[name]
    return normalized(rig.matrix_world @ bone.tail
                      - rig.matrix_world @ bone.head)


def keyframe(bone: bpy.types.PoseBone, frame: int,
             previous: dict[str, Quaternion]) -> None:
    bone.rotation_mode = "QUATERNION"
    rotation = bone.rotation_quaternion.copy()
    prior = previous.get(bone.name)
    if prior is not None and prior.dot(rotation) < 0.0:
        rotation.negate()
        bone.rotation_quaternion = rotation
    previous[bone.name] = rotation.copy()
    bone.keyframe_insert("location", frame=frame)
    bone.keyframe_insert("rotation_quaternion", frame=frame)
    bone.keyframe_insert("scale", frame=frame)


def align_direction(rig: bpy.types.Object, name: str,
                    desired_world: Vector, frame: int,
                    previous: dict[str, Quaternion]) -> None:
    bone = rig.pose.bones[name]
    current = normalized(bone.tail - bone.head)
    desired = normalized(
        rig.matrix_world.to_3x3().inverted() @ desired_world)
    pivot = bone.head.copy()
    bone.matrix = (
        Matrix.Translation(pivot)
        @ current.rotation_difference(desired).to_matrix().to_4x4()
        @ Matrix.Translation(-pivot)
        @ bone.matrix
    )
    keyframe(bone, frame, previous)


def joint_angle(first: Vector, middle: Vector, last: Vector) -> float:
    left = first - middle
    right = last - middle
    if left.length < 1.0e-8 or right.length < 1.0e-8:
        return 0.0
    return math.degrees(left.angle(right))


def main() -> None:
    args = parse_args()
    rig = bpy.data.objects.get(args.rig)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("anatomical EVA armature is missing")
    missing_target = set(CHAINS) - set(rig.pose.bones.keys())
    if missing_target:
        raise RuntimeError("target rig is missing bones: "
                           + ", ".join(sorted(missing_target)))

    source = np.load(args.landmarks)
    names = [str(value) for value in source["landmark_names"]]
    source_index = {name: index for index, name in enumerate(names)}
    required = {name for pair in CHAINS.values() for name in pair}
    required.update({"pelvis", "hip_l", "hip_r"})
    missing_source = required - set(source_index)
    if missing_source:
        raise RuntimeError("source landmarks are missing: "
                           + ", ".join(sorted(missing_source)))
    positions = np.asarray(source["positions_H"], dtype=np.float64)
    contacts = np.asarray(source["foot_contact"], dtype=np.bool_)
    fps = float(source["fps"][0])
    if positions.shape[0] < 3 or contacts.shape != (len(positions), 2):
        raise RuntimeError("invalid full-body landmark trajectory")

    target_height = (
        rest_head(rig, "head")
        - 0.5 * (rest_head(rig, "foot_l")
                 + rest_head(rig, "foot_r"))
    ).length
    source_origin = Vector(tuple(
        positions[0, source_index["pelvis"]]))
    root_rest = rig.data.bones["root"].matrix_local.copy()
    action = bpy.data.actions.new(args.action_name)
    action.use_fake_user = True
    action["project_seele_source_id"] = args.source_id
    action["project_seele_authority"] = (
        "full_body_normalized_landmarks_with_captured_support")
    action["eva_contact_l"] = json.dumps(
        contacts[:, 0].astype(int).tolist(), separators=(",", ":"))
    action["eva_contact_r"] = json.dumps(
        contacts[:, 1].astype(int).tolist(), separators=(",", ":"))
    rig.animation_data.action = action
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = len(positions)
    scene.render.fps = int(round(fps))
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    previous: dict[str, Quaternion] = {}
    desired_directions: dict[int, dict[str, Vector]] = {}

    target_forward = Vector((0.0, 1.0, 0.0))
    target_up = Vector((0.0, 0.0, 1.0))
    for frame, row in enumerate(positions, start=1):
        scene.frame_set(frame)
        up = Vector((0.0, 0.0, 1.0))
        source_left = Vector(tuple(
            row[source_index["hip_l"]]
            - row[source_index["hip_r"]]))
        source_left.z = 0.0
        source_left = normalized(source_left)
        source_forward = normalized(source_left.cross(up))
        desired_forward = normalized(SOURCE_TO_TARGET @ source_forward)
        desired_forward.z = 0.0
        desired_forward.normalize()
        root_rotation = target_forward.rotation_difference(desired_forward)

        source_delta = Vector(tuple(
            row[source_index["pelvis"]])) - source_origin
        mapped = SOURCE_TO_TARGET @ source_delta * target_height
        mapped.x *= args.root_horizontal_scale
        mapped.y *= args.root_horizontal_scale
        mapped.z *= args.root_vertical_scale
        root = rig.pose.bones["root"]
        root.rotation_mode = "QUATERNION"
        root.matrix = (Matrix.Translation(mapped)
                       @ root_rotation.to_matrix().to_4x4()
                       @ root_rest)
        keyframe(root, frame, previous)
        bpy.context.view_layer.update()

        desired_directions[frame] = {}
        for target_name, (first_name, second_name) in CHAINS.items():
            source_direction = Vector(tuple(
                row[source_index[second_name]]
                - row[source_index[first_name]]))
            if source_direction.length < 1.0e-8 and target_name == "aim_pitch":
                # Some synchronized CMU exports collapse thorax and neck onto
                # the same marker.  Preserve the captured chest axis using the
                # adjacent abdomen-to-neck span rather than inventing motion.
                source_direction = Vector(tuple(
                    row[source_index["neck"]]
                    - row[source_index["abdomen"]]))
            desired = normalized(SOURCE_TO_TARGET @ source_direction)
            desired_directions[frame][target_name] = desired.copy()
            align_direction(rig, target_name, desired, frame, previous)
            bpy.context.view_layer.update()

    direction_errors = []
    rotation_steps = []
    knees = []
    elbows = []
    previous_pose = None
    root_positions = []
    for frame in range(1, len(positions) + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        current = {}
        for name, desired in desired_directions[frame].items():
            actual = pose_direction(rig, name)
            direction_errors.append(math.degrees(actual.angle(desired)))
            rotation = rig.pose.bones[name].matrix.to_quaternion()
            rotation.normalize()
            current[name] = rotation
            if previous_pose is not None:
                radians = previous_pose[name].rotation_difference(
                    rotation).angle
                rotation_steps.append(math.degrees(
                    min(radians, 2.0 * math.pi - radians)))
        previous_pose = current
        root_positions.append(pose_head(rig, "root"))
        for side in ("l", "r"):
            knees.append(joint_angle(
                pose_head(rig, f"leg_{side}"),
                pose_head(rig, f"shin_{side}"),
                pose_head(rig, f"foot_{side}")))
            elbows.append(joint_angle(
                pose_head(rig, f"arm_{side}"),
                pose_head(rig, f"forearm_{side}"),
                pose_head(rig, f"hand_{side}")))
    root_travel = (root_positions[-1] - root_positions[0]).length
    report = {
        "schema": 1,
        "source": str(args.landmarks.resolve()),
        "sourceId": args.source_id,
        "frames": len(positions),
        "fps": fps,
        "targetHeight": target_height,
        "rootHorizontalScale": args.root_horizontal_scale,
        "rootVerticalScale": args.root_vertical_scale,
        "rootTravel": root_travel,
        "maximumDirectionErrorDegrees": max(direction_errors),
        "p95RotationStepDegrees": float(np.percentile(
            rotation_steps, 95.0)),
        "maximumRotationStepDegrees": max(rotation_steps),
        "minimumKneeDegrees": min(knees),
        "minimumElbowDegrees": min(elbows),
        "contactFraction": contacts.mean(axis=0).tolist(),
        "gates": {
            "directionErrorLe0p1": max(direction_errors) <= 0.1,
            "p95RotationStepLe20": float(np.percentile(
                rotation_steps, 95.0)) <= 20.0,
            "kneesNotInverted": min(knees) >= 12.0,
            "elbowsNotInverted": min(elbows) >= 12.0,
        },
        "status": "full_body_anatomical_candidate_not_live",
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
