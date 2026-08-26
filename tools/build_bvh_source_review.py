"""Build a bounded interactive Blender review from one source BVH."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--start", required=True, type=int)
parser.add_argument("--end", required=True, type=int)
parser.add_argument("--event", action="append", default=[])
parser.add_argument("--source-name", required=True)
parser.add_argument("--source-url", required=True)
parser.add_argument("--license", required=True)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

if not args.source.is_file():
    raise SystemExit(f"missing BVH: {args.source}")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_anim.bvh(
    filepath=str(args.source.resolve()), target="ARMATURE", global_scale=0.01,
    frame_start=1, use_fps_scale=False, update_scene_fps=True,
    update_scene_duration=True, rotate_mode="NATIVE",
    axis_forward="-Z", axis_up="Y",
)
rig = bpy.context.object
rig.name = "SOURCE_MOTION_ARMATURE"
rig.show_in_front = True
rig.data.display_type = "STICK"
scene = bpy.context.scene
available_start = int(rig.animation_data.action.frame_range[0])
available_end = int(rig.animation_data.action.frame_range[1])
if not (available_start <= args.start < args.end <= available_end):
    raise SystemExit(
        f"review range {args.start}-{args.end} outside "
        f"{available_start}-{available_end}"
    )
scene.frame_start = args.start
scene.frame_end = args.end
scene.frame_set(args.start)
scene.timeline_markers.new("FRAGMENT_START", frame=args.start)
scene.timeline_markers.new("FRAGMENT_END", frame=args.end)
events = []
for value in args.event:
    label, frame_text = value.rsplit(":", 1)
    frame = int(frame_text)
    if not args.start <= frame <= args.end:
        raise SystemExit(f"event {label} outside fragment: {frame}")
    scene.timeline_markers.new(label, frame=frame)
    events.append({"label": label, "frame": frame})
readme = {
    "schema": 1,
    "source_name": args.source_name,
    "source_file": str(args.source.resolve()),
    "source_url": args.source_url,
    "license": args.license,
    "native_fps": scene.render.fps / scene.render.fps_base,
    "available_frames": [available_start, available_end],
    "review_frames": [args.start, args.end],
    "events": events,
    "status": "original_source_skeleton_not_an_accepted_EVA_motion",
}
text = bpy.data.texts.new("README_SOURCE_MOTION_REVIEW")
text.write(json.dumps(readme, ensure_ascii=False, indent=2))
args.output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
print(json.dumps(readme, ensure_ascii=False))
