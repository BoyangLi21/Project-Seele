#!/usr/bin/env python3
"""Audit synchronized CMCD actors for real paired-contact source windows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np


EFFECTORS = {
    "hand_l": ("LeftHand", True),
    "hand_r": ("RightHand", True),
    "wrist_l": ("LeftHand", False),
    "wrist_r": ("RightHand", False),
    "elbow_l": ("LeftForeArm", False),
    "elbow_r": ("RightForeArm", False),
    "toe_l": ("LeftToeBase", True),
    "toe_r": ("RightToeBase", True),
    "ankle_l": ("LeftFoot", False),
    "ankle_r": ("RightFoot", False),
}

TARGETS = {
    "head": ("Head", True),
    "neck": ("Neck", False),
    "thorax": ("Spine1", False),
    "pelvis": ("Hips", False),
    "shoulder_l": ("LeftArm", False),
    "shoulder_r": ("RightArm", False),
    "elbow_l": ("LeftForeArm", False),
    "elbow_r": ("RightForeArm", False),
    "wrist_l": ("LeftHand", False),
    "wrist_r": ("RightHand", False),
    "hand_l": ("LeftHand", True),
    "hand_r": ("RightHand", True),
    "knee_l": ("LeftLeg", False),
    "knee_r": ("RightLeg", False),
    "ankle_l": ("LeftFoot", False),
    "ankle_r": ("RightFoot", False),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor-a", required=True, type=Path)
    parser.add_argument("--actor-b", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--pair-name", required=True)
    parser.add_argument("--sample-fps", type=float, default=60.0)
    parser.add_argument("--contact-threshold-H", type=float, default=0.10)
    parser.add_argument("--best-blend", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def import_actor(path: Path, name: str):
    bpy.ops.import_anim.bvh(
        filepath=str(path.resolve()), target="ARMATURE", global_scale=0.01,
        frame_start=1, use_fps_scale=False, update_scene_fps=True,
        update_scene_duration=True, rotate_mode="NATIVE",
        axis_forward="-Z", axis_up="Y",
    )
    actor = bpy.context.object
    actor.name = name
    actor.show_in_front = True
    actor.data.display_type = "STICK"
    return actor


def point(actor, spec):
    bone = actor.pose.bones[spec[0]]
    return actor.matrix_world @ (bone.tail if spec[1] else bone.head)


def contiguous_segments(flags: np.ndarray, minimum_frames: int):
    segments = []
    start = None
    for index, flag in enumerate(flags):
        if flag and start is None:
            start = index
        if start is not None and (not flag or index == len(flags) - 1):
            end = index if flag and index == len(flags) - 1 else index - 1
            if end - start + 1 >= minimum_frames:
                segments.append((start, end))
            start = None
    return segments


def main() -> None:
    args = parse_args()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    actor_a = import_actor(args.actor_a, "CMCD_ACTOR_A")
    range_a = actor_a.animation_data.action.frame_range
    actor_b = import_actor(args.actor_b, "CMCD_ACTOR_B")
    range_b = actor_b.animation_data.action.frame_range
    scene = bpy.context.scene
    native_fps = scene.render.fps / scene.render.fps_base
    end = min(int(math.floor(range_a[1])), int(math.floor(range_b[1])))
    step = native_fps / args.sample_fps
    frames = np.arange(1.0, end + step * 0.25, step, dtype=np.float64)
    frames[-1] = min(frames[-1], float(end))

    distances: dict[str, list[float]] = {}
    root_separation = []
    heights = []
    for frame in frames:
        whole = math.floor(frame)
        scene.frame_set(whole, subframe=frame - whole)
        bpy.context.view_layer.update()
        roots = [point(actor, TARGETS["pelvis"])
                 for actor in (actor_a, actor_b)]
        root_separation.append((roots[0] - roots[1]).length)
        for actor in (actor_a, actor_b):
            heights.append(
                point(actor, TARGETS["head"]).z
                - min(point(actor, TARGETS["ankle_l"]).z,
                      point(actor, TARGETS["ankle_r"]).z)
            )
        for source_label, source_actor, target_label, target_actor in (
            ("a", actor_a, "b", actor_b),
            ("b", actor_b, "a", actor_a),
        ):
            for effector_name, effector_spec in EFFECTORS.items():
                effector = point(source_actor, effector_spec)
                for target_name, target_spec in TARGETS.items():
                    key = (f"{source_label}_{effector_name}_to_"
                           f"{target_label}_{target_name}")
                    distances.setdefault(key, []).append(
                        (effector - point(target_actor, target_spec)).length
                    )

    height = float(np.median(heights))
    root_separation = np.asarray(root_separation, dtype=np.float64) / height
    minimum_segment_frames = max(2, int(round(0.05 * args.sample_fps)))
    contacts = []
    for key, raw_values in distances.items():
        values = np.asarray(raw_values, dtype=np.float64) / height
        segments = contiguous_segments(
            values <= args.contact_threshold_H, minimum_segment_frames
        )
        if not segments:
            continue
        best_start, best_end = min(
            segments, key=lambda segment: float(np.min(
                values[segment[0]:segment[1] + 1]
            ))
        )
        local = values[best_start:best_end + 1]
        closest = best_start + int(np.argmin(local))
        contacts.append({
            "pair": key,
            "segment_frames": [
                float(frames[best_start]), float(frames[best_end])
            ],
            "duration_seconds": (best_end - best_start + 1)
                                / args.sample_fps,
            "closest_frame": float(frames[closest]),
            "minimum_H": float(np.min(local)),
            "p95_H": float(np.percentile(local, 95.0)),
        })
    contacts.sort(key=lambda row: (
        row["minimum_H"], -row["duration_seconds"], row["pair"]
    ))
    # Nearby wrist/hand variants describe the same physical event. Keep all in
    # JSON but expose a compact first review queue.
    review_queue = contacts[:24]
    failures = []
    if int(range_a[1]) != int(range_b[1]):
        failures.append("paired_frame_counts_do_not_match")
    if not contacts:
        failures.append("no_cross_actor_contact_segments")
    if float(np.min(root_separation)) < 0.20:
        failures.append("actor_roots_overlap")
    report = {
        "schema": 1,
        "pair_name": args.pair_name,
        "actor_files": [str(args.actor_a.resolve()), str(args.actor_b.resolve())],
        "source": "Cologne Motion Capture Database",
        "source_url": "https://mocap.web.th-koeln.de/index.php",
        "license": "CC BY 4.0",
        "native_fps": native_fps,
        "sample_fps": args.sample_fps,
        "frames": [float(frames[0]), float(frames[-1])],
        "body_height_units": height,
        "contact_threshold_H": args.contact_threshold_H,
        "root_separation_H": {
            "minimum": float(np.min(root_separation)),
            "median": float(np.median(root_separation)),
            "maximum": float(np.max(root_separation)),
        },
        "contact_segment_count": len(contacts),
        "review_queue": review_queue,
        "all_contact_segments": contacts,
        "failures": failures,
        "passed_shared_source_gate": not failures,
        "status": "source_pair_screen_not_an_accepted_EVA_motion",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# CMCD paired source audit — {args.pair_name}", "",
        "Source-space contact screen only; every event needs 3D review.", "",
        "| Rank | Pair | Frames | Duration | Min | P95 |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(review_queue, 1):
        lines.append(
            f"| {rank} | `{row['pair']}` | "
            f"{row['segment_frames'][0]:.1f}–{row['segment_frames'][1]:.1f} | "
            f"{row['duration_seconds']:.3f} s | {row['minimum_H']:.4f} H | "
            f"{row['p95_H']:.4f} H |"
        )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.best_blend is not None:
        for rank, row in enumerate(review_queue[:8], 1):
            scene.timeline_markers.new(
                f"CONTACT_{rank}_{row['pair'][:40]}",
                frame=int(round(row["closest_frame"])),
            )
        text = bpy.data.texts.new("README_CMCD_PAIR_AUDIT")
        text.write(json.dumps(report, ensure_ascii=False, indent=2))
        args.best_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.best_blend.resolve()))
    print(json.dumps({
        "pair": args.pair_name,
        "passed": report["passed_shared_source_gate"],
        "contacts": len(contacts),
        "top": review_queue[:5],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
