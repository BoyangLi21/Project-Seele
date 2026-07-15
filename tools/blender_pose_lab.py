#!/usr/bin/env python3
"""Project SEELE Blender pose lab for the authoritative Unit-01 runtime rig.

This script is intentionally executed by Blender, not by the system Python.
It imports the exact rigid triangle meshes, Bedrock bone hierarchy and GeckoLib
animation channels used by the local ``eva_real_model`` resource pack.  The
coordinate conversion mirrors ``render_unit01_rig_preview.py`` and the in-game
``BakedModelFactory`` path, so a pose exported from this lab does not require a
second round of axis guessing.

Build the local lab::

    blender --background --python tools/blender_pose_lab.py -- --build

Open the saved lab with its Project SEELE sidebar registered::

    blender external-assets/work/pose-lab/Project_SEELE_Unit01_PoseLab.blend \
      --python tools/blender_pose_lab.py -- --interactive
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = (PROJECT_ROOT / "run" / "resourcepacks" / "eva_real_model" /
              "assets" / "projectseele")
POSE_LAB_ROOT = PROJECT_ROOT / "external-assets" / "work" / "pose-lab"
POSE_BLEND = POSE_LAB_ROOT / "Project_SEELE_Unit01_PoseLab.blend"
EXPORT_ROOT = POSE_LAB_ROOT / "exports"
CAPTURE_ROOT = POSE_LAB_ROOT / "captures"
REFERENCE_ROOT = POSE_LAB_ROOT / "references"

GEO_PATH = ASSET_ROOT / "geo" / "eva_unit01.geo.json"
ANIMATION_PATH = ASSET_ROOT / "animations" / "eva_unit01.animation.json"
BODY_MESH_PATH = ASSET_ROOT / "mesh" / "eva_unit01.mesh.json"
BODY_TEXTURE_PATH = ASSET_ROOT / "textures" / "entity" / "eva_unit01.png"

ARMATURE_NAME = "SEELE_Unit01_Rig"
BODY_COLLECTION = "01_BODY"
ATTACHMENT_COLLECTION = "02_ATTACHMENTS"
REFERENCE_COLLECTION = "03_REFERENCES"
CAMERA_COLLECTION = "04_CAMERAS"
ENVIRONMENT_COLLECTION = "05_ENVIRONMENT"

# Ten Bedrock model pixels are represented by one Blender unit.  This keeps a
# 192-pixel EVA around 19.2 Blender units tall while retaining useful decimal
# precision.  Export divides translations by this value again.
MODEL_SCALE = 0.1
BONE_DISPLAY_LENGTH = 0.75

# Runtime model coordinates are X=right, Y=up, Z=back.  Blender is Z-up.  The
# right-handed mapping is runtime (X, Y, Z) -> Blender (X, -Z, Y).
RUNTIME_FORWARD = Vector((0.0, 1.0, 0.0))
MODEL_HEIGHT_PIXELS = 192.0
MODEL_CENTRE_Z = MODEL_HEIGHT_PIXELS * MODEL_SCALE * 0.50

MESH_SOURCES = {
    "body": {
        "mesh": BODY_MESH_PATH,
        "texture": BODY_TEXTURE_PATH,
        "collection": BODY_COLLECTION,
    },
    "knife": {
        "mesh": ASSET_ROOT / "mesh" / "progressive_knife.mesh.json",
        "texture": ASSET_ROOT / "textures" / "entity" / "progressive_knife.png",
        "collection": ATTACHMENT_COLLECTION,
    },
    "cannon": {
        "mesh": ASSET_ROOT / "mesh" / "positron_cannon.mesh.json",
        "texture": ASSET_ROOT / "textures" / "entity" / "positron_cannon.png",
        "collection": ATTACHMENT_COLLECTION,
    },
    "lance": {
        "mesh": ASSET_ROOT / "mesh" / "longinus_lance.mesh.json",
        "texture": ASSET_ROOT / "textures" / "entity" / "longinus_lance.png",
        "collection": ATTACHMENT_COLLECTION,
    },
    "entry_plug": {
        "mesh": ASSET_ROOT / "mesh" / "entry_plug.mesh.json",
        "texture": ASSET_ROOT / "textures" / "entity" / "entry_plug.png",
        "collection": ATTACHMENT_COLLECTION,
    },
}

REFERENCE_SOURCES = (
    ("REF_KNEEL_DIAGRAM", "kneel_diagram.jpg", (-27.0, 0.0, 10.0)),
    ("REF_KNEEL_PHOTO", "kneel_photo.jpg", (27.0, 0.0, 10.0)),
    ("REF_PRONE_FIRE", "prone_fire.jpg", (0.0, -2.0, 28.0)),
)

# Presets load real channels from the current animation JSON.  Later layers
# replace only the bones/channels they contain, matching the offline preview's
# base + overlay convention.
PRESETS = {
    "IDLE": {
        "label": "站立 / Idle",
        "layers": (("animation.eva_unit01.idle", 0.0),),
        "weapon": "NONE",
        "stance": "standing",
    },
    "CROUCH": {
        "label": "当前单膝跪 / Crouch",
        "layers": (("animation.eva_unit01.crouch", 0.0),),
        "weapon": "NONE",
        "stance": "crouch",
    },
    "PRONE": {
        "label": "当前卧姿 / Prone",
        "layers": (("animation.eva_unit01.prone", 0.0),),
        "weapon": "NONE",
        "stance": "prone",
    },
    "CRAWL_A": {
        "label": "匍匐 A / Crawl 0.00s",
        "layers": (("animation.eva_unit01.crawl", 0.0),),
        "weapon": "NONE",
        "stance": "prone",
    },
    "CRAWL_B": {
        "label": "匍匐 B / Crawl 0.70s",
        "layers": (("animation.eva_unit01.crawl", 0.70),),
        "weapon": "NONE",
        "stance": "prone",
    },
    "CANNON": {
        "label": "阳电子炮瞄准 / Cannon",
        "layers": (("animation.eva_unit01.aim", 0.0),),
        "weapon": "CANNON",
        "stance": "standing",
    },
    "PRONE_CANNON": {
        "label": "卧姿射击 / Prone Cannon",
        "layers": (("animation.eva_unit01.prone", 0.0),
                   ("animation.eva_unit01.prone_aim", 0.0)),
        "weapon": "CANNON",
        "stance": "prone",
    },
    "KNIFE_READY": {
        "label": "反握刀准备 / Knife Ready",
        "layers": (("animation.eva_unit01.knife_ready", 0.0),),
        "weapon": "KNIFE",
        "stance": "standing",
    },
    "KNIFE_CONTACT": {
        "label": "反握刀命中 / Knife Contact",
        "layers": (("animation.eva_unit01.knife", 0.28),),
        "weapon": "KNIFE",
        "stance": "standing",
    },
    "LANCE_READY": {
        "label": "双手持枪准备 / Lance Ready",
        "layers": (("animation.eva_unit01.lance_ready", 0.0),),
        "weapon": "LANCE",
        "stance": "standing",
    },
    "LANCE_CONTACT": {
        "label": "朗枪突刺命中 / Lance Contact",
        "layers": (("animation.eva_unit01.visual_lance_contact", 0.0),),
        "weapon": "LANCE",
        "stance": "standing",
    },
}

PILOT_HIDDEN_BODY_BONES = {
    "head", "torso_lower", "torso_upper", "pylon_l", "pylon_r",
}

SELECTION_GROUPS = {
    "TORSO": ("root", "torso_lower", "torso_upper", "aim_pitch", "head", "horn"),
    "ARMS": ("arm_l", "forearm_l", "hand_l", "arm_r", "forearm_r", "hand_r"),
    "LEFT_ARM": ("arm_l", "forearm_l", "hand_l"),
    "RIGHT_ARM": ("arm_r", "forearm_r", "hand_r"),
    "LEGS": ("leg_l", "shin_l", "foot_l", "leg_r", "shin_r", "foot_r"),
    "FINGERS": (
        "finger_thumb_l", "finger_thumb_tip_l",
        "finger_index_l", "finger_index_tip_l",
        "finger_middle_l", "finger_middle_tip_l",
        "finger_ring_l", "finger_ring_tip_l",
        "finger_little_l", "finger_little_tip_l",
        "finger_thumb_r", "finger_thumb_tip_r",
        "finger_index_r", "finger_index_tip_r",
        "finger_middle_r", "finger_middle_tip_r",
        "finger_ring_r", "finger_ring_tip_r",
        "finger_little_r", "finger_little_tip_r",
    ),
    "WEAPONS": ("knife", "cannon", "lance", "entry_plug", "plug_hatch_l", "plug_hatch_r"),
}


def parse_arguments():
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="rebuild the local .blend lab")
    parser.add_argument("--interactive", action="store_true", help="register the sidebar UI")
    parser.add_argument("--validate", action="store_true", help="validate the currently open lab")
    parser.add_argument("--preset", choices=tuple(PRESETS),
                        help="apply a pose preset before validation/rendering")
    parser.add_argument("--render-check", type=Path,
                        help="render the front camera to this PNG during validation")
    return parser.parse_args(arguments)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def vector3(value, label):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must be a three-number vector, got {value!r}")
    return tuple(float(component) for component in value)


def sample_channel(channel, time, label):
    if isinstance(channel, list):
        return vector3(channel, label)
    if not isinstance(channel, dict) or not channel:
        raise ValueError(f"{label} is not a supported Gecko channel")
    keyframes = sorted((float(key), vector3(value, f"{label}@{key}"))
                       for key, value in channel.items())
    if time <= keyframes[0][0]:
        return keyframes[0][1]
    if time >= keyframes[-1][0]:
        return keyframes[-1][1]
    for (left_time, left), (right_time, right) in zip(keyframes, keyframes[1:]):
        if left_time <= time <= right_time:
            alpha = (time - left_time) / (right_time - left_time)
            return tuple(left[index] + (right[index] - left[index]) * alpha
                         for index in range(3))
    raise AssertionError("unreachable animation sample")


def sample_animation(animation_name, requested_time):
    animations = read_json(ANIMATION_PATH).get("animations", {})
    if animation_name not in animations:
        raise ValueError(f"animation not found: {animation_name}")
    animation = animations[animation_name]
    length = float(animation.get("animation_length", 0.0))
    sample_time = float(requested_time)
    if animation.get("loop") is True and length > 0.0:
        sample_time %= length
    elif length > 0.0:
        sample_time = min(max(sample_time, 0.0), length)
    rotations = {}
    positions = {}
    for bone_name, channels in animation.get("bones", {}).items():
        if "rotation" in channels:
            rotations[bone_name] = sample_channel(
                channels["rotation"], sample_time,
                f"{animation_name}/{bone_name}/rotation")
        if "position" in channels:
            positions[bone_name] = sample_channel(
                channels["position"], sample_time,
                f"{animation_name}/{bone_name}/position")
    return rotations, positions


def runtime_to_blender(value):
    x, y, z = (float(component) for component in value)
    return Vector((x, -z, y)) * MODEL_SCALE


def reflected_runtime_pivot(raw_pivot):
    x, y, z = (float(component) for component in raw_pivot)
    return (-x, y, z)


def ensure_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def link_object_only(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def create_texture_material(name, texture_path):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (0.35, 0.12, 0.55, 1.0)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(texture_path), check_existing=True)
    texture.interpolation = "Linear"
    try:
        emission = nodes.new("ShaderNodeEmission")
        links.new(texture.outputs["Color"], emission.inputs["Color"])
        links.new(emission.outputs["Emission"], output.inputs["Surface"])
    except RuntimeError:
        # Blender builds that fold the Emission node into Principled BSDF.
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        links.new(texture.outputs["Color"], shader.inputs["Base Color"])
        emission_input = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
        if emission_input is not None:
            links.new(texture.outputs["Color"], emission_input)
        strength = shader.inputs.get("Emission Strength")
        if strength is not None:
            strength.default_value = 0.35
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def create_armature(geo):
    armature_data = bpy.data.armatures.new(f"{ARMATURE_NAME}_Data")
    armature = bpy.data.objects.new(ARMATURE_NAME, armature_data)
    bpy.context.scene.collection.objects.link(armature)
    armature.show_in_front = True
    armature.data.display_type = "BBONE"
    armature["seele_axis_contract"] = (
        "runtime (X,Y,Z) -> Blender (X,-Z,Y); raw rotations -> (-X,-Y,+Z)")
    armature["seele_model_scale"] = MODEL_SCALE

    bones = geo["minecraft:geometry"][0].get("bones", [])
    by_name = {bone["name"]: bone for bone in bones}
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for source in bones:
        name = source["name"]
        raw_pivot = source.get("pivot", (0.0, 0.0, 0.0))
        head = runtime_to_blender(reflected_runtime_pivot(raw_pivot))
        edit_bone = armature_data.edit_bones.new(name)
        edit_bone.head = head
        edit_bone.tail = head + Vector((0.0, 0.0, BONE_DISPLAY_LENGTH))
        # With the bone pointing along global +Z, align local Z to Blender -Y.
        # This yields local X/Y/Z == runtime X/Y/Z after the axis mapping.
        edit_bone.align_roll(Vector((0.0, -1.0, 0.0)))
        edit_bone.use_connect = False
    for source in bones:
        parent = source.get("parent")
        if parent and parent in armature_data.edit_bones:
            armature_data.edit_bones[source["name"]].parent = armature_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="POSE")
    for source in bones:
        pose_bone = armature.pose.bones[source["name"]]
        pose_bone.rotation_mode = "XYZ"
        pose_bone["seele_raw_pivot"] = list(source.get("pivot", (0.0, 0.0, 0.0)))
        pose_bone["seele_bind_rotation"] = list(source.get("rotation", (0.0, 0.0, 0.0)))
    bpy.ops.object.mode_set(mode="OBJECT")

    # Bone collections are an editor convenience only; failure here must not
    # invalidate the actual transform contract on a future Blender release.
    try:
        for group_name, members in SELECTION_GROUPS.items():
            bone_collection = armature_data.collections.new(group_name)
            for member in members:
                if member in armature_data.bones:
                    bone_collection.assign(armature_data.bones[member])
    except (AttributeError, RuntimeError, TypeError):
        pass
    return armature, by_name


def create_mesh_part(source_name, bone_name, part, stride, material, armature, collection):
    values = part["vertices"]
    if stride != 8:
        raise ValueError(f"{source_name}/{bone_name}: expected stride 8, got {stride}")
    if len(values) % (stride * 3) != 0:
        raise ValueError(f"{source_name}/{bone_name}: incomplete triangle data")
    pivot = tuple(float(value) for value in part["pivot"])
    vertices = []
    uvs = []
    for start in range(0, len(values), stride):
        absolute = tuple(float(values[start + axis]) + pivot[axis] for axis in range(3))
        emitted = (-absolute[0], absolute[1], absolute[2])
        vertices.append(tuple(runtime_to_blender(emitted)))
        u = float(values[start + 3])
        v = float(values[start + 4])
        uvs.append((u, 1.0 - v))
    faces = [(index, index + 1, index + 2)
             for index in range(0, len(vertices), 3)]
    mesh = bpy.data.meshes.new(f"MESH_{source_name}_{bone_name}")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            uv_layer.data[loop_index].uv = uvs[vertex_index]
    mesh.update()

    obj = bpy.data.objects.new(f"{source_name.upper()}__{bone_name}", mesh)
    collection.objects.link(obj)
    obj["seele_source"] = source_name
    obj["seele_bone"] = bone_name
    obj["seele_rigid_part"] = True
    vertex_group = obj.vertex_groups.new(name=bone_name)
    vertex_group.add(range(len(vertices)), 1.0, "REPLACE")
    modifier = obj.modifiers.new("Project_SEELE_Rigid_Rig", "ARMATURE")
    modifier.object = armature
    modifier.use_deform_preserve_volume = False
    return obj


def create_mesh_source(source_name, definition, armature):
    mesh_data = read_json(definition["mesh"])
    stride = int(mesh_data.get("stride", 0))
    material = create_texture_material(
        f"MAT_{source_name}", definition["texture"])
    collection = ensure_collection(definition["collection"])
    objects = []
    for bone_name, part in mesh_data.get("parts", {}).items():
        if bone_name not in armature.data.bones:
            raise ValueError(f"{source_name}: mesh part has no rig bone: {bone_name}")
        objects.append(create_mesh_part(
            source_name, bone_name, part, stride, material, armature, collection))
    return objects


def create_floor_and_axes():
    collection = ensure_collection(ENVIRONMENT_COLLECTION)
    bpy.ops.mesh.primitive_plane_add(size=70.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.object
    floor.name = "POSE_LAB_FLOOR"
    link_object_only(floor, collection)
    material = bpy.data.materials.new("MAT_PoseLabFloor")
    material.diffuse_color = (0.055, 0.065, 0.08, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = (0.025, 0.035, 0.05, 1.0)
        shader.inputs["Roughness"].default_value = 0.92
    floor.data.materials.append(material)

    # Thin axis bars make foot contact and model facing obvious in every view.
    for name, location, scale, colour in (
            ("AXIS_X", (0.0, 0.0, 0.015), (32.0, 0.035, 0.025), (0.55, 0.04, 0.04, 1.0)),
            ("AXIS_FORWARD", (0.0, 0.0, 0.020), (0.035, 32.0, 0.030), (0.04, 0.30, 0.70, 1.0))):
        bpy.ops.mesh.primitive_cube_add(location=location)
        bar = bpy.context.object
        bar.name = name
        bar.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        link_object_only(bar, collection)
        bar_material = bpy.data.materials.new(f"MAT_{name}")
        bar_material.diffuse_color = colour
        bar.data.materials.append(bar_material)


def aim_camera(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_camera(name, location, target, lens=58.0):
    collection = ensure_collection(CAMERA_COLLECTION)
    camera_data = bpy.data.cameras.new(f"{name}_Data")
    camera = bpy.data.objects.new(name, camera_data)
    collection.objects.link(camera)
    camera.location = location
    camera.data.lens = lens
    camera.data.sensor_width = 36.0
    aim_camera(camera, target)
    return camera


def set_pilot_camera_stance(stance):
    camera = bpy.data.objects.get("CAM_PILOT")
    if camera is None:
        return
    sockets = {
        "standing": (24.63, 1.00),
        "crouch": (19.70, 0.80),
        "prone": (7.00, 12.00),
    }
    eye_blocks, forward_blocks = sockets.get(stance, sockets["standing"])
    pixels_per_block = 16.0 / 2.5
    eye_pixels = eye_blocks * pixels_per_block
    forward_pixels = forward_blocks * pixels_per_block
    camera.location = runtime_to_blender((0.0, eye_pixels, -forward_pixels))
    camera.data.lens = 52.0
    aim_camera(camera, camera.location + RUNTIME_FORWARD * 20.0)
    camera["seele_stance"] = stance


def create_cameras():
    target = Vector((0.0, 0.0, MODEL_CENTRE_Z))
    front = create_camera("CAM_FRONT", (0.0, 48.0, MODEL_CENTRE_Z), target, 52.0)
    create_camera("CAM_SIDE", (48.0, 0.0, MODEL_CENTRE_Z), target, 52.0)
    create_camera("CAM_BACK", (0.0, -48.0, MODEL_CENTRE_Z), target, 52.0)
    create_camera("CAM_HIGH_3Q", (33.0, 37.0, 24.0), target, 50.0)
    create_camera("CAM_PILOT", (0.0, 0.0, 15.76), (0.0, 20.0, 15.76), 52.0)
    set_pilot_camera_stance("standing")
    bpy.context.scene.camera = front


def create_reference_images():
    collection = ensure_collection(REFERENCE_COLLECTION)
    for object_name, filename, location in REFERENCE_SOURCES:
        path = REFERENCE_ROOT / filename
        if not path.exists():
            print(f"POSE LAB reference missing (optional): {path}")
            continue
        image = bpy.data.images.load(str(path), check_existing=True)
        bpy.ops.object.empty_add(type="IMAGE", location=location,
                                 rotation=(math.radians(90.0), 0.0, 0.0))
        reference = bpy.context.object
        reference.name = object_name
        reference.data = image
        reference.empty_display_size = 12.0
        reference.color[3] = 0.92
        reference["seele_reference"] = True
        link_object_only(reference, collection)
        reference.hide_set(True)
        reference.hide_render = True


def reset_pose(armature):
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)


def apply_pose_layers(armature, layers):
    reset_pose(armature)
    rotations = {}
    positions = {}
    for animation_name, sample_time in layers:
        layer_rotations, layer_positions = sample_animation(animation_name, sample_time)
        rotations.update(layer_rotations)
        positions.update(layer_positions)
    for pose_bone in armature.pose.bones:
        bind = tuple(float(value) for value in
                     pose_bone.get("seele_bind_rotation", (0.0, 0.0, 0.0)))
        animated = rotations.get(pose_bone.name, (0.0, 0.0, 0.0))
        raw = tuple(bind[index] + animated[index] for index in range(3))
        pose_bone.rotation_euler = tuple(math.radians(value) for value in
                                         (-raw[0], -raw[1], raw[2]))
        raw_position = positions.get(pose_bone.name, (0.0, 0.0, 0.0))
        runtime_position = (-raw_position[0], raw_position[1], raw_position[2])
        pose_bone.location = tuple(value * MODEL_SCALE for value in runtime_position)
    bpy.context.view_layer.update()


def set_attachment_visibility(active_weapon):
    active = active_weapon.lower()
    for obj in bpy.data.objects:
        source = obj.get("seele_source")
        if source in {"knife", "cannon", "lance"}:
            visible = source == active
            obj.hide_set(not visible)
            obj.hide_render = not visible


def set_entry_plug_visibility(visible):
    for obj in bpy.data.objects:
        if obj.get("seele_source") == "entry_plug":
            obj.hide_set(not visible)
            obj.hide_render = not visible


def set_pilot_body_visibility(pilot_view):
    for obj in bpy.data.objects:
        if obj.get("seele_source") != "body":
            continue
        hidden = pilot_view and obj.get("seele_bone") in PILOT_HIDDEN_BODY_BONES
        obj.hide_set(hidden)
        obj.hide_render = hidden


def set_reference_visibility(visible):
    for obj in bpy.data.objects:
        if obj.get("seele_reference"):
            obj.hide_set(not visible)


def activate_camera(name):
    camera = bpy.data.objects.get(name)
    if camera is None:
        raise ValueError(f"camera not found: {name}")
    bpy.context.scene.camera = camera
    for area in bpy.context.screen.areas if bpy.context.screen else ():
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_perspective = "CAMERA"


def apply_named_preset(scene, preset_name):
    definition = PRESETS[preset_name]
    armature = bpy.data.objects.get(ARMATURE_NAME)
    if armature is None:
        raise ValueError(f"armature not found: {ARMATURE_NAME}")
    apply_pose_layers(armature, definition["layers"])
    scene.seele_weapon = definition["weapon"]
    set_attachment_visibility(definition["weapon"])
    set_pilot_camera_stance(definition["stance"])
    scene["seele_current_preset"] = preset_name
    scene["seele_current_layers"] = json.dumps(definition["layers"])


def clean_number(value):
    rounded = round(float(value), 4)
    return 0.0 if abs(rounded) < 0.00005 else rounded


def export_current_pose(scene):
    armature = bpy.data.objects.get(ARMATURE_NAME)
    if armature is None:
        raise ValueError(f"armature not found: {ARMATURE_NAME}")
    bones = {}
    for pose_bone in armature.pose.bones:
        bind = tuple(float(value) for value in
                     pose_bone.get("seele_bind_rotation", (0.0, 0.0, 0.0)))
        euler = pose_bone.rotation_euler
        raw_rotation = (
            -math.degrees(euler.x) - bind[0],
            -math.degrees(euler.y) - bind[1],
            math.degrees(euler.z) - bind[2],
        )
        location = pose_bone.location
        raw_position = (
            -location.x / MODEL_SCALE,
            location.y / MODEL_SCALE,
            location.z / MODEL_SCALE,
        )
        channels = {}
        if any(abs(value) > 0.00005 for value in raw_rotation):
            channels["rotation"] = [clean_number(value) for value in raw_rotation]
        if any(abs(value) > 0.00005 for value in raw_position):
            channels["position"] = [clean_number(value) for value in raw_position]
        if channels:
            bones[pose_bone.name] = channels

    export_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", scene.seele_export_name).strip("_")
    export_name = export_name or "pose_lab_export"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    output = EXPORT_ROOT / f"{export_name}_{stamp}.animation.json"
    animation_name = (export_name if export_name.startswith("animation.") else
                      f"animation.eva_unit01.{export_name}")
    payload = {
        "format_version": "1.8.0",
        "animations": {
            animation_name: {
                "animation_length": 0.0,
                "bones": bones,
            }
        },
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    metadata = {
        "exported_at": datetime.now().astimezone().isoformat(),
        "blender_version": bpy.app.version_string,
        "source_animation_sha256": file_sha256(ANIMATION_PATH),
        "source_geo_sha256": file_sha256(GEO_PATH),
        "preset": scene.get("seele_current_preset", "CUSTOM"),
        "weapon": scene.seele_weapon,
        "axis_contract": armature.get("seele_axis_contract"),
        "animation_json": str(output),
    }
    output.with_suffix(".meta.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def capture_current_pose(scene):
    preset = str(scene.get("seele_current_preset", "custom")).lower()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = CAPTURE_ROOT / f"{preset}_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    previous_camera = scene.camera
    previous_pilot = scene.seele_pilot_view
    scene.seele_pilot_view = False
    set_pilot_body_visibility(False)
    for slug, camera_name in (("front", "CAM_FRONT"), ("side", "CAM_SIDE"),
                              ("back", "CAM_BACK"), ("high_3q", "CAM_HIGH_3Q")):
        scene.camera = bpy.data.objects[camera_name]
        scene.render.filepath = str(output_dir / f"{slug}.png")
        bpy.ops.render.render(write_still=True)
    scene.seele_pilot_view = True
    set_pilot_body_visibility(True)
    scene.camera = bpy.data.objects["CAM_PILOT"]
    scene.render.filepath = str(output_dir / "pilot.png")
    bpy.ops.render.render(write_still=True)
    scene.seele_pilot_view = previous_pilot
    set_pilot_body_visibility(previous_pilot)
    scene.camera = previous_camera
    return output_dir


def scene_setup():
    scene = bpy.context.scene
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        pass
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Project_SEELE_PoseLab_World")
    scene.world.color = (0.008, 0.012, 0.022)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene["seele_pose_lab_version"] = 1
    scene["seele_project_root"] = str(PROJECT_ROOT)
    scene["seele_source_hashes"] = json.dumps({
        "geo": file_sha256(GEO_PATH),
        "animation": file_sha256(ANIMATION_PATH),
        "body_mesh": file_sha256(BODY_MESH_PATH),
    })


def build_lab():
    missing = [path for path in (GEO_PATH, ANIMATION_PATH, BODY_MESH_PATH,
                                 BODY_TEXTURE_PATH)
               if not path.exists()]
    if missing:
        raise SystemExit("missing authoritative pose-lab input(s): " +
                         ", ".join(str(path) for path in missing))
    POSE_LAB_ROOT.mkdir(parents=True, exist_ok=True)
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    register_properties_and_ui()
    for collection_name in (BODY_COLLECTION, ATTACHMENT_COLLECTION,
                            REFERENCE_COLLECTION, CAMERA_COLLECTION,
                            ENVIRONMENT_COLLECTION):
        ensure_collection(collection_name)
    geo = read_json(GEO_PATH)
    armature, _ = create_armature(geo)
    for source_name, definition in MESH_SOURCES.items():
        if definition["mesh"].exists() and definition["texture"].exists():
            create_mesh_source(source_name, definition, armature)
        else:
            print(f"POSE LAB optional source missing: {source_name}")
    create_floor_and_axes()
    create_cameras()
    create_reference_images()
    scene_setup()
    scene = bpy.context.scene
    scene.seele_pose_preset = "IDLE"
    scene.seele_weapon = "NONE"
    scene.seele_show_entry_plug = True
    scene.seele_pilot_view = False
    scene.seele_show_references = False
    scene.seele_export_name = "pose_lab_export"
    apply_named_preset(scene, "IDLE")
    set_entry_plug_visibility(True)
    set_reference_visibility(False)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(POSE_BLEND))
    print(f"POSE LAB built: {POSE_BLEND}")


def validate_lab(render_check=None):
    required_objects = {
        ARMATURE_NAME, "CAM_FRONT", "CAM_SIDE", "CAM_BACK", "CAM_PILOT",
        "BODY__head", "BODY__arm_l", "BODY__arm_r", "BODY__leg_l", "BODY__leg_r",
        "CANNON__cannon", "KNIFE__knife", "LANCE__lance",
    }
    missing_objects = sorted(required_objects - set(bpy.data.objects.keys()))
    armature = bpy.data.objects.get(ARMATURE_NAME)
    required_bones = {
        "root", "torso_lower", "torso_upper", "head", "arm_l", "forearm_l",
        "hand_l", "arm_r", "forearm_r", "hand_r", "leg_l", "shin_l",
        "foot_l", "leg_r", "shin_r", "foot_r", "cannon", "knife", "lance",
    }
    missing_bones = (sorted(required_bones - set(armature.data.bones.keys()))
                     if armature else sorted(required_bones))
    if missing_objects or missing_bones:
        raise SystemExit(
            f"POSE LAB validation failed; objects={missing_objects}, bones={missing_bones}")
    contract = armature.get("seele_axis_contract", "")
    if "(-X,-Y,+Z)" not in contract:
        raise SystemExit(f"POSE LAB axis contract missing or stale: {contract!r}")
    if render_check:
        render_check = Path(render_check)
        render_check.parent.mkdir(parents=True, exist_ok=True)
        set_pilot_body_visibility(False)
        bpy.context.scene.camera = bpy.data.objects["CAM_FRONT"]
        bpy.context.scene.render.filepath = str(render_check)
        bpy.ops.render.render(write_still=True)
    print(f"POSE LAB validated: {len(bpy.data.objects)} objects / "
          f"{len(armature.data.bones)} bones / Blender {bpy.app.version_string}")


def update_weapon(scene, _context):
    set_attachment_visibility(scene.seele_weapon)


def update_entry_plug(scene, _context):
    set_entry_plug_visibility(scene.seele_show_entry_plug)


def update_pilot_view(scene, _context):
    set_pilot_body_visibility(scene.seele_pilot_view)
    if scene.seele_pilot_view and bpy.data.objects.get("CAM_PILOT"):
        scene.camera = bpy.data.objects["CAM_PILOT"]


def update_references(scene, _context):
    set_reference_visibility(scene.seele_show_references)


class SEELE_OT_apply_preset(bpy.types.Operator):
    bl_idname = "seele.apply_preset"
    bl_label = "载入姿势"
    bl_description = "从游戏正在使用的 GeckoLib JSON 载入所选姿势"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            apply_named_preset(context.scene, context.scene.seele_pose_preset)
        except Exception as exception:
            self.report({"ERROR"}, str(exception))
            return {"CANCELLED"}
        self.report({"INFO"}, f"已载入：{PRESETS[context.scene.seele_pose_preset]['label']}")
        return {"FINISHED"}


class SEELE_OT_reset_pose(bpy.types.Operator):
    bl_idname = "seele.reset_pose"
    bl_label = "清空姿势"
    bl_description = "恢复所有骨骼到模型绑定姿势"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        armature = bpy.data.objects.get(ARMATURE_NAME)
        if armature is None:
            self.report({"ERROR"}, "找不到初号机骨架")
            return {"CANCELLED"}
        reset_pose(armature)
        context.scene["seele_current_preset"] = "CUSTOM"
        return {"FINISHED"}


class SEELE_OT_select_group(bpy.types.Operator):
    bl_idname = "seele.select_group"
    bl_label = "选择关节组"
    bl_options = {"REGISTER", "UNDO"}

    group: bpy.props.StringProperty()

    def execute(self, context):
        armature = bpy.data.objects.get(ARMATURE_NAME)
        if armature is None:
            return {"CANCELLED"}
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="POSE")
        for bone in armature.data.bones:
            bone.select = False
        names = SELECTION_GROUPS.get(self.group, ())
        selected = [name for name in names if name in armature.data.bones]
        for name in selected:
            armature.data.bones[name].select = True
        if selected:
            armature.data.bones.active = armature.data.bones[selected[-1]]
        return {"FINISHED"}


class SEELE_OT_set_camera(bpy.types.Operator):
    bl_idname = "seele.set_camera"
    bl_label = "切换观察机位"

    camera_name: bpy.props.StringProperty()

    def execute(self, _context):
        try:
            activate_camera(self.camera_name)
        except Exception as exception:
            self.report({"ERROR"}, str(exception))
            return {"CANCELLED"}
        return {"FINISHED"}


class SEELE_OT_export_pose(bpy.types.Operator):
    bl_idname = "seele.export_pose"
    bl_label = "导出当前动作 JSON"
    bl_description = "按游戏轴向导出当前全部骨骼，不会覆盖正式动画"

    def execute(self, context):
        try:
            output = export_current_pose(context.scene)
        except Exception as exception:
            self.report({"ERROR"}, str(exception))
            return {"CANCELLED"}
        self.report({"INFO"}, f"已导出：{output}")
        print(f"POSE LAB export: {output}")
        return {"FINISHED"}


class SEELE_OT_capture_pose(bpy.types.Operator):
    bl_idname = "seele.capture_pose"
    bl_label = "输出五视图 PNG"
    bl_description = "渲染正面、侧面、背面、三分之四和驾驶员视角"

    def execute(self, context):
        try:
            output = capture_current_pose(context.scene)
        except Exception as exception:
            self.report({"ERROR"}, str(exception))
            return {"CANCELLED"}
        self.report({"INFO"}, f"截图目录：{output}")
        print(f"POSE LAB captures: {output}")
        return {"FINISHED"}


class SEELE_OT_save_lab(bpy.types.Operator):
    bl_idname = "seele.save_lab"
    bl_label = "保存 Pose Lab"
    bl_description = "保存到本项目固定的本地 .blend 文件"

    def execute(self, _context):
        bpy.ops.wm.save_as_mainfile(filepath=str(POSE_BLEND))
        self.report({"INFO"}, f"已保存：{POSE_BLEND}")
        return {"FINISHED"}


class SEELE_PT_pose_lab(bpy.types.Panel):
    bl_label = "Project SEELE — 初号机动作台"
    bl_idname = "SEELE_PT_pose_lab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Project SEELE"

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        box = layout.box()
        box.label(text="1. 载入当前游戏动作", icon="ARMATURE_DATA")
        box.prop(scene, "seele_pose_preset", text="姿势")
        row = box.row(align=True)
        row.operator("seele.apply_preset", icon="IMPORT")
        row.operator("seele.reset_pose", icon="LOOP_BACK")

        box = layout.box()
        box.label(text="2. 选择需要调整的关节", icon="BONE_DATA")
        row = box.row(align=True)
        operator = row.operator("seele.select_group", text="躯干/头")
        operator.group = "TORSO"
        operator = row.operator("seele.select_group", text="双臂")
        operator.group = "ARMS"
        row = box.row(align=True)
        operator = row.operator("seele.select_group", text="左臂")
        operator.group = "LEFT_ARM"
        operator = row.operator("seele.select_group", text="右臂")
        operator.group = "RIGHT_ARM"
        row = box.row(align=True)
        operator = row.operator("seele.select_group", text="双腿")
        operator.group = "LEGS"
        operator = row.operator("seele.select_group", text="十根手指")
        operator.group = "FINGERS"
        operator = box.operator("seele.select_group", text="武器/插入栓骨骼")
        operator.group = "WEAPONS"

        box = layout.box()
        box.label(text="3. 可见物与驾驶视角", icon="HIDE_OFF")
        box.prop(scene, "seele_weapon", text="武器")
        box.prop(scene, "seele_show_entry_plug", text="显示插入栓与舱盖")
        box.prop(scene, "seele_show_references", text="显示人类姿势参考图")
        box.prop(scene, "seele_pilot_view", text="驾驶员视角遮挡规则")

        box = layout.box()
        box.label(text="4. 固定检查机位", icon="CAMERA_DATA")
        row = box.row(align=True)
        for label, name in (("正", "CAM_FRONT"), ("侧", "CAM_SIDE"),
                            ("背", "CAM_BACK")):
            operator = row.operator("seele.set_camera", text=label)
            operator.camera_name = name
        row = box.row(align=True)
        operator = row.operator("seele.set_camera", text="3/4")
        operator.camera_name = "CAM_HIGH_3Q"
        operator = row.operator("seele.set_camera", text="驾驶员")
        operator.camera_name = "CAM_PILOT"

        box = layout.box()
        box.label(text="5. 导出给游戏", icon="FILE_TICK")
        box.prop(scene, "seele_export_name", text="动作名")
        row = box.row(align=True)
        row.operator("seele.export_pose", icon="EXPORT")
        row.operator("seele.capture_pose", icon="RENDER_STILL")
        box.operator("seele.save_lab", icon="FILE_TICK")

        help_box = layout.box()
        help_box.label(text="局部旋转：R 后按两次 X / Y / Z")
        help_box.label(text="撤销：Ctrl+Z；正交视图：小键盘 1/3/7")
        help_box.label(text="红 X=左右，绿 Y=上下，蓝 Z=前后（骨骼局部轴）")


CLASSES = (
    SEELE_OT_apply_preset,
    SEELE_OT_reset_pose,
    SEELE_OT_select_group,
    SEELE_OT_set_camera,
    SEELE_OT_export_pose,
    SEELE_OT_capture_pose,
    SEELE_OT_save_lab,
    SEELE_PT_pose_lab,
)


def register_properties_and_ui():
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, AttributeError):
            pass
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.seele_pose_preset = bpy.props.EnumProperty(
        name="Pose preset",
        items=[(identifier, definition["label"], "")
               for identifier, definition in PRESETS.items()],
        default="IDLE",
    )
    bpy.types.Scene.seele_weapon = bpy.props.EnumProperty(
        name="Weapon",
        items=(("NONE", "徒手", ""), ("CANNON", "阳电子炮", ""),
               ("KNIFE", "高振动粒子刀", ""), ("LANCE", "朗基努斯之枪", "")),
        default="NONE",
        update=update_weapon,
    )
    bpy.types.Scene.seele_show_entry_plug = bpy.props.BoolProperty(
        name="Show entry plug", default=True, update=update_entry_plug)
    bpy.types.Scene.seele_pilot_view = bpy.props.BoolProperty(
        name="Pilot view", default=False, update=update_pilot_view)
    bpy.types.Scene.seele_show_references = bpy.props.BoolProperty(
        name="Show references", default=False, update=update_references)
    bpy.types.Scene.seele_export_name = bpy.props.StringProperty(
        name="Export name", default="pose_lab_export")


def main():
    args = parse_arguments()
    if args.build:
        build_lab()
        if args.preset:
            apply_named_preset(bpy.context.scene, args.preset)
        if args.validate:
            validate_lab(args.render_check)
        return
    register_properties_and_ui()
    if args.preset:
        bpy.context.scene.seele_pose_preset = args.preset
        apply_named_preset(bpy.context.scene, args.preset)
    if args.validate:
        validate_lab(args.render_check)
    else:
        scene = bpy.context.scene
        set_attachment_visibility(getattr(scene, "seele_weapon", "NONE"))
        set_entry_plug_visibility(getattr(scene, "seele_show_entry_plug", True))
        set_pilot_body_visibility(getattr(scene, "seele_pilot_view", False))
        set_reference_visibility(getattr(scene, "seele_show_references", False))
        print(f"POSE LAB interactive UI registered for Blender {bpy.app.version_string}")


if __name__ == "__main__":
    main()
