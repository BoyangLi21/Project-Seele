#!/usr/bin/env python3
"""Screen source motions for the original-aligned EVA combat vocabulary.

The audit runs on the original performer before retargeting.  It identifies
support, limb-energy peaks and whole-body travel without claiming that a source
clip is already a finished EVA action.
"""

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
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--sample-hz", type=float, default=60.0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in tuple(bpy.data.actions):
        bpy.data.actions.remove(block)
    for block in tuple(bpy.data.armatures):
        bpy.data.armatures.remove(block)


def point(rig: bpy.types.Object, name: str, tail: bool = False) -> Vector:
    bone = rig.pose.bones[name]
    return rig.matrix_world @ (bone.tail if tail else bone.head)


def angle(a: Vector, b: Vector, c: Vector) -> float:
    first = a - b
    second = c - b
    if first.length < 1.0e-8 or second.length < 1.0e-8:
        return 0.0
    return math.degrees(first.angle(second))


def pctl(values, q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def local_peaks(values: np.ndarray, threshold: float,
                separation: int, limit: int = 8) -> list[int]:
    peaks = []
    for index in range(1, len(values) - 1):
        if values[index] < threshold:
            continue
        if values[index] < values[index - 1] or values[index] < values[index + 1]:
            continue
        if peaks and index - peaks[-1] < separation:
            if values[index] > values[peaks[-1]]:
                peaks[-1] = index
            continue
        peaks.append(index)
    return sorted(peaks, key=lambda index: values[index], reverse=True)[:limit]


def decide(role: str, metrics: dict) -> tuple[str, list[str]]:
    reasons = []
    best = metrics["best_event"]
    if role.startswith("paired_"):
        return "paired_review_required", [
            "must be evaluated with the matching actor and shared contacts"
        ]
    if "sequence" in role:
        return "reference_only", [
            "sequence label is too broad; segment and review individual events"
        ]
    if "jump_kick" in role:
        if best["swing_height_H"] < 0.20:
            reasons.append("aerial striking foot does not reach 0.20 H")
        if metrics["flight_fraction"] < 0.02:
            reasons.append("no measured two-foot flight")
        return ("aerial_kick_reference" if not reasons
                else "source_reject"), reasons
    if "kick" in role:
        if best["channel"] not in {"left_foot", "right_foot"}:
            reasons.append("dominant event is not a foot action")
        if best["swing_height_H"] < 0.08:
            reasons.append("swing foot does not reach 0.08 H")
        if not best["opposite_foot_contact"]:
            reasons.append("no planted opposite foot at peak")
        if best["opposite_foot_window_travel_H"] > 0.08:
            reasons.append("support foot travels over 0.08 H")
        if not reasons:
            return "source_shortlist", reasons
        if "swing foot does not reach 0.08 H" in reasons:
            return "source_reject", reasons
        return "source_contact_repair_required", reasons
    if "block" in role or "reach" in role:
        if best["channel"] not in {"left_hand", "right_hand"}:
            reasons.append("dominant event is not a hand/forearm action")
        if metrics["root_planar_travel_H"] > 0.60:
            reasons.append("excessive root travel for a ward/deflection")
        return ("source_shortlist" if not reasons else "source_reject"), reasons
    if "lunge" in role:
        if metrics["root_planar_travel_H"] < 0.05:
            reasons.append("lunge has insufficient body entry")
        return ("source_shortlist" if not reasons else "source_reject"), reasons
    if "leap" in role or "dive" in role or "pounce" in role:
        if metrics["flight_fraction"] < 0.02:
            reasons.append("no measured two-foot flight")
        return ("pounce_reference" if not reasons else "source_reject"), reasons
    if "body_entry" in role or "dodge" in role:
        if metrics["root_planar_travel_H"] < 0.05:
            reasons.append("insufficient whole-body displacement")
        if metrics["root_planar_travel_H"] > 2.0:
            reasons.append("capture is too long for one combat fragment")
        if reasons == ["capture is too long for one combat fragment"]:
            return "requires_segmentation", reasons
        return ("source_shortlist" if not reasons else "source_reject"), reasons
    return "reference_only", ["no automatic role-specific gate"]


def analyse(path: Path, asset: dict, sample_hz: float) -> dict:
    clear_scene()
    bpy.ops.import_anim.bvh(
        filepath=str(path.resolve()), target="ARMATURE", global_scale=0.01,
        frame_start=1, use_fps_scale=False, update_scene_fps=True,
        update_scene_duration=True, rotate_mode="NATIVE",
        axis_forward="-Z", axis_up="Y",
    )
    rig = next(obj for obj in bpy.context.scene.objects
               if obj.type == "ARMATURE")
    scene = bpy.context.scene
    native_fps = scene.render.fps / scene.render.fps_base
    action = rig.animation_data.action
    action_start = int(math.ceil(action.frame_range[0]))
    action_end = int(math.floor(action.frame_range[1]))
    step = max(1, int(round(native_fps / max(1.0, sample_hz))))
    frames = list(range(action_start, action_end + 1, step))
    if frames[-1] != action_end:
        frames.append(action_end)
    dt = step / native_fps
    rows = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        left_ankle = point(rig, "LeftFoot")
        right_ankle = point(rig, "RightFoot")
        left_toe = point(rig, "LeftToeBase")
        right_toe = point(rig, "RightToeBase")
        rows.append({
            "frame": frame,
            "root": point(rig, "Hips"),
            "head": point(rig, "Head", tail=True),
            "left_hand": point(rig, "LeftHand", tail=True),
            "right_hand": point(rig, "RightHand", tail=True),
            "left_foot": left_ankle,
            "right_foot": right_ankle,
            "left_floor": min(left_ankle.z, left_toe.z),
            "right_floor": min(right_ankle.z, right_toe.z),
            "left_knee": angle(point(rig, "LeftUpLeg"),
                               point(rig, "LeftLeg"), left_ankle),
            "right_knee": angle(point(rig, "RightUpLeg"),
                                point(rig, "RightLeg"), right_ankle),
            "left_elbow": angle(point(rig, "LeftArm"),
                                point(rig, "LeftForeArm"),
                                point(rig, "LeftHand")),
            "right_elbow": angle(point(rig, "RightArm"),
                                 point(rig, "RightForeArm"),
                                 point(rig, "RightHand")),
        })
    heights = [row["head"].z
               - min(row["left_floor"], row["right_floor"])
               for row in rows]
    height = max(1.0e-6, pctl(heights, 50.0))
    floor = pctl([min(row["left_floor"], row["right_floor"])
                  for row in rows], 2.0)
    channels = ("left_hand", "right_hand", "left_foot", "right_foot")
    velocities = {name: np.zeros(len(rows), dtype=float) for name in channels}
    root_velocity = np.zeros(len(rows), dtype=float)
    for index in range(1, len(rows)):
        duration = max(1.0e-6, (frames[index] - frames[index - 1]) / native_fps)
        for name in channels:
            velocities[name][index] = (
                rows[index][name] - rows[index - 1][name]
            ).length / duration / height
        root_delta = rows[index]["root"] - rows[index - 1]["root"]
        root_delta.z = 0.0
        root_velocity[index] = root_delta.length / duration / height
    contacts = {}
    for side in ("left", "right"):
        contacts[side] = np.asarray([
            row[f"{side}_floor"] <= floor + 0.03 * height
            and velocities[f"{side}_foot"][index] <= 0.30
            for index, row in enumerate(rows)
        ], dtype=bool)
    flight = ~(contacts["left"] | contacts["right"])

    energy = np.maximum.reduce([velocities[name] for name in channels])
    edge_margin = max(2, int(round(0.25 * native_fps / step)))
    energy[:edge_margin] = 0.0
    energy[-edge_margin:] = 0.0
    threshold = max(0.35, pctl(energy, 82.0))
    peaks = local_peaks(
        energy, threshold,
        max(1, int(round(0.38 * native_fps / step))),
    )
    if not peaks:
        peaks = [int(np.argmax(energy))]
    events = []
    window = max(1, int(round(0.24 * native_fps / step)))

    def make_event(index: int, channel: str) -> dict:
        side = "left" if channel.startswith("left") else "right"
        opposite = "right" if side == "left" else "left"
        first = max(0, index - window)
        last = min(len(rows) - 1, index + window)
        swing_height = 0.0
        opposite_contact = False
        opposite_travel = 0.0
        if channel.endswith("foot"):
            swing_height = max(
                0.0, rows[index][f"{side}_floor"] - floor
            ) / height
            opposite_contact = bool(contacts[opposite][index])
            points = [rows[item][f"{opposite}_foot"]
                      for item in range(first, last + 1)]
            opposite_travel = sum(
                (points[item] - points[item - 1]).length
                for item in range(1, len(points))
            ) / height
        return {
            "frame": int(rows[index]["frame"]),
            "time_seconds": (rows[index]["frame"] - frames[0]) / native_fps,
            "channel": channel,
            "peak_speed_H_per_s": float(velocities[channel][index]),
            "swing_height_H": swing_height,
            "opposite_foot_contact": opposite_contact,
            "two_foot_flight": bool(flight[index]),
            "opposite_foot_window_travel_H": opposite_travel,
            "root_speed_H_per_s": float(root_velocity[index]),
            "left_knee_degrees": rows[index]["left_knee"],
            "right_knee_degrees": rows[index]["right_knee"],
            "left_elbow_degrees": rows[index]["left_elbow"],
            "right_elbow_degrees": rows[index]["right_elbow"],
        }

    for index in sorted(peaks):
        channel = max(channels, key=lambda name: velocities[name][index])
        events.append(make_event(index, channel))
    # A simultaneous arm counterbalance can be faster than the actual kick.
    # Preserve the strongest event for every limb so the role-specific gate
    # evaluates the intended effector rather than whichever marker moved most.
    for channel in channels:
        values = velocities[channel].copy()
        values[:edge_margin] = 0.0
        values[-edge_margin:] = 0.0
        index = int(np.argmax(values))
        if not any(event["frame"] == rows[index]["frame"]
                   and event["channel"] == channel for event in events):
            events.append(make_event(index, channel))
    events.sort(key=lambda event: event["frame"])
    dominant_channels = {
        channel: float(np.max(values)) for channel, values in velocities.items()
    }
    role = asset["role"]
    if "kick" in role:
        relevant_channels = {"left_foot", "right_foot"}
    elif ("block" in role or "reach" in role or "lunge" in role
          or role.startswith("paired_") or "sequence" in role):
        relevant_channels = {"left_hand", "right_hand"}
    else:
        relevant_channels = set(channels)
    relevant_events = [event for event in events
                       if event["channel"] in relevant_channels]
    if "jump_kick" in role:
        best_event = max(
            relevant_events,
            key=lambda event: (
                bool(event["two_foot_flight"]),
                event["swing_height_H"],
                event["peak_speed_H_per_s"],
            ),
            default=max(events, key=lambda event: event["peak_speed_H_per_s"]),
        )
    elif "kick" in role:
        best_event = max(
            relevant_events,
            key=lambda event: (
                bool(event["opposite_foot_contact"]),
                event["swing_height_H"]
                - 0.35 * event["opposite_foot_window_travel_H"],
                event["peak_speed_H_per_s"],
            ),
            default=max(events, key=lambda event: event["peak_speed_H_per_s"]),
        )
    else:
        best_event = max(
            relevant_events,
            key=lambda event: event["peak_speed_H_per_s"],
            default=max(events, key=lambda event: event["peak_speed_H_per_s"]),
        )
    root_delta = rows[-1]["root"] - rows[0]["root"]
    root_delta.z = 0.0
    metrics = {
        "native_fps": native_fps,
        "sample_step": step,
        "sampled_hz": native_fps / step,
        "frames": [frames[0], frames[-1]],
        "duration_seconds": (frames[-1] - frames[0]) / native_fps,
        "body_height_units": height,
        "root_planar_travel_H": root_delta.length / height,
        "root_speed_p95_H_per_s": pctl(root_velocity, 95.0),
        "flight_fraction": float(np.mean(flight)),
        "minimum_knee_degrees": min(
            min(row["left_knee"] for row in rows),
            min(row["right_knee"] for row in rows),
        ),
        "maximum_limb_speeds_H_per_s": dominant_channels,
        "best_event": best_event,
        "events": events,
    }
    decision, reasons = decide(asset["role"], metrics)
    return {
        "file": asset["file"],
        "role": asset["role"],
        "description": asset["description"],
        "subject": asset["subject"],
        "trial": asset["trial"],
        "decision": decision,
        "reasons": reasons,
        "metrics": metrics,
    }


def main() -> None:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    root = args.manifest.parent
    results = []
    for asset in manifest["assets"]:
        source = root / asset["file"]
        results.append(analyse(source, asset, args.sample_hz))
        print(f"audited {source.name}: {results[-1]['decision']}")
    counts = {}
    for row in results:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
    payload = {
        "schema": 1,
        "source_manifest": str(args.manifest.resolve()),
        "authority": "original source skeleton; no EVA retarget",
        "limitations": [
            "automatic source gate cannot approve EVA style",
            "paired captures require a shared-space two-actor audit",
            "all shortlisted clips still require mesh-seam, contact and 3D review",
        ],
        "counts": counts,
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# EVA original-combat source screening R01", "",
        "Original performer audit only; no row is an accepted EVA animation.",
        "", "| Source | Role | Decision | Dominant event | Root travel | Flight | Reasons |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in results:
        metrics = row["metrics"]
        event = metrics["best_event"]
        lines.append(
            f"| `{Path(row['file']).name}` | {row['role']} | "
            f"{row['decision']} | {event['channel']} "
            f"{event['peak_speed_H_per_s']:.2f} H/s @ {event['frame']} | "
            f"{metrics['root_planar_travel_H']:.3f} H | "
            f"{metrics['flight_fraction']:.3f} | "
            f"{'; '.join(row['reasons']) or 'source gate passed'} |"
        )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "clips": len(results), "counts": counts,
        "output": str(args.output_json),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
