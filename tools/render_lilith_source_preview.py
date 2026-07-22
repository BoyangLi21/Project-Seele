#!/usr/bin/env python3
"""Blender-only visual audit for the local Kiki Lilith source."""

from pathlib import Path
import math
import sys

import bpy
from mathutils import Vector


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(values) != 2:
        raise SystemExit("usage: blender --python render_lilith_source_preview.py -- INPUT OUTPUT_DIR")
    return Path(values[0]).resolve(), Path(values[1]).resolve()


def point_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def material(name, colour, metallic=0.0, roughness=0.5):
    result = bpy.data.materials.new(name)
    result.diffuse_color = colour
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = colour
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return result


def add_cross():
    red = material("SEELE_Red_Cross", (0.65, 0.002, 0.006, 1.0), 0.15, 0.33)
    for location, scale in (((0, 88, 705), (70, 16, 520)),
                            ((0, 88, 840), (410, 16, 70))):
        bpy.ops.mesh.primitive_cube_add(location=location)
        obj = bpy.context.object
        obj.scale = tuple(value * 0.5 for value in scale)
        obj.data.materials.append(red)


def apply_audit_materials():
    palette = {
        "m_lilith": (0.92, 0.90, 0.84, 1.0),
        "lambert1": (0.92, 0.90, 0.84, 1.0),
        "blinn5": (0.04, 0.015, 0.055, 1.0),
        "blinn7": (0.78, 0.72, 0.62, 1.0),
        "blinn8": (0.08, 0.08, 0.09, 1.0),
        "m_longinus": (0.55, 0.006, 0.012, 1.0),
        "m_ojos": (0.005, 0.005, 0.005, 1.0),
    }
    audit_materials = {name: material("audit_" + name, colour)
                       for name, colour in palette.items()}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or "cross_" in obj.name.lower():
            continue
        source_name = next((slot.material.name for slot in obj.material_slots
                            if slot.material is not None), "m_lilith")
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
        obj.hide_render = False
        obj.hide_set(False)
        obj.data.materials.clear()
        obj.data.materials.append(audit_materials.get(
            source_name, audit_materials["m_lilith"]))

def configure_scene(output):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("SEELE_Terminal_Dogma")
    scene.world.color = (0.006, 0.008, 0.012)
    scene.view_settings.look = "AgX - Medium High Contrast"

    bpy.ops.object.light_add(type="AREA", location=(-420, -720, 1080))
    key = bpy.context.object
    key.data.energy = 1500
    key.data.shape = "DISK"
    key.data.size = 600
    point_camera(key, (0, 0, 720))
    bpy.ops.object.light_add(type="AREA", location=(500, 140, 760))
    fill = bpy.context.object
    fill.data.energy = 900
    fill.data.color = (0.35, 0.45, 1.0)
    fill.data.size = 500
    point_camera(fill, (0, 0, 720))
    bpy.ops.object.light_add(type="AREA", location=(0, -200, 300))
    rim = bpy.context.object
    rim.data.energy = 700
    rim.data.color = (1.0, 0.12, 0.08)
    rim.data.size = 300
    point_camera(rim, (0, 0, 700))

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1250
    scene.camera = camera
    camera.data.clip_end = 5000.0
    return scene, camera


def main():
    source, output = arguments()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    for obj in list(bpy.context.scene.objects):
        if "cross_" in obj.name.lower():
            bpy.data.objects.remove(obj, do_unlink=True)
    apply_audit_materials()
    add_cross()
    scene, camera = configure_scene(output)
    target = (0, 0, 705)

    camera.location = (0, -1600, 705)
    point_camera(camera, target)
    scene.render.filepath = str(output / "lilith_kiki_front.png")
    bpy.ops.render.render(write_still=True)

    camera.location = (1450, -180, 705)
    point_camera(camera, target)
    scene.render.filepath = str(output / "lilith_kiki_side.png")
    bpy.ops.render.render(write_still=True)
    print("LILITH_PREVIEW", output)


if __name__ == "__main__":
    main()
