#!/usr/bin/env python3
"""Render synchronized physical-rig landmarks for a paired interaction."""

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


def positions(state) -> tuple[list[str], np.ndarray]:
    if "actual_positions" in state.files:
        names = [str(value) for value in state["target_landmark_names"]]
        points = np.asarray(state["actual_positions"], dtype=np.float64)
        roots = np.asarray(state["qpos"], dtype=np.float64)[:, None, :3]
        return ["pelvis", *names], np.concatenate((roots, points), axis=1)
    names = [str(value) for value in state["landmark_names"]]
    return names, np.asarray(state["positions_H"], dtype=np.float64)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor-a", required=True, type=Path)
    parser.add_argument("--actor-b", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--sheet", type=Path)
    parser.add_argument("--landmark-a", default="hand_r")
    parser.add_argument("--landmark-b", default="elbow_l")
    parser.add_argument("--contact-distance", type=float, default=0.18)
    parser.add_argument("--coordinate-unit", choices=("m", "H"), default="m")
    parser.add_argument("--fps", type=float, default=60.0)
    args = parser.parse_args()

    actor_a = np.load(args.actor_a)
    actor_b = np.load(args.actor_b)
    names_a, points_a = positions(actor_a)
    names_b, points_b = positions(actor_b)
    if len(points_a) != len(points_b):
        raise RuntimeError("paired states have different frame counts")
    index_a = {name: index for index, name in enumerate(names_a)}
    index_b = {name: index for index, name in enumerate(names_b)}
    all_points = np.concatenate((points_a, points_b), axis=1)
    minimum = np.min(all_points, axis=(0, 1))
    maximum = np.max(all_points, axis=(0, 1))
    center = 0.5 * (minimum + maximum)
    span = max(float(np.max(maximum - minimum)), 4.5)
    half = span * 0.58
    views = [
        (12.0, 180.0, "actor-A front"),
        (12.0, -90.0, "interaction side"),
        (12.0, 0.0, "actor-B front"),
        (28.0, -135.0, "three-quarter"),
    ]

    def draw_actor(axis, points, index, color, label):
        for chain in CHAINS:
            xyz = np.stack([points[index[name]] for name in chain])
            axis.plot(xyz[:, 0], xyz[:, 1], xyz[:, 2],
                      color=color, linewidth=4.0, solid_capstyle="round")
        axis.scatter(points[:, 0], points[:, 1], points[:, 2],
                     color=color, s=12, depthshade=False, label=label)

    frames = []
    for frame_index in range(len(points_a)):
        figure = plt.figure(figsize=(9.6, 7.2), dpi=100, facecolor="#07090d")
        for panel, (elevation, azimuth, title) in enumerate(views, 1):
            axis = figure.add_subplot(2, 2, panel, projection="3d")
            axis.set_facecolor("#0c1118")
            draw_actor(axis, points_a[frame_index], index_a,
                       "#8b5cf6", "attacker")
            draw_actor(axis, points_b[frame_index], index_b,
                       "#ef4444", "target")
            contact_a = points_a[frame_index, index_a[args.landmark_a]]
            contact_b = points_b[frame_index, index_b[args.landmark_b]]
            distance = float(np.linalg.norm(contact_a - contact_b))
            contact_color = "#facc15" if distance <= args.contact_distance else "#64748b"
            axis.plot(
                [contact_a[0], contact_b[0]],
                [contact_a[1], contact_b[1]],
                [contact_a[2], contact_b[2]],
                color=contact_color, linewidth=2.5,
            )
            axis.set_xlim(center[0] - half, center[0] + half)
            axis.set_ylim(center[1] - half, center[1] + half)
            axis.set_zlim(max(0.0, center[2] - half), center[2] + half)
            axis.set_box_aspect((1, 1, 1))
            axis.view_init(elev=elevation, azim=azimuth)
            axis.set_title(title, color="#dbeafe", fontsize=9)
            axis.set_axis_off()
        frame_key = ("source_frames" if "source_frames" in actor_a.files
                     else "frames")
        source_frame = float(actor_a[frame_key][frame_index])
        figure.suptitle(
            f"paired grab attach | source {source_frame:.1f} | "
            f"contact {distance:.3f} {args.coordinate_unit}",
            color="white", fontsize=11,
        )
        figure.tight_layout(pad=0.8)
        figure.canvas.draw()
        rgba = np.asarray(figure.canvas.buffer_rgba())
        frames.append(rgba[:, :, :3].copy())
        plt.close(figure)

    args.video.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(
        args.video, frames, fps=args.fps, codec="libx264", quality=8,
        macro_block_size=None,
    )
    if args.sheet is not None:
        chosen = np.linspace(0, len(frames) - 1, 6).astype(int)
        sheet_rows = [
            np.concatenate((frames[chosen[index]], frames[chosen[index + 1]]),
                           axis=1)
            for index in range(0, 6, 2)
        ]
        args.sheet.parent.mkdir(parents=True, exist_ok=True)
        imageio.imwrite(args.sheet, np.concatenate(sheet_rows, axis=0))
    print({
        "video": str(args.video.resolve()),
        "sheet": None if args.sheet is None else str(args.sheet.resolve()),
        "frames": len(frames),
        "fps": args.fps,
    })


if __name__ == "__main__":
    main()
