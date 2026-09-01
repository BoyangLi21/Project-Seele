#!/usr/bin/env python3
"""Audit free Mixamo-rig FBX combat takes without visually approving them.

The report locates separated wrist-speed peaks and records finger extension,
trajectory and body-relative position.  It is a source-screening aid: an open
palm or downward knife path may become eligible for retargeting, but the report
does not claim that the resulting EVA motion is visually acceptable.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--peak-count", type=int, default=24)
    parser.add_argument("--minimum-separation-seconds", type=float,
                        default=0.45)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def world_head(rig: bpy.types.Object, name: str) -> Vector:
    return rig.matrix_world @ rig.pose.bones[name].head


def world_tail(rig: bpy.types.Object, name: str) -> Vector:
    return rig.matrix_world @ rig.pose.bones[name].tail


def moving_average(values: list[float], radius: int) -> list[float]:
    prefix = [0.0]
    for value in values:
        prefix.append(prefix[-1] + value)
    output = []
    for index in range(len(values)):
        left = max(0, index - radius)
        right = min(len(values), index + radius + 1)
        output.append((prefix[right] - prefix[left]) / (right - left))
    return output


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    if not source.is_file() or source.suffix.lower() != ".fbx":
        raise SystemExit(f"expected an FBX source: {source}")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(
        filepath=str(source), automatic_bone_orientation=False,
    )
    armatures = [obj for obj in bpy.context.scene.objects
                 if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise SystemExit(f"expected one armature, found {len(armatures)}")
    rig = armatures[0]
    action = rig.animation_data.action if rig.animation_data else None
    if action is None:
        raise SystemExit("source armature has no active action")

    available_bones = set(rig.pose.bones.keys())
    if "mixamorig:Hips" in available_bones:
        prefix = "mixamorig:"
    elif "Hips" in available_bones:
        prefix = ""
    else:
        raise SystemExit("source is not a supported Mixamo hierarchy")
    required = {
        prefix + name for name in (
            "Hips", "Spine2", "LeftUpLeg", "RightUpLeg",
            "LeftForeArm", "LeftHand", "RightForeArm", "RightHand",
            "LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3",
            "LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3",
            "LeftHandRing1", "LeftHandRing2", "LeftHandRing3",
            "LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3",
            "RightHandIndex1", "RightHandIndex2", "RightHandIndex3",
            "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3",
            "RightHandRing1", "RightHandRing2", "RightHandRing3",
            "RightHandPinky1", "RightHandPinky2", "RightHandPinky3",
        )
    }
    missing = sorted(required - available_bones)
    if missing:
        raise SystemExit("missing Mixamo bones: " + ", ".join(missing))

    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    first = int(math.ceil(action.frame_range[0]))
    last = int(math.floor(action.frame_range[1]))
    frames = list(range(first, last + 1))
    scene.frame_set(first)
    bpy.context.view_layer.update()

    up = Vector((0.0, 0.0, 1.0))
    left = (world_head(rig, prefix + "LeftUpLeg")
            - world_head(rig, prefix + "RightUpLeg"))
    left -= up * left.dot(up)
    left.normalize()
    forward = left.cross(up).normalized()
    body_height = (
        world_tail(rig, prefix + "Head").z
        - min(world_head(rig, prefix + "LeftFoot").z,
              world_head(rig, prefix + "RightFoot").z)
    )
    if body_height <= 1.0e-8:
        raise SystemExit("invalid source body height")

    fingers = ("Index", "Middle", "Ring", "Pinky")
    chain_lengths: dict[str, dict[str, float]] = {"l": {}, "r": {}}
    for side, label in (("l", "Left"), ("r", "Right")):
        hand = rig.data.bones[prefix + label + "Hand"]
        for finger in fingers:
            chain = [rig.data.bones[prefix + label + "Hand" + finger + str(i)]
                     for i in (1, 2, 3)]
            chain_lengths[side][finger] = (
                (rig.matrix_world @ chain[0].head_local
                 - rig.matrix_world @ hand.head_local).length
                + sum((rig.matrix_world @ bone.tail_local
                       - rig.matrix_world @ bone.head_local).length
                      for bone in chain)
            )

    positions: dict[str, list[Vector]] = {"l": [], "r": []}
    thorax: list[Vector] = []
    openness: dict[str, list[float]] = {"l": [], "r": []}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        thorax.append(world_head(rig, prefix + "Spine2"))
        for side, label in (("l", "Left"), ("r", "Right")):
            wrist = world_head(rig, prefix + label + "Hand")
            positions[side].append(wrist)
            ratios = []
            for finger in fingers:
                tip = world_tail(
                    rig, prefix + label + "Hand" + finger + "3"
                )
                ratios.append((tip - wrist).length
                              / chain_lengths[side][finger])
            openness[side].append(sum(ratios) / len(ratios))

    speeds: dict[str, list[float]] = {"l": [0.0], "r": [0.0]}
    for side in ("l", "r"):
        speeds[side].extend(
            (positions[side][index] - positions[side][index - 1]).length
            * fps / body_height
            for index in range(1, len(frames))
        )
    energy = moving_average([
        max(speeds["l"][index], speeds["r"][index])
        for index in range(len(frames))
    ], max(1, int(round(fps * 0.055))))

    separation = max(1, int(round(
        args.minimum_separation_seconds * fps
    )))
    padding = max(2, int(round(fps * 0.18)))
    selected: list[int] = []
    for index in sorted(range(len(frames)), key=energy.__getitem__,
                        reverse=True):
        if index < padding or index >= len(frames) - padding:
            continue
        if any(abs(index - existing) < separation for existing in selected):
            continue
        selected.append(index)
        if len(selected) >= args.peak_count:
            break
    selected.sort()

    def canonical(vector: Vector) -> list[float]:
        return [round(vector.dot(forward) / body_height, 6),
                round(vector.dot(left) / body_height, 6),
                round(vector.dot(up) / body_height, 6)]

    peaks = []
    for index in selected:
        side = "l" if speeds["l"][index] > speeds["r"][index] else "r"
        delta = positions[side][index + padding] \
            - positions[side][index - padding]
        instantaneous = (positions[side][index + 1]
                         - positions[side][index - 1]) * (fps * 0.5)
        relative = positions[side][index] - thorax[index]
        minimum_offset = max(2, int(round(fps * 0.18)))
        before_range = range(
            max(0, index - int(round(fps * 1.20))),
            max(1, index - minimum_offset + 1),
        )
        after_range = range(
            min(len(frames) - 1, index + minimum_offset),
            min(len(frames), index + int(round(fps * 1.40)) + 1),
        )
        window_start = min(before_range, key=energy.__getitem__)
        window_end = min(after_range, key=energy.__getitem__)
        peaks.append({
            "frame": frames[index],
            "seconds": round((frames[index] - first) / fps, 5),
            "primary_hand": side,
            "smoothed_wrist_speed_body_heights_per_second": round(
                energy[index], 6
            ),
            "primary_hand_openness": round(openness[side][index], 6),
            "other_hand_openness": round(
                openness["r" if side == "l" else "l"][index], 6
            ),
            "trajectory_forward_left_up_body_heights": canonical(delta),
            "instantaneous_velocity_forward_left_up_body_heights_per_second":
                canonical(instantaneous),
            "wrist_from_thorax_forward_left_up_body_heights": canonical(
                relative
            ),
            "recommended_window": {
                "start_frame": frames[window_start],
                "end_frame": frames[window_end],
                "duration_seconds": round(
                    (window_end - window_start) / fps, 5
                ),
                "start_energy": round(energy[window_start], 6),
                "end_energy": round(energy[window_end], 6),
            },
        })

    report = {
        "schema": 1,
        "source": str(source),
        "action": action.name,
        "fps": fps,
        "frame_range": [first, last],
        "body_height_source_units": body_height,
        "peak_count": len(peaks),
        "peaks": peaks,
        "status": "SOURCE_SCREENING_ONLY_NOT_VISUALLY_APPROVED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "source": source.name,
        "frames": len(frames),
        "fps": fps,
        "peaks": len(peaks),
        "output": str(args.output),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
