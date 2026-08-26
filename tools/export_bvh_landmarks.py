"""Export normalized world-space landmarks from a BVH review window."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


LANDMARKS = [
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
    ("toe_r", "RightToeBase", False)
]


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
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_anim.bvh(
    filepath=str(args.source.resolve()), target="ARMATURE", global_scale=0.01,
    frame_start=1, use_fps_scale=False, update_scene_fps=True,
    update_scene_duration=True, rotate_mode="NATIVE",
    axis_forward="-Z", axis_up="Y",
)
rig = bpy.context.object
action = rig.animation_data.action
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
    rest_world_point("Head", tail=True).z
    - min(
        rest_world_point("LeftFoot").z,
        rest_world_point("LeftToeBase").z,
        rest_world_point("RightFoot").z,
        rest_world_point("RightToeBase").z,
    )
)


def set_source_frame(value: float) -> None:
    whole = math.floor(value)
    scene.frame_set(whole, subframe=value - whole)


def world_point(bone_name: str, tail: bool = False) -> Vector:
    bone = rig.pose.bones[bone_name]
    return rig.matrix_world @ (bone.tail if tail else bone.head)


set_source_frame(frames[0])
bpy.context.view_layer.update()
origin = world_point("Hips")
# BVH import has already converted the capture to Blender's gravity frame.
# Body lean is motion, not a coordinate-system axis; deriving "up" from the
# pelvis-to-head line tilts the floor and creates impossible one-foot heights.
up = Vector((0.0, 0.0, 1.0))
left = world_point("LeftUpLeg") - world_point("RightUpLeg")
left -= up * left.dot(up)
left.normalize()
forward = left.cross(up).normalized()
toe_hint = (
    world_point("LeftToeBase") - world_point("LeftFoot")
    + world_point("RightToeBase") - world_point("RightFoot")
)
toe_hint -= up * toe_hint.dot(up)
toe_alignment = forward.dot(toe_hint.normalized()) if toe_hint.length else 0.0


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
        (patch_z <= floor + 0.03) & (speed <= 0.30)
    )

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
        "forward_world": list(forward),
        "left_world": list(left),
        "up_world": list(up),
        "foot_forward_alignment": toe_alignment
    },
    "status": "source_landmarks_not_an_accepted_EVA_motion"
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
