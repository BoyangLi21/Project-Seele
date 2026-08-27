#!/usr/bin/env python3
"""Return an audited strike along its own collision-screened pose path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--impact-hold-frames", type=int, default=3)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    source = np.load(args.state)
    frame_count = len(source["qpos"])
    if frame_count < 3:
        raise RuntimeError("strike requires at least three frames")
    hold = max(0, args.impact_hold_frames)
    indices = np.concatenate((
        np.arange(frame_count, dtype=np.int64),
        np.full(hold, frame_count - 1, dtype=np.int64),
        np.arange(frame_count - 2, -1, -1, dtype=np.int64),
    ))
    fields = {}
    for key in source.files:
        value = source[key]
        fields[key] = (
            value[indices] if value.ndim > 0 and value.shape[0] == frame_count
            else value
        )
    fields["source_frames"] = np.arange(len(indices), dtype=np.float64)
    qpos = np.asarray(fields["qpos"], dtype=np.float64)
    dt = float(source["timestep"][0])
    qvel = np.zeros((len(qpos), model.nv), dtype=np.float64)
    for frame in range(len(qpos)):
        before = max(0, frame - 1)
        after = min(len(qpos) - 1, frame + 1)
        mujoco.mj_differentiatePos(
            model, qvel[frame], max(dt, (after - before) * dt),
            qpos[before], qpos[after],
        )
    fields["qvel"] = qvel
    fields["reversible_source_index"] = indices
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **fields)
    report = {
        "schema": 1,
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "source_frames": frame_count,
        "output_frames": len(indices),
        "impact_frame": frame_count - 1,
        "impact_hold_frames": hold,
        "recovery_authority": "reverse_of_same_screened_pose_path",
        "new_interpolated_pose_count": 0,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
