#!/usr/bin/env python3
"""Convert a blended stance change into one planted foot plus one real step."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--end", required=True, type=int)
    parser.add_argument("--support", choices=("left", "right"), required=True)
    parser.add_argument("--lift-bh", type=float, default=0.025)
    parser.add_argument("--root-curve", choices=("exact", "smooth"),
                        default="smooth")
    parser.add_argument("--maximum-leg-extension", type=float, default=0.985)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def head(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].head


def iter_fcurves(action):
    if hasattr(action, "fcurves"):
        yield from action.fcurves
        return
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                yield from channelbag.fcurves


def main():
    args = parse_args()
    scene = bpy.context.scene
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    if not (scene.frame_start <= args.start < args.end <= scene.frame_end):
        raise SystemExit("transition range outside action")
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    samples = {side: [] for side in ("l", "r")}
    authority_root = "world_root" if "world_root" in rig.pose.bones else "root"
    root_matrices = []
    heights = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        root_matrices.append(rig.pose.bones[authority_root].matrix.copy())
        for side in ("l", "r"):
            samples[side].append({
                "hip": head(rig, f"leg_{side}"),
                "knee": head(rig, f"shin_{side}"),
                "ankle": head(rig, f"foot_{side}"),
                "foot_rotation": (
                    rig.matrix_world @ rig.pose.bones[f"foot_{side}"].matrix
                ).to_quaternion(),
            })
        heights.append(head(rig, "head").z - min(
            samples["l"][-1]["ankle"].z,
            samples["r"][-1]["ankle"].z))
    height = float(np.median(heights))
    lift = max(0.0, args.lift_bh) * height
    support = "l" if args.support == "left" else "r"
    moving = "r" if support == "l" else "l"
    start_index = args.start - scene.frame_start
    support_anchor = samples[support][start_index]["ankle"].copy()
    root_corrections = []
    end_index = args.end - scene.frame_start
    end_correction = support_anchor - samples[support][end_index]["ankle"]
    end_correction.z = 0.0
    for frame, index in zip(frames, range(len(frames))):
        if frame < args.start:
            correction = Vector((0.0, 0.0, 0.0))
        elif frame <= args.end:
            if args.root_curve == "exact":
                correction = support_anchor - samples[support][index]["ankle"]
                correction.z = 0.0
            else:
                phase = ((frame - args.start)
                         / max(1, args.end - args.start))
                phase = phase * phase * (3.0 - 2.0 * phase)
                correction = end_correction * phase
        else:
            correction = end_correction.copy()
        root_corrections.append(correction)

    collection = bpy.data.collections.new("EVA_COMBAT_STEP_HELPERS")
    scene.collection.children.link(collection)
    helpers = {}
    constraints = {}
    for side in ("l", "r"):
        ankle_target = bpy.data.objects.new(f"STEP_ANKLE_{side}", None)
        pole_target = bpy.data.objects.new(f"STEP_POLE_{side}", None)
        collection.objects.link(ankle_target)
        collection.objects.link(pole_target)
        helpers[side] = (ankle_target, pole_target)
        ik = rig.pose.bones[f"shin_{side}"].constraints.new("IK")
        ik.name = f"SEELE_COMBAT_STEP_{side}"
        ik.target = ankle_target
        ik.pole_target = pole_target
        ik.chain_count = 2
        ik.use_stretch = False
        ik.iterations = 128
        copy_rotation = rig.pose.bones[f"foot_{side}"].constraints.new(
            "COPY_ROTATION")
        copy_rotation.name = f"SEELE_COMBAT_STEP_ROTATION_{side}"
        copy_rotation.target = ankle_target
        copy_rotation.owner_space = "WORLD"
        copy_rotation.target_space = "WORLD"
        copy_rotation.mix_mode = "REPLACE"
        constraints[side] = (ik, copy_rotation)

    # One bend sign for the whole step prevents an IK branch flip.
    bend_sign = {}
    for side in ("l", "r"):
        dots = []
        for index in range(start_index, args.end - scene.frame_start + 1):
            sample = samples[side][index]
            axis = sample["ankle"] - sample["hip"]
            projection = sample["hip"] + axis * (
                (sample["knee"] - sample["hip"]).dot(axis)
                / max(axis.length_squared, 1.0e-9))
            bend = sample["knee"] - projection
            lateral = samples["r"][index]["hip"] - samples["l"][index]["hip"]
            lateral.z = 0.0
            if bend.length > 1.0e-7 and lateral.length > 1.0e-7:
                lateral.normalize()
                forward = Vector((-lateral.y, lateral.x, 0.0))
                dots.append(bend.dot(forward))
        bend_sign[side] = 1.0 if not dots or float(np.median(dots)) >= 0 else -1.0

    pole_angles = {}
    scene.frame_set(args.start)
    bpy.context.view_layer.update()
    for side in ("l", "r"):
        ankle_target, pole_target = helpers[side]
        ik, copy_rotation = constraints[side]
        sample = samples[side][start_index]
        ankle_target.location = sample["ankle"]
        ankle_target.rotation_mode = "QUATERNION"
        ankle_target.rotation_quaternion = sample["foot_rotation"]
        axis = sample["ankle"] - sample["hip"]
        lateral = (samples["r"][start_index]["hip"]
                   - samples["l"][start_index]["hip"])
        lateral.z = 0.0
        lateral.normalize()
        forward = Vector((-lateral.y, lateral.x, 0.0))
        outward = -lateral if side == "l" else lateral
        bend = forward * bend_sign[side] + outward * 0.05
        if axis.length > 1.0e-7:
            axis.normalize()
            bend -= axis * bend.dot(axis)
        bend.normalize()
        leg_length = ((sample["knee"] - sample["hip"]).length
                      + (sample["ankle"] - sample["knee"]).length)
        pole_target.location = sample["knee"] + bend * leg_length * 1.5
        copy_rotation.influence = 1.0
        ik.influence = 1.0
        best_angle = 0.0
        best_error = float("inf")
        for angle_value in np.linspace(-math.pi, math.pi, 145):
            ik.pole_angle = float(angle_value)
            bpy.context.view_layer.update()
            error = (head(rig, f"shin_{side}") - sample["knee"]).length
            if error < best_error:
                best_error = error
                best_angle = float(angle_value)
        ik.pole_angle = best_angle
        ik.influence = 0.0
        copy_rotation.influence = 0.0
        pole_angles[side] = best_angle

    for frame, index in zip(frames, range(len(frames))):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        root_bone = rig.pose.bones[authority_root]
        root_matrix = root_matrices[index].copy()
        root_matrix.translation += (
            rig.matrix_world.to_3x3().inverted()
            @ root_corrections[index])
        root_bone.matrix = root_matrix
        root_bone.keyframe_insert("location", frame=frame)
        root_bone.keyframe_insert("rotation_quaternion", frame=frame)
        root_bone.keyframe_insert("scale", frame=frame)
        bpy.context.view_layer.update()
        active = args.start <= frame <= args.end
        phase = ((frame - args.start) / max(1, args.end - args.start)
                 if active else 0.0)
        for side in ("l", "r"):
            ankle_target, pole_target = helpers[side]
            ik, copy_rotation = constraints[side]
            sample = samples[side][index]
            desired = sample["ankle"] + root_corrections[index]
            if active and side == support:
                desired = support_anchor.copy()
            elif active and side == moving:
                desired.z += lift * math.sin(math.pi * phase) ** 2
            ankle_target.location = desired
            ankle_target.rotation_mode = "QUATERNION"
            ankle_target.rotation_quaternion = sample["foot_rotation"]

            corrected_hip = sample["hip"] + root_corrections[index]
            corrected_knee = sample["knee"] + root_corrections[index]
            leg_length = ((sample["knee"] - sample["hip"]).length
                          + (sample["ankle"] - sample["knee"]).length)
            maximum_reach = min(0.999, max(
                0.80, args.maximum_leg_extension)) * leg_length
            reach = desired - corrected_hip
            if reach.length > maximum_reach:
                desired = corrected_hip + reach.normalized() * maximum_reach
                ankle_target.location = desired
            axis = desired - corrected_hip
            lateral = samples["r"][index]["hip"] - samples["l"][index]["hip"]
            lateral.z = 0.0
            if lateral.length < 1.0e-7:
                lateral = Vector((1.0, 0.0, 0.0))
            lateral.normalize()
            forward = Vector((-lateral.y, lateral.x, 0.0))
            outward = -lateral if side == "l" else lateral
            bend = forward * bend_sign[side] + outward * 0.05
            if axis.length > 1.0e-7:
                axis.normalize()
                bend -= axis * bend.dot(axis)
            if bend.length < 1.0e-7:
                bend = forward
            bend.normalize()
            pole_target.location = corrected_knee + bend * leg_length * 1.5
            constraint_active = frame >= args.start
            ik.influence = 1.0 if constraint_active else 0.0
            copy_rotation.influence = 1.0 if constraint_active else 0.0
            ankle_target.keyframe_insert("location", frame=frame)
            ankle_target.keyframe_insert("rotation_quaternion", frame=frame)
            pole_target.keyframe_insert("location", frame=frame)
            ik.keyframe_insert("influence", frame=frame)
            copy_rotation.keyframe_insert("influence", frame=frame)

    for side in ("l", "r"):
        for helper in helpers[side]:
            for curve in iter_fcurves(helper.animation_data.action):
                for key in curve.keyframe_points:
                    key.interpolation = "LINEAR"
    for curve in iter_fcurves(rig.animation_data.action):
        for key in curve.keyframe_points:
            key.interpolation = (
                "CONSTANT" if "constraints[" in curve.data_path
                else "LINEAR")

    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.nla.bake(frame_start=scene.frame_start, frame_end=scene.frame_end,
                     step=1, only_selected=False, visual_keying=True,
                     clear_constraints=True, use_current_action=True,
                     clean_curves=False, bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    for pair in helpers.values():
        for helper in pair:
            bpy.data.objects.remove(helper, do_unlink=True)
    bpy.data.collections.remove(collection)
    report = {
        "schema": 1, "frames": [args.start, args.end],
        "support": args.support,
        "moving": "right" if args.support == "left" else "left",
        "lift_body_heights": args.lift_bh,
        "body_height_units": height,
        "root_correction_end_body_heights": end_correction.length / height,
        "root_curve": args.root_curve,
        "maximum_leg_extension": args.maximum_leg_extension,
        "pole_angles_degrees": {
            side: math.degrees(value) for side, value in pole_angles.items()
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(json.dumps(report, indent=2))


main()
