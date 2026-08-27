#!/usr/bin/env python3
"""Splice an optimized contiguous window back into a full EVA state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--window", required=True, type=Path)
    parser.add_argument("--start-index", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    base = np.load(args.base)
    window = np.load(args.window)
    base_count = len(base["qpos"])
    window_count = len(window["qpos"])
    first = args.start_index
    last = first + window_count
    if not 0 <= first < last <= base_count:
        raise RuntimeError(
            f"window [{first},{last}) outside base length {base_count}"
        )
    if ([str(value) for value in base["tangent_names"]]
            != [str(value) for value in window["tangent_names"]]):
        raise RuntimeError("tangent contracts differ")
    if ([str(value) for value in base["target_landmark_names"]]
            != [str(value) for value in window["target_landmark_names"]]):
        raise RuntimeError("landmark contracts differ")

    fields = {key: base[key].copy() for key in base.files}
    replaced = []
    added = []
    for key in window.files:
        value = window[key]
        if value.ndim == 0 or value.shape[0] != window_count:
            continue
        if key in fields and fields[key].ndim > 0:
            if fields[key].shape[0] != base_count:
                continue
            if fields[key].shape[1:] != value.shape[1:]:
                raise RuntimeError(f"shape mismatch for {key}")
        else:
            fields[key] = np.zeros(
                (base_count, *value.shape[1:]), dtype=value.dtype
            )
            added.append(key)
        fields[key][first:last] = value
        replaced.append(key)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **fields)
    report = {
        "schema": 1,
        "base_state": str(args.base.resolve()),
        "window_state": str(args.window.resolve()),
        "output_state": str(args.output.resolve()),
        "base_frames": base_count,
        "window_indices": [first, last - 1],
        "window_frames": window_count,
        "replaced_fields": sorted(replaced),
        "added_fields": sorted(added),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
