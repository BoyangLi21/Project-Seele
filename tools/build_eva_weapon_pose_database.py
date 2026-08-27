#!/usr/bin/env python3
"""Convert reviewed Gecko weapon layers into the exact 3D motion schema."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from mathutils import Euler, Quaternion


POSES = {
    "knife_ready_review": ("knife_ready",),
    "knife_strike_review": ("knife",),
    "knife_heavy_review": ("knife_heavy",),
    "prone_knife_review": ("prone", "prone_knife"),
    "crouch_knife_review": ("crouch", "crouch_knife"),
    "rifle_aim_review": ("rifle_aim",),
    "rifle_fire_review": ("rifle_aim", "rifle_fire"),
    "prone_rifle_review": ("prone", "prone_rifle_aim"),
    "lance_ready_review": ("lance_ready",),
    "lance_thrust_review": ("lance_thrust",),
    "prone_lance_review": ("prone", "prone_lance_ready"),
    "prone_lance_thrust_review": ("prone", "prone_lance_thrust"),
    "crouch_lance_thrust_review": ("crouch", "crouch_lance_thrust"),
    "crouch_review": ("crouch",),
    "stand_to_crouch_review": ("stand_to_crouch",),
    "crouch_to_stand_review": ("crouch_to_stand",),
    "crouch_walk_review": ("crouch_walk",),
    "prone_review": ("prone",),
    "crouch_to_prone_review": ("crouch_to_prone",),
    "prone_to_crouch_review": ("prone_to_crouch",),
    "crawl_review": ("crawl",),
    "berserk_roar_review": ("berserk_roar",),
    "berserk_run_review": ("berserk_run",),
    "berserk_claw_r_review": ("berserk_claw_r",),
    "berserk_claw_l_review": ("berserk_claw_l",),
    "berserk_pounce_review": ("berserk_pounce",),
}


def pose_role(name: str) -> str:
    if name in {"crouch_review", "crouch_walk_review"}:
        return "crouch"
    if name in {"prone_review", "crawl_review"}:
        return "candidate_prone"
    if name in {
            "stand_to_crouch_review", "crouch_to_stand_review",
            "crouch_to_prone_review", "prone_to_crouch_review"}:
        return "candidate_posture_transition"
    return "weapon_pose_review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-motion-db", required=True, type=Path)
    parser.add_argument("--animation", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def channel_value(channel, seconds: float, duration: float):
    if isinstance(channel, list):
        return [float(value) for value in channel]
    keys = sorted((float(time), [float(value) for value in value])
                  for time, value in channel.items())
    if duration > 0.0:
        seconds = min(duration, max(0.0, seconds))
    if seconds <= keys[0][0]:
        return keys[0][1]
    if seconds >= keys[-1][0]:
        return keys[-1][1]
    for (left_time, left), (right_time, right) in zip(keys, keys[1:]):
        if left_time <= seconds <= right_time:
            alpha = (seconds - left_time) / max(1.0e-8, right_time - left_time)
            return [a + (b - a) * alpha for a, b in zip(left, right)]
    return keys[-1][1]


def authored_quaternion(degrees) -> list[float]:
    quat = Euler(tuple(math.radians(float(value)) for value in degrees),
                 "XYZ").to_quaternion()
    quat.normalize()
    return [round(float(quat.w), 7), round(float(quat.x), 7),
            round(float(quat.y), 7), round(float(quat.z), 7)]


def main() -> None:
    args = parse_args()
    base = json.loads(args.base_motion_db.read_text(encoding="utf-8"))
    animation = json.loads(args.animation.read_text(encoding="utf-8"))["animations"]
    bones = list(base["bones"])
    for layer_names in POSES.values():
        for layer_name in layer_names:
            for bone_name in animation[
                    f"animation.eva_unit01.{layer_name}"]["bones"]:
                if bone_name not in bones:
                    bones.append(bone_name)
    for name in ("knife", "cannon", "lance"):
        if name not in bones:
            bones.append(name)
    base_frame = copy.deepcopy(base["clips"]["idle"]["frames"][0])
    identity = [1.0, 0.0, 0.0, 0.0]
    while len(base_frame["rotation_wxyz"]) < len(bones):
        base_frame["rotation_wxyz"].append(list(identity))
    clips = {"idle": copy.deepcopy(base["clips"]["idle"])}
    # Extend idle frames to the union bone contract as well.
    for frame in clips["idle"]["frames"]:
        while len(frame["rotation_wxyz"]) < len(bones):
            frame["rotation_wxyz"].append(list(identity))
    fps = float(base.get("sample_rate", 30.0))
    for output_name, layer_names in POSES.items():
        layers = [animation[f"animation.eva_unit01.{name}"]
                  for name in layer_names]
        duration = max(float(layer.get("animation_length", 0.0))
                       for layer in layers)
        count = max(2, int(round(duration * fps)) + 1)
        frames = []
        for frame_index in range(count):
            seconds = min(duration, frame_index / fps)
            frame = copy.deepcopy(base_frame)
            positions = {}
            for layer in layers:
                layer_duration = float(layer.get("animation_length", duration))
                for bone_name, channels in layer.get("bones", {}).items():
                    if bone_name not in bones:
                        continue
                    bone_index = bones.index(bone_name)
                    if "rotation" in channels:
                        frame["rotation_wxyz"][bone_index] = authored_quaternion(
                            channel_value(channels["rotation"], seconds,
                                          layer_duration)
                        )
                    if "position" in channels:
                        positions[bone_name] = [round(float(value), 7)
                                                for value in channel_value(
                            channels["position"], seconds, layer_duration
                        )]
            if positions:
                frame["bone_position_xyz"] = positions
            frame["foot_contact"] = [False, False]
            frame["hand_contact"] = [False, False]
            frames.append(frame)
        clips[output_name] = {
            "duration_seconds": round(duration, 6),
            "loop": bool(all(layer.get("loop", False) for layer in layers)),
            "role": pose_role(output_name),
            "source_layers": list(layer_names),
            "frames": frames,
        }
    output = copy.deepcopy(base)
    output["bones"] = bones
    output["clips"] = clips
    output["weapon_pose_review"] = {
        "source_animation": str(args.animation.resolve()),
        "poses": {name: list(layers) for name, layers in POSES.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"EVA weapon pose DB: clips={len(clips)} bones={len(bones)} output={args.output}")


if __name__ == "__main__":
    main()
