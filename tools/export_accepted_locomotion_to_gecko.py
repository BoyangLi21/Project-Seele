#!/usr/bin/env python3
"""Export the approved anatomical EVA locomotion actions to GeckoLib JSON.

Run this script through Blender 3.6 with the accepted idle blend opened.  The
offline rig uses an anatomical rest pose while the Minecraft Tiger mesh keeps
its authored Bedrock rest hierarchy, so copying Euler channels is invalid.
This exporter solves the complete rigid-part transform back onto a runtime
armature before emitting any Gecko keyframes.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_eva_motion_lab_3d import runtime_pivot, target_to_blender


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--mesh", required=True, type=Path)
parser.add_argument("--geo", required=True, type=Path)
parser.add_argument("--direct", required=True, type=Path)
parser.add_argument("--jump", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--audit", required=True, type=Path)
parser.add_argument("--walk-blend", type=Path)
parser.add_argument("--walk-action")
parser.add_argument("--walk-fps", type=float)
parser.add_argument("--run-blend", type=Path)
parser.add_argument("--run-action")
parser.add_argument("--run-fps", type=float)
parser.add_argument(
    "--source-label",
    default="approved EVA unarmed locomotion R02",
)
parser.add_argument("--scale", type=float, default=0.05)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

scene = bpy.context.scene
target = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
target_mesh = bpy.data.objects["EVA_ANATOMICAL_RIGID_MESH"]
idle_action = target.animation_data.action


def load_action(path, action_name, unique_name):
    with bpy.data.libraries.load(str(path), link=False) as (source, loaded):
        if action_name not in source.actions:
            raise RuntimeError(f"{action_name} missing from {path}")
        loaded.actions = [action_name]
    action = loaded.actions[0]
    action.name = unique_name
    return action


walk_blend = (args.walk_blend
              or args.direct / "EVA_Walk_Loop_HUMAN_HANDS.blend")
walk_action = (args.walk_action
               or "EVA_UNARMED_Walk_Loop_MOTIONX_HANDS")
run_blend = (args.run_blend
             or args.direct / "EVA_Sprint_Loop_HUMAN_HANDS.blend")
run_action = (args.run_action
              or "EVA_UNARMED_Sprint_Loop_MOTIONX_HANDS")

actions = {
    "idle": idle_action,
    "walk": load_action(
        walk_blend, walk_action, "EXPORT_WALK"),
    "jog": load_action(
        args.direct / "EVA_Jog_Fwd_Loop_HUMAN_HANDS.blend",
        "EVA_UNARMED_Jog_Fwd_Loop_MOTIONX_HANDS", "EXPORT_JOG"),
    "run": load_action(
        run_blend, run_action, "EXPORT_SPRINT"),
    "takeoff": load_action(
        args.jump / "Jump_Start_HUMAN_HANDS.blend",
        "EVA_ROKOKO_DIRECT_Jump_Start", "EXPORT_JUMP_START"),
    "jump": load_action(
        args.jump / "Jump_Loop_HUMAN_HANDS.blend",
        "EVA_ROKOKO_DIRECT_Jump_Loop", "EXPORT_JUMP_LOOP"),
    "land": load_action(
        args.jump / "Jump_Land_HUMAN_HANDS.blend",
        "EVA_ROKOKO_DIRECT_Jump_Land", "EXPORT_JUMP_LAND"),
}
LOOPS = {"idle", "walk", "jog", "run", "jump"}
# Phase offsets are the accepted R02 60 Hz motion-matching result.
PHASE_SAMPLES = {"idle": 0, "walk": 37, "jog": 11, "run": 7, "jump": 0}
# The ACCAD candidates are reviewed at the source capture rates. Keeping them
# avoids inventing an extra timing convention between the approved Blender
# result and GeckoLib; Gecko interpolates the timestamped keys at render rate.
NATIVE_SOURCE_FPS = {
    "walk": args.walk_fps,
    "run": args.run_fps,
}
if args.walk_blend is not None:
    PHASE_SAMPLES["walk"] = 0
if args.run_blend is not None:
    PHASE_SAMPLES["run"] = 0
THUMB_DRIVER = {"finger_thumb_l": "hand_l", "finger_thumb_r": "hand_r"}

geo_bones = json.loads(args.geo.read_text(encoding="utf-8"))["minecraft:geometry"][0]["bones"]
by_name = {row["name"]: row for row in geo_bones}
parents = {row["name"]: row.get("parent") for row in geo_bones}


def make_runtime_armature():
    data = bpy.data.armatures.new("EVA_RUNTIME_EXPORT_ARMATURE_DATA")
    armature = bpy.data.objects.new("EVA_RUNTIME_EXPORT_ARMATURE", data)
    scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for row in geo_bones:
        bone = data.edit_bones.new(row["name"])
        bone.head = target_to_blender(runtime_pivot(row.get("pivot", [0, 0, 0]))) * args.scale
        bone.tail = bone.head + Vector((0.0, 0.0, 0.25))
        bone.align_roll(Vector((0.0, -1.0, 0.0)))
        bone.use_connect = False
    for row in geo_bones:
        parent = row.get("parent")
        if parent and parent in data.edit_bones:
            data.edit_bones[row["name"]].parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="POSE")
    for row in geo_bones:
        pose = armature.pose.bones[row["name"]]
        pose.rotation_mode = "XYZ"
        pose["seele_bind_rotation"] = list(row.get("rotation", [0, 0, 0]))
    bpy.ops.object.mode_set(mode="OBJECT")
    armature.select_set(False)
    return armature


runtime = make_runtime_armature()


def rigid_fit(source_points, target_points):
    source = np.asarray(source_points, dtype=float)
    destination = np.asarray(target_points, dtype=float)
    source_center = source.mean(axis=0)
    target_center = destination.mean(axis=0)
    covariance = (source - source_center).T @ (destination - target_center)
    left, _, right = np.linalg.svd(covariance)
    rotation = right.T @ left.T
    if np.linalg.det(rotation) < 0.0:
        right[-1, :] *= -1.0
        rotation = right.T @ left.T
    translation = target_center - rotation @ source_center
    matrix = Matrix.Identity(4)
    for row in range(3):
        for column in range(3):
            matrix[row][column] = float(rotation[row, column])
        matrix[row][3] = float(translation[row])
    fitted = (rotation @ source.T).T + translation
    errors = np.linalg.norm(fitted - destination, axis=1)
    return matrix, float(np.sqrt(np.mean(errors * errors))), float(errors.max())


mesh_payload = json.loads(args.mesh.read_text(encoding="utf-8"))
stride = int(mesh_payload.get("stride", 0))
if stride != 8:
    raise RuntimeError(f"expected stride 8, got {stride}")
cursor = 0
part_pretransforms = {}
rest_fit = {}
for bone_name, part in mesh_payload["parts"].items():
    pivot = runtime_pivot(part["pivot"])
    values = [float(value) for value in part["vertices"]]
    source_points = []
    target_points = []
    for offset in range(0, len(values), stride):
        local = Vector((-values[offset], values[offset + 1], values[offset + 2]))
        source_point = target_to_blender(pivot + local) * args.scale
        source_points.append(tuple(source_point))
        target_points.append(tuple(target_mesh.data.vertices[cursor].co))
        cursor += 1
    transform, rms, maximum = rigid_fit(source_points, target_points)
    part_pretransforms[bone_name] = transform
    rest_fit[bone_name] = {"rms": rms, "maximum": maximum,
                           "vertices": len(source_points)}
if cursor != len(target_mesh.data.vertices):
    raise RuntimeError(
        f"mesh revision mismatch: JSON={cursor} blend={len(target_mesh.data.vertices)}")

mesh_bones = set(mesh_payload["parts"])
export_bones = set(mesh_bones)
for bone_name in tuple(mesh_bones):
    parent = parents.get(bone_name)
    while parent is not None:
        export_bones.add(parent)
        parent = parents.get(parent)
bone_order = [row["name"] for row in geo_bones if row["name"] in export_bones]


def source_samples(action, loop, phase_samples, native_fps=None):
    start = float(action.frame_range[0])
    end = float(action.frame_range[1])
    if native_fps is not None:
        if native_fps <= 0.0:
            raise RuntimeError(f"invalid native source rate: {native_fps}")
        first = int(math.ceil(start - 1.0e-6))
        last = int(math.floor(end + 1.0e-6))
        frames = [float(frame) for frame in range(first, last + 1)]
        if not frames:
            raise RuntimeError(f"action {action.name} has no integer samples")
        if loop:
            phase = phase_samples % len(frames)
            frames = frames[phase:] + frames[:phase]
            samples = [(frame, index / native_fps)
                       for index, frame in enumerate(frames)]
            # Close at the next source sample, not on the final captured
            # sample.  This preserves the accepted cycle duration and lets
            # Gecko interpolate the measured last-to-first seam once.
            samples.append((frames[0], len(frames) / native_fps))
            return samples
        return [(frame, index / native_fps)
                for index, frame in enumerate(frames)]
    step = 0.5
    intervals = max(1, int(round((end - start) / step)))
    if loop:
        frames = [start + index * step for index in range(intervals)]
        phase = phase_samples % len(frames)
        frames = frames[phase:] + frames[:phase]
        frames = frames + [frames[0]]
    else:
        frames = [start + index * step for index in range(intervals + 1)]
    return [(frame, index / 60.0) for index, frame in enumerate(frames)]


def set_frame(value):
    whole = math.floor(value)
    scene.frame_set(whole, subframe=value - whole)
    bpy.context.view_layer.update()


def clean(value):
    value = round(float(value), 5)
    return 0.0 if abs(value) < 0.000005 else value


def time_key(seconds):
    return f"{seconds:.5f}".rstrip("0").rstrip(".") or "0"


def solve_runtime_pose(root_reference):
    for name in bone_order:
        pose = runtime.pose.bones[name]
        pose.rotation_mode = "QUATERNION"
        pose.location = (0.0, 0.0, 0.0)
        pose.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pose.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()

    desired = {}
    for name in bone_order:
        driver = THUMB_DRIVER.get(name, name)
        if driver not in target.pose.bones:
            deformation_rotation = Matrix.Identity(3).to_quaternion()
        else:
            deformation_rotation = (
                target.pose.bones[driver].matrix.to_quaternion()
                @ target.data.bones[driver].matrix_local.to_quaternion().inverted()
            )
        pre_rotation = part_pretransforms.get(
            name, Matrix.Identity(4)).to_quaternion()
        desired_rotation = (
            deformation_rotation @ pre_rotation
            @ runtime.data.bones[name].matrix_local.to_quaternion()
        )
        desired_rotation.normalize()
        pose = runtime.pose.bones[name]
        # Parent motion determines every articulated joint position.  Only
        # root translation is allowed; child translations would detach limbs
        # even if a single offline frame happened to fit perfectly.
        current_translation = pose.matrix.translation.copy()
        if name == "root":
            current_translation += (
                target.pose.bones["root"].matrix.translation - root_reference
            )
        matrix = desired_rotation.to_matrix().to_4x4()
        matrix.translation = current_translation
        pose.matrix = matrix
        basis = pose.matrix_basis.copy()
        basis_rotation = basis.to_quaternion()
        basis_rotation.normalize()
        basis_location = (basis.translation.copy() if name == "root"
                          else Vector((0.0, 0.0, 0.0)))
        pose.location = basis_location
        pose.rotation_quaternion = basis_rotation
        pose.scale = (1.0, 1.0, 1.0)
        bpy.context.view_layer.update()
        desired[name] = matrix
    return desired


animations = {}
audit_actions = {}
for suffix, action in actions.items():
    loop = suffix in LOOPS
    samples = source_samples(
        action, loop, PHASE_SAMPLES.get(suffix, 0),
        NATIVE_SOURCE_FPS.get(suffix),
    )
    channels = {name: {"rotation": {}, "position": {}} for name in bone_order}
    previous_euler = {name: None for name in bone_order}
    max_rotation = 0.0
    max_position = 0.0
    root_locations = []
    target.animation_data.action = action
    set_frame(samples[0][0])
    root_reference = target.pose.bones["root"].matrix.translation.copy()
    for source_frame, output_time in samples:
        target.animation_data.action = action
        set_frame(source_frame)
        solve_runtime_pose(root_reference)
        key = time_key(output_time)
        for name in bone_order:
            basis = runtime.pose.bones[name].matrix_basis.copy()
            euler = (basis.to_euler("XYZ", previous_euler[name])
                     if previous_euler[name] is not None
                     else basis.to_euler("XYZ"))
            previous_euler[name] = euler.copy()
            bind = by_name[name].get("rotation", [0, 0, 0])
            authored_rotation = [
                clean(-math.degrees(euler.x) - float(bind[0])),
                clean(-math.degrees(euler.y) - float(bind[1])),
                clean(math.degrees(euler.z) - float(bind[2])),
            ]
            if name == "root":
                # Minecraft owns chassis heading and world orientation.  A
                # second yaw authority is forbidden. The ACCAD R32
                # actions are the exception for pitch/roll: their reviewed
                # root alignment carries the pelvis weight transfer and the
                # constant correction that removes source-body side lean.
                # Entity yaw still owns world heading and is never authored by
                # these forward-only cycles.
                if not (suffix in {"walk", "run"}
                        and NATIVE_SOURCE_FPS.get(suffix)):
                    authored_rotation = [0.0, 0.0, 0.0]
            if name == "head" and suffix in {"idle", "walk", "jog", "run"}:
                # Runtime camera/entity yaw already supplies gaze direction.
                # The source head micro-motion is amplified by the sixty-
                # block model and reads as shaking, so locomotion keeps a
                # stable neck while inheriting natural torso movement.
                authored_rotation = [0.0, 0.0, 0.0]
            location = basis.translation
            authored_position = [
                clean(-location.x / args.scale),
                clean(location.y / args.scale),
                clean(location.z / args.scale),
            ]
            channels[name]["rotation"][key] = authored_rotation
            channels[name]["position"][key] = authored_position
            max_rotation = max(max_rotation, *(abs(value) for value in authored_rotation))
            max_position = max(max_position, *(abs(value) for value in authored_position))
        root_locations.append(channels["root"]["position"][key])

    emitted = {}
    for name, bone_channels in channels.items():
        rotations = list(bone_channels["rotation"].values())
        positions = list(bone_channels["position"].values())
        output_channels = {}
        if any(any(abs(value) > 0.00005 for value in sample)
               for sample in rotations):
            output_channels["rotation"] = bone_channels["rotation"]
        if any(any(abs(value) > 0.00005 for value in sample)
               for sample in positions):
            output_channels["position"] = bone_channels["position"]
        if output_channels:
            emitted[name] = output_channels
    duration = samples[-1][1]
    animation = {"animation_length": clean(duration), "bones": emitted}
    if loop:
        animation["loop"] = True
    animations[f"animation.eva_unit01.{suffix}"] = animation
    audit_actions[suffix] = {
        "source_action": action.name,
        "source_frames": [float(action.frame_range[0]),
                          float(action.frame_range[1])],
        "phase_samples_60hz": PHASE_SAMPLES.get(suffix, 0),
        "output_keys": len(samples),
        "native_source_fps": NATIVE_SOURCE_FPS.get(suffix),
        "animation_length": clean(duration),
        "bones": len(emitted),
        "maximum_authored_rotation_degrees": max_rotation,
        "maximum_authored_position_pixels": max_position,
        "root_position_ranges": [
            clean(max(sample[axis] for sample in root_locations)
                  - min(sample[axis] for sample in root_locations))
            for axis in range(3)
        ],
    }

# Ascending and descending use one continuous airborne action in Java.  Keep a
# compatibility alias for visual-lab commands that still request `fall`.
animations["animation.eva_unit01.fall"] = json.loads(json.dumps(
    animations["animation.eva_unit01.jump"]))

payload = {
    "schema": 1,
    "source": args.source_label,
    "sample_rate_hz": 60,
    "native_source_rates_hz": {
        name: rate for name, rate in NATIVE_SOURCE_FPS.items()
        if rate is not None
    },
    "replace_animations": animations,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
audit = {
    "schema": 1,
    "mesh_vertices": cursor,
    "export_bones": bone_order,
    "rest_fit_maximum": max(row["maximum"] for row in rest_fit.values()),
    "rest_fit_rms_maximum": max(row["rms"] for row in rest_fit.values()),
    "rest_fit": rest_fit,
    "actions": audit_actions,
}
args.audit.parent.mkdir(parents=True, exist_ok=True)
args.audit.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "animations": list(animations),
    "mesh_vertices": cursor,
    "rest_fit_maximum": audit["rest_fit_maximum"],
    "actions": audit_actions,
}, indent=2))
