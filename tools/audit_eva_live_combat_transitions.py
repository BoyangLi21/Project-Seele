#!/usr/bin/env python3
"""Audit live ordinary/kick seams and the render-rate inertial connector."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
FPS = 60.0
PLAYBACK_SPEED = 1.5
TRANSITION_HALF_LIFE = 0.060
TRANSITION_SECONDS = 0.14


def normalize(value: list[float]) -> list[float]:
    length = math.sqrt(sum(item * item for item in value))
    return [item / length for item in value]


def slerp(first: list[float], second: list[float], amount: float) -> list[float]:
    left = normalize(first)
    right = normalize(second)
    dot = sum(a * b for a, b in zip(left, right))
    if dot < 0.0:
        right = [-value for value in right]
        dot = -dot
    dot = max(-1.0, min(1.0, dot))
    if dot > 0.9995:
        return normalize([
            a + (b - a) * amount for a, b in zip(left, right)
        ])
    angle = math.acos(dot)
    sine = math.sin(angle)
    return normalize([
        a * math.sin((1.0 - amount) * angle) / sine
        + b * math.sin(amount * angle) / sine
        for a, b in zip(left, right)
    ])


def angle(first: list[float], second: list[float]) -> float:
    dot = abs(sum(a * b for a, b in zip(normalize(first), normalize(second))))
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def sample(frames: list[dict], source_frame: float) -> dict:
    position = min(max(0.0, source_frame), len(frames) - 1)
    first = int(math.floor(position))
    second = min(len(frames) - 1, first + 1)
    amount = position - first
    return {
        "rotation_wxyz": [
            slerp(left, right, amount)
            for left, right in zip(
                frames[first]["rotation_wxyz"],
                frames[second]["rotation_wxyz"],
            )
        ],
        "root_y": (
            frames[first]["root_m"][1]
            + (frames[second]["root_m"][1]
               - frames[first]["root_m"][1]) * amount
        ),
    }


def raw_seam(first: dict, second: dict) -> float:
    return max(
        angle(left, right)
        for left, right in zip(
            first["rotation_wxyz"], second["rotation_wxyz"]
        )
    )


def simulate_transition(source_last: dict, destination: list[dict],
                        destination_family: str) -> dict:
    current = [list(value) for value in source_last["rotation_wxyz"]]
    current_root = float(source_last["root_m"][1])
    maximum_step = 0.0
    maximum_root_step = 0.0
    for render_frame in range(24):
        elapsed = render_frame / FPS
        target = sample(destination, render_frame * PLAYBACK_SPEED)
        half_life = (TRANSITION_HALF_LIFE
                     if elapsed < TRANSITION_SECONDS
                     else 0.030 if destination_family == "kick" else 0.025)
        alpha = 1.0 - math.exp(-math.log(2.0) / FPS / half_life)
        updated = [
            slerp(before, wanted, alpha)
            for before, wanted in zip(current, target["rotation_wxyz"])
        ]
        maximum_step = max(
            maximum_step,
            max(angle(before, after)
                for before, after in zip(current, updated)),
        )
        root_step = (target["root_y"] - current_root) * alpha
        root_step = max(-0.0055, min(0.0055, root_step))
        next_root = current_root + root_step
        maximum_root_step = max(
            maximum_root_step, abs(next_root - current_root)
        )
        current = updated
        current_root = next_root
    return {
        "maximumRenderedRotationStepDegrees": maximum_step,
        "maximumRenderedRootYStepMetres": maximum_root_step,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ordinary", required=True, type=Path)
    parser.add_argument("--kick", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    ordinary = json.loads(args.ordinary.read_text(encoding="utf-8"))
    kick = json.loads(args.kick.read_text(encoding="utf-8"))
    failures = []
    if ordinary["bones"] != kick["bones"]:
        failures.append("ordinary and kick live bone orders differ")
    clips = ordinary["clips"]
    kick_frames = kick["clips"]["kick_side_left"]["frames"]
    internal_pairs = (
        ("ordinary_attack_group_c_stage_1",
         "ordinary_attack_group_c_stage_2"),
        ("ordinary_attack_group_c_stage_2",
         "ordinary_attack_group_c_stage_3"),
        ("ordinary_attack_group_c_stage_3",
         "ordinary_attack_group_c_stage_1_loop"),
        ("ordinary_attack_group_c_stage_1_loop",
         "ordinary_attack_group_c_stage_2"),
    )
    internal = []
    for first_name, second_name in internal_pairs:
        seam = raw_seam(
            clips[first_name]["frames"][-1],
            clips[second_name]["frames"][0],
        )
        internal.append({
            "from": first_name,
            "to": second_name,
            "rawBoundaryRotationDegrees": seam,
        })
        if seam > 3.0:
            failures.append(
                f"ordinary seam {first_name}->{second_name} {seam:.5f} > 3"
            )
    loop_steps = [
        raw_seam(before, after)
        for before, after in zip(
            clips["ordinary_attack_group_c_stage_1_loop"]["frames"],
            clips["ordinary_attack_group_c_stage_1_loop"]["frames"][1:],
        )
    ]
    maximum_loop_step = max(loop_steps, default=0.0)
    if maximum_loop_step > 20.0:
        failures.append(
            f"ordinary loop connector step {maximum_loop_step:.5f} > 20"
        )

    cross = []
    for ordinary_name in (
        "ordinary_attack_group_c_stage_1",
        "ordinary_attack_group_c_stage_2",
        "ordinary_attack_group_c_stage_3",
        "ordinary_attack_group_c_stage_1_loop",
    ):
        result = simulate_transition(
            clips[ordinary_name]["frames"][-1], kick_frames, "kick"
        )
        result.update({"from": ordinary_name, "to": "kick_side_left"})
        cross.append(result)
    kick_to_ordinary = simulate_transition(
        kick_frames[-1],
        clips["ordinary_attack_group_c_stage_1"]["frames"],
        "ordinary",
    )
    kick_to_ordinary.update({
        "from": "kick_side_left",
        "to": "ordinary_attack_group_c_stage_1",
    })
    cross.append(kick_to_ordinary)
    maximum_cross_rotation = max(
        row["maximumRenderedRotationStepDegrees"] for row in cross
    )
    maximum_cross_root = max(
        row["maximumRenderedRootYStepMetres"] for row in cross
    )
    if maximum_cross_rotation > 20.0:
        failures.append(
            f"cross-action rendered rotation {maximum_cross_rotation:.5f} > 20"
        )
    if maximum_cross_root > 0.006:
        failures.append(
            f"cross-action rendered root step {maximum_cross_root:.7f} > 0.006"
        )
    entity_source = (REPO / (
        "src/main/java/com/projectseele/entity/EvaUnit01Entity.java"
    )).read_text(encoding="utf-8")
    engine_source = (REPO / (
        "src/main/java/com/projectseele/client/render/EvaMotionEngineV2.java"
    )).read_text(encoding="utf-8")
    code = {
        "crossActionBuffer30Ticks": (
            "CROSS_ACTION_BUFFER_TICKS = 30" in entity_source
        ),
        "ordinaryToKickBuffer": "kickAfterOrdinaryBufferTicks" in entity_source,
        "kickToOrdinaryBuffer": "ordinaryAfterKickBufferTicks" in entity_source,
        "renderTransitionHalfLife": "return 0.060D" in engine_source,
        "rootInertialization": "currentLiveRootYOffset" in engine_source,
        "rootStepLimit": "MAX_LIVE_ROOT_STEP_METRES = 0.0055F" in engine_source,
        "geckoEntryInitialization": (
            "geckoRotationAsMotionQuaternion(geckoBone)" in engine_source
        ),
    }
    failures.extend(
        f"transition code contract missing: {name}"
        for name, passed in code.items() if not passed
    )
    report = {
        "schema": 1,
        "result": "PASS" if not failures else "FAIL",
        "automaticVisualApproval": False,
        "ordinaryPlaybackSpeedMultiplier": PLAYBACK_SPEED,
        "kickPlaybackSpeedMultiplier": PLAYBACK_SPEED,
        "internalOrdinaryBoundaries": internal,
        "maximumLoopConnectorStepDegrees": maximum_loop_step,
        "crossActionTransitions": cross,
        "maximumCrossActionRenderedRotationStepDegrees": (
            maximum_cross_rotation),
        "maximumCrossActionRenderedRootYStepMetres": maximum_cross_root,
        "runtimeCodeContract": code,
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
