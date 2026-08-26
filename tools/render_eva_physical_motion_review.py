#!/usr/bin/env python3
"""Render a clean four-view review of an EVA physical state trajectory."""

from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np


def camera(azimuth: float, elevation: float, distance: float):
    result = mujoco.MjvCamera()
    result.type = mujoco.mjtCamera.mjCAMERA_FREE
    result.azimuth = azimuth
    result.elevation = elevation
    result.distance = distance
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--sheet", type=Path)
    parser.add_argument("--fps", type=float, default=60.0)
    parser.add_argument("--show-contacts", action="store_true")
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    state = np.load(args.state)
    qpos = np.asarray(state["qpos"], dtype=np.float64)
    qvel = np.asarray(state["qvel"], dtype=np.float64)
    source_dt = float(state["timestep"][0])
    duration = max(0.0, (len(qpos) - 1) * source_dt)
    target_times = np.arange(0.0, duration + 0.25 / args.fps,
                             1.0 / args.fps)
    indices = np.minimum(
        np.rint(target_times / source_dt).astype(int), len(qpos) - 1
    )
    renderer = mujoco.Renderer(model, width=480, height=360)
    option = mujoco.MjvOption()
    option.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = args.show_contacts
    option.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = args.show_contacts
    cameras = [
        camera(90.0, -5.0, 5.0),
        camera(0.0, -5.0, 5.0),
        camera(180.0, -5.0, 5.0),
        camera(135.0, -12.0, 5.0),
    ]
    pelvis = model.body("pelvis").id
    frames = []
    for state_index in indices:
        data.qpos[:] = qpos[state_index]
        data.qvel[:] = qvel[state_index]
        mujoco.mj_forward(model, data)
        views = []
        for view_camera in cameras:
            view_camera.lookat[:] = data.xpos[pelvis]
            view_camera.lookat[2] += 0.55
            renderer.update_scene(
                data, camera=view_camera, scene_option=option
            )
            views.append(renderer.render().copy())
        frames.append(np.concatenate((
            np.concatenate((views[0], views[1]), axis=1),
            np.concatenate((views[2], views[3]), axis=1),
        ), axis=0))
    renderer.close()
    args.video.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(
        args.video, frames, fps=args.fps, codec="libx264", quality=8,
        macro_block_size=None,
    )
    if args.sheet is not None:
        chosen = np.linspace(0, len(frames) - 1, 6).astype(int)
        rows = [
            np.concatenate([frames[index] for index in chosen[offset:offset + 2]],
                           axis=1)
            for offset in range(0, len(chosen), 2)
        ]
        sheet = np.concatenate(rows, axis=0)
        args.sheet.parent.mkdir(parents=True, exist_ok=True)
        imageio.imwrite(args.sheet, sheet)
    print({
        "video": str(args.video.resolve()),
        "sheet": None if args.sheet is None else str(args.sheet.resolve()),
        "frames": len(frames),
        "fps": args.fps,
        "duration_seconds": len(frames) / args.fps,
        "contacts": args.show_contacts,
    })


if __name__ == "__main__":
    main()
