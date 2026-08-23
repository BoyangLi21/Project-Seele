#!/usr/bin/env python3
"""Split a full audited CMU jump into phase-aware EVA controller clips."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--clip", default="cmu_jump")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def slice_clip(source: dict, first: int, last: int,
               role: str, loop: bool = False) -> dict:
    output = copy.deepcopy(source)
    output["frames"] = copy.deepcopy(source["frames"][first:last + 1])
    output["duration_seconds"] = round(
        max(1, last - first) / 30.0, 6
    )
    output["loop"] = loop
    output["role"] = role
    output["source_slice"] = [first, last]
    output.pop("phase_frame_indices", None)
    output.pop("closed_endpoint", None)
    return output


def main() -> None:
    args = parse_args()
    document = json.loads(args.motion_db.read_text(encoding="utf-8"))
    source = document["clips"].get(args.clip)
    if source is None:
        raise SystemExit(f"missing jump clip {args.clip}")
    phases = source.get("phase_frame_indices")
    if phases is None:
        raise SystemExit("jump clip has no phase_frame_indices")
    takeoff = int(phases["takeoff"])
    apex = int(phases["apex"])
    landing = int(phases["landing"])
    last = len(source["frames"]) - 1
    if not 0 < takeoff < apex < landing < last:
        raise SystemExit(f"invalid jump phases: {phases} / last={last}")
    output = copy.deepcopy(document)
    output["clips"] = {
        "idle": copy.deepcopy(document["clips"]["idle"]),
        "jump_takeoff": slice_clip(source, 0, min(last, takeoff + 1),
                                   "airborne_takeoff"),
        "jump_airborne": slice_clip(source, takeoff, landing,
                                    "airborne_ballistic"),
        "jump_landing": slice_clip(source, max(0, landing - 1), last,
                                   "airborne_landing"),
    }
    output["jump_controller"] = {
        "source_clip": args.clip,
        "takeoff_frame": takeoff,
        "apex_frame": apex,
        "landing_frame": landing,
        "airborne_apex_normalized": round(
            (apex - takeoff) / (landing - takeoff), 7
        ),
        "sampling": {
            "rising": "map vertical-velocity/time to takeoff..apex",
            "falling": "map fall progress to apex..landing",
            "touchdown": "transition to landing with inertialization",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA jump controller: phases={takeoff}/{apex}/{landing}/{last} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
