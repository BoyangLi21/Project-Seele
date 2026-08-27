#!/usr/bin/env python3
"""Render one source or physical EVA landmark trajectory from four views."""

from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


CHAINS = [
    ("pelvis", "abdomen", "thorax", "neck", "head"),
    ("thorax", "shoulder_l", "elbow_l", "wrist_l", "hand_l"),
    ("thorax", "shoulder_r", "elbow_r", "wrist_r", "hand_r"),
    ("pelvis", "hip_l", "knee_l", "ankle_l", "toe_l"),
    ("pelvis", "hip_r", "knee_r", "ankle_r", "toe_r"),
]


def load_positions(state):
    if "positions_H" in state.files:
        return ([str(value) for value in state["landmark_names"]],
                np.asarray(state["positions_H"], dtype=np.float64), "H")
    names = [str(value) for value in state["target_landmark_names"]]
    points = np.asarray(state["actual_positions"], dtype=np.float64)
    roots = np.asarray(state["qpos"], dtype=np.float64)[:, None, :3]
    return (["pelvis", *names], np.concatenate((roots, points), axis=1), "m")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--sheet", type=Path)
    parser.add_argument("--fps", type=float, default=60.0)
    parser.add_argument("--title", default="EVA motion source review")
    parser.add_argument("--sheet-only", action="store_true")
    args = parser.parse_args()

    state = np.load(args.state)
    names, points, unit = load_positions(state)
    index = {name: idx for idx, name in enumerate(names)}
    minimum = np.min(points, axis=(0, 1))
    maximum = np.max(points, axis=(0, 1))
    center = 0.5 * (minimum + maximum)
    span = max(float(np.max(maximum - minimum)), 1.25 if unit == "H" else 4.5)
    half = span * 0.60
    frame_key = "frames" if "frames" in state.files else "source_frames"
    source_frames = np.asarray(state[frame_key], dtype=np.float64)
    contacts = (
        np.asarray(state["foot_contact"], dtype=np.bool_)
        if "foot_contact" in state.files else None
    )
    views = [
        (10.0, 180.0, "front"),
        (10.0, -90.0, "side"),
        (10.0, 0.0, "back"),
        (28.0, -135.0, "three-quarter"),
    ]
    render_indices = (np.linspace(0, len(points) - 1, 6).astype(int)
                      if args.sheet_only else np.arange(len(points)))
    frames = []
    for frame_index in render_indices:
        row = points[frame_index]
        figure = plt.figure(figsize=(9.6, 7.2), dpi=100, facecolor="#07090d")
        for panel, (elevation, azimuth, title) in enumerate(views, 1):
            axis = figure.add_subplot(2, 2, panel, projection="3d")
            axis.set_facecolor("#0c1118")
            for chain in CHAINS:
                xyz = np.stack([row[index[name]] for name in chain])
                axis.plot(xyz[:, 0], xyz[:, 1], xyz[:, 2],
                          color="#8b5cf6", linewidth=4.0,
                          solid_capstyle="round")
            axis.scatter(row[:, 0], row[:, 1], row[:, 2],
                         color="#c4b5fd", s=12, depthshade=False)
            if contacts is not None:
                for side_index, side in enumerate(("l", "r")):
                    color = ("#22c55e" if contacts[frame_index, side_index]
                             else "#64748b")
                    for name in (f"ankle_{side}", f"toe_{side}"):
                        value = row[index[name]]
                        axis.scatter(value[0], value[1], value[2],
                                     color=color, s=34, depthshade=False)
            axis.set_xlim(center[0] - half, center[0] + half)
            axis.set_ylim(center[1] - half, center[1] + half)
            axis.set_zlim(min(0.0, center[2] - half), center[2] + half)
            axis.set_box_aspect((1, 1, 1))
            axis.view_init(elev=elevation, azim=azimuth)
            axis.set_title(title, color="#dbeafe", fontsize=9)
            axis.set_axis_off()
        figure.suptitle(
            f"{args.title} | source {source_frames[frame_index]:.1f}",
            color="white", fontsize=11,
        )
        figure.tight_layout(pad=0.8)
        figure.canvas.draw()
        rgba = np.asarray(figure.canvas.buffer_rgba())
        frames.append(rgba[:, :, :3].copy())
        plt.close(figure)
    if not args.sheet_only:
        args.video.parent.mkdir(parents=True, exist_ok=True)
        imageio.mimsave(
            args.video, frames, fps=args.fps, codec="libx264", quality=8,
            macro_block_size=None,
        )
    if args.sheet is not None:
        chosen = (np.arange(6) if args.sheet_only else
                  np.linspace(0, len(frames) - 1, 6).astype(int))
        rows = [
            np.concatenate((frames[chosen[offset]], frames[chosen[offset + 1]]),
                           axis=1)
            for offset in range(0, 6, 2)
        ]
        args.sheet.parent.mkdir(parents=True, exist_ok=True)
        imageio.imwrite(args.sheet, np.concatenate(rows, axis=0))
    print({
        "video": str(args.video.resolve()),
        "sheet": None if args.sheet is None else str(args.sheet.resolve()),
        "frames": len(frames), "fps": args.fps, "unit": unit,
        "sheet_only": args.sheet_only,
    })


if __name__ == "__main__":
    main()
