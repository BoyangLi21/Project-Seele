#!/usr/bin/env python3
"""Compose captured strike stages into an input-buffered EVA combo demo.

The next stage is inertialized from the current ending pose.  No stage returns
to a canonical stand pose.  The output demo repeats the three-stage order twice
to expose the stage-three to stage-one continuation; live gameplay must advance
only when a new left-click is buffered.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from mathutils import Quaternion


IDENTITY = Quaternion((1.0, 0.0, 0.0, 0.0))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--inertial-frames", type=int, default=12)
    parser.add_argument("--review-cycle-count", type=int, default=2)
    parser.add_argument("--stage-order", action="append", default=[])
    parser.add_argument("--output-clip", default="ordinary_combo_hold_demo")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def rounded(value: Quaternion) -> list[float]:
    value.normalize()
    return [round(float(value.w), 7), round(float(value.x), 7),
            round(float(value.y), 7), round(float(value.z), 7)]


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def angle_degrees(first: list[float], second: list[float]) -> float:
    a = Quaternion(tuple(float(value) for value in first))
    b = Quaternion(tuple(float(value) for value in second))
    a.normalize()
    b.normalize()
    return math.degrees(a.rotation_difference(b).angle)


def adjusted_stage(frames: list[dict], prior: dict | None,
                   inertial_frames: int) -> list[dict]:
    if prior is None:
        return copy.deepcopy(frames)
    start = frames[0]
    root_offset = [
        float(prior["root_m"][axis]) - float(start["root_m"][axis])
        for axis in range(3)
    ]
    offsets = []
    for before, after in zip(
            prior["rotation_wxyz"], start["rotation_wxyz"]):
        previous = Quaternion(tuple(float(value) for value in before))
        incoming = Quaternion(tuple(float(value) for value in after))
        previous.normalize()
        incoming.normalize()
        offset = previous @ incoming.inverted()
        offset.normalize()
        offsets.append(offset)
    output = []
    for index, source in enumerate(frames):
        frame = copy.deepcopy(source)
        frame["root_m"] = [
            round(float(source["root_m"][axis]) + root_offset[axis], 7)
            for axis in range(3)
        ]
        amount = smoothstep(index / max(1, inertial_frames))
        rotations = []
        for offset, source_rotation in zip(
                offsets, source["rotation_wxyz"]):
            decay = offset.slerp(IDENTITY, amount)
            value = decay @ Quaternion(tuple(
                float(component) for component in source_rotation))
            rotations.append(rounded(value))
        frame["rotation_wxyz"] = rotations
        output.append(frame)
    return output


def main() -> None:
    args = parse_args()
    if args.inertial_frames < 4:
        raise SystemExit("at least four inertial frames are required")
    if args.review_cycle_count < 2:
        raise SystemExit("review must include at least two cycles")
    document = json.loads(args.input.read_text(encoding="utf-8"))
    order = args.stage_order or [
        "combo_forearm_right",
        "combo_forearm_left",
        "combo_forearm_lariat",
    ]
    missing = set(order) - set(document["clips"])
    if missing:
        raise RuntimeError("missing combo stages: " + ", ".join(sorted(missing)))
    bones = list(document["bones"])
    frames = []
    boundaries = []
    boundary_steps = []
    prior = None
    contact_offsets = {
        "combo_forearm_right": 19,
        "combo_forearm_left": 19,
        "combo_forearm_lariat": 20,
        "overhand_combo_right": 39,
        "overhand_combo_left": 36,
        "overhand_combo_heavy": 33,
        "g1_combo_right_down": 14,
        "g1_combo_left_sweep": 16,
        "g1_combo_right_drive": 20,
        "group_a_right_down": 14,
        "group_a_left_sweep": 16,
        "group_a_right_drive": 20,
        "group_b_right_burst": 16,
        "group_b_left_rise": 18,
        "group_b_right_reap": 16,
        "group_c_right_drive": 20,
        "group_c_left_double": 48,
        "group_c_right_finish": 17,
        "group_d_right_entry": 20,
        "group_d_left_burst": 16,
        "group_d_right_drop": 20,
    }
    for cycle in range(args.review_cycle_count):
        for stage_index, name in enumerate(order, 1):
            source_frames = document["clips"][name]["frames"]
            adjusted = adjusted_stage(
                source_frames, prior, args.inertial_frames)
            if frames:
                # The first inertialized pose equals the previous ending pose.
                adjusted = adjusted[1:]
            first = len(frames)
            frames.extend(adjusted)
            last = len(frames) - 1
            contact = min(last, first + contact_offsets.get(
                name, max(1, len(source_frames) // 2)))
            buffer_open = min(last, contact + 5)
            boundaries.append({
                "cycle": cycle + 1,
                "stage": stage_index,
                "sourceClip": name,
                "frameRange": [first, last],
                "contactFrame": contact,
                "bufferWindow": [buffer_open, last],
            })
            if first > 0:
                step = max(
                    angle_degrees(
                        frames[first - 1]["rotation_wxyz"][bone_index],
                        frames[first]["rotation_wxyz"][bone_index],
                    )
                    for bone_index in range(len(bones))
                )
                boundary_steps.append({
                    "cycle": cycle + 1,
                    "stage": stage_index,
                    "maximumRotationStepDegrees": step,
                })
            prior = frames[-1]

    maximum_step = 0.0
    maximum_location = None
    for frame_index in range(1, len(frames)):
        for bone_index, bone in enumerate(bones):
            value = angle_degrees(
                frames[frame_index - 1]["rotation_wxyz"][bone_index],
                frames[frame_index]["rotation_wxyz"][bone_index],
            )
            if value > maximum_step:
                maximum_step = value
                maximum_location = {
                    "frame": frame_index,
                    "bone": bone,
                }
    root_origin = frames[0]["root_m"]
    maximum_root_range = max(math.sqrt(sum(
        (float(frame["root_m"][axis]) - float(root_origin[axis])) ** 2
        for axis in range(3)
    )) for frame in frames)
    failures = []
    if maximum_step > 20.0:
        failures.append(
            f"maximum rotation step {maximum_step:.5f} > 20 degrees")
    output = {
        "schema": 2,
        "coordinate_system": document["coordinate_system"],
        "quaternion_order": document["quaternion_order"],
        "sample_rate": document["sample_rate"],
        "preview_only": True,
        "live_gameplay_replacement": False,
        "human_review": {"status": "CANDIDATE_REQUIRES_HUMAN_REVIEW"},
        "authority": "buffered_current_pose_inertialized_combo_review",
        "root_authority": document["root_authority"],
        "sources": document.get("sources", []),
        "bones": bones,
        "combo_contract": {
            "input": "repeated_left_click",
            "advanceRule": "advance_only_when_next_click_is_buffered",
            "bufferWindows": boundaries,
            "onRelease": "recover_from_current_pose_not_canonical_stand",
            "onHit": "server_contact_result_selects_follow_through",
            "onMiss": "continue_current_momentum_then_recover_or_buffer",
            "standResetBetweenStages": False,
            "reviewCycles": args.review_cycle_count,
            "inertialFrames": args.inertial_frames,
        },
        "clips": {
            args.output_clip: {
                "duration_seconds": round(
                    (len(frames) - 1) / float(document["sample_rate"]), 7),
                "loop": False,
                "role": "buffered_left_click_combo_hold_review_only",
                "kind": "ordinary_buffered_combo",
                "support_mode": "CAPTURED_FULL_BODY_WITH_INERTIAL_TRANSITIONS",
                "grip": "CURLED_FOREARM_CONTACT",
                "frames": frames,
            }
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    report = {
        "schema": 1,
        "result": ("ELIGIBLE_FOR_EXACT_GATE"
                   if not failures else "FAIL"),
        "automaticVisualApproval": False,
        "clip": args.output_clip,
        "frames": len(frames),
        "durationSeconds": output["clips"][
            args.output_clip]["duration_seconds"],
        "cycles": args.review_cycle_count,
        "stageOrder": order,
        "boundaries": boundaries,
        "boundaryRotationSteps": boundary_steps,
        "maximumRotationStepDegrees": maximum_step,
        "maximumRotationStepLocation": maximum_location,
        "maximumRootRangeMetres": maximum_root_range,
        "failures": failures,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
