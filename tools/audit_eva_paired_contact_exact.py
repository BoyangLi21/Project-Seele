#!/usr/bin/env python3
"""Audit synchronized attacker/target contact in an exact two-Tiger scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_eva_motion_lab_exact import object_bounds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attacker-db", required=True, type=Path)
    parser.add_argument("--target-db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--clip", default="eva_contact_combo_hold_demo")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def joint(name: str, target: bool = False) -> Vector:
    prefix = "TARGET::" if target else ""
    return bpy.data.objects[f"{prefix}JOINT::{name}"].matrix_world.translation


def main() -> None:
    args = parse_args()
    attacker = json.loads(args.attacker_db.read_text(encoding="utf-8"))
    target = json.loads(args.target_db.read_text(encoding="utf-8"))
    if bpy.context.scene.get("attacker_motion_db_sha256") != hashlib.sha256(
            args.attacker_db.read_bytes()).hexdigest():
        raise RuntimeError("paired scene attacker database hash differs")
    if bpy.context.scene.get("target_motion_db_sha256") != hashlib.sha256(
            args.target_db.read_bytes()).hexdigest():
        raise RuntimeError("paired scene target database hash differs")
    clip_name = args.clip
    attacker_frames = attacker["clips"][clip_name]["frames"]
    target_frames = target["clips"][clip_name]["frames"]
    if len(attacker_frames) != len(target_frames):
        raise RuntimeError("paired database frame counts differ")
    scene = bpy.context.scene
    attacker_parts = [obj for obj in scene.objects
                      if obj.name.startswith("PART::")]
    target_parts = [obj for obj in scene.objects
                    if obj.name.startswith("TARGET::PART::")]
    if len(attacker_parts) != 43 or len(target_parts) != 43:
        raise RuntimeError("paired exact scene must contain 43+43 parts")

    rows = []
    for index in range(len(attacker_frames)):
        scene.frame_set(index + 1)
        bpy.context.view_layer.update()
        minimum, maximum = object_bounds(attacker_parts)
        height = maximum[2] - minimum[2]
        root_a = joint("root")
        root_b = joint("root", target=True)
        hand_l = joint("hand_l")
        hand_r = joint("hand_r")
        shoulder_l = joint("arm_l", target=True)
        shoulder_r = joint("arm_r", target=True)
        torso = joint("torso_upper", target=True)
        head = joint("head", target=True)
        left_shoulder = (hand_l - shoulder_r).length / height
        right_shoulder = (hand_r - shoulder_l).length / height
        left_torso = (hand_l - torso).length / height
        right_torso = (hand_r - torso).length / height
        left_head = (hand_l - head).length / height
        right_head = (hand_r - head).length / height
        rows.append({
            "frame": index,
            "height": height,
            "root_a": root_a.copy(),
            "root_b": root_b.copy(),
            "hand_l": hand_l.copy(),
            "hand_r": hand_r.copy(),
            "target_root": root_b.copy(),
            "leftShoulderDistanceH": left_shoulder,
            "rightShoulderDistanceH": right_shoulder,
            "leftTorsoDistanceH": left_torso,
            "rightTorsoDistanceH": right_torso,
            "leftHeadDistanceH": left_head,
            "rightHeadDistanceH": right_head,
            "expectedHandContact": list(attacker_frames[index].get(
                "hand_contact", (False, False))),
        })

    failures = []
    minimum_shoulder = min(min(
        row["leftShoulderDistanceH"], row["rightShoulderDistanceH"])
        for row in rows)
    minimum_body = min(min(
        row["leftTorsoDistanceH"], row["rightTorsoDistanceH"])
        for row in rows)
    expected = []
    actual = []
    contact_samples = []
    for row in rows:
        for side, key in enumerate(("leftShoulderDistanceH",
                                    "rightShoulderDistanceH")):
            if row["expectedHandContact"][side]:
                expected.append(row[key])
                actual.append(row[key] <= 0.25)
                contact_samples.append({
                    "frame": row["frame"],
                    "distanceH": row[key],
                    "within0p25H": row[key] <= 0.25,
                })
    contact_mode = "source_hand_to_shoulder"
    if not expected:
        contact_frames = {
            int(value["contactFrame"])
            for value in attacker.get("combo_contract", {}).get(
                "bufferWindows", [])
        }
        for row in rows:
            if row["frame"] not in contact_frames:
                continue
            distance = min(
                row["leftShoulderDistanceH"],
                row["rightShoulderDistanceH"],
                row["leftTorsoDistanceH"],
                row["rightTorsoDistanceH"],
                row["leftHeadDistanceH"],
                row["rightHeadDistanceH"],
            )
            expected.append(distance)
            actual.append(distance <= 0.25)
            contact_samples.append({
                "frame": row["frame"],
                "distanceH": distance,
                "within0p25H": distance <= 0.25,
            })
        contact_mode = "buffered_strike_to_head_torso_or_shoulder"
    contact_coverage = sum(actual) / len(actual) if actual else 0.0
    minimum_expected_contact = min(expected) if expected else float("inf")
    root_separation = [
        (row["root_b"] - row["root_a"]).length / row["height"]
        for row in rows
    ]
    target_origin = rows[0]["target_root"]
    target_reaction = max(
        (row["target_root"] - target_origin).length / row["height"]
        for row in rows)
    attacker_origin = rows[0]["root_a"]
    attacker_entry = max(
        (row["root_a"] - attacker_origin).length / row["height"]
        for row in rows)
    hand_range = max(
        max((row[key] - rows[0][key]).length / row["height"]
            for row in rows)
        for key in ("hand_l", "hand_r")
    )
    maximum_relative_step = 0.0
    for previous, current in zip(rows, rows[1:]):
        before = previous["root_b"] - previous["root_a"]
        after = current["root_b"] - current["root_a"]
        maximum_relative_step = max(
            maximum_relative_step,
            (after - before).length / current["height"])

    if minimum_expected_contact > 0.18:
        failures.append(
            "minimum expected contact "
            f"{minimum_expected_contact:.5f} H > 0.18 H")
    if contact_coverage < 0.50:
        failures.append(
            f"expected contact coverage {contact_coverage:.1%} < 50%")
    if min(root_separation) < 0.25:
        failures.append(
            f"root separation {min(root_separation):.5f} H < 0.25 H")
    if max(root_separation) > 1.10:
        failures.append(
            f"root separation {max(root_separation):.5f} H > 1.10 H")
    if target_reaction < 0.03:
        failures.append(
            f"target reaction {target_reaction:.5f} H < 0.03 H")
    if attacker_entry < 0.03 or hand_range < 0.10:
        failures.append(
            "whole-body contact dynamics missing: "
            f"entry={attacker_entry:.5f} hand={hand_range:.5f} H")
    if maximum_relative_step > 0.04:
        failures.append(
            f"relative root step {maximum_relative_step:.5f} H > 0.04 H")

    report = {
        "schema": 1,
        "authority": "exact_two_tiger_synchronized_contact_matrices",
        "clip": clip_name,
        "frames": len(rows),
        "failureCount": len(failures),
        "failures": failures,
        "minimumHandShoulderDistanceH": minimum_shoulder,
        "minimumHandTorsoDistanceH": minimum_body,
        "minimumExpectedContactDistanceH": minimum_expected_contact,
        "contactMode": contact_mode,
        "expectedContactSamples": len(expected),
        "contactSamples": contact_samples,
        "expectedContactCoverageWithin0p25H": contact_coverage,
        "rootSeparationH": {
            "minimum": min(root_separation),
            "maximum": max(root_separation),
        },
        "attackerEntryRangeH": attacker_entry,
        "targetReactionRangeH": target_reaction,
        "handRangeH": hand_range,
        "maximumRelativeRootStepH": maximum_relative_step,
        "result": ("ELIGIBLE_FOR_HUMAN_REVIEW_ONLY"
                   if not failures else "FAIL"),
        "automaticVisualApproval": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "frames": len(rows),
        "failures": len(failures),
        "minimumContactH": minimum_shoulder,
        "coverage": contact_coverage,
        "result": report["result"],
    }))
    if args.strict and failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
