#!/usr/bin/env python3
"""Apply a tapered offline vertical root offset over a source-frame window."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--source-start", required=True, type=float)
    parser.add_argument("--source-end", required=True, type=float)
    parser.add_argument("--offset-m", required=True, type=float)
    parser.add_argument("--fade-frames", type=int, default=2)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    source = np.load(args.state)
    frames = np.asarray(source["source_frames"], dtype=np.float64)
    selected = np.flatnonzero(
        (frames >= args.source_start - 1.0e-4)
        & (frames <= args.source_end + 1.0e-4)
    )
    if not len(selected):
        raise RuntimeError("offset window contains no frames")
    first, last = int(selected[0]), int(selected[-1])
    weights = np.zeros(len(frames), dtype=np.float64)
    weights[first:last + 1] = 1.0
    fade = max(0, args.fade_frames)
    for step in range(1, fade + 1):
        weight = (fade + 1 - step) / (fade + 1)
        if first - step >= 0:
            weights[first - step] = max(weights[first - step], weight)
        if last + step < len(weights):
            weights[last + step] = max(weights[last + step], weight)
    offset = weights * args.offset_m
    fields = {key: source[key] for key in source.files}
    qpos = np.asarray(source["qpos"], dtype=np.float64).copy()
    desired = np.asarray(source["desired_positions"], dtype=np.float64).copy()
    actual = np.asarray(source["actual_positions"], dtype=np.float64).copy()
    qpos[:, 2] += offset
    desired[:, :, 2] += offset[:, None]
    actual[:, :, 2] += offset[:, None]
    fields.update({
        "qpos": qpos,
        "desired_positions": desired,
        "actual_positions": actual,
        "root_window_offset_m": offset,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **fields)
    report = {
        "schema": 1,
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "source_window": [args.source_start, args.source_end],
        "frame_indices": [first, last],
        "offset_m": args.offset_m,
        "fade_frames": fade,
        "maximum_offset_step_m": float(np.max(
            np.abs(np.diff(offset)), initial=0.0
        )),
        "joint_coordinates_changed": False,
        "runtime_root_write_authorized": False,
        "status": "offline_reference_offset_requires_full_reaudit",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
