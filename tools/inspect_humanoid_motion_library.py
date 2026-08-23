#!/usr/bin/env python3
"""Inventory a GLB/FBX humanoid motion library with Blender.

Run with Blender so the report is generated from the same importer used by
the offline retarget pipeline::

    blender --background --python tools/inspect_humanoid_motion_library.py -- \
        --source path/to/library.glb --output artifacts/mocap/inventory.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def iter_action_fcurves(action: bpy.types.Action):
    if hasattr(action, "fcurves"):
        yield from action.fcurves
        return
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                yield from channelbag.fcurves


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes):
        for datablock in tuple(datablocks):
            datablocks.remove(datablock)


def import_source(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)
    elif suffix == ".bvh":
        bpy.ops.import_anim.bvh(
            filepath=str(path), target="ARMATURE", global_scale=1.0,
            frame_start=1, use_fps_scale=False, update_scene_fps=True,
            update_scene_duration=True, rotate_mode="NATIVE",
            axis_forward="-Z", axis_up="Y",
        )
    else:
        raise SystemExit(f"unsupported source type: {path}")


def action_report(action: bpy.types.Action, fps: float) -> dict:
    start, end = action.frame_range
    curves = list(iter_action_fcurves(action))
    groups = sorted({curve.group.name for curve in curves if curve.group})
    keyed_paths = sorted({curve.data_path for curve in curves})
    keyframes = sum(len(curve.keyframe_points) for curve in curves)
    return {
        "name": action.name,
        "frame_start": round(float(start), 5),
        "frame_end": round(float(end), 5),
        "frames": round(float(end - start), 5),
        "duration_seconds": round(float(end - start) / fps, 6),
        "fcurves": len(curves),
        "keyframes": keyframes,
        "bone_groups": groups,
        "keyed_paths": keyed_paths,
    }


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    if not source.is_file():
        raise SystemExit(f"motion source not found: {source}")

    reset_scene()
    import_source(source)
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    armatures = []
    for obj in sorted(
        (obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"),
        key=lambda item: item.name,
    ):
        armatures.append(
            {
                "object": obj.name,
                "data": obj.data.name,
                "bones": [
                    {
                        "name": bone.name,
                        "parent": bone.parent.name if bone.parent else None,
                        "use_deform": bool(bone.use_deform),
                        "head_local": [round(float(value), 7) for value in bone.head_local],
                        "tail_local": [round(float(value), 7) for value in bone.tail_local],
                        "matrix_local": [
                            [round(float(value), 7) for value in row]
                            for row in bone.matrix_local
                        ],
                    }
                    for bone in obj.data.bones
                ],
            }
        )

    report = {
        "schema": 1,
        "source": str(source),
        "fps": fps,
        "armatures": armatures,
        "actions": [
            action_report(action, fps)
            for action in sorted(bpy.data.actions, key=lambda item: item.name)
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"motion inventory: armatures={len(armatures)} "
        f"actions={len(report['actions'])} output={args.output}"
    )


if __name__ == "__main__":
    main()
