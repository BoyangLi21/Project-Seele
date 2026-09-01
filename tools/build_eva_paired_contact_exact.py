#!/usr/bin/env python3
"""Build an exact two-Tiger review scene for synchronized contact mocap."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_eva_motion_lab_3d import (
    add_readme,
    add_stage,
    load_geo,
    make_collection,
    make_material,
    principled_node,
    reset_scene,
)
from build_eva_motion_lab_armature import geometry_bind_rotations
from build_eva_motion_lab_exact import (
    animate_exact,
    build_parts,
    make_contact_marker,
    make_joint,
    validate_body_texture_dimensions,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--texture", required=True, type=Path)
    parser.add_argument("--attacker-db", required=True, type=Path)
    parser.add_argument("--target-db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--clip", default="eva_contact_combo_hold_demo")
    parser.add_argument("--display-scale", type=float, default=0.05)
    parser.add_argument("--target-master-y", type=float, default=0.0)
    parser.add_argument("--target-master-yaw-degrees", type=float,
                        default=0.0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def solid_material(name: str, color: tuple[float, float, float, float]):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = principled_node(material)
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = 0.78
    return material


def contact_sets(prefix: str, master, collection):
    feet = {
        side: (
            make_contact_marker(
                f"{prefix}CONTACT_{side.upper()}_PLANTED",
                (0.05, 1.0, 0.18, 1.0), master, collection),
            make_contact_marker(
                f"{prefix}CONTACT_{side.upper()}_AIR",
                (1.0, 0.05, 0.03, 1.0), master, collection),
        ) for side in ("l", "r")
    }
    hands = {
        side: (
            make_contact_marker(
                f"{prefix}HAND_{side.upper()}_CONTACT",
                (0.05, 0.85, 1.0, 1.0), master, collection),
            make_contact_marker(
                f"{prefix}HAND_{side.upper()}_FREE",
                (1.0, 0.05, 0.75, 1.0), master, collection),
        ) for side in ("l", "r")
    }
    return feet, hands


def one_clip(document: dict, clip_name: str) -> dict:
    clip = document["clips"].get(clip_name)
    if clip is None:
        raise RuntimeError("paired database is missing contact-combo demo")
    output = dict(document)
    output["clips"] = {clip_name: clip}
    return output


def main() -> None:
    args = parse_args()
    for path in (args.mesh, args.geo, args.texture,
                 args.attacker_db, args.target_db):
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    attacker = one_clip(json.loads(
        args.attacker_db.read_text(encoding="utf-8")), args.clip)
    target = one_clip(json.loads(
        args.target_db.read_text(encoding="utf-8")), args.clip)
    if len(attacker["clips"][args.clip]["frames"]) \
            != len(target["clips"][args.clip]["frames"]):
        raise RuntimeError("paired databases have different frame counts")

    reset_scene()
    texture_dimensions = validate_body_texture_dimensions(
        args.geo, args.texture)
    scene = bpy.context.scene
    scene.world.color = (0.008, 0.012, 0.02)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    stage = make_collection("00_STAGE")
    attacker_collection = make_collection("10_ATTACKER_EXACT_MESH")
    target_collection = make_collection("11_TARGET_EXACT_MESH")
    attacker_joints_collection = make_collection("20_ATTACKER_JOINTS")
    target_joints_collection = make_collection("21_TARGET_JOINTS")
    contact_collection = make_collection("30_CONTACT_DEBUG")
    add_stage(stage)

    bones, pivots, parents = load_geo(args.geo)
    bone_order = [bone["name"] for bone in bones]
    bind_rotations = geometry_bind_rotations(bones)
    attacker_master = bpy.data.objects.new("EVA_EXACT_ROOT", None)
    attacker_master.scale = (args.display_scale,) * 3
    attacker_collection.objects.link(attacker_master)
    target_master = bpy.data.objects.new("TARGET::EVA_EXACT_ROOT", None)
    target_master.scale = (args.display_scale,) * 3
    target_master.location.y = args.target_master_y
    target_master.rotation_euler[2] = math.radians(
        args.target_master_yaw_degrees)
    target_collection.objects.link(target_master)

    attacker_parts = build_parts(
        args.mesh, attacker_master, attacker_collection,
        make_material(args.texture))
    target_parts = build_parts(
        args.mesh, target_master, target_collection,
        solid_material("TARGET_PROXY_RED", (0.24, 0.035, 0.045, 1.0)),
        name_prefix="TARGET::")
    attacker_joints = {
        name: make_joint(name, pivot, attacker_master,
                         attacker_joints_collection)
        for name, pivot in pivots.items()
    }
    target_joints = {
        name: make_joint(name, pivot, target_master,
                         target_joints_collection, name_prefix="TARGET::")
        for name, pivot in pivots.items()
    }
    attacker_contacts, attacker_hands = contact_sets(
        "A::", attacker_master, contact_collection)
    target_contacts, target_hands = contact_sets(
        "B::", target_master, contact_collection)

    attacker_ranges = animate_exact(
        attacker, bone_order, pivots, parents, bind_rotations,
        attacker_parts, attacker_joints, attacker_contacts, attacker_hands,
        gap_frames=0)
    target_ranges = animate_exact(
        target, bone_order, pivots, parents, bind_rotations,
        target_parts, target_joints, target_contacts, target_hands,
        gap_frames=0)
    if attacker_ranges != target_ranges:
        raise RuntimeError("paired exact animation ranges differ")
    add_readme(attacker, attacker_ranges)
    contact_collection.hide_render = True
    attacker_joints_collection.hide_render = True
    target_joints_collection.hide_render = True
    scene["project_seele_paired_contact_lab"] = True
    scene["clip_count"] = 1
    scene["body_texture_dimensions"] = texture_dimensions
    scene["attacker_motion_db_sha256"] = hashlib.sha256(
        args.attacker_db.read_bytes()).hexdigest()
    scene["target_motion_db_sha256"] = hashlib.sha256(
        args.target_db.read_bytes()).hexdigest()
    scene.frame_set(1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(json.dumps({
        "frames": scene.frame_end,
        "attackerParts": len(attacker_parts),
        "targetParts": len(target_parts),
        "attackerJoints": len(attacker_joints),
        "targetJoints": len(target_joints),
        "output": str(args.output.resolve()),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
