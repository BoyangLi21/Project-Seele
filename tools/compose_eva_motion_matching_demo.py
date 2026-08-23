#!/usr/bin/env python3
"""Compose the standalone motion-matching decisions into one audited 3D clip."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_cmu_motion_candidates import (
    lock_contact_feet,
    runtime_target_pivots,
)
from build_eva_motion_database import load_target_pivots, rounded_quaternion


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--simulation", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--blend-frames", type=int, default=5)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def angular_velocity(previous: Quaternion, current: Quaternion,
                     fps: float) -> Vector:
    if previous.dot(current) < 0.0:
        current = Quaternion((-current.w, -current.x,
                              -current.y, -current.z))
    delta = previous.conjugated() @ current
    delta.normalize()
    return delta.to_exponential_map() * fps


def begin_inertialization(source_previous: dict, source: dict,
                          target: dict, target_next: dict,
                          fps: float) -> dict:
    offsets = []
    velocities = []
    for sp_values, source_values, target_values, tn_values in zip(
            source_previous["rotation_wxyz"], source["rotation_wxyz"],
            target["rotation_wxyz"], target_next["rotation_wxyz"]):
        sp = Quaternion(tuple(sp_values))
        src = Quaternion(tuple(source_values))
        dst = Quaternion(tuple(target_values))
        dst_next = Quaternion(tuple(tn_values))
        offset = dst.conjugated() @ src
        if offset.w < 0.0:
            offset = Quaternion((-offset.w, -offset.x,
                                 -offset.y, -offset.z))
        offsets.append(offset.to_exponential_map())
        velocities.append(
            angular_velocity(sp, src, fps)
            - angular_velocity(dst, dst_next, fps)
        )
    source_velocity = (float(source["root_m"][1])
                       - float(source_previous["root_m"][1])) * fps
    target_velocity = (float(target_next["root_m"][1])
                       - float(target["root_m"][1])) * fps
    return {
        "rotation_offset": offsets,
        "rotation_velocity": velocities,
        "root_offset": (float(source["root_m"][1])
                        - float(target["root_m"][1])),
        "root_velocity": source_velocity - target_velocity,
        "source_contact": list(source["foot_contact"]),
    }


def apply_inertialization(target: dict, state: dict, frame_index: int,
                          frame_count: int, fps: float) -> dict:
    output = copy.deepcopy(target)
    if frame_count <= 1:
        return output
    u = frame_index / (frame_count - 1)
    h00 = 2.0 * u * u * u - 3.0 * u * u + 1.0
    h10 = u * u * u - 2.0 * u * u + u
    duration = (frame_count - 1) / fps
    rotations = []
    for target_values, offset, velocity in zip(
            target["rotation_wxyz"], state["rotation_offset"],
            state["rotation_velocity"]):
        residual = offset * h00 + velocity * (h10 * duration)
        result = Quaternion(tuple(target_values)) @ Quaternion(residual)
        result.normalize()
        rotations.append(rounded_quaternion(result))
    output["rotation_wxyz"] = rotations
    output["root_m"][1] = round(
        float(target["root_m"][1])
        + state["root_offset"] * h00
        + state["root_velocity"] * h10 * duration,
        7,
    )
    if u < 0.5:
        output["foot_contact"] = list(state["source_contact"])
    return output


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    simulation = json.loads(args.simulation.read_text(encoding="utf-8"))
    fps = float(motion.get("sample_rate", 30.0))
    interval = int(simulation["decision_interval_frames"])
    frames = []
    transitions = []
    previous_clip = None
    path = Vector((0.0, 0.0))
    yaw = 0.0
    stop_elapsed = None
    for decision in simulation["decisions"]:
        clip_name = decision["to_clip"]
        clip = motion["clips"][clip_name]
        source_frames = clip["frames"]
        start = int(decision["to_frame"])
        changed = previous_clip is not None and previous_clip != clip_name
        inertial_state = None
        if changed:
            transitions.append({
                "output_frame": len(frames),
                "from": previous_clip,
                "to": clip_name,
            })
        for local_index in range(interval):
            source_index = start + local_index
            if clip.get("loop"):
                source_index %= max(1, len(source_frames) - 1)
            else:
                source_index = min(len(source_frames) - 1, source_index)
            target = copy.deepcopy(source_frames[source_index])
            if changed and frames and local_index == 0:
                next_index = source_index + 1
                if clip.get("loop"):
                    next_index %= max(1, len(source_frames) - 1)
                else:
                    next_index = min(len(source_frames) - 1, next_index)
                inertial_state = begin_inertialization(
                    frames[-2] if len(frames) >= 2 else frames[-1],
                    frames[-1], target, source_frames[next_index], fps,
                )
            if (inertial_state is not None
                    and local_index < args.blend_frames):
                target = apply_inertialization(
                    target, inertial_state, local_index,
                    args.blend_frames, fps,
                )
            speed = float(decision["desired_speed_mps"])
            stopping = bool(decision["stopping"])
            if stopping:
                stop_elapsed = 0.0 if stop_elapsed is None else stop_elapsed
                speed *= max(0.0, 1.0 - stop_elapsed / 1.0)
                stop_elapsed += 1.0 / fps
            else:
                stop_elapsed = None
            turn = float(decision["desired_turn_degrees"])
            if abs(turn) > 1.0e-5:
                yaw -= math.radians(turn) / 0.8 / fps
            facing = Vector((math.sin(yaw), -math.cos(yaw)))
            path += facing * (speed / fps)
            target["root_m"][0] = round(float(-path.x), 7)
            target["root_m"][2] = round(float(-path.y), 7)
            target["root_yaw_radians"] = round(float(yaw), 7)
            frames.append(target)
        previous_clip = clip_name
    pivots = runtime_target_pivots(load_target_pivots(args.geo))
    lock_contact_feet(frames, list(motion["bones"]), pivots,
                      Vector((0.0, 0.0, 0.0)))
    output = copy.deepcopy(motion)
    output["clips"] = {
        "idle": copy.deepcopy(motion["clips"]["idle"]),
        "motion_matching_demo": {
            "duration_seconds": round((len(frames) - 1) / fps, 6),
            "loop": False,
            "role": "motion_matching_demo",
            "frames": frames,
            "transitions": transitions,
        },
    }
    output["motion_matching_demo"] = {
        "simulation": str(args.simulation.resolve()),
        "transition_count": len(transitions),
        "inertialization_frames": args.blend_frames,
        "inertialization": "cubic quaternion exponential-map offset decay",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA motion matching demo: frames={len(frames)} "
        f"transitions={len(transitions)} output={args.output}"
    )


if __name__ == "__main__":
    main()
