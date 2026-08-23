#!/usr/bin/env python3
"""Build a trajectory/contact feature database for EVA motion matching."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_motion_lab_3d import load_geo, target_to_blender
from build_eva_motion_lab_armature import deformation_matrices


HORIZONS_SECONDS = (0.20, 0.40, 0.60)
INCLUDED_ROLES = {"idle", "candidate_locomotion", "candidate_trajectory"}


def semantic_tags(clip_name: str, role: str) -> list[str]:
    tags = []
    if clip_name == "idle":
        tags.append("idle")
    if role == "candidate_locomotion":
        tags.append("cyclic")
    if "stop" in clip_name:
        tags.append("stop_transition")
    if "start" in clip_name:
        tags.append("start_transition")
    if "turn_left" in clip_name or "veer_left" in clip_name:
        tags.append("left")
    if "turn_right" in clip_name or "veer_right" in clip_name:
        tags.append("right")
    if "turn_" in clip_name:
        tags.append("hard_turn")
    if "veer_" in clip_name:
        tags.append("veer")
    return tags


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def virtual_travel(clip: dict, frame_index: int, cycles: int = 0) -> Vector:
    travel = clip.get("root_travel_m", (0.0, 0.0, 0.0))
    period = max(1, len(clip["frames"]) - 1)
    phase = frame_index / period
    return Vector((-float(travel[0]), -float(travel[2]), 0.0)) \
        * (phase + cycles)


def root_basis(facing: Vector) -> tuple[Vector, Vector]:
    forward = Vector((facing.x, facing.y, 0.0))
    if forward.length < 1.0e-6:
        forward = Vector((0.0, -1.0, 0.0))
    forward.normalize()
    right = Vector((-forward.y, forward.x, 0.0))
    return right, forward


def local_2d(vector: Vector, facing: Vector) -> tuple[float, float]:
    right, forward = root_basis(facing)
    return vector.dot(right), vector.dot(forward)


def build_states(clip: dict, db_bones: list[str], bone_order: list[str],
                 pivots, parents, fps: float) -> list[dict]:
    states = []
    for index, frame in enumerate(clip["frames"]):
        matrices = deformation_matrices(
            frame, db_bones, bone_order, pivots, parents
        )
        virtual = virtual_travel(clip, index)
        root = (matrices["root"] @ target_to_blender(pivots["root"])) \
            / 112.0 + virtual
        yaw = float(frame.get("root_yaw_radians", 0.0))
        facing = Vector((math.sin(yaw), -math.cos(yaw), 0.0))
        feet = {
            side: (matrices[f"foot_{side}"]
                   @ target_to_blender(pivots[f"foot_{side}"]))
                  / 112.0 + virtual
            for side in ("l", "r")
        }
        states.append({
            "root": root,
            "facing": facing,
            "feet": feet,
            "contact": list(frame["foot_contact"]),
        })
    for index, state in enumerate(states):
        previous = states[max(0, index - 1)]
        following = states[min(len(states) - 1, index + 1)]
        denominator = 1.0 if index in (0, len(states) - 1) else 2.0
        state["root_velocity"] = (
            following["root"] - previous["root"]
        ) * (fps / denominator)
        state["foot_velocity"] = {
            side: (following["feet"][side] - previous["feet"][side])
                  * (fps / denominator)
            for side in ("l", "r")
        }
    return states


def future_state(states: list[dict], clip: dict, start: int,
                 offset: int) -> tuple[dict, Vector]:
    target = start + offset
    extra = Vector((0.0, 0.0, 0.0))
    if clip.get("loop"):
        period = max(1, len(states) - 1)
        cycles, target = divmod(target, period)
        extra = virtual_travel(clip, 0, cycles)
    else:
        target = min(len(states) - 1, target)
    return states[target], extra


def feature_names() -> list[str]:
    names = ["root_velocity_right", "root_velocity_forward"]
    for side in ("l", "r"):
        names.extend((f"{side}_foot_right", f"{side}_foot_up",
                      f"{side}_foot_forward", f"{side}_foot_velocity_right",
                      f"{side}_foot_velocity_forward", f"{side}_contact"))
    for horizon in HORIZONS_SECONDS:
        label = str(horizon).replace(".", "p")
        names.extend((f"future_{label}_right", f"future_{label}_forward",
                      f"future_{label}_facing_right",
                      f"future_{label}_facing_forward"))
    return names


def state_feature(states: list[dict], clip: dict, index: int,
                  fps: float) -> list[float]:
    state = states[index]
    facing = state["facing"]
    root = state["root"]
    root_velocity = local_2d(state["root_velocity"], facing)
    values = [root_velocity[0], root_velocity[1]]
    for side_index, side in enumerate(("l", "r")):
        relative = state["feet"][side] - root
        foot_2d = local_2d(relative, facing)
        velocity_2d = local_2d(state["foot_velocity"][side], facing)
        values.extend((foot_2d[0], relative.z, foot_2d[1],
                       velocity_2d[0], velocity_2d[1],
                       1.0 if state["contact"][side_index] else 0.0))
    for horizon in HORIZONS_SECONDS:
        future, extra = future_state(
            states, clip, index, int(round(horizon * fps))
        )
        delta = future["root"] + extra - root
        delta_2d = local_2d(delta, facing)
        future_facing = local_2d(future["facing"], facing)
        values.extend((delta_2d[0], delta_2d[1],
                       future_facing[0], future_facing[1]))
    return values


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    bones, pivots, parents = load_geo(args.geo)
    bone_order = [bone["name"] for bone in bones]
    db_bones = list(motion["bones"])
    fps = float(motion.get("sample_rate", 30.0))
    entries = []
    clip_ranges = {}
    for clip_name, clip in motion["clips"].items():
        role = clip.get("role", "unknown")
        if clip_name != "idle" and role not in INCLUDED_ROLES:
            continue
        states = build_states(clip, db_bones, bone_order, pivots, parents, fps)
        first = len(entries)
        for index in range(len(states)):
            entries.append({
                "clip": clip_name,
                "frame": index,
                "role": role,
                "tags": semantic_tags(clip_name, role),
                "feature": state_feature(states, clip, index, fps),
            })
        clip_ranges[clip_name] = [first, len(entries) - 1]
    if not entries:
        raise SystemExit("no motion-matching entries selected")
    names = feature_names()
    columns = list(zip(*(entry["feature"] for entry in entries)))
    means = [statistics.fmean(column) for column in columns]
    standard_deviations = [
        max(1.0e-5, statistics.pstdev(column)) for column in columns
    ]
    for entry in entries:
        entry["normalized"] = [
            round((value - means[index]) / standard_deviations[index], 6)
            for index, value in enumerate(entry.pop("feature"))
        ]
    output = {
        "schema": 1,
        "sample_rate": fps,
        "source_motion_db": str(args.motion_db.resolve()),
        "feature_names": names,
        "feature_mean": [round(value, 7) for value in means],
        "feature_stddev": [round(value, 7) for value in standard_deviations],
        "weights": [
            1.5 if "future" in name else
            1.35 if "contact" in name else
            2.75 if "root_velocity" in name else 1.0
            for name in names
        ],
        "clip_ranges": clip_ranges,
        "entry_count": len(entries),
        "entries": entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA motion matching DB: clips={len(clip_ranges)} "
        f"entries={len(entries)} dimensions={len(names)} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
