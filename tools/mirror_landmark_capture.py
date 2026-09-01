#!/usr/bin/env python3
"""Mirror a normalized human landmark capture across its sagittal plane."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = np.load(args.input)
    names = [str(value) for value in source["landmark_names"]]
    index = {name: offset for offset, name in enumerate(names)}
    positions = np.asarray(source["positions_H"], dtype=np.float64).copy()
    mirrored = positions.copy()
    mirrored[:, :, 1] *= -1.0
    handled = set()
    for name, left_index in index.items():
        if not name.endswith("_l"):
            continue
        right_name = name[:-1] + "r"
        if right_name not in index:
            continue
        right_index = index[right_name]
        mirrored[:, left_index] = positions[:, right_index]
        mirrored[:, left_index, 1] *= -1.0
        mirrored[:, right_index] = positions[:, left_index]
        mirrored[:, right_index, 1] *= -1.0
        handled.update((left_index, right_index))
    payload = {
        key: np.asarray(source[key])
        for key in source.files
    }
    payload["positions_H"] = mirrored
    payload["root_yaw_rad"] = -np.asarray(
        source["root_yaw_rad"], dtype=np.float64)
    payload["foot_contact"] = np.asarray(
        source["foot_contact"], dtype=bool)[:, ::-1]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **payload)
    metadata = {
        "schema": 1,
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "sourceId": args.source_id,
        "operation": "sagittal_position_mirror_with_left_right_swap",
        "samples": int(len(mirrored)),
        "swappedLandmarks": len(handled),
        "contactFraction": payload["foot_contact"].mean(axis=0).tolist(),
        "status": "MIRRORED_REAL_CAPTURE_NOT_VISUALLY_APPROVED",
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(
        metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == "__main__":
    main()
