#!/usr/bin/env python3
"""Exercise the EVA motion matcher over an eight-second control trajectory."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--decision-frames", type=int, default=8)
    parser.add_argument("--transition-cost", type=float, default=7.5)
    return parser.parse_args()


def control(time: float) -> tuple[float, float, bool]:
    if time < 1.0:
        return 0.0, 0.0, False
    if time < 2.5:
        return 1.45 * min(1.0, (time - 1.0) / 0.65), 0.0, False
    if time < 4.5:
        return 1.45 + (4.2 - 1.45) * min(1.0, (time - 2.5) / 0.8), 0.0, False
    if time < 5.3:
        return 4.2, 90.0, False
    if time < 6.8:
        return 4.2, 0.0, False
    return 4.2, 0.0, True


def desired(speed: float, turn: float, stop: bool,
            horizon: float) -> tuple[float, float, float, float]:
    if stop:
        duration = 0.75
        t = min(duration, horizon)
        forward = max(0.0, speed * t - 0.5 * speed / duration * t * t)
        return 0.0, forward, 0.0, 1.0
    if abs(turn) < 1.0e-5:
        return 0.0, speed * horizon, 0.0, 1.0
    duration = 0.8
    angle = math.radians(turn) * min(1.0, horizon / duration)
    angular_speed = abs(math.radians(turn)) / duration
    radius = speed / max(angular_speed, 1.0e-6)
    sign = -1.0 if turn > 0.0 else 1.0
    return (sign * radius * (1.0 - math.cos(abs(angle))),
            radius * math.sin(abs(angle)),
            sign * math.sin(abs(angle)), math.cos(abs(angle)))


def main() -> None:
    args = parse_args()
    db = json.loads(args.database.read_text(encoding="utf-8"))
    entries = db["entries"]
    names = db["feature_names"]
    lookup = {name: index for index, name in enumerate(names)}
    means, stddev, weights = db["feature_mean"], db["feature_stddev"], db["weights"]
    fps = float(db["sample_rate"])
    by_clip = {}
    for entry_index, entry in enumerate(entries):
        by_clip.setdefault(entry["clip"], []).append(entry_index)
    current_index = by_clip["idle"][0]
    decisions = []
    total_frames = int(round(8.0 * fps))
    for frame in range(0, total_frames, args.decision_frames):
        time = frame / fps
        speed, turn, stopping = control(time)
        current = entries[current_index]
        query = [current["normalized"][index] * stddev[index] + means[index]
                 for index in range(len(names))]
        query[lookup["root_velocity_right"]] = 0.0
        query[lookup["root_velocity_forward"]] = 0.0 if time < 1.0 else speed
        for horizon in (0.20, 0.40, 0.60):
            label = str(horizon).replace(".", "p")
            values = desired(speed, turn, stopping, horizon)
            for suffix, value in zip(("right", "forward", "facing_right",
                                      "facing_forward"), values):
                query[lookup[f"future_{label}_{suffix}"]] = value
        normalized = [(query[index] - means[index]) / stddev[index]
                      for index in range(len(names))]
        candidates = []
        starting = current["clip"] == "idle" and speed > 0.15
        for index, entry in enumerate(entries):
            if starting and "start_transition" not in entry.get("tags", []):
                continue
            if stopping and not ({"stop_transition", "idle"}
                                 & set(entry.get("tags", []))):
                continue
            cost = sum(weights[axis]
                       * (entry["normalized"][axis] - normalized[axis]) ** 2
                       for axis in range(len(names)))
            tags = set(entry.get("tags", []))
            if not stopping and "stop_transition" in tags:
                cost += 3.0
            if abs(turn) < 1.0e-5 and ({"left", "right"} & tags):
                cost += 8.0
            if turn > 0.0 and "right" in tags:
                cost += 12.0
            if turn < 0.0 and "left" in tags:
                cost += 12.0
            candidates.append((cost, index))
        candidates.sort(key=lambda item: item[0])
        best_cost, best_index = candidates[0]
        continuation_cost = next(
            (cost for cost, index in candidates if index == current_index),
            float("inf"),
        )
        transition_cost = (0.0 if starting else
                           1.5 if stopping else
                           4.0 if abs(turn) > 1.0e-5 else
                           args.transition_cost)
        if (best_index != current_index
                and best_cost + transition_cost < continuation_cost):
            cost, chosen_index = best_cost + transition_cost, best_index
        else:
            cost, chosen_index = continuation_cost, current_index
        chosen = entries[chosen_index]
        decisions.append({
            "time_seconds": round(time, 4),
            "desired_speed_mps": round(speed, 4),
            "desired_turn_degrees": turn,
            "stopping": stopping,
            "from_clip": current["clip"],
            "from_frame": current["frame"],
            "to_clip": chosen["clip"],
            "to_frame": chosen["frame"],
            "cost": round(cost, 6),
        })
        clip_entries = by_clip[chosen["clip"]]
        local = chosen["frame"] + args.decision_frames
        if local >= len(clip_entries):
            local = (local % max(1, len(clip_entries) - 1)
                     if chosen["role"] == "candidate_locomotion"
                     else len(clip_entries) - 1)
        current_index = clip_entries[local]
    output = {
        "schema": 1,
        "database": str(args.database.resolve()),
        "decision_interval_frames": args.decision_frames,
        "transition_count": sum(
            decision["from_clip"] != decision["to_clip"]
            for decision in decisions
        ),
        "clip_sequence": [decisions[0]["from_clip"]] + [
            decision["to_clip"] for decision in decisions
            if decision["from_clip"] != decision["to_clip"]
        ],
        "decisions": decisions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA motion matching simulation: decisions={len(decisions)} "
        f"transitions={output['transition_count']} output={args.output}"
    )


if __name__ == "__main__":
    main()
