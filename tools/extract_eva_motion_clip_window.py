#!/usr/bin/env python3
"""Extract, rebase and optionally close one EVA motion-review clip window."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path


def normalized(values: list[float]) -> list[float]:
    length = math.sqrt(sum(value * value for value in values))
    if length <= 1.0e-12:
        raise ValueError("zero-length quaternion")
    return [value / length for value in values]


def slerp_wxyz(left: list[float], right: list[float], amount: float) -> list[float]:
    first = normalized([float(value) for value in left])
    second = normalized([float(value) for value in right])
    dot = sum(a * b for a, b in zip(first, second))
    if dot < 0.0:
        second = [-value for value in second]
        dot = -dot
    dot = max(-1.0, min(1.0, dot))
    if dot > 0.9995:
        return normalized([
            (1.0 - amount) * a + amount * b
            for a, b in zip(first, second)
        ])
    angle = math.acos(dot)
    scale = math.sin(angle)
    return [
        (math.sin((1.0 - amount) * angle) * a
         + math.sin(amount * angle) * b) / scale
        for a, b in zip(first, second)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--start", required=True, type=int,
                        help="zero-based inclusive frame")
    parser.add_argument("--end", required=True, type=int,
                        help="zero-based exclusive frame")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--output-clip", required=True)
    parser.add_argument("--in-place-horizontal", action="store_true",
                        help="remove the window's linear horizontal travel")
    parser.add_argument("--loop-bridge", type=int, default=0,
                        help="replace the final N frames with a seam bridge")
    parser.add_argument("--hold-frames", type=int, default=0,
                        help="repeat the extracted final pose for N frames")
    parser.add_argument("--attachment", action="append", default=[],
                        choices=("knife", "cannon", "lance"),
                        help="append an identity attachment channel")
    args = parser.parse_args()

    document = json.loads(args.input.read_text(encoding="utf-8"))
    source_clip = document["clips"].get(args.clip)
    if source_clip is None:
        raise SystemExit(f"unknown clip {args.clip}")
    source_frames = source_clip["frames"]
    if not 0 <= args.start < args.end <= len(source_frames):
        raise SystemExit(
            f"window {args.start}:{args.end} outside 0:{len(source_frames)}")
    frames = copy.deepcopy(source_frames[args.start:args.end])
    if len(frames) < 2 and args.hold_frames < 2:
        raise SystemExit("window must contain at least two frames")

    if args.hold_frames:
        if args.hold_frames < 2:
            raise SystemExit("hold frames must be at least two")
        frames = [copy.deepcopy(frames[-1]) for _ in range(args.hold_frames)]

    attachments = [name for name in dict.fromkeys(args.attachment)
                   if name not in document["bones"]]
    for frame in frames:
        frame["rotation_wxyz"].extend(
            [[1.0, 0.0, 0.0, 0.0] for _ in attachments])

    origin = [float(value) for value in frames[0]["root_m"]]
    end_root = [float(value) for value in frames[-1]["root_m"]]
    for index, frame in enumerate(frames):
        root = [float(value) for value in frame["root_m"]]
        root[0] -= origin[0]
        root[2] -= origin[2]
        if args.in_place_horizontal:
            phase = index / (len(frames) - 1)
            root[0] -= (end_root[0] - origin[0]) * phase
            root[2] -= (end_root[2] - origin[2]) * phase
        frame["root_m"] = [round(value, 7) for value in root]

    bridge = args.loop_bridge
    if bridge:
        if not 2 <= bridge < len(frames) // 3:
            raise SystemExit("loop bridge must be at least 2 and under one third")
        anchor = copy.deepcopy(frames[-bridge - 1])
        target = frames[0]
        replacement = []
        for index in range(bridge):
            amount = (index + 1) / (bridge + 1)
            row = copy.deepcopy(anchor)
            row["rotation_wxyz"] = [
                [round(value, 7) for value in slerp_wxyz(a, b, amount)]
                for a, b in zip(anchor["rotation_wxyz"],
                                target["rotation_wxyz"])
            ]
            row["root_m"] = [
                round((1.0 - amount) * float(a) + amount * float(b), 7)
                for a, b in zip(anchor["root_m"], target["root_m"])
            ]
            row["foot_contact"] = copy.deepcopy(
                anchor["foot_contact"] if amount < 0.5
                else target["foot_contact"])
            if "hand_contact" in anchor or "hand_contact" in target:
                row["hand_contact"] = copy.deepcopy(
                    anchor.get("hand_contact", [False, False])
                    if amount < 0.5 else
                    target.get("hand_contact", [False, False]))
            replacement.append(row)
        frames[-bridge:] = replacement

    clip = copy.deepcopy(source_clip)
    clip["frames"] = frames
    clip["duration_seconds"] = round(
        (len(frames) - 1) / float(document["sample_rate"]), 6)
    clip["loop"] = bool(bridge or args.hold_frames)
    clip["role"] = "extracted_direct_mocap_window"
    output = copy.deepcopy(document)
    output["bones"] = list(document["bones"]) + attachments
    output["clips"] = {args.output_clip: clip}
    output["preview_only"] = True
    output.setdefault("modifications", []).append({
        "operation": "clip_window_extract",
        "source_clip": args.clip,
        "source_frames_zero_based": [args.start, args.end],
        "in_place_horizontal": args.in_place_horizontal,
        "loop_bridge_frames": bridge,
        "hold_frames": args.hold_frames,
        "attachments": attachments,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "output": str(args.output.resolve()),
        "clip": args.output_clip,
        "frames": len(frames),
        "loop": bool(bridge or args.hold_frames),
        "in_place_horizontal": args.in_place_horizontal,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
