#!/usr/bin/env python3
"""Run deterministic trajectory queries against the EVA motion-match DB."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


SCENARIOS = {
    "idle": {"speed": 0.0, "turn_degrees": 0.0, "stop": False},
    "walk_forward": {"speed": 1.45, "turn_degrees": 0.0, "stop": False},
    "run_forward": {"speed": 4.2, "turn_degrees": 0.0, "stop": False},
    "walk_left_90": {"speed": 1.45, "turn_degrees": 90.0, "stop": False},
    "walk_right_90": {"speed": 1.45, "turn_degrees": -90.0, "stop": False},
    "run_left_90": {"speed": 4.2, "turn_degrees": 90.0, "stop": False},
    "run_right_90": {"speed": 4.2, "turn_degrees": -90.0, "stop": False},
    "walk_stop": {"speed": 1.45, "turn_degrees": 0.0, "stop": True},
    "run_stop": {"speed": 4.2, "turn_degrees": 0.0, "stop": True},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top", type=int, default=8)
    return parser.parse_args()


def desired_trajectory(speed: float, turn_degrees: float,
                       stop: bool, horizon: float) -> tuple[float, float, float, float]:
    if stop:
        duration = 0.60
        time = min(horizon, duration)
        acceleration = speed / duration
        forward = max(0.0, speed * time - 0.5 * acceleration * time * time)
        return 0.0, forward, 0.0, 1.0
    if abs(turn_degrees) < 1.0e-5:
        return 0.0, speed * horizon, 0.0, 1.0
    duration = 0.60
    full_angle = math.radians(turn_degrees)
    angular_speed = full_angle / duration
    angle = angular_speed * min(horizon, duration)
    radius = speed / max(abs(angular_speed), 1.0e-6)
    sign = -1.0 if turn_degrees > 0.0 else 1.0
    right = sign * radius * (1.0 - math.cos(abs(angle)))
    forward = radius * math.sin(abs(angle))
    facing_right = sign * math.sin(abs(angle))
    facing_forward = math.cos(abs(angle))
    return right, forward, facing_right, facing_forward


def main() -> None:
    args = parse_args()
    db = json.loads(args.database.read_text(encoding="utf-8"))
    names = list(db["feature_names"])
    name_to_index = {name: index for index, name in enumerate(names)}
    means = db["feature_mean"]
    stddev = db["feature_stddev"]
    weights = db["weights"]
    entries = db["entries"]
    def representative(clip_name: str):
        candidates = [entry for entry in entries if entry["clip"] == clip_name]
        return candidates[len(candidates) // 2]
    results = {}
    for scenario_name, scenario in SCENARIOS.items():
        base_name = ("idle" if scenario["speed"] <= 0.01 else
                     "cmu_run" if scenario["speed"] >= 3.0 else
                     "cmu_walk_a")
        base = representative(base_name)
        query = [base["normalized"][index] * stddev[index] + means[index]
                 for index in range(len(names))]
        query[name_to_index["root_velocity_right"]] = 0.0
        query[name_to_index["root_velocity_forward"]] = scenario["speed"]
        for horizon in (0.20, 0.40, 0.60):
            label = str(horizon).replace(".", "p")
            values = desired_trajectory(
                scenario["speed"], scenario["turn_degrees"],
                scenario["stop"], horizon,
            )
            for suffix, value in zip(("right", "forward", "facing_right",
                                      "facing_forward"), values):
                query[name_to_index[f"future_{label}_{suffix}"]] = value
        normalized = [(query[index] - means[index]) / stddev[index]
                      for index in range(len(names))]
        scored = []
        for entry in entries:
            if (scenario["stop"]
                    and not ({"stop_transition", "idle"}
                             & set(entry.get("tags", [])))):
                continue
            cost = sum(
                weights[index]
                * (entry["normalized"][index] - normalized[index]) ** 2
                for index in range(len(names))
            )
            tags = set(entry.get("tags", []))
            if not scenario["stop"] and "stop_transition" in tags:
                cost += 3.0
            if abs(scenario["turn_degrees"]) < 1.0e-5 \
                    and ({"left", "right"} & tags):
                cost += 8.0
            if scenario["turn_degrees"] > 0.0 and "right" in tags:
                cost += 12.0
            if scenario["turn_degrees"] < 0.0 and "left" in tags:
                cost += 12.0
            scored.append({
                "clip": entry["clip"],
                "frame": entry["frame"],
                "role": entry["role"],
                "cost": cost,
            })
        scored.sort(key=lambda item: item["cost"])
        results[scenario_name] = scored[:args.top]
    output = {
        "schema": 1,
        "database": str(args.database.resolve()),
        "scenarios": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"EVA motion matching queries: scenarios={len(results)} output={args.output}")


if __name__ == "__main__":
    main()
