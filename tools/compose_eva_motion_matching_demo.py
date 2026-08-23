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


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def blend_frame(previous: dict, target: dict, amount: float) -> dict:
    output = copy.deepcopy(target)
    rotations = []
    for first_values, second_values in zip(
            previous["rotation_wxyz"], target["rotation_wxyz"]):
        first = Quaternion(tuple(first_values))
        second = Quaternion(tuple(second_values))
        if first.dot(second) < 0.0:
            second = Quaternion((-second.w, -second.x,
                                 -second.y, -second.z))
        rotations.append(rounded_quaternion(first.slerp(second, amount)))
    output["rotation_wxyz"] = rotations
    output["root_m"][1] = round(
        float(previous["root_m"][1]) * (1.0 - amount)
        + float(target["root_m"][1]) * amount, 7
    )
    if amount < 0.5:
        output["foot_contact"] = list(previous["foot_contact"])
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
            if changed and frames and local_index < args.blend_frames:
                amount = smoothstep((local_index + 1) / args.blend_frames)
                target = blend_frame(frames[-1], target, amount)
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
        "blend_frames": args.blend_frames,
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
