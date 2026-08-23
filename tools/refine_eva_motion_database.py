#!/usr/bin/env python3
"""Apply offline contact locking and stride fitting to an EVA motion DB."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_cmu_motion_candidates import (
    fit_loop_root_travel,
    lock_contact_feet,
    runtime_target_pivots,
)
from build_eva_motion_database import load_target_pivots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--target-geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def vector(values) -> Vector:
    return Vector(tuple(float(value) for value in values))


def main() -> None:
    args = parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    bones = list(document["bones"])
    pivots = runtime_target_pivots(load_target_pivots(args.target_geo))
    locked = 0
    fitted = 0
    for clip in document["clips"].values():
        frames = clip["frames"]
        travel = vector(clip.get("root_travel_m", (0.0, 0.0, 0.0)))
        if clip.get("loop"):
            travel = fit_loop_root_travel(frames, bones, pivots, travel)
            clip["root_travel_m"] = [
                round(float(value), 7) for value in travel
            ]
            clip["retargeted_stride_meters"] = round(
                math.hypot(travel.x, travel.z), 7
            )
            fitted += 1
        lock_contact_feet(frames, bones, pivots, travel)
        locked += 1
    document["offline_refinement"] = {
        "method": "velocity_contact_annotation_plus_shared_pelvis_ik_lock",
        "reference": "https://theorangeduck.com/page/inverse-kinematics-foot-locking",
        "clips_locked": locked,
        "loop_strides_fitted": fitted,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA motion refinement: locked={locked} fitted={fitted} "
        f"bytes={args.output.stat().st_size} output={args.output}"
    )


if __name__ == "__main__":
    main()
