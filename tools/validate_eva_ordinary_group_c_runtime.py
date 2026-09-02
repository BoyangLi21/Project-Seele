#!/usr/bin/env python3
"""Validate the promoted 1.5x Phase-T group-C live attack resource."""

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
LOOP_CLIP = "ordinary_attack_group_c_stage_1_loop"


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
            "playback_speed_multiplier") != 1.5:
        failures.append("playback speed multiplier is not 1.5")
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
        if float(clip.get("playback_speed_multiplier", 0.0)) != 1.5:
            failures.append(f"{name}: playback multiplier differs from 1.5")
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
            "contactTick20Hz": round(contact / 60.0 / 1.5 * 20.0),
        })
    loop_clip = live.get("clips", {}).get(LOOP_CLIP)
    if loop_clip is None:
        failures.append(f"missing live loop connector {LOOP_CLIP}")
    else:
        loop_frames = loop_clip.get("frames", [])
        entry_frames = live["clips"][STAGES[0][0]]["frames"]
        finish_frames = live["clips"][STAGES[2][0]]["frames"]
        if len(loop_frames) != len(entry_frames):
            failures.append("loop connector frame count differs from stage 1")
        elif (loop_frames[0]["rotation_wxyz"]
              != finish_frames[-1]["rotation_wxyz"]
              or loop_frames[0]["root_m"] != finish_frames[-1]["root_m"]):
            failures.append("loop connector does not start at stage 3 final pose")
        else:
            transition_frames = int(loop_clip.get(
                "loop_transition_frames", 0))
            if transition_frames != 12:
                failures.append("loop connector must use 12 transition frames")
            if any(
                loop["rotation_wxyz"] != entry["rotation_wxyz"]
                for loop, entry in zip(
                    loop_frames[transition_frames:],
                    entry_frames[transition_frames:])
            ):
                failures.append(
                    "loop connector changes stage 1 rotations after transition")
            loop_steps = []
            for before, after in zip(loop_frames, loop_frames[1:]):
                loop_steps.append(max(
                    quaternion_angle(left, right)
                    for left, right in zip(
                        before["rotation_wxyz"], after["rotation_wxyz"])
                ))
            maximum_boundary = max(
                maximum_boundary, max(loop_steps, default=0.0))
            stage_reports.append({
                "clip": LOOP_CLIP,
                "logicalStage": 0,
                "frames": len(loop_frames),
                "runtimeDurationSeconds": loop_clip[
                    "runtime_duration_seconds"],
                "contactFrame": loop_clip["contact_frame"],
                "contactTick20Hz": round(
                    loop_clip["contact_frame"] / 60.0 / 1.5 * 20.0),
                "loopTransitionFrames": transition_frames,
                "contactAuthority": loop_clip.get("contact_authority"),
            })
    stabilization = live.get("root_contact_stabilization", {})
    if stabilization.get("method") != "single_support_kick_exact_root_lock":
        failures.append("loop connector exact root support lock is missing")
    if maximum_boundary > 20.0:
        failures.append(
            f"stage/connector rotation {maximum_boundary:.5f} > 20 degrees"
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
        "entityPlayback1p5x": (
            "ORDINARY_ATTACK_PLAYBACK_SPEED = 1.5F" in entity_source
        ),
        "entityFrameIntervals": (
            "{44, 62, 32}" in entity_source
            and "{20, 48, 17}" in entity_source
        ),
        "serverContactResolution": (
            "resolveOrdinaryGroupCContact" in entity_source
            and "pendingOrdinaryContactTicks" in entity_source
        ),
        "serverRootAuthority": (
            "EvaLiveCombatMotion.ordinary" in entity_source
            and "applyLiveCombatRootMotion(true)" in entity_source
        ),
        "liveDatabaseLoaded": (
            "motion/eva_ordinary_attack_group_c_v1.json" in engine_source
        ),
        "liveClipNames": all(
            name in engine_source for name, *_ in STAGES
        ) and LOOP_CLIP in engine_source,
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
        "playbackSpeedMultiplier": 1.5,
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
