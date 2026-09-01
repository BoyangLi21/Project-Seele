#!/usr/bin/env python3
"""Synchronize real target-reaction mocap to buffered strike contact frames."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eva_paired_contact_combo import inertialize, maximum_step


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-stages", required=True, type=Path)
    parser.add_argument("--attacker-combo", required=True, type=Path)
    parser.add_argument("--attacker-compose-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--inertial-frames", type=int, default=8)
    parser.add_argument("--clip", default="ordinary_combo_hold_demo")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def main() -> None:
    args = parse_args()
    stages = json.loads(args.target_stages.read_text(encoding="utf-8"))
    attacker = json.loads(args.attacker_combo.read_text(encoding="utf-8"))
    compose = json.loads(
        args.attacker_compose_report.read_text(encoding="utf-8"))
    clip_name = args.clip
    attacker_frames = attacker["clips"][clip_name]["frames"]
    reactions = [
        "target_hurt_right",
        "target_hurt_left",
        "target_push_heavy",
    ]
    events = sorted(compose["boundaries"], key=lambda value: (
        value["cycle"], value["stage"]))
    if len(events) % len(reactions):
        raise RuntimeError("attacker event count is not a whole combo cycle")

    ready = copy.deepcopy(stages["clips"][reactions[0]]["frames"][0])
    ready["root_m"] = [0.0, 0.0, 0.0]
    output = []
    event_report = []
    current = ready
    for event_index, event in enumerate(events):
        contact = int(event["contactFrame"])
        while len(output) < contact:
            output.append(copy.deepcopy(current))
        reaction_name = reactions[event_index % len(reactions)]
        source = stages["clips"][reaction_name]["frames"]
        adjusted = inertialize(source, current, args.inertial_frames)
        next_contact = (int(events[event_index + 1]["contactFrame"])
                        if event_index + 1 < len(events)
                        else len(attacker_frames))
        allowed = max(1, next_contact - len(output))
        inserted = adjusted[:allowed]
        output.extend(copy.deepcopy(inserted))
        current = output[-1]
        event_report.append({
            "cycle": event["cycle"],
            "stage": event["stage"],
            "contactFrame": contact,
            "reaction": reaction_name,
            "insertedFrames": len(inserted),
        })
    while len(output) < len(attacker_frames):
        output.append(copy.deepcopy(current))
    output = output[:len(attacker_frames)]
    maximum, location = maximum_step(output, stages["bones"])
    failures = []
    if maximum > 20.0:
        failures.append(
            f"target reaction rotation step {maximum:.5f} > 20 degrees")

    document = {
        "schema": 2,
        "coordinate_system": stages["coordinate_system"],
        "quaternion_order": stages["quaternion_order"],
        "sample_rate": stages["sample_rate"],
        "preview_only": True,
        "live_gameplay_replacement": False,
        "human_review": {"status": "CANDIDATE_REQUIRES_HUMAN_REVIEW"},
        "authority": "synchronized_real_mocap_hit_reaction_target_proxy",
        "root_authority": "REVIEW_LOCAL_ONLY_TARGET_REACTION_PROXY",
        "sources": stages.get("sources", []),
        "bones": list(stages["bones"]),
        "target_reaction_contract": {
            "trigger": "server_confirmed_hit_only",
            "miss": "no_target_reaction",
            "events": event_report,
            "inertialFrames": args.inertial_frames,
        },
        "clips": {
            clip_name: {
                "duration_seconds": attacker["clips"][
                    clip_name]["duration_seconds"],
                "loop": False,
                "role": "synchronized_target_hit_reaction_review_only",
                "kind": "target_hit_reaction_timeline",
                "support_mode": "CAPTURED_FULL_BODY_REACTIONS",
                "grip": "TARGET_REACTION_HANDS",
                "frames": output,
            }
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    report = {
        "schema": 1,
        "result": ("ELIGIBLE_FOR_EXACT_PAIRED_GATE"
                   if not failures else "FAIL"),
        "automaticVisualApproval": False,
        "frames": len(output),
        "durationSeconds": document["clips"][clip_name]["duration_seconds"],
        "events": event_report,
        "maximumRotationStepDegrees": maximum,
        "maximumRotationStepLocation": location,
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
