#!/usr/bin/env python3
"""Audit synchronized CMU subject-18/19 pull-resistance captures."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--best-blend", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in tuple(bpy.data.actions):
        bpy.data.actions.remove(block)
    for block in tuple(bpy.data.armatures):
        bpy.data.armatures.remove(block)


def import_actor(path: Path, name: str):
    bpy.ops.import_anim.bvh(
        filepath=str(path.resolve()), target="ARMATURE", global_scale=0.01,
        frame_start=1, use_fps_scale=False, update_scene_fps=True,
        update_scene_duration=True, rotate_mode="NATIVE",
        axis_forward="-Z", axis_up="Y",
    )
    actor = bpy.context.object
    actor.name = name
    actor.data.name = f"{name}_ARMATURE"
    actor.show_in_front = True
    actor.data.display_type = "STICK"
    return actor


def point(actor, name: str, tail: bool = False) -> Vector:
    bone = actor.pose.bones[name]
    return actor.matrix_world @ (bone.tail if tail else bone.head)


def segments(flags: list[bool], minimum: int) -> list[tuple[int, int]]:
    repaired = list(flags)
    for index in range(1, len(repaired) - 1):
        if not repaired[index] and repaired[index - 1] and repaired[index + 1]:
            repaired[index] = True
    result = []
    first = None
    for index, flag in enumerate(repaired):
        if flag and first is None:
            first = index
        if first is not None and (not flag or index == len(repaired) - 1):
            last = index if flag and index == len(repaired) - 1 else index - 1
            if last - first + 1 >= minimum:
                result.append((first, last))
            first = None
    return result


def analyse_pair(source_dir: Path, trial: str, save_blend: Path | None = None):
    clear_scene()
    actor_a = import_actor(source_dir / f"18_{trial}.bvh", "CMU_18_ACTOR_A")
    end_a = int(actor_a.animation_data.action.frame_range[1])
    actor_b = import_actor(source_dir / f"19_{trial}.bvh", "CMU_19_ACTOR_B")
    end_b = int(actor_b.animation_data.action.frame_range[1])
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    end = min(end_a, end_b)
    frames = list(range(1, end + 1, 2))
    if frames[-1] != end:
        frames.append(end)
    body_heights = {"a": [], "b": []}
    rows = []
    targets = {
        "left_wrist": ("LeftHand", False),
        "right_wrist": ("RightHand", False),
        "left_elbow": ("LeftForeArm", False),
        "right_elbow": ("RightForeArm", False),
    }
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        row = {
            "frame": frame,
            "a_root": point(actor_a, "Hips"),
            "b_root": point(actor_b, "Hips"),
            "a_left_hand": point(actor_a, "LeftHand", tail=True),
            "a_right_hand": point(actor_a, "RightHand", tail=True),
        }
        for name, (bone, tail) in targets.items():
            row[f"b_{name}"] = point(actor_b, bone, tail=tail)
        for key, actor in (("a", actor_a), ("b", actor_b)):
            body_heights[key].append(
                point(actor, "Head", tail=True).z
                - min(point(actor, "LeftFoot").z,
                      point(actor, "RightFoot").z)
            )
        distances = {}
        for hand in ("left_hand", "right_hand"):
            for target in targets:
                distances[f"{hand}_to_{target}"] = (
                    row[f"a_{hand}"] - row[f"b_{target}"]
                ).length
        row["distances"] = distances
        rows.append(row)
    height = float(np.median(body_heights["a"] + body_heights["b"]))
    pair_names = sorted(rows[0]["distances"])
    distance_series = {
        pair: np.asarray([row["distances"][pair] / height for row in rows])
        for pair in pair_names
    }
    best_pair = min(pair_names, key=lambda pair: float(np.percentile(
        distance_series[pair], 5.0)))
    best_values = distance_series[best_pair]
    threshold = min(0.14, max(0.055,
        float(np.percentile(best_values, 5.0)) + 0.025))
    contact_flags = list(best_values <= threshold)
    contact_segments = segments(
        contact_flags, max(3, int(round(0.12 * fps / 2.0)))
    )
    contact_indices = [
        index for first, last in contact_segments
        for index in range(first, last + 1)
    ]
    root_separation = np.asarray([
        (row["a_root"] - row["b_root"]).length / height for row in rows
    ])
    root_a_travel = sum(
        (rows[index]["a_root"] - rows[index - 1]["a_root"]).length
        for index in range(1, len(rows))
    ) / height
    root_b_travel = sum(
        (rows[index]["b_root"] - rows[index - 1]["b_root"]).length
        for index in range(1, len(rows))
    ) / height
    contact_duration = len(contact_indices) * 2.0 / fps
    intended_target = "elbow" if trial in {"05", "06"} else "wrist"
    target_match = intended_target in best_pair
    failures = []
    if abs(end_a - end_b) > 1:
        failures.append("actor_frame_counts_do_not_match")
    if not contact_indices:
        failures.append("no_stable_contact_segment")
    if not target_match:
        failures.append("closest_landmark_disagrees_with_catalogue_label")
    if contact_indices and float(np.percentile(
            best_values[contact_indices], 95.0)) > 0.12:
        failures.append("contact_anchor_p95_over_0_12H")
    if float(np.percentile(root_separation, 95.0)) > 2.0:
        failures.append("actors_not_in_shared_interaction_space")
    result = {
        "trial": trial,
        "files": [f"18_{trial}.bvh", f"19_{trial}.bvh"],
        "fps": fps,
        "actor_frames": [end_a, end_b],
        "sampled_frames": len(frames),
        "body_height_units": height,
        "catalogue_target": intended_target,
        "best_contact_pair": best_pair,
        "contact_threshold_H": threshold,
        "contact_segments": [
            [frames[first], frames[last]] for first, last in contact_segments
        ],
        "contact_duration_seconds": contact_duration,
        "contact_min_H": float(np.min(best_values)),
        "contact_p95_H": (float(np.percentile(best_values[contact_indices], 95.0))
                            if contact_indices else None),
        "root_separation_H": {
            "minimum": float(np.min(root_separation)),
            "median": float(np.median(root_separation)),
            "maximum": float(np.max(root_separation)),
        },
        "root_accumulated_travel_H": {"a": root_a_travel, "b": root_b_travel},
        "failures": failures,
        "passed_source_pair_gate": not failures,
    }
    if save_blend is not None:
        scene.frame_start = 1
        scene.frame_end = end
        for first, last in result["contact_segments"]:
            scene.timeline_markers.new("CONTACT_BEGIN", frame=first)
            scene.timeline_markers.new("CONTACT_END", frame=last)
        text = bpy.data.texts.new("README_CMU_PAIRED_REVIEW")
        text.write(json.dumps(result, ensure_ascii=False, indent=2))
        save_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(save_blend.resolve()))
    return result


def main() -> None:
    args = parse_args()
    first_pass = [analyse_pair(args.source_dir, trial)
                  for trial in ("03", "04", "05", "06")]
    ranked = sorted(first_pass, key=lambda row: (
        len(row["failures"]),
        row["contact_p95_H"] if row["contact_p95_H"] is not None else 999.0,
        -row["contact_duration_seconds"],
    ))
    for rank, row in enumerate(ranked, 1):
        row["rank"] = rank
    best = ranked[0]
    if args.best_blend is not None:
        analyse_pair(args.source_dir, best["trial"], args.best_blend)
    payload = {
        "schema": 1,
        "authority": "CMU synchronized source actors before EVA retarget",
        "source": "https://mocap.cs.cmu.edu/search.php?maincat=1&subcat=1",
        "result": ranked,
        "recommended_first_pair": best["trial"],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# CMU paired pull/resistance source audit R01", "",
        "Source-space pair audit only; no EVA retarget is approved.", "",
        "| Rank | Trial | Catalogue target | Closest pair | Contact P95 | Duration | Root separation median | Failures |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ]
    for row in ranked:
        p95 = (f"{row['contact_p95_H']:.4f} H"
               if row["contact_p95_H"] is not None else "n/a")
        lines.append(
            f"| {row['rank']} | `{row['trial']}` | {row['catalogue_target']} | "
            f"{row['best_contact_pair']} | {p95} | "
            f"{row['contact_duration_seconds']:.2f} s | "
            f"{row['root_separation_H']['median']:.3f} H | "
            f"{', '.join(row['failures']) or 'none'} |"
        )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "recommended": best["trial"],
        "passed": sum(row["passed_source_pair_gate"] for row in ranked),
        "output": str(args.output_json),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
