#!/usr/bin/env python3
"""Extract an inclusive source-frame window from a landmark NPZ capture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--start-source-frame", required=True, type=float)
    parser.add_argument("--end-source-frame", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--clip-name", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_source_frame >= args.end_source_frame:
        raise SystemExit("start source frame must be before end source frame")
    source = np.load(args.source)
    frames = np.asarray(source["frames"], dtype=np.float64)
    tolerance = 1.0e-6
    mask = ((frames >= args.start_source_frame - tolerance)
            & (frames <= args.end_source_frame + tolerance))
    selected = np.flatnonzero(mask)
    if len(selected) < 3:
        raise SystemExit(
            f"window {args.start_source_frame}-{args.end_source_frame} "
            f"has only {len(selected)} samples"
        )
    first = int(selected[0])
    last = int(selected[-1]) + 1
    payload = {
        key: np.asarray(source[key])[first:last]
        if key in {"frames", "positions_H", "root_yaw_rad", "foot_contact"}
        else np.asarray(source[key])
        for key in source.files
    }
    payload["frames"] = payload["frames"] - payload["frames"][0]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **payload)
    fps = float(payload["fps"][0])
    report = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "clipName": args.clip_name,
        "requestedSourceFrames": [
            args.start_source_frame, args.end_source_frame
        ],
        "actualSourceFrames": [float(frames[first]), float(frames[last - 1])],
        "samples": last - first,
        "fps": fps,
        "durationSeconds": (last - first - 1) / fps,
        "contactFraction": np.asarray(
            payload["foot_contact"], dtype=np.float64
        ).mean(axis=0).tolist(),
        "status": "SOURCE_WINDOW_NOT_VISUALLY_APPROVED",
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
