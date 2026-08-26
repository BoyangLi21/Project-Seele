#!/usr/bin/env python3
"""Compare a composed EVA action segment against its source action."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--composed-start", required=True, type=int)
    parser.add_argument("--reference-start", required=True, type=int)
    parser.add_argument("--count", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def load_action(path):
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (source, loaded):
        matches = [name for name in source.actions
                   if "ANATOMICAL_FISTS" in name.upper()]
        loaded.actions = matches
    return loaded.actions[0]


def sample(rig, action, frame):
    rig.animation_data.action = action
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {
        bone.name: (bone.matrix_basis.to_quaternion().normalized(),
                    bone.matrix_basis.translation.copy())
        for bone in rig.pose.bones
    }


def main():
    parsed = args()
    rig = bpy.data.objects["EVA_ANATOMICAL_ARMATURE"]
    composed = rig.animation_data.action
    reference = load_action(parsed.reference)
    rotations = {}
    locations = {}
    for offset in range(parsed.count):
        first = sample(rig, composed, parsed.composed_start + offset)
        second = sample(rig, reference, parsed.reference_start + offset)
        for name in first:
            rotations.setdefault(name, []).append(math.degrees(
                first[name][0].rotation_difference(second[name][0]).angle))
            locations.setdefault(name, []).append(
                (first[name][1] - second[name][1]).length)
    report = {
        "rotation_max_degrees": {name: max(values)
                                 for name, values in rotations.items()},
        "rotation_range_degrees": {
            name: max(values) - min(values) for name, values in rotations.items()
        },
        "location_delta_range": {
            name: max(values) - min(values) for name, values in locations.items()
        },
    }
    parsed.output.parent.mkdir(parents=True, exist_ok=True)
    parsed.output.write_text(json.dumps(report, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps({
        "rotation_top": sorted(report["rotation_max_degrees"].items(),
                               key=lambda row: row[1], reverse=True)[:10],
        "location_top": sorted(report["location_delta_range"].items(),
                               key=lambda row: row[1], reverse=True)[:10],
        "rotation_range_top": sorted(
            report["rotation_range_degrees"].items(),
            key=lambda row: row[1], reverse=True)[:10],
    }, indent=2))


main()
