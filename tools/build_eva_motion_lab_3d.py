#!/usr/bin/env python3
"""Build a real Blender 3D animation lab for the current EVA motion database.

The scene contains the exact local EVA triangle mesh, its runtime hierarchy,
all retargeted clips on one labelled timeline, contact indicators, a floor and
an optional CC0 human source mannequin.  It is the primary animation review
surface; Minecraft is only the later integration target.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector


CORE_SEQUENCE = (
    "idle",
    "walk",
    "formal_walk",
    "jog",
    "sprint",
    "crouch_idle",
    "crouch_walk",
    "jump_start",
    "jump_loop",
    "jump_land",
    "punch_jab",
    "punch_cross",
    "knife_idle",
    "knife_attack",
    "rifle_idle",
    "rifle_shoot",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--texture", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--source-human", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--display-scale", type=float, default=0.05)
    parser.add_argument("--gap-frames", type=int, default=12)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in tuple(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for datablock in tuple(datablocks):
            datablocks.remove(datablock)


def target_to_blender(vector: Vector) -> Vector:
    """Runtime/Gecko model coordinates (Y up) -> Blender (Z up)."""
    return Vector((vector.x, -vector.z, vector.y))


def runtime_pivot(raw: list[float]) -> Vector:
    return Vector((-float(raw[0]), float(raw[1]), float(raw[2])))


def quaternion_to_blender(wxyz: list[float]) -> Quaternion:
    authored = Quaternion(tuple(float(value) for value in wxyz))
    euler = authored.to_euler("XYZ")
    # Gecko's Builtin BakedModelFactory conversion: (-X, -Y, +Z).
    runtime = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_matrix()
    basis = Matrix(((1.0, 0.0, 0.0),
                    (0.0, 0.0, -1.0),
                    (0.0, 1.0, 0.0)))
    result = (basis @ runtime @ basis.inverted()).to_quaternion()
    result.normalize()
    return result


def make_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object,
                       collection: bpy.types.Collection) -> None:
    for current in tuple(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def principled_node(material: bpy.types.Material) -> bpy.types.Node:
    return next(
        node for node in material.node_tree.nodes
        if node.bl_idname == "ShaderNodeBsdfPrincipled"
    )


def iter_action_fcurves(action: bpy.types.Action):
    """Yield legacy and Blender 4.4+/5.x layered-action F-curves."""
    if hasattr(action, "fcurves"):
        yield from action.fcurves
        return
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                yield from channelbag.fcurves


def make_material(texture_path: Path) -> bpy.types.Material:
    material = bpy.data.materials.new("EVA-01 Body")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = principled_node(material)
    image_node = nodes.new("ShaderNodeTexImage")
    image_node.image = bpy.data.images.load(str(texture_path.resolve()),
                                             check_existing=True)
    image_node.interpolation = "Linear"
    links.new(image_node.outputs["Color"], principled.inputs["Base Color"])
    links.new(image_node.outputs["Alpha"], principled.inputs["Alpha"])
    principled.inputs["Roughness"].default_value = 0.72
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    else:
        material.blend_method = "CLIP"
    return material


def load_geo(path: Path) -> tuple[list[dict], dict[str, Vector], dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    bones = payload["minecraft:geometry"][0]["bones"]
    pivots = {
        bone["name"]: runtime_pivot(bone.get("pivot", [0, 0, 0]))
        for bone in bones
    }
    parents = {
        bone["name"]: bone["parent"]
        for bone in bones if "parent" in bone
    }
    return bones, pivots, parents


def build_rig(
    bones: list[dict],
    pivots: dict[str, Vector],
    parents: dict[str, str],
    collection: bpy.types.Collection,
    scale: float,
) -> tuple[bpy.types.Object, dict[str, bpy.types.Object]]:
    master = bpy.data.objects.new("EVA_MOTION_LAB_ROOT", None)
    master.empty_display_type = "PLAIN_AXES"
    master.scale = (scale, scale, scale)
    collection.objects.link(master)

    controls = {}
    for bone in bones:
        name = bone["name"]
        control = bpy.data.objects.new(f"BONE::{name}", None)
        control.empty_display_type = "ARROWS"
        control.empty_display_size = 2.4
        collection.objects.link(control)
        parent_name = parents.get(name)
        if parent_name is None:
            control.parent = master
            local = pivots[name]
        else:
            control.parent = controls[parent_name]
            local = pivots[name] - pivots[parent_name]
        control.location = target_to_blender(local)
        control.rotation_mode = "QUATERNION"
        control.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        controls[name] = control
    return master, controls


def build_mesh_parts(
    path: Path,
    controls: dict[str, bpy.types.Object],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> list[bpy.types.Object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stride = int(payload["stride"])
    if stride != 8:
        raise ValueError(f"unsupported local mesh stride {stride}")
    objects = []
    for bone_name, part in payload["parts"].items():
        if bone_name not in controls:
            raise ValueError(f"mesh part has no target bone: {bone_name}")
        values = [float(value) for value in part["vertices"]]
        vertices = []
        uvs = []
        for index in range(0, len(values), stride):
            # Mesh values are relative to the raw Bedrock pivot. Gecko emits
            # X reflected; the parent control already sits at reflected pivot.
            local_runtime = Vector((-values[index], values[index + 1],
                                    values[index + 2]))
            vertices.append(tuple(target_to_blender(local_runtime)))
            uvs.append((values[index + 3], 1.0 - values[index + 4]))
        faces = [tuple(range(index, index + 3))
                 for index in range(0, len(vertices), 3)]
        mesh = bpy.data.meshes.new(f"MESH::{bone_name}")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        uv_layer = mesh.uv_layers.new(name="UVMap")
        for polygon in mesh.polygons:
            polygon.use_smooth = False
            for loop_index in polygon.loop_indices:
                uv_layer.data[loop_index].uv = uvs[mesh.loops[loop_index].vertex_index]
        obj = bpy.data.objects.new(f"PART::{bone_name}", mesh)
        collection.objects.link(obj)
        obj.parent = controls[bone_name]
        obj.location = (0.0, 0.0, 0.0)
        obj.data.materials.append(material)
        objects.append(obj)
    return objects


def make_contact_marker(name: str, color: tuple[float, float, float, float],
                        foot: bpy.types.Object,
                        collection: bpy.types.Collection) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=2.2)
    marker = bpy.context.object
    marker.name = name
    move_to_collection(marker, collection)
    marker.parent = foot
    marker.location = (0.0, 0.0, -18.2)
    material = bpy.data.materials.new(f"MAT::{name}")
    material.diffuse_color = color
    material.use_nodes = True
    shader = principled_node(material)
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Emission Color" if "Emission Color" in shader.inputs else "Emission"].default_value = color
    shader.inputs["Emission Strength"].default_value = 2.5
    marker.data.materials.append(material)
    return marker


def animate_sequence(
    motion: dict,
    controls: dict[str, bpy.types.Object],
    contacts: dict[str, tuple[bpy.types.Object, bpy.types.Object]],
    gap_frames: int,
) -> tuple[int, dict[str, tuple[int, int]]]:
    scene = bpy.context.scene
    sample_rate = float(motion["sample_rate"])
    scene.render.fps = int(round(sample_rate))
    scene.render.fps_base = 1.0
    db_bones = list(motion["bones"])
    sequence = [name for name in CORE_SEQUENCE if name in motion["clips"]]
    sequence.extend(sorted(set(motion["clips"]) - set(sequence)))
    frame_cursor = 1
    ranges = {}
    root = controls["root"]

    for clip_name in sequence:
        clip = motion["clips"][clip_name]
        start = frame_cursor
        scene.timeline_markers.new(clip_name.upper(), frame=start)
        for local_frame, frame_data in enumerate(clip["frames"]):
            frame = start + local_frame
            for bone_index, bone_name in enumerate(db_bones):
                control = controls.get(bone_name)
                if control is None:
                    continue
                control.rotation_quaternion = quaternion_to_blender(
                    frame_data["rotation_wxyz"][bone_index]
                )
                control.keyframe_insert("rotation_quaternion", frame=frame,
                                        group=clip_name)
            root_m = Vector(tuple(float(value)
                                  for value in frame_data["root_m"]))
            # Same scale as the Java evaluator. Gecko reflects animated X.
            root_runtime = Vector((-root_m.x, root_m.y, root_m.z)) * 112.0
            root.location = target_to_blender(root_runtime)
            root.keyframe_insert("location", frame=frame, group=clip_name)

            for side, contact in zip(("l", "r"), frame_data["foot_contact"]):
                green, red = contacts[side]
                green.hide_viewport = green.hide_render = not bool(contact)
                red.hide_viewport = red.hide_render = bool(contact)
                for marker in (green, red):
                    marker.keyframe_insert("hide_viewport", frame=frame,
                                           group=clip_name)
                    marker.keyframe_insert("hide_render", frame=frame,
                                           group=clip_name)
        end = start + len(clip["frames"]) - 1
        ranges[clip_name] = (start, end)
        frame_cursor = end + gap_frames + 1

    for obj in (*controls.values(),
                *(marker for pair in contacts.values() for marker in pair)):
        if obj.animation_data is None or obj.animation_data.action is None:
            continue
        for curve in iter_action_fcurves(obj.animation_data.action):
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"
    scene.frame_start = 1
    scene.frame_end = max(1, frame_cursor - gap_frames - 1)
    scene.frame_set(1)
    return scene.frame_end, ranges


def add_source_human(path: Path, ranges: dict[str, tuple[int, int]],
                     collection: bpy.types.Collection) -> None:
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    for obj in imported:
        move_to_collection(obj, collection)
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise ValueError(f"expected one source armature, found {len(armatures)}")
    armature = armatures[0]
    armature.name = "CC0_HUMAN_SOURCE"
    armature.location.x = -15.0
    armature.scale = (5.5, 5.5, 5.5)
    armature.animation_data_create()
    armature.animation_data.action = None
    track = armature.animation_data.nla_tracks.new()
    track.name = "CC0 Source Actions"
    for clip_name, (start, _end) in ranges.items():
        source_action = None
        for action in bpy.data.actions:
            if action.name == {
                "idle": "Idle_Loop_Armature",
                "walk": "Walk_Loop_Armature",
                "formal_walk": "Walk_Formal_Loop_Armature",
                "jog": "Jog_Fwd_Loop_Armature",
                "sprint": "Sprint_Loop_Armature",
                "crouch_idle": "Crouch_Idle_Loop_Armature",
                "crouch_walk": "Crouch_Fwd_Loop_Armature",
                "jump_start": "Jump_Start_Armature",
                "jump_loop": "Jump_Loop_Armature",
                "jump_land": "Jump_Land_Armature",
                "punch_jab": "Punch_Jab_Armature",
                "punch_cross": "Punch_Cross_Armature",
                "knife_idle": "Sword_Idle_Armature",
                "knife_attack": "Sword_Attack_Armature",
                "rifle_idle": "Pistol_Idle_Loop_Armature",
                "rifle_shoot": "Pistol_Shoot_Armature",
            }.get(clip_name):
                source_action = action
                break
        if source_action is None:
            continue
        strip = track.strips.new(clip_name, start, source_action)
        strip.extrapolation = "NOTHING"
        strip.blend_type = "REPLACE"


def add_stage(collection: bpy.types.Collection) -> None:
    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.object
    floor.name = "LAB_FLOOR"
    move_to_collection(floor, collection)
    mat = bpy.data.materials.new("MAT::Floor")
    mat.diffuse_color = (0.025, 0.035, 0.05, 1.0)
    mat.metallic = 0.25
    mat.roughness = 0.48
    floor.data.materials.append(mat)

    bpy.ops.object.light_add(type="AREA", location=(5.0, -8.0, 15.0))
    key = bpy.context.object
    key.name = "KEY_LIGHT"
    key.data.energy = 1800.0
    key.data.shape = "DISK"
    key.data.size = 8.0
    move_to_collection(key, collection)

    bpy.ops.object.light_add(type="AREA", location=(-10.0, 5.0, 8.0))
    fill = bpy.context.object
    fill.name = "FILL_LIGHT"
    fill.data.energy = 900.0
    fill.data.size = 10.0
    move_to_collection(fill, collection)

    bpy.ops.object.camera_add(location=(18.0, -24.0, 10.0),
                              rotation=(math.radians(67.0), 0.0,
                                        math.radians(36.0)))
    camera = bpy.context.object
    camera.name = "REVIEW_CAMERA"
    camera.data.lens = 58.0
    move_to_collection(camera, collection)
    bpy.context.scene.camera = camera


def add_readme(motion: dict, ranges: dict[str, tuple[int, int]]) -> None:
    text = bpy.data.texts.new("README_EVA_MOTION_LAB")
    text.write(
        "Project SEELE EVA Motion Lab V2\n\n"
        "Rotate freely in the 3D viewport; timeline markers select clips.\n"
        "Green foot marker = authored contact; red = swing/airborne.\n"
        "EVA mesh is the exact local runtime triangle mesh.\n"
        "Human reference is Quaternius CC0 when bundled.\n\n"
    )
    for name, frame_range in ranges.items():
        text.write(f"{name}: frames {frame_range[0]}..{frame_range[1]}\n")
    text.write("\nSources:\n")
    for source in motion.get("sources", []):
        text.write(f"- {source['name']} — {source['license']} — {source['url']}\n")


def main() -> None:
    args = parse_args()
    for path in (args.mesh, args.geo, args.texture, args.motion_db):
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    reset_scene()
    scene = bpy.context.scene
    scene.world.color = (0.008, 0.012, 0.02)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        scene.view_settings.look = "Medium High Contrast"

    stage = make_collection("00_STAGE")
    rig_collection = make_collection("10_EVA_RUNTIME_RIG")
    mesh_collection = make_collection("20_EVA_BODY_MESH")
    contact_collection = make_collection("30_CONTACT_DEBUG")
    source_collection = make_collection("40_CC0_HUMAN_REFERENCE")
    add_stage(stage)

    bones, pivots, parents = load_geo(args.geo)
    _master, controls = build_rig(
        bones, pivots, parents, rig_collection, args.display_scale
    )
    material = make_material(args.texture)
    build_mesh_parts(args.mesh, controls, mesh_collection, material)
    contacts = {
        side: (
            make_contact_marker(f"CONTACT_{side.upper()}_PLANTED",
                                (0.05, 1.0, 0.18, 1.0),
                                controls[f"foot_{side}"], contact_collection),
            make_contact_marker(f"CONTACT_{side.upper()}_AIR",
                                (1.0, 0.05, 0.03, 1.0),
                                controls[f"foot_{side}"], contact_collection),
        )
        for side in ("l", "r")
    }
    motion = json.loads(args.motion_db.read_text(encoding="utf-8"))
    frame_end, ranges = animate_sequence(
        motion, controls, contacts, args.gap_frames
    )
    if args.source_human is not None and args.source_human.is_file():
        add_source_human(args.source_human, ranges, source_collection)
    add_readme(motion, ranges)

    scene["project_seele_motion_lab"] = True
    scene["motion_schema"] = int(motion["schema"])
    scene["clip_count"] = len(motion["clips"])
    scene["frame_end"] = frame_end
    scene.tool_settings.use_keyframe_insert_auto = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(
        f"EVA 3D motion lab: clips={len(ranges)} frames={frame_end} "
        f"objects={len(scene.objects)} output={args.output}"
    )


if __name__ == "__main__":
    main()
