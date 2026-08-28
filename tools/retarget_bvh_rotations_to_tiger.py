#!/usr/bin/env python3
"""Retarget BVH joint rotations and root travel directly to the Tiger rig."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

BONES = (
    "root", "torso_lower", "torso_upper", "aim_pitch", "neck", "head",
    "clavicle_l", "arm_l", "forearm_l", "wrist_l", "hand_l",
    "clavicle_r", "arm_r", "forearm_r", "wrist_r", "hand_r",
    "leg_l", "shin_l", "ankle_l", "foot_l",
    "leg_r", "shin_r", "ankle_r", "foot_r",
)
PARENT = {
    "root": None,
    "torso_lower": "root", "torso_upper": "torso_lower",
    "aim_pitch": "torso_upper", "neck": "torso_upper", "head": "neck",
    "clavicle_l": "aim_pitch", "arm_l": "clavicle_l",
    "forearm_l": "arm_l", "wrist_l": "forearm_l", "hand_l": "wrist_l",
    "clavicle_r": "aim_pitch", "arm_r": "clavicle_r",
    "forearm_r": "arm_r", "wrist_r": "forearm_r", "hand_r": "wrist_r",
    "leg_l": "torso_lower", "shin_l": "leg_l",
    "ankle_l": "shin_l", "foot_l": "ankle_l",
    "leg_r": "torso_lower", "shin_r": "leg_r",
    "ankle_r": "shin_r", "foot_r": "ankle_r",
}


PROFILES = {
    "tuffles": {
        "root": "Hip", "torso_lower": "LowerSpine",
        "torso_upper": "Chest", "neck": "Neck", "head": "Head",
        "clavicle_l": "LClavicle", "arm_l": "LShoulder",
        "forearm_l": "LForearm", "wrist_l": "LHand", "hand_l": "LHand",
        "clavicle_r": "RClavicle", "arm_r": "RShoulder",
        "forearm_r": "RForearm", "wrist_r": "RHand", "hand_r": "RHand",
        "leg_l": "LThigh", "shin_l": "LShin",
        "ankle_l": "LFoot", "foot_l": "LFoot",
        "leg_r": "RThigh", "shin_r": "RShin",
        "ankle_r": "RFoot", "foot_r": "RFoot",
        "hip_l": "LThigh", "hip_r": "RThigh",
        "toe_l": "LToe", "toe_r": "RToe",
    },
    "standard_bvh": {
        "root": "Hips", "torso_lower": "Spine",
        "torso_upper": "Spine1", "neck": "Neck", "head": "Head",
        "clavicle_l": "LeftShoulder", "arm_l": "LeftArm",
        "forearm_l": "LeftForeArm", "wrist_l": "LeftHand",
        "hand_l": "LeftHand",
        "clavicle_r": "RightShoulder", "arm_r": "RightArm",
        "forearm_r": "RightForeArm", "wrist_r": "RightHand",
        "hand_r": "RightHand",
        "leg_l": "LeftUpLeg", "shin_l": "LeftLeg",
        "ankle_l": "LeftFoot", "foot_l": "LeftFoot",
        "leg_r": "RightUpLeg", "shin_r": "RightLeg",
        "ankle_r": "RightFoot", "foot_r": "RightFoot",
        "hip_l": "LeftUpLeg", "hip_r": "RightUpLeg",
        "toe_l": "LeftToeBase", "toe_r": "RightToeBase",
    },
    "100style": {
        "root": "Hips", "torso_lower": "Chest2",
        "torso_upper": "Chest4", "neck": "Neck", "head": "Head",
        "clavicle_l": "LeftCollar", "arm_l": "LeftShoulder",
        "forearm_l": "LeftElbow", "wrist_l": "LeftWrist",
        "hand_l": "LeftWrist",
        "clavicle_r": "RightCollar", "arm_r": "RightShoulder",
        "forearm_r": "RightElbow", "wrist_r": "RightWrist",
        "hand_r": "RightWrist",
        "leg_l": "LeftHip", "shin_l": "LeftKnee",
        "ankle_l": "LeftAnkle", "foot_l": "LeftAnkle",
        "leg_r": "RightHip", "shin_r": "RightKnee",
        "ankle_r": "RightAnkle", "foot_r": "RightAnkle",
        "hip_l": "LeftHip", "hip_r": "RightHip",
        "toe_l": "LeftToe", "toe_r": "RightToe",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--end", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--output-fps", type=float, default=60.0)
    parser.add_argument("--reference-frame", type=int,
                        help="standing source frame used only for root height")
    parser.add_argument("--attachment", action="append", default=[],
                        choices=("knife", "cannon", "lance"),
                        help="append an identity attachment channel for a later exact solve")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def blender_to_authored(quat: Quaternion) -> list[float]:
    basis = Matrix(((1.0, 0.0, 0.0),
                    (0.0, 0.0, -1.0),
                    (0.0, 1.0, 0.0)))
    runtime = basis.inverted() @ quat.to_matrix() @ basis
    euler = runtime.to_euler("XYZ")
    authored = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_quaternion()
    authored.normalize()
    return [round(float(authored.w), 7), round(float(authored.x), 7),
            round(float(authored.y), 7), round(float(authored.z), 7)]


def world_head(rig: bpy.types.Object, bone_name: str) -> Vector:
    return rig.matrix_world @ rig.pose.bones[bone_name].head


def world_tail(rig: bpy.types.Object, bone_name: str) -> Vector:
    return rig.matrix_world @ rig.pose.bones[bone_name].tail


def rest_head(rig: bpy.types.Object, bone_name: str) -> Vector:
    return rig.matrix_world @ rig.data.bones[bone_name].head_local


def rest_tail(rig: bpy.types.Object, bone_name: str) -> Vector:
    return rig.matrix_world @ rig.data.bones[bone_name].tail_local


def rotation_matrix(matrix: Matrix) -> Matrix:
    return matrix.to_3x3().normalized()


def main() -> None:
    args = parse_args()
    attachments = list(dict.fromkeys(args.attachment))
    header = args.source.read_text(encoding="utf-8", errors="ignore")[:4096]
    if "ROOT Hip\n" in header or "ROOT Hip\r\n" in header:
        axis_forward, axis_up = "-Y", "Z"
    else:
        axis_forward, axis_up = "-Z", "Y"
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_anim.bvh(
        filepath=str(args.source.resolve()), target="ARMATURE",
        global_scale=0.01, frame_start=1, use_fps_scale=False,
        update_scene_fps=True, update_scene_duration=True,
        rotate_mode="NATIVE", axis_forward=axis_forward, axis_up=axis_up,
    )
    rig = next(obj for obj in bpy.context.scene.objects
               if obj.type == "ARMATURE")
    available = set(rig.pose.bones.keys())
    matches = [
        (name, profile) for name, profile in PROFILES.items()
        if all(source_name in available for source_name in set(profile.values()))
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"expected one BVH rotation profile, got {[name for name, _ in matches]}"
        )
    profile_name, profile = matches[0]
    scene = bpy.context.scene
    native_fps = scene.render.fps / scene.render.fps_base
    action = rig.animation_data.action
    available_range = (int(math.ceil(action.frame_range[0])),
                       int(math.floor(action.frame_range[1])))
    if not (available_range[0] <= args.start < args.end <= available_range[1]):
        raise SystemExit(
            f"range {args.start}-{args.end} outside {available_range}")
    frame_step = native_fps / args.output_fps
    source_frames = list(np.arange(
        float(args.start), float(args.end) + frame_step * 0.25,
        frame_step, dtype=np.float64))
    source_frames[-1] = min(source_frames[-1], float(args.end))

    def set_frame(value: float) -> None:
        whole = math.floor(value)
        scene.frame_set(whole, subframe=value - whole)
        bpy.context.view_layer.update()

    reference_frame = args.reference_frame or args.start
    if not available_range[0] <= reference_frame <= available_range[1]:
        raise SystemExit(f"reference frame {reference_frame} outside {available_range}")
    # A prone/crouched clip does not provide a reliable facing or height
    # basis. Derive both from the caller-selected standing frame instead.
    set_frame(float(reference_frame))
    up = Vector((0.0, 0.0, 1.0))
    source_left = world_head(rig, profile["hip_l"]) \
        - world_head(rig, profile["hip_r"])
    source_left.z = 0.0
    source_left.normalize()
    source_forward = source_left.cross(up).normalized()
    toe_hint = (
        world_head(rig, profile["toe_l"]) - world_head(rig, profile["ankle_l"])
        + world_head(rig, profile["toe_r"]) - world_head(rig, profile["ankle_r"])
    )
    toe_hint.z = 0.0
    if toe_hint.length > 1.0e-8 and source_forward.dot(toe_hint) < 0.0:
        source_forward.negate()
        source_left = up.cross(source_forward).normalized()
    source_basis = Matrix((source_forward, source_left, up)).transposed()
    target_forward = Vector((0.0, 1.0, 0.0))
    target_left = Vector((-1.0, 0.0, 0.0))
    target_basis = Matrix((target_forward, target_left, up)).transposed()
    source_to_target = target_basis @ source_basis.inverted()

    rest_height = rest_tail(rig, profile["head"]).z - min(
        rest_head(rig, profile["ankle_l"]).z,
        rest_head(rig, profile["toe_l"]).z,
        rest_head(rig, profile["ankle_r"]).z,
        rest_head(rig, profile["toe_r"]).z,
    )
    dynamic_height = world_tail(rig, profile["head"]).z - min(
        world_head(rig, profile["ankle_l"]).z,
        world_head(rig, profile["toe_l"]).z,
        world_head(rig, profile["ankle_r"]).z,
        world_head(rig, profile["toe_r"]).z,
    )
    source_height = max(rest_height, dynamic_height)
    if source_height <= 1.0e-8:
        raise RuntimeError("source rest height is not positive")
    source_to_meters = 1.75 / source_height
    reference_root = source_to_target @ world_head(rig, profile["root"])
    set_frame(source_frames[0])
    source_origin = world_head(rig, profile["root"])
    identity = Quaternion((1.0, 0.0, 0.0, 0.0))
    output_frames = []
    foot_positions = {"l": [], "r": []}
    maximum_step = 0.0
    maximum_step_location = None
    previous_local = None

    for output_index, source_frame in enumerate(source_frames):
        set_frame(source_frame)
        desired_global = {"root": identity.copy(),
                          "aim_pitch": identity.copy()}
        for target_name in BONES:
            if target_name in {"root", "aim_pitch"}:
                continue
            source_name = profile[target_name]
            pose_world = rig.matrix_world @ rig.pose.bones[source_name].matrix
            rest_world = rig.matrix_world @ rig.data.bones[source_name].matrix_local
            delta = (rotation_matrix(pose_world)
                     @ rotation_matrix(rest_world).inverted())
            converted = source_to_target @ delta @ source_to_target.inverted()
            desired_global[target_name] = converted.to_quaternion()
            desired_global[target_name].normalize()
        # aim_pitch is an empty runtime socket between torso and clavicles.
        # It must inherit the torso globally so its local bind stays identity.
        desired_global["aim_pitch"] = desired_global["torso_upper"].copy()
        local = {}
        for bone_name in BONES:
            parent = PARENT[bone_name]
            local[bone_name] = (desired_global[bone_name]
                                if parent is None else
                                desired_global[parent].conjugated()
                                @ desired_global[bone_name])
            local[bone_name].normalize()
            if (previous_local is not None
                    and previous_local[bone_name].dot(local[bone_name]) < 0.0):
                local[bone_name] = Quaternion(tuple(
                    -value for value in local[bone_name]))
        if previous_local is not None:
            for bone_name in BONES:
                step = previous_local[bone_name].rotation_difference(
                    local[bone_name]).angle
                if step > maximum_step:
                    maximum_step = step
                    maximum_step_location = {
                        "frame": output_index, "bone": bone_name}
        previous_local = {name: value.copy() for name, value in local.items()}
        current_root = source_to_target @ world_head(rig, profile["root"])
        start_root = source_to_target @ source_origin
        target_delta = Vector((
            current_root.x - start_root.x,
            current_root.y - start_root.y,
            current_root.z - reference_root.z,
        )) * source_to_meters
        root_m = (-target_delta.x, target_delta.z, -target_delta.y)
        for side in ("l", "r"):
            foot_positions[side].append(
                source_to_target @ world_head(rig, profile[f"ankle_{side}"])
                * source_to_meters)
        output_frames.append({
            "root_m": [round(float(value), 7) for value in root_m],
            "rotation_wxyz": (
                [blender_to_authored(local[name]) for name in BONES]
                + [[1.0, 0.0, 0.0, 0.0] for _ in attachments]
            ),
            "foot_contact": [False, False],
        })

    dt = 1.0 / args.output_fps
    for side_index, side in enumerate(("l", "r")):
        positions = foot_positions[side]
        floor = sorted(point.z for point in positions)[
            max(0, int(round((len(positions) - 1) * 0.02)))]
        for index, frame in enumerate(output_frames):
            before = max(0, index - 1)
            after = min(len(positions) - 1, index + 1)
            duration = max(dt, (after - before) * dt)
            speed = (positions[after] - positions[before]).length / duration
            frame["foot_contact"][side_index] = bool(
                positions[index].z <= floor + 0.035 and speed <= 0.35)

    payload = {
        "schema": 3,
        "coordinate_system": "direct_bvh_global_rotation_to_tiger",
        "quaternion_order": "wxyz",
        "sample_rate": args.output_fps,
        "preview_only": True,
        "authority": "direct_source_joint_rotations_and_root_translation",
        "sources": [{
            "name": args.source_name, "url": args.source_url,
            "license": args.license,
            "modifications": [
                "BVH rest-relative global rotation transfer",
                "source-facing to Tiger-facing basis conversion",
                "source root translation scaled to 1.75 metre performer",
            ],
        }],
        "bones": list(BONES) + attachments,
        "clips": {
            args.clip: {
                "duration_seconds": round(
                    (len(output_frames) - 1) / args.output_fps, 6),
                "loop": False,
                "role": "direct_bvh_rotation_retarget_candidate",
                "frames": output_frames,
            }
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    report = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "source_profile": profile_name,
        "import_axis_forward": axis_forward,
        "import_axis_up": axis_up,
        "source_frames": [float(source_frames[0]), float(source_frames[-1])],
        "reference_frame": reference_frame,
        "native_fps": native_fps,
        "output_fps": args.output_fps,
        "output_frames": len(output_frames),
        "source_to_meters": source_to_meters,
        "toe_forward_alignment": (None if toe_hint.length <= 1.0e-8 else
                                  source_forward.dot(toe_hint.normalized())),
        "maximum_local_rotation_step_degrees": math.degrees(maximum_step),
        "maximum_local_rotation_step_location": maximum_step_location,
        "status": "direct_rotation_candidate_requires_exact_and_human_review",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
