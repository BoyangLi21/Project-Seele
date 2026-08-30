#!/usr/bin/env python3
"""Bake exact-scene root lift corrections back into Gecko animation curves."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


MODEL_UNITS_PER_METRE = 112.0


def clean(value: float) -> float:
    result = round(float(value), 5)
    return 0.0 if abs(result) < 0.000005 else result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--original-db", required=True, type=Path)
    parser.add_argument("--grounded-db", required=True, type=Path)
    parser.add_argument("--map", action="append", required=True,
                        help="pose_clip=animation_suffix")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    patch = json.loads(args.patch.read_text(encoding="utf-8"))
    original = json.loads(args.original_db.read_text(encoding="utf-8"))
    grounded = json.loads(args.grounded_db.read_text(encoding="utf-8"))
    fps = float(original.get("sample_rate", 30.0))
    if abs(fps - float(grounded.get("sample_rate", fps))) > 1.0e-8:
        raise RuntimeError("motion database sample rates differ")

    report = {}
    for specification in args.map:
        if "=" not in specification:
            raise SystemExit(f"invalid mapping {specification!r}")
        pose_name, suffix = specification.split("=", 1)
        source_frames = original["clips"][pose_name]["frames"]
        grounded_frames = grounded["clips"][pose_name]["frames"]
        if len(source_frames) != len(grounded_frames):
            raise RuntimeError(f"frame count differs for {pose_name}")
        corrections = [
            float(after["root_m"][1]) - float(before["root_m"][1])
            for before, after in zip(source_frames, grounded_frames)
        ]
        animation_name = f"animation.eva_unit01.{suffix}"
        animation = patch["replace_animations"][animation_name]
        if not animation.get("loop") and corrections:
            # Transition endpoints already match the adjacent stance.  A
            # symmetric max filter may spill a neighbouring lift onto the
            # first/last sample; keep both exact transition contracts intact.
            corrections[0] = 0.0
            corrections[-1] = 0.0
        root = animation["bones"]["root"]
        position = root.get("position")
        if not isinstance(position, dict) or not position:
            raise RuntimeError(f"{animation_name} has no keyed root position")
        maximum = 0.0
        for key, value in position.items():
            frame_index = min(
                len(corrections) - 1,
                max(0, int(round(float(key) * fps))),
            )
            lift_pixels = corrections[frame_index] * MODEL_UNITS_PER_METRE
            value[1] = clean(float(value[1]) + lift_pixels)
            maximum = max(maximum, lift_pixels)
        report[animation_name] = {
            "pose_clip": pose_name,
            "maximum_lift_pixels": clean(maximum),
            "keys": len(position),
        }

    patch["exact_grounding_bake"] = {
        "authority": "exact_runtime_pose_database_root_only_clearance",
        "sample_rate_hz": fps,
        "animations": report,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(patch, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(patch["exact_grounding_bake"], ensure_ascii=False))


if __name__ == "__main__":
    main()
