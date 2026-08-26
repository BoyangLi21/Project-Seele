"""Render close views of both EVA ankle seams at selected frames."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", required=True, type=Path)
parser.add_argument("--frames", default="1,34,78,108,109,127,150")
parser.add_argument("--mesh", default="EVA_ANATOMICAL_RIGID_MESH")
parser.add_argument("--rig", default="EVA_ANATOMICAL_ARMATURE")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

output = args.output_dir.resolve()
output.mkdir(parents=True, exist_ok=True)
frames = [int(value) for value in args.frames.split(",") if value.strip()]
mesh = bpy.data.objects[args.mesh]
rig = bpy.data.objects[args.rig]
scene = bpy.context.scene

for obj in scene.objects:
    if obj.type == "MESH":
        obj.hide_render = (
            obj != mesh
            and not obj.name.startswith("EVA_ANKLE_JOINT_SLEEVE_")
        )
mesh.hide_render = False

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world.color = (0.015, 0.015, 0.018)

bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = "ANKLE_SEAM_DIAGNOSTIC_CAMERA"
camera.data.type = "ORTHO"
camera.data.ortho_scale = 2.2
scene.camera = camera

for location, energy, size in (
    ((4.0, -5.0, 8.0), 1200.0, 5.0),
    ((-4.0, 2.0, 4.0), 750.0, 4.0),
):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.data.energy = energy
    light.data.size = size


def world_bone_point(name: str, endpoint: str) -> Vector:
    bone = rig.pose.bones[name]
    point = bone.head if endpoint == "head" else bone.tail
    return rig.matrix_world @ point


for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    for side in ("l", "r"):
        center = (
            world_bone_point(f"shin_{side}", "tail")
            + world_bone_point(f"foot_{side}", "head")
        ) * 0.5
        for view, direction in (
            ("front", Vector((0.0, -1.0, 0.10))),
            ("side", Vector((-1.0 if side == "l" else 1.0, 0.0, 0.10))),
        ):
            direction.normalize()
            camera.location = center + direction * 5.0
            camera.rotation_euler = (
                center - camera.location
            ).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(
                output / f"frame_{frame:03d}_{side}_{view}.png"
            )
            bpy.ops.render.render(write_still=True)

print({"output": str(output), "frames": frames})
