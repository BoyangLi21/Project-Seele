"""Render one exported spatial-twin GLB with an automatic isometric camera.

Run through Blender::

  blender --background --python tools/render_spatial_twin_blender.py -- \
    --input artifacts/.../models/geofront_overview_lod4.glb \
    --output artifacts/.../evidence/geofront_isometric.png
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blend", type=Path)
    parser.add_argument("--width", type=int, default=1500)
    parser.add_argument("--height", type=int, default=1100)
    parser.add_argument("--hide", default="",
                        help="Comma-separated semantic object names to hide")
    parser.add_argument("--view", default="iso",
                        choices=("iso", "north", "south", "east",
                                 "west", "top"))
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def main() -> None:
    args = arguments()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    hidden = {name.strip() for name in args.hide.split(",") if name.strip()}
    for obj in meshes:
        if obj.name in hidden or any(obj.name.startswith(name + ".")
                                     for name in hidden):
            obj.hide_render = True
            obj.hide_viewport = True
    meshes = [obj for obj in meshes if not obj.hide_render]
    if not meshes:
        raise RuntimeError("GLB imported no mesh objects")

    corners = []
    for obj in meshes:
        corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    minimum = Vector((min(v.x for v in corners), min(v.y for v in corners),
                      min(v.z for v in corners)))
    maximum = Vector((max(v.x for v in corners), max(v.y for v in corners),
                      max(v.z for v in corners)))
    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    radius = max(extent.x, extent.y, extent.z)

    camera_data = bpy.data.cameras.new("SpatialTwinCamera")
    camera = bpy.data.objects.new("SpatialTwinCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    directions = {
        "iso": Vector((1.35, -1.55, 1.0)),
        # GLB axes are X, -Minecraft-Z, Minecraft-Y.
        "north": Vector((0.0, 1.0, 0.08)),
        "south": Vector((0.0, -1.0, 0.08)),
        "east": Vector((1.0, 0.0, 0.08)),
        "west": Vector((-1.0, 0.0, 0.08)),
        "top": Vector((0.0, 0.0, 1.0)),
    }
    direction = directions[args.view].normalized()
    camera.location = center + direction * radius * 2.2
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = radius * 1.5
    camera_data.clip_start = 0.1
    camera_data.clip_end = radius * 8.0
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.curvature_ridge_factor = 1.7
    scene.display.shading.curvature_valley_factor = 1.2
    scene.display.shading.background_type = "THEME"
    scene.display.shading.show_specular_highlight = False
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(args.output.resolve())
    scene.render.film_transparent = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    if args.blend:
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
    print(f"rendered {args.output} bounds={tuple(minimum)}..{tuple(maximum)}")


if __name__ == "__main__":
    main()
