#!/usr/bin/env python3
"""Validate the promoted 2x Phase-T group-C live attack resource."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STAGES = (
    ("ordinary_attack_group_c_stage_1", 0, 44, 20),
    ("ordinary_attack_group_c_stage_2", 45, 107, 48),
    ("ordinary_attack_group_c_stage_3", 108, 140, 17),
)


def quaternion_angle(first: list[float], second: list[float]) -> float:
    dot = abs(sum(left * right for left, right in zip(first, second)))
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(2.0 * math.acos(dot))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--live", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    live = json.loads(args.live.read_text(encoding="utf-8"))
    failures = []
    if live.get("schema") != 2:
        failures.append("live motion schema is not 2")
    if live.get("preview_only") is not False:
        failures.append("live resource is still preview-only")
    if live.get("live_gameplay_replacement") is not True:
        failures.append("live gameplay replacement flag is false")
    if live.get("gameplay_contract", {}).get(
            "playback_speed_multiplier") != 2.0:
        failures.append("playback speed multiplier is not 2.0")
    if live.get("human_review", {}).get("selected") != "ordinary_group_c":
        failures.append("human-selected group C lock is missing")
    if len(live.get("bones", [])) != 50 or "knife" in live.get("bones", []):
        failures.append("live unarmed resource must contain 50 non-knife bones")

    source = selection.get("clips", {}).get("ordinary_group_c", {}).get(
        "frames", []
    )
    stage_reports = []
    previous = None
    maximum_boundary = 0.0
    for name, first, last, contact in STAGES:
        clip = live.get("clips", {}).get(name)
        if clip is None:
            failures.append(f"missing live stage {name}")
            continue
        frames = clip.get("frames", [])
        expected = source[first:last + 1]
        if len(frames) != len(expected):
            failures.append(
                f"{name}: {len(frames)} frames != {len(expected)} expected"
            )
            continue
        for index, (actual, original) in enumerate(zip(frames, expected)):
            expected_rotations = original["rotation_wxyz"][:-1]
            if actual["rotation_wxyz"] != expected_rotations:
                failures.append(f"{name}: pose differs at frame {index}")
                break
            if actual["root_m"] != original["root_m"]:
                failures.append(f"{name}: root differs at frame {index}")
                break
            if actual["foot_contact"] != original["foot_contact"]:
                failures.append(f"{name}: contacts differ at frame {index}")
                break
        if int(clip.get("contact_frame", -1)) != contact:
            failures.append(f"{name}: contact frame differs from contract")
        if float(clip.get("playback_speed_multiplier", 0.0)) != 2.0:
            failures.append(f"{name}: playback multiplier differs from 2.0")
        if previous is not None:
            boundary = max(
                quaternion_angle(before, after)
                for before, after in zip(
                    previous["rotation_wxyz"],
                    frames[0]["rotation_wxyz"],
                )
            )
            maximum_boundary = max(maximum_boundary, boundary)
        previous = frames[-1]
        stage_reports.append({
            "clip": name,
            "sourceFrameRange": [first, last],
            "frames": len(frames),
            "runtimeDurationSeconds": clip["runtime_duration_seconds"],
            "contactFrame": contact,
            "contactTick20Hz": round(contact / 60.0 / 2.0 * 20.0),
        })
    if maximum_boundary > 5.0:
        failures.append(
            f"stage boundary rotation {maximum_boundary:.5f} > 5 degrees"
        )
    entity_source = (REPO / (
        "src/main/java/com/projectseele/entity/EvaUnit01Entity.java"
    )).read_text(encoding="utf-8")
    engine_source = (REPO / (
        "src/main/java/com/projectseele/client/render/EvaMotionEngineV2.java"
    )).read_text(encoding="utf-8")
    graph_source = (REPO / (
        "src/main/java/com/projectseele/client/render/EvaPoseGraph.java"
    )).read_text(encoding="utf-8")
    code_tokens = {
        "entityPlayback2x": (
            "ORDINARY_ATTACK_PLAYBACK_SPEED = 2.0F" in entity_source
        ),
        "entityFrameIntervals": (
            "{44, 62, 32}" in entity_source
            and "{20, 48, 17}" in entity_source
        ),
        "serverContactResolution": (
            "resolveOrdinaryGroupCContact" in entity_source
            and "pendingOrdinaryContactTicks" in entity_source
        ),
        "liveDatabaseLoaded": (
            "motion/eva_ordinary_attack_group_c_v1.json" in engine_source
        ),
        "threeLiveClipNames": all(
            name in engine_source for name, *_ in STAGES
        ),
        "livePoseOwner": (
            "MOTION_ENGINE_LIVE_ACTION" in engine_source
            and "motionWrites.owner()" in graph_source
        ),
        "motionOwnsAimAndHead": (
            'contains("aim_pitch")' in graph_source
            and 'contains("head")' in graph_source
        ),
    }
    failures.extend(
        f"runtime code contract missing: {name}"
        for name, passed in code_tokens.items() if not passed
    )
    report = {
        "schema": 1,
        "result": "PASS" if not failures else "FAIL",
        "automaticVisualApproval": False,
        "selectedGroup": "ordinary_group_c",
        "playbackSpeedMultiplier": 2.0,
        "bones": len(live.get("bones", [])),
        "clips": len(live.get("clips", {})),
        "frames": sum(len(clip.get("frames", []))
                      for clip in live.get("clips", {}).values()),
        "maximumStageBoundaryRotationDegrees": maximum_boundary,
        "stages": stage_reports,
        "runtimeCodeContract": code_tokens,
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
