#!/usr/bin/env python3
"""Put final composed crouch ankles on opposite sides of the EVA root."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_eva_motion_lab_exact import ranges_from_db
from build_eva_cmu_motion_candidates import runtime_target_pivots
from build_eva_motion_database import (
    clamp,
    load_target_pivots,
    rounded_quaternion,
    solve_target_limb,
)
from build_eva_motion_lab_3d import target_to_blender
from solve_eva_weapon_hand_contacts import blender_to_authored


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gap-frames", type=int, default=12)
    parser.add_argument("--ankle-half-width", type=float, default=18.0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def main() -> None:
    args = parse_args()
    document = json.loads(args.motion_db.read_text(encoding="utf-8"))
    output = copy.deepcopy(document)
    ranges = ranges_from_db(document, args.gap_frames)
    pivots = runtime_target_pivots(load_target_pivots(args.geo))
    bone_indices = {name: index for index, name in enumerate(output["bones"])}
    master_scale = float(bpy.data.objects["EVA_EXACT_ROOT"].scale.x)
    diagnostics = []

    for clip_name in ("crouch_review", "crouch_walk_review"):
        if clip_name not in output["clips"]:
            continue
        timeline_start, _timeline_end = ranges[clip_name]
        for frame_index, frame in enumerate(
                output["clips"][clip_name]["frames"]):
            bpy.context.scene.frame_set(timeline_start + frame_index)
            bpy.context.view_layer.update()
            root = bpy.data.objects["JOINT::root"].matrix_world
            root_origin = root.translation
            root_right = root.to_quaternion() @ Vector((1.0, 0.0, 0.0))
            row = {"clip": clip_name, "frame": frame_index, "sides": {}}
            for side, sign in (("l", -1.0), ("r", 1.0)):
                hip_world = bpy.data.objects[
                    f"JOINT::leg_{side}"].matrix_world.translation
                knee_world = bpy.data.objects[
                    f"JOINT::shin_{side}"].matrix_world.translation
                ankle_world = bpy.data.objects[
                    f"JOINT::ankle_{side}"].matrix_world.translation
                lateral = ((ankle_world - root_origin).dot(root_right)
                           / master_scale)
                desired_lateral = sign * args.ankle_half_width
                desired_world = ankle_world + root_right * (
                    desired_lateral - lateral) * master_scale
                parent_rotation = bpy.data.objects[
                    "JOINT::torso_lower"].matrix_world.to_quaternion()
                vector = (parent_rotation.conjugated()
                          @ (desired_world - hip_world)) / master_scale
                upper_rest = target_to_blender(
                    pivots[f"shin_{side}"] - pivots[f"leg_{side}"])
                lower_rest = target_to_blender(
                    pivots[f"ankle_{side}"] - pivots[f"shin_{side}"])
                direction = vector.normalized()
                current_knee = (parent_rotation.conjugated()
                                @ (knee_world - hip_world)) / master_scale
                pole = current_knee - direction * current_knee.dot(direction)
                if pole.length < 1.0e-6:
                    pole = Vector((sign, 0.0, -0.35))
                leg, shin = solve_target_limb(
                    Vector((0.0, 0.0, 0.0)), upper_rest,
                    upper_rest + lower_rest, direction,
                    clamp(vector.length / (
                        upper_rest.length + lower_rest.length), 0.08, 0.995),
                    pole,
                )
                frame["rotation_wxyz"][bone_indices[f"leg_{side}"]] = \
                    rounded_quaternion(blender_to_authored(leg))
                frame["rotation_wxyz"][bone_indices[f"shin_{side}"]] = \
                    rounded_quaternion(blender_to_authored(shin))
                row["sides"][side] = {
                    "before": round(lateral, 6),
                    "target": round(desired_lateral, 6),
                }
            diagnostics.append(row)

    output["crouch_final_contact_solve"] = {
        "authority": "final_composed_exact_scene_ankle_lateral_ik",
        "ankle_half_width_model_pixels": args.ankle_half_width,
        "frames": diagnostics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA final crouch contact solve: frames={len(diagnostics)} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
