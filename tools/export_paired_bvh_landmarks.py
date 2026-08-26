"""Export two synchronized BVH actors in one normalized interaction frame."""

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
    ("toe_r", "RightToeBase", False),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-a", required=True, type=Path)
    parser.add_argument("--source-b", required=True, type=Path)
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--end", required=True, type=int)
    parser.add_argument("--output-a", required=True, type=Path)
    parser.add_argument("--output-b", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--output-fps", type=float, default=60.0)
    parser.add_argument("--body-height-source-units", type=float)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def import_actor(path: Path, name: str):
    bpy.ops.import_anim.bvh(
        filepath=str(path.resolve()), target="ARMATURE", global_scale=0.01,
        frame_start=1, use_fps_scale=False, update_scene_fps=True,
        update_scene_duration=True, rotate_mode="NATIVE",
        axis_forward="-Z", axis_up="Y",
    )
    actor = bpy.context.object
    actor.name = name
    return actor


def point(actor, bone_name: str, tail: bool = False) -> Vector:
    bone = actor.pose.bones[bone_name]
    return actor.matrix_world @ (bone.tail if tail else bone.head)


def rest_point(actor, bone_name: str, tail: bool = False) -> Vector:
    bone = actor.data.bones[bone_name]
    return actor.matrix_world @ (bone.tail_local if tail else bone.head_local)


def rest_height(actor) -> float:
    return float(
        rest_point(actor, "Head", tail=True).z
        - min(
            rest_point(actor, "LeftFoot").z,
            rest_point(actor, "LeftToeBase").z,
            rest_point(actor, "RightFoot").z,
            rest_point(actor, "RightToeBase").z,
        )
    )


def main() -> None:
    args = parse_args()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    actor_a = import_actor(args.source_a, "PAIR_ACTOR_A")
    range_a = actor_a.animation_data.action.frame_range
    actor_b = import_actor(args.source_b, "PAIR_ACTOR_B")
    range_b = actor_b.animation_data.action.frame_range
    available = [
        max(int(math.ceil(range_a[0])), int(math.ceil(range_b[0]))),
        min(int(math.floor(range_a[1])), int(math.floor(range_b[1]))),
    ]
    if not (available[0] <= args.start < args.end <= available[1]):
        raise SystemExit(
            f"range {args.start}-{args.end} outside paired {available}"
        )

    scene = bpy.context.scene
    native_fps = scene.render.fps / scene.render.fps_base
    frame_step = native_fps / args.output_fps
    frames = list(np.arange(
        float(args.start), float(args.end) + frame_step * 0.25,
        frame_step, dtype=np.float64,
    ))
    frames[-1] = min(frames[-1], float(args.end))

    def set_frame(value: float) -> None:
        whole = math.floor(value)
        scene.frame_set(whole, subframe=value - whole)
        bpy.context.view_layer.update()

    set_frame(frames[0])
    origin = point(actor_a, "Hips")
    up = Vector((0.0, 0.0, 1.0))
    left = point(actor_a, "LeftUpLeg") - point(actor_a, "RightUpLeg")
    left -= up * left.dot(up)
    left.normalize()
    forward = left.cross(up).normalized()

    def canonical(value: Vector) -> np.ndarray:
        delta = value - origin
        return np.asarray(
            (delta.dot(forward), delta.dot(left), delta.dot(up)),
            dtype=np.float64,
        )

    names = [name for name, _, _ in LANDMARKS]
    index = {name: idx for idx, name in enumerate(names)}
    positions = {"a": [], "b": []}
    yaws = {"a": [], "b": []}
    heights = {"a": [], "b": []}
    actors = {"a": actor_a, "b": actor_b}
    for frame in frames:
        set_frame(frame)
        for key, actor in actors.items():
            row = np.stack([
                canonical(point(actor, bone_name, tail=tail))
                for _, bone_name, tail in LANDMARKS
            ])
            positions[key].append(row)
            dynamic_left = row[index["hip_l"]] - row[index["hip_r"]]
            dynamic_left[2] = 0.0
            dynamic_left /= max(np.linalg.norm(dynamic_left), 1.0e-8)
            dynamic_forward = np.asarray(
                (dynamic_left[1], -dynamic_left[0], 0.0),
                dtype=np.float64,
            )
            yaws[key].append(math.atan2(
                dynamic_forward[1], dynamic_forward[0]
            ))
            heights[key].append(
                row[index["head"], 2]
                - min(row[index["ankle_l"], 2],
                      row[index["toe_l"], 2],
                      row[index["ankle_r"], 2],
                      row[index["toe_r"], 2])
            )

    dynamic_median_height = float(np.median(heights["a"] + heights["b"]))
    rest_heights = {"a": rest_height(actor_a), "b": rest_height(actor_b)}
    if args.body_height_source_units is not None:
        body_height = float(args.body_height_source_units)
        body_height_method = "explicit_full_source_pair_audit"
    else:
        body_height = float(max(
            np.median(list(rest_heights.values())), dynamic_median_height
        ))
        body_height_method = "max_rest_and_window_height_fallback"
    if body_height <= 1.0e-8:
        raise RuntimeError("body height must be positive")
    normalized = {
        key: np.asarray(value, dtype=np.float64) / max(body_height, 1.0e-8)
        for key, value in positions.items()
    }
    floor = float(np.percentile(np.concatenate([
        normalized[key][:, index[name], 2]
        for key in ("a", "b")
        for name in ("ankle_l", "toe_l", "ankle_r", "toe_r")
    ]), 2.0))
    contacts = {}
    dt = 1.0 / args.output_fps
    for key in ("a", "b"):
        result = np.zeros((len(frames), 2), dtype=np.bool_)
        for side_index, side in enumerate(("l", "r")):
            ankle = normalized[key][:, index[f"ankle_{side}"]]
            toe = normalized[key][:, index[f"toe_{side}"]]
            patch_z = np.minimum(ankle[:, 2], toe[:, 2])
            speed = np.zeros(len(frames), dtype=np.float64)
            if len(frames) > 1:
                step_speed = (
                    np.linalg.norm(np.diff(ankle[:, :2], axis=0), axis=1)
                    / dt
                )
                speed[1:] = step_speed
                speed[0] = step_speed[0]
            result[:, side_index] = (
                (patch_z <= floor + 0.03) & (speed <= 0.30)
            )
        contacts[key] = result

    outputs = {"a": args.output_a, "b": args.output_b}
    for key in ("a", "b"):
        outputs[key].parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            outputs[key],
            frames=np.asarray(frames, dtype=np.float64),
            fps=np.asarray([args.output_fps], dtype=np.float64),
            landmark_names=np.asarray(names),
            positions_H=normalized[key],
            root_yaw_rad=np.unwrap(
                np.asarray(yaws[key], dtype=np.float64)
            ),
            foot_contact=contacts[key],
            body_height_source_units=np.asarray(
                [body_height], dtype=np.float64
            ),
            shared_interaction_frame=np.asarray([True]),
            actor=np.asarray([key]),
        )

    hand_a = normalized["a"][:, index["hand_r"]]
    elbow_b = normalized["b"][:, index["elbow_l"]]
    contact_distance = np.linalg.norm(hand_a - elbow_b, axis=1)
    metadata = {
        "schema": 1,
        "source_name": args.source_name,
        "source_files": [
            str(args.source_a.resolve()), str(args.source_b.resolve())
        ],
        "source_url": args.source_url,
        "license": args.license,
        "frames": [float(frames[0]), float(frames[-1])],
        "native_fps": native_fps,
        "fps": args.output_fps,
        "body_height_source_units": body_height,
        "body_height_method": body_height_method,
        "actor_rest_height_source_units": rest_heights,
        "dynamic_window_median_height_source_units": dynamic_median_height,
        "coordinate_system": "+X actor-A forward, +Y actor-A left, +Z up",
        "initial_root_separation_H": float(np.linalg.norm(
            normalized["a"][0, index["pelvis"]]
            - normalized["b"][0, index["pelvis"]]
        )),
        "initial_yaw_rad": {
            key: float(np.unwrap(np.asarray(yaws[key]))[0])
            for key in ("a", "b")
        },
        "right_hand_a_to_left_elbow_b_H": {
            "minimum": float(np.min(contact_distance)),
            "p95": float(np.percentile(contact_distance, 95.0)),
        },
        "contact_fraction": {
            key: contacts[key].mean(axis=0).tolist()
            for key in ("a", "b")
        },
        "status": "paired_source_landmarks_not_accepted_EVA_motion",
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == "__main__":
    main()
