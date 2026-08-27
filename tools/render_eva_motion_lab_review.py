#!/usr/bin/env python3
"""Render one clip from an existing EVA Blender motion-lab scene."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fps", type=int, default=60)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def bounds(frame_start: int, frame_end: int) -> tuple[Vector, float]:
    scene = bpy.context.scene
    points = []
    stride = max(1, (frame_end - frame_start) // 8)
    frames = list(range(frame_start, frame_end + 1, stride))
    if frames[-1] != frame_end:
        frames.append(frame_end)
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in scene.objects:
            if obj.type != "MESH" or obj.name == "LAB_FLOOR":
                continue
            points.extend(obj.matrix_world @ Vector(corner)
                          for corner in obj.bound_box)
    minimum = Vector(tuple(min(point[axis] for point in points)
                           for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points)
                           for axis in range(3)))
    centre = (minimum + maximum) * 0.5
    extent = max(maximum.x - minimum.x, maximum.y - minimum.y,
                 maximum.z - minimum.z)
    return centre, extent


def main() -> None:
    args = parse_args()
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    clip = motion["clips"].get(args.clip)
    if clip is None:
        raise RuntimeError(f"unknown clip {args.clip}")
    marker = bpy.context.scene.timeline_markers.get(args.clip.upper())
    if marker is None:
        raise RuntimeError(f"timeline marker missing for {args.clip}")
    start = int(marker.frame)
    end = start + len(clip["frames"]) - 1
    centre, extent = bounds(start, end)

    camera = bpy.context.scene.camera
    # The reviewed Tiger mesh faces authored +Z, which the Blender review
    # conversion maps toward -Y. Stand on -Y for a front three-quarter view.
    camera.location = centre + Vector((1.45 * extent, -2.15 * extent,
                                       0.55 * extent))
    camera.rotation_euler = (centre - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    camera.data.lens = 58.0

    scene = bpy.context.scene
    scene.frame_start = start
    scene.frame_end = end
    scene.frame_set(start)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.fps = args.fps
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame_dir = args.output.parent / f"{args.output.stem}_frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str((frame_dir / "frame_").resolve())
    bpy.ops.render.render(animation=True)
    print({
        "clip": args.clip,
        "frames": [start, end],
        "fps": args.fps,
        "camera_centre": tuple(round(value, 5) for value in centre),
        "camera_extent": round(extent, 5),
        "frame_directory": str(frame_dir.resolve()),
        "output": str(args.output.resolve()),
    })


if __name__ == "__main__":
    main()
