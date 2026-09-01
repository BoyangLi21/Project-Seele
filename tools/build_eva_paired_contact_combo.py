#!/usr/bin/env python3
"""Build a two-actor, target-contact EVA combo from synchronized CMU mocap."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils import Quaternion


IDENTITY = Quaternion((1.0, 0.0, 0.0, 0.0))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-db", required=True, type=Path)
    parser.add_argument("--actor-a-landmarks", required=True, type=Path)
    parser.add_argument("--actor-b-landmarks", required=True, type=Path)
    parser.add_argument("--attacker-output", required=True, type=Path)
    parser.add_argument("--target-output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--target-height", type=float, default=6.954349331037082)
    parser.add_argument("--root-horizontal-scale", type=float, default=0.75)
    parser.add_argument("--root-vertical-scale", type=float, default=0.65)
    parser.add_argument("--target-distance-scale", type=float, default=1.0)
    parser.add_argument("--display-scale", type=float, default=0.05)
    parser.add_argument("--inertial-frames", type=int, default=12)
    parser.add_argument("--review-cycle-count", type=int, default=2)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def rounded(value: Quaternion) -> list[float]:
    value.normalize()
    return [round(float(value.w), 7), round(float(value.x), 7),
            round(float(value.y), 7), round(float(value.z), 7)]


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def angle(first: list[float], second: list[float]) -> float:
    a = Quaternion(tuple(float(value) for value in first))
    b = Quaternion(tuple(float(value) for value in second))
    return math.degrees(a.rotation_difference(b).angle)


def inertialize(frames: list[dict], prior: dict,
                inertial_frames: int) -> list[dict]:
    start = frames[0]
    root_offset = [
        float(prior["root_m"][axis]) - float(start["root_m"][axis])
        for axis in range(3)
    ]
    offsets = []
    for before, incoming_value in zip(
            prior["rotation_wxyz"], start["rotation_wxyz"]):
        previous = Quaternion(tuple(float(value) for value in before))
        incoming = Quaternion(tuple(
            float(value) for value in incoming_value))
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
        frame["rotation_wxyz"] = [
            rounded(offset.slerp(IDENTITY, amount)
                    @ Quaternion(tuple(float(value) for value in rotation)))
            for offset, rotation in zip(offsets, source["rotation_wxyz"])
        ]
        output.append(frame)
    return output


def repeated(frames: list[dict], cycle_count: int,
             inertial_frames: int) -> tuple[list[dict], list[float]]:
    output = copy.deepcopy(frames)
    boundaries = []
    for _ in range(1, cycle_count):
        adjusted = inertialize(frames, output[-1], inertial_frames)
        first_new = adjusted[1]
        boundaries.append(max(
            angle(output[-1]["rotation_wxyz"][index],
                  first_new["rotation_wxyz"][index])
            for index in range(len(first_new["rotation_wxyz"]))))
        output.extend(adjusted[1:])
    return output, boundaries


def maximum_step(frames: list[dict], bones: list[str]) -> tuple[float, dict]:
    maximum = 0.0
    location = {"frame": 0, "bone": bones[0]}
    for frame in range(1, len(frames)):
        for index, bone in enumerate(bones):
            value = angle(frames[frame - 1]["rotation_wxyz"][index],
                          frames[frame]["rotation_wxyz"][index])
            if value > maximum:
                maximum = value
                location = {"frame": frame, "bone": bone}
    return maximum, location


def document(template: dict, frames: list[dict], role: str,
             combo_contract: dict) -> dict:
    rate = float(template["sample_rate"])
    return {
        "schema": 2,
        "coordinate_system": template["coordinate_system"],
        "quaternion_order": template["quaternion_order"],
        "sample_rate": rate,
        "preview_only": True,
        "live_gameplay_replacement": False,
        "human_review": {"status": "CANDIDATE_REQUIRES_HUMAN_REVIEW"},
        "authority": role,
        "root_authority": template["root_authority"],
        "sources": template.get("sources", []),
        "bones": list(template["bones"]),
        "combo_contract": combo_contract,
        "clips": {
            "eva_contact_combo_hold_demo": {
                "duration_seconds": round((len(frames) - 1) / rate, 7),
                "loop": False,
                "role": role,
                "kind": "paired_target_contact_combo",
                "support_mode": "SYNCHRONIZED_PAIRED_CAPTURE",
                "grip": "TWO_HAND_CONTACT_CONTROL",
                "frames": frames,
            }
        },
    }


def main() -> None:
    args = parse_args()
    if args.review_cycle_count < 2:
        raise SystemExit("paired review must contain at least two cycles")
    pair_db = json.loads(args.pair_db.read_text(encoding="utf-8"))
    attacker = copy.deepcopy(
        pair_db["clips"]["contact_combo_attacker"]["frames"])
    target = copy.deepcopy(
        pair_db["clips"]["contact_combo_target"]["frames"])
    if len(attacker) != len(target):
        raise RuntimeError("paired clips have different frame counts")

    source_a = np.load(args.actor_a_landmarks)
    source_b = np.load(args.actor_b_landmarks)
    names = [str(value) for value in source_a["landmark_names"]]
    if names != [str(value) for value in source_b["landmark_names"]]:
        raise RuntimeError("paired landmark schemas differ")
    index = {name: offset for offset, name in enumerate(names)}
    positions_a = np.asarray(source_a["positions_H"], dtype=np.float64)
    positions_b = np.asarray(source_b["positions_H"], dtype=np.float64)
    relative = (positions_b[0, index["pelvis"]]
                - positions_a[0, index["pelvis"]])
    units_per_metre = args.display_scale * 112.0
    horizontal = args.target_height * args.root_horizontal_scale \
        / units_per_metre
    vertical = args.target_height * args.root_vertical_scale \
        / units_per_metre
    target_offset = np.asarray((
        relative[1] * horizontal,
        relative[2] * vertical,
        -relative[0] * horizontal,
    ))
    target_offset[[0, 2]] *= args.target_distance_scale
    for frame in target:
        frame["root_m"] = [
            round(float(frame["root_m"][axis])
                  + float(target_offset[axis]), 7)
            for axis in range(3)
        ]

    right_distance = np.linalg.norm(
        positions_a[:, index["hand_r"]]
        - positions_b[:, index["shoulder_l"]], axis=1)
    left_distance = np.linalg.norm(
        positions_a[:, index["hand_l"]]
        - positions_b[:, index["shoulder_r"]], axis=1)
    hand_contacts = np.column_stack((
        left_distance < 0.10,
        right_distance < 0.10,
    ))
    for frame, contacts in zip(attacker, hand_contacts):
        frame["hand_contact"] = [bool(value) for value in contacts]
    for frame, contacts in zip(target, hand_contacts):
        frame["hand_contact"] = [bool(contacts[1]), bool(contacts[0])]

    attacker_frames, attacker_boundaries = repeated(
        attacker, args.review_cycle_count, args.inertial_frames)
    target_frames, target_boundaries = repeated(
        target, args.review_cycle_count, args.inertial_frames)
    source_frames = len(attacker)
    stages = [
        {"stage": 1, "name": "body_entry_and_first_shoulder_contact",
         "sourceFrameRange": [45, 117], "sampleRange": [0, 35],
         "contactSample": 16},
        {"stage": 2, "name": "two_hand_clamp_and_body_drive",
         "sourceFrameRange": [117, 181], "sampleRange": [36, 67],
         "contactSample": 51},
        {"stage": 3, "name": "second_contact_and_shove_follow_through",
         "sourceFrameRange": [181, 259], "sampleRange": [68, 107],
         "contactSample": 82},
    ]
    windows = []
    for cycle in range(args.review_cycle_count):
        cycle_start = cycle * (source_frames - 1)
        for stage in stages:
            source_first = stage["sampleRange"][0]
            if cycle > 0:
                source_first = max(1, source_first)
            first = cycle_start + source_first
            last = cycle_start + stage["sampleRange"][1]
            contact = cycle_start + stage["contactSample"]
            windows.append({
                "cycle": cycle + 1,
                "stage": stage["stage"],
                "name": stage["name"],
                "frameRange": [first, last],
                "contactFrame": contact,
                "bufferWindow": [min(last, contact + 5), last],
            })
    contract = {
        "input": "repeated_left_click",
        "advanceRule": "advance_only_when_next_click_is_buffered",
        "stages": windows,
        "onRelease": "recover_from_current_contact_pose",
        "onMiss": "body_entry_brake_without_target_teleport",
        "onHit": "continue_paired_contact_branch",
        "standResetBetweenStages": False,
        "reviewCycles": args.review_cycle_count,
        "inertialFramesAtCycleBoundary": args.inertial_frames,
        "targetRequired": True,
    }
    attacker_doc = document(
        pair_db, attacker_frames,
        "paired_contact_combo_attacker_review_only", contract)
    target_doc = document(
        pair_db, target_frames,
        "paired_contact_combo_target_proxy_review_only", contract)

    for path, payload in ((args.attacker_output, attacker_doc),
                          (args.target_output, target_doc)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8")
    attacker_step, attacker_location = maximum_step(
        attacker_frames, pair_db["bones"])
    target_step, target_location = maximum_step(
        target_frames, pair_db["bones"])
    root_separation = np.asarray([
        math.dist(a["root_m"], b["root_m"])
        for a, b in zip(attacker_frames, target_frames)
    ])
    failures = []
    if max(attacker_step, target_step) > 20.0:
        failures.append("rotation_step_over_20_degrees")
    if float(root_separation.min()) < 0.30:
        failures.append("paired_root_separation_under_0_30_m")
    report = {
        "schema": 1,
        "result": ("ELIGIBLE_FOR_EXACT_PAIRED_GATE"
                   if not failures else "FAIL"),
        "automaticVisualApproval": False,
        "sourceFrames": source_frames,
        "outputFrames": len(attacker_frames),
        "durationSeconds": (len(attacker_frames) - 1)
                           / float(pair_db["sample_rate"]),
        "reviewCycles": args.review_cycle_count,
        "targetInitialOffsetRootM": target_offset.tolist(),
        "targetDistanceScale": args.target_distance_scale,
        "attackerMaximumRotationStepDegrees": attacker_step,
        "attackerMaximumRotationStepLocation": attacker_location,
        "targetMaximumRotationStepDegrees": target_step,
        "targetMaximumRotationStepLocation": target_location,
        "attackerCycleBoundarySteps": attacker_boundaries,
        "targetCycleBoundarySteps": target_boundaries,
        "rootSeparationMetres": {
            "minimum": float(root_separation.min()),
            "maximum": float(root_separation.max()),
        },
        "sourceHandContactFraction": hand_contacts.mean(axis=0).tolist(),
        "stages": windows,
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
