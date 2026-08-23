#!/usr/bin/env python3
"""Compose ranked EVA punch/knife candidates into inertialized 3D combos."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_cmu_motion_candidates import (
    lock_contact_feet,
    runtime_target_pivots,
)
from build_eva_motion_database import load_target_pivots
from compose_eva_motion_matching_demo import (
    apply_inertialization,
    begin_inertialization,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--ranking", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--inertialization-frames", type=int, default=6)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def compose(names: list[str], motion: dict, pivots,
            blend_frames: int) -> tuple[list[dict], list[dict]]:
    fps = float(motion.get("sample_rate", 30.0))
    output = []
    transitions = []
    origin = Vector((0.0, 0.0))
    accumulated_yaw = 0.0
    for clip_index, name in enumerate(names):
        source = motion["clips"][name]["frames"]
        start_root = Vector((float(source[0]["root_m"][0]),
                             float(source[0]["root_m"][2])))
        start_yaw = float(source[0].get("root_yaw_radians", 0.0))
        state = None
        if output:
            transitions.append({
                "output_frame": len(output),
                "from": names[clip_index - 1],
                "to": name,
            })
            state = begin_inertialization(
                output[-2] if len(output) >= 2 else output[-1],
                output[-1], source[0], source[min(1, len(source) - 1)], fps,
            )
        for frame_index, source_frame in enumerate(source):
            frame = copy.deepcopy(source_frame)
            if state is not None and frame_index < blend_frames:
                frame = apply_inertialization(
                    frame, state, frame_index, blend_frames, fps
                )
            relative = Vector((float(source_frame["root_m"][0]),
                               float(source_frame["root_m"][2]))) - start_root
            frame["root_m"][0] = round(float(origin.x + relative.x), 7)
            frame["root_m"][2] = round(float(origin.y + relative.y), 7)
            frame["root_yaw_radians"] = round(
                accumulated_yaw
                + float(source_frame.get("root_yaw_radians", 0.0))
                - start_yaw,
                7,
            )
            output.append(frame)
        origin = Vector((float(output[-1]["root_m"][0]),
                         float(output[-1]["root_m"][2])))
        accumulated_yaw = float(output[-1].get("root_yaw_radians", 0.0))
    lock_contact_feet(output, list(motion["bones"]), pivots,
                      Vector((0.0, 0.0, 0.0)))
    return output, transitions


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    ranking = json.loads(args.ranking.read_text(encoding="utf-8"))
    pivots = runtime_target_pivots(load_target_pivots(args.geo))
    fps = float(motion.get("sample_rate", 30.0))
    clips = {"idle": copy.deepcopy(motion["clips"]["idle"])}
    combo_contract = {}
    for kind, output_name in (("punch", "punch_combo_demo"),
                              ("sword", "knife_combo_demo")):
        names = list(ranking["shortlist"][kind])
        frames, transitions = compose(
            names, motion, pivots, args.inertialization_frames
        )
        clips[output_name] = {
            "duration_seconds": round((len(frames) - 1) / fps, 6),
            "loop": False,
            "role": "combat_combo_demo",
            "frames": frames,
            "source_clips": names,
            "transitions": transitions,
        }
        combo_contract[output_name] = names
    output = copy.deepcopy(motion)
    output["clips"] = clips
    output["combat_combo_demo"] = {
        "ranking": str(args.ranking.resolve()),
        "inertialization_frames": args.inertialization_frames,
        "combos": combo_contract,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA combat combo: punch={len(clips['punch_combo_demo']['frames'])} "
        f"knife={len(clips['knife_combo_demo']['frames'])} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
