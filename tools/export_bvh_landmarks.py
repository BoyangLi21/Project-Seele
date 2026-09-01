"""Export normalized world-space landmarks from a BVH or FBX review window."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


LANDMARK_PROFILES = {
    "tuffles": [
        ("pelvis", "Hip", False),
        ("abdomen", "LowerSpine", False),
        ("thorax", "Chest", False),
        ("neck", "Neck", False),
        ("head", "Head", False),
        ("clavicle_l", "LClavicle", False),
        ("shoulder_l", "LShoulder", False),
        ("elbow_l", "LForearm", False),
        ("wrist_l", "LHand", False),
        ("hand_l", "LHand", True),
        ("clavicle_r", "RClavicle", False),
        ("shoulder_r", "RShoulder", False),
        ("elbow_r", "RForearm", False),
        ("wrist_r", "RHand", False),
        ("hand_r", "RHand", True),
        ("hip_l", "LThigh", False),
        ("knee_l", "LShin", False),
        ("ankle_l", "LFoot", False),
        ("toe_l", "LToe", False),
        ("hip_r", "RThigh", False),
        ("knee_r", "RShin", False),
        ("ankle_r", "RFoot", False),
        ("toe_r", "RToe", False),
    ],
    "rokoko_mixamo": [
        ("pelvis", "mixamorig:Hips", False),
        ("abdomen", "mixamorig:Spine", False),
        ("thorax", "mixamorig:Spine2", False),
        ("neck", "mixamorig:Neck", False),
        ("head", "mixamorig:Head", False),
        ("clavicle_l", "mixamorig:LeftShoulder", False),
        ("shoulder_l", "mixamorig:LeftArm", False),
        ("elbow_l", "mixamorig:LeftForeArm", False),
        ("wrist_l", "mixamorig:LeftHand", False),
        ("hand_l", "mixamorig:LeftHand", True),
        ("clavicle_r", "mixamorig:RightShoulder", False),
        ("shoulder_r", "mixamorig:RightArm", False),
        ("elbow_r", "mixamorig:RightForeArm", False),
        ("wrist_r", "mixamorig:RightHand", False),
        ("hand_r", "mixamorig:RightHand", True),
        ("hip_l", "mixamorig:LeftUpLeg", False),
        ("knee_l", "mixamorig:LeftLeg", False),
        ("ankle_l", "mixamorig:LeftFoot", False),
        ("toe_l", "mixamorig:LeftToeBase", False),
        ("hip_r", "mixamorig:RightUpLeg", False),
        ("knee_r", "mixamorig:RightLeg", False),
        ("ankle_r", "mixamorig:RightFoot", False),
        ("toe_r", "mixamorig:RightToeBase", False),
    ],
    "cmu_accad": [
        ("pelvis", "Hips", False),
        ("abdomen", "Spine", False),
        ("thorax", "Spine1", False),
        ("neck", "Neck", False),
        ("head", "Head", False),
        ("clavicle_l", "LeftShoulder", False),
        ("shoulder_l", "LeftArm", False),
        ("elbow_l", "LeftForeArm", False),
        ("wrist_l", "LeftHand", False),
        ("hand_l", "LeftHand", True),
        ("clavicle_r", "RightShoulder", False),
        ("shoulder_r", "RightArm", False),
        ("elbow_r", "RightForeArm", False),
        ("wrist_r", "RightHand", False),
        ("hand_r", "RightHand", True),
        ("hip_l", "LeftUpLeg", False),
        ("knee_l", "LeftLeg", False),
        ("ankle_l", "LeftFoot", False),
        ("toe_l", "LeftToeBase", False),
        ("hip_r", "RightUpLeg", False),
        ("knee_r", "RightLeg", False),
        ("ankle_r", "RightFoot", False),
        ("toe_r", "RightToeBase", False),
    ],
    "bandai_namco_dataset_1": [
        ("pelvis", "Hips", False),
        ("abdomen", "Spine", False),
        ("thorax", "Chest", False),
        ("neck", "Neck", False),
        ("head", "Head", False),
        ("clavicle_l", "Shoulder_L", False),
        ("shoulder_l", "UpperArm_L", False),
        ("elbow_l", "LowerArm_L", False),
        ("wrist_l", "Hand_L", False),
        ("hand_l", "Hand_L", True),
        ("clavicle_r", "Shoulder_R", False),
        ("shoulder_r", "UpperArm_R", False),
        ("elbow_r", "LowerArm_R", False),
        ("wrist_r", "Hand_R", False),
        ("hand_r", "Hand_R", True),
        ("hip_l", "UpperLeg_L", False),
        ("knee_l", "LowerLeg_L", False),
        ("ankle_l", "Foot_L", False),
        ("toe_l", "Toes_L", False),
        ("hip_r", "UpperLeg_R", False),
        ("knee_r", "LowerLeg_R", False),
        ("ankle_r", "Foot_R", False),
        ("toe_r", "Toes_R", False),
    ],
    "eyes_japan_takiguchi": [
        ("pelvis", "Hips", False),
        ("abdomen", "Chest", False),
        ("thorax", "Chest2", False),
        ("neck", "Neck", False),
        ("head", "Head", False),
        ("clavicle_l", "LeftCollar", False),
        ("shoulder_l", "LeftShoulder", False),
        ("elbow_l", "LeftElbow", False),
        ("wrist_l", "LeftWrist", False),
        ("hand_l", "LeftWrist", True),
        ("clavicle_r", "RightCollar", False),
        ("shoulder_r", "RightShoulder", False),
        ("elbow_r", "RightElbow", False),
        ("wrist_r", "RightWrist", False),
        ("hand_r", "RightWrist", True),
        ("hip_l", "LeftHip", False),
        ("knee_l", "LeftKnee", False),
        ("ankle_l", "LeftAnkle", False),
        ("toe_l", "LeftAnkle", True),
        ("hip_r", "RightHip", False),
        ("knee_r", "RightKnee", False),
        ("ankle_r", "RightAnkle", False),
        ("toe_r", "RightAnkle", True),
    ],
    "eyes_japan_yokoyama": [
        ("pelvis", "Hips", False),
        ("abdomen", "Chest", False),
        ("thorax", "Chest", True),
        ("neck", "Neck", False),
        ("head", "Head", True),
        ("clavicle_l", "LeftCollar", False),
        ("shoulder_l", "LeftUpArm", False),
        ("elbow_l", "LeftLowArm", False),
        ("wrist_l", "LeftHand", False),
        ("hand_l", "LeftHand", True),
        ("clavicle_r", "RightCollar", False),
        ("shoulder_r", "RightUpArm", False),
        ("elbow_r", "RightLowArm", False),
        ("wrist_r", "RightHand", False),
        ("hand_r", "RightHand", True),
        ("hip_l", "LeftUpLeg", False),
        ("knee_l", "LeftLowLeg", False),
        ("ankle_l", "LeftFoot", False),
        ("toe_l", "LeftFoot", True),
        ("hip_r", "RightUpLeg", False),
        ("knee_r", "RightLowLeg", False),
        ("ankle_r", "RightFoot", False),
        ("toe_r", "RightFoot", True),
    ],
}


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--start", required=True, type=int)
parser.add_argument("--end", required=True, type=int)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--metadata", required=True, type=Path)
parser.add_argument("--source-name", required=True)
parser.add_argument("--source-url", required=True)
parser.add_argument("--license", required=True)
parser.add_argument("--output-fps", type=float)
parser.add_argument("--body-height-source-units", type=float)
parser.add_argument("--basis-frame", type=int,
                    help="standing frame used to derive forward/left axes")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
source = args.source.resolve()
if source.suffix.lower() == ".bvh":
    header = source.read_text(encoding="utf-8", errors="ignore")[:4096]
    if "ROOT Hip\n" in header or "ROOT Hip\r\n" in header:
        axis_forward, axis_up = "-Y", "Z"
    else:
        axis_forward, axis_up = "-Z", "Y"
    bpy.ops.import_anim.bvh(
        filepath=str(source), target="ARMATURE", global_scale=0.01,
        frame_start=1, use_fps_scale=False, update_scene_fps=True,
        update_scene_duration=True, rotate_mode="NATIVE",
        axis_forward=axis_forward, axis_up=axis_up,
    )
elif source.suffix.lower() == ".fbx":
    bpy.ops.import_scene.fbx(
        filepath=str(source), automatic_bone_orientation=False,
    )
else:
    raise SystemExit(f"unsupported motion source: {source}")
armatures = [
    obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"
]
if len(armatures) != 1:
    raise RuntimeError(
        f"expected one source armature, found {len(armatures)}"
    )
rig = armatures[0]
if rig.animation_data is None or rig.animation_data.action is None:
    raise RuntimeError("source armature has no active animation action")
action = rig.animation_data.action
available_bones = set(rig.pose.bones.keys())
matches = [
    (name, landmarks)
    for name, landmarks in LANDMARK_PROFILES.items()
    if all(bone_name in available_bones
           for _, bone_name, _ in landmarks)
]
if len(matches) != 1:
    raise RuntimeError(
        "expected one supported BVH landmark profile, matched "
        f"{[name for name, _ in matches]}; bones="
        + ", ".join(sorted(available_bones))
    )
source_profile, LANDMARKS = matches[0]
bone_for = {name: bone_name for name, bone_name, _ in LANDMARKS}
available = [int(math.ceil(action.frame_range[0])),
             int(math.floor(action.frame_range[1]))]
if not (available[0] <= args.start < args.end <= available[1]):
    raise SystemExit(f"range {args.start}-{args.end} outside {available}")
scene = bpy.context.scene
native_fps = scene.render.fps / scene.render.fps_base
fps = args.output_fps or native_fps
frame_step = native_fps / fps
frames = list(np.arange(
    float(args.start), float(args.end) + frame_step * 0.25,
    frame_step, dtype=np.float64,
))
frames[-1] = min(frames[-1], float(args.end))


def rest_world_point(bone_name: str, tail: bool = False) -> Vector:
    bone = rig.data.bones[bone_name]
    return rig.matrix_world @ (bone.tail_local if tail else bone.head_local)


rest_body_height = (
    rest_world_point(bone_for["head"], tail=True).z
    - min(
        rest_world_point(bone_for["ankle_l"]).z,
        rest_world_point(bone_for["toe_l"]).z,
        rest_world_point(bone_for["ankle_r"]).z,
        rest_world_point(bone_for["toe_r"]).z,
    )
)


def set_source_frame(value: float) -> None:
    whole = math.floor(value)
    scene.frame_set(whole, subframe=value - whole)


def world_point(bone_name: str, tail: bool = False) -> Vector:
    bone = rig.pose.bones[bone_name]
    return rig.matrix_world @ (bone.tail if tail else bone.head)


basis_frame = args.basis_frame or frames[0]
if not available[0] <= basis_frame <= available[1]:
    raise SystemExit(f"basis frame {basis_frame} outside {available}")
set_source_frame(float(basis_frame))
bpy.context.view_layer.update()
# BVH import has already converted the capture to Blender's gravity frame.
# Body lean is motion, not a coordinate-system axis; deriving "up" from the
# pelvis-to-head line tilts the floor and creates impossible one-foot heights.
up = Vector((0.0, 0.0, 1.0))
left = world_point(bone_for["hip_l"]) - world_point(bone_for["hip_r"])
left -= up * left.dot(up)
left.normalize()
forward = left.cross(up).normalized()
toe_hint = (
    world_point(bone_for["toe_l"]) - world_point(bone_for["ankle_l"])
    + world_point(bone_for["toe_r"]) - world_point(bone_for["ankle_r"])
)
toe_hint -= up * toe_hint.dot(up)
toe_alignment = forward.dot(toe_hint.normalized()) if toe_hint.length else 0.0
set_source_frame(frames[0])
bpy.context.view_layer.update()
origin = world_point(bone_for["pelvis"])


def canonical(point_value: Vector) -> np.ndarray:
    delta = point_value - origin
    return np.asarray((delta.dot(forward), delta.dot(left), delta.dot(up)),
                      dtype=np.float64)


positions = []
yaws = []
heights = []
for frame in frames:
    set_source_frame(frame)
    bpy.context.view_layer.update()
    row = np.stack([
        canonical(world_point(bone_name, tail=tail))
        for _, bone_name, tail in LANDMARKS
    ])
    positions.append(row)
    index = {name: idx for idx, (name, _, _) in enumerate(LANDMARKS)}
    dynamic_left = row[index["hip_l"]] - row[index["hip_r"]]
    dynamic_left[2] = 0.0
    if np.linalg.norm(dynamic_left) < 1.0e-8:
        dynamic_left = np.asarray((0.0, 1.0, 0.0))
    else:
        dynamic_left /= np.linalg.norm(dynamic_left)
    dynamic_forward = np.asarray((dynamic_left[1], -dynamic_left[0], 0.0))
    if dynamic_forward[0] < 0.0:
        dynamic_forward *= -1.0
    yaws.append(math.atan2(dynamic_forward[1], dynamic_forward[0]))
    heights.append(
        row[index["head"], 2]
        - min(row[index["ankle_l"], 2], row[index["toe_l"], 2],
              row[index["ankle_r"], 2], row[index["toe_r"], 2])
    )
positions = np.asarray(positions, dtype=np.float64)
yaws = np.unwrap(np.asarray(yaws, dtype=np.float64))
dynamic_median_height = float(np.median(heights))
if args.body_height_source_units is not None:
    body_height = float(args.body_height_source_units)
    body_height_method = "explicit_full_source_audit"
else:
    body_height = float(max(rest_body_height, dynamic_median_height))
    body_height_method = "max_rest_and_window_height_fallback"
if body_height <= 1.0e-8:
    raise RuntimeError("body height must be positive")
normalized = positions / max(body_height, 1.0e-8)
names = [name for name, _, _ in LANDMARKS]
index = {name: idx for idx, name in enumerate(names)}
floor_values = np.minimum.reduce([
    normalized[:, index["ankle_l"], 2],
    normalized[:, index["toe_l"], 2],
    normalized[:, index["ankle_r"], 2],
    normalized[:, index["toe_r"], 2],
])
floor = float(np.percentile(floor_values, 2.0))
contacts = np.zeros((len(frames), 2), dtype=np.bool_)
dt = 1.0 / fps
contact_height = (0.055 if source_profile.startswith("eyes_japan") else 0.03)
contact_speed = (0.55 if source_profile.startswith("eyes_japan") else 0.30)
contact_patch_heights = []
for side_index, side in enumerate(("l", "r")):
    ankle = normalized[:, index[f"ankle_{side}"]]
    toe = normalized[:, index[f"toe_{side}"]]
    patch_z = np.minimum(ankle[:, 2], toe[:, 2])
    speed = np.zeros(len(frames), dtype=np.float64)
    if len(frames) > 1:
        step_speed = np.linalg.norm(np.diff(ankle[:, :2], axis=0), axis=1) / dt
        speed[1:] = step_speed
        speed[0] = step_speed[0]
    contacts[:, side_index] = (
        (patch_z <= floor + contact_height) & (speed <= contact_speed)
    )
    contact_patch_heights.append(patch_z)
if source_profile.startswith("eyes_japan"):
    contact_patch_heights = np.column_stack(contact_patch_heights)
    for frame_index in range(len(frames)):
        if contacts[frame_index].any():
            continue
        side_index = int(np.argmin(contact_patch_heights[frame_index]))
        if (contact_patch_heights[frame_index, side_index]
                <= floor + contact_height):
            contacts[frame_index, side_index] = True

args.output.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(
    args.output,
    frames=np.asarray(frames, dtype=np.float64),
    fps=np.asarray([fps], dtype=np.float64),
    landmark_names=np.asarray(names),
    positions_H=normalized,
    root_yaw_rad=yaws,
    foot_contact=contacts,
    body_height_source_units=np.asarray([body_height], dtype=np.float64),
)
metadata = {
    "schema": 1,
    "source_name": args.source_name,
    "source_profile": source_profile,
    "source_file": str(args.source.resolve()),
    "source_url": args.source_url,
    "license": args.license,
    "frames": [float(frames[0]), float(frames[-1])],
    "native_fps": native_fps,
    "fps": fps,
    "landmarks": names,
    "body_height_source_units": body_height,
    "body_height_method": body_height_method,
    "rest_skeleton_height_source_units": rest_body_height,
    "dynamic_window_median_height_source_units": dynamic_median_height,
    "coordinate_system": "+X forward, +Y left, +Z up",
    "basis": {
        "source_frame": float(basis_frame),
        "forward_world": list(forward),
        "left_world": list(left),
        "up_world": list(up),
        "foot_forward_alignment": toe_alignment
    },
    "status": "source_landmarks_not_an_accepted_EVA_motion"
}
metadata["contact_thresholds_H"] = {
    "height": contact_height,
    "horizontal_speed_per_second": contact_speed,
}
args.metadata.parent.mkdir(parents=True, exist_ok=True)
args.metadata.write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "output": str(args.output), "frames": metadata["frames"],
    "fps": fps, "height": body_height,
    "toe_alignment": toe_alignment,
    "contact_fraction": contacts.mean(axis=0).tolist(),
}, ensure_ascii=False))
