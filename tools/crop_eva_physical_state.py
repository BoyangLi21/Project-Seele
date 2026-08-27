#!/usr/bin/env python3
"""Crop a deterministic EVA state archive by source-frame range."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--start", required=True, type=float)
    parser.add_argument("--end", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    source = np.load(args.state)
    frames = np.asarray(source["source_frames"], dtype=np.float64)
    mask = (frames >= args.start - 1.0e-6) & (frames <= args.end + 1.0e-6)
    indices = np.flatnonzero(mask)
    if not len(indices):
        raise RuntimeError("crop contains no source frames")
    if np.any(np.diff(indices) != 1):
        raise RuntimeError("crop is not contiguous")
    first, last = int(indices[0]), int(indices[-1])
    fields = {}
    for key in source.files:
        value = source[key]
        if value.ndim > 0 and value.shape[0] == len(frames):
            fields[key] = value[first:last + 1]
        else:
            fields[key] = value
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **fields)
    report = {
        "schema": 1,
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "requested_source_frames": [args.start, args.end],
        "actual_source_frames": [float(frames[first]), float(frames[last])],
        "input_frames": len(frames),
        "output_frames": last - first + 1,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
