#!/usr/bin/env python3
"""Report component-wise Euler discontinuities in the accepted locomotion patch."""

import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("patch", type=Path)
parser.add_argument("--threshold", type=float, default=25.0)
parser.add_argument("--top", type=int, default=20)
args = parser.parse_args()

animations = json.loads(args.patch.read_text(
    encoding="utf-8"))["replace_animations"]
report = {}
for animation_name, animation in animations.items():
    rows = []
    for bone, channels in animation.get("bones", {}).items():
        rotation = channels.get("rotation")
        if not isinstance(rotation, dict):
            continue
        values = list(rotation.items())
        for (first_time, first), (second_time, second) in zip(
                values, values[1:]):
            delta = [second[index] - first[index] for index in range(3)]
            maximum = max(abs(value) for value in delta)
            if maximum > args.threshold:
                rows.append({
                    "kind": "step", "bone": bone,
                    "from": first_time, "to": second_time,
                    "delta": delta, "maximum": maximum,
                })
        if animation.get("loop") and values:
            first_time, first = values[0]
            last_time, last = values[-1]
            delta = [first[index] - last[index] for index in range(3)]
            maximum = max(abs(value) for value in delta)
            if maximum > 0.5:
                rows.append({
                    "kind": "loop", "bone": bone,
                    "from": last_time, "to": first_time,
                    "delta": delta, "maximum": maximum,
                })
    report[animation_name] = sorted(
        rows, key=lambda row: row["maximum"], reverse=True)

print(json.dumps({name: rows[:args.top] for name, rows in report.items()},
                 indent=2))
