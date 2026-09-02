#!/usr/bin/env python3
"""Validate the promoted 1.5x K1 side-kick resource and runtime wiring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--live", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    live = json.loads(args.live.read_text(encoding="utf-8"))
    failures = []
    clip = live.get("clips", {}).get("kick_side_left")
    review_clip = review.get("clips", {}).get("kick_group_side_left")
    if live.get("schema") != 2 or live.get("preview_only") is not False:
        failures.append("live kick schema/preview contract differs")
    if live.get("live_gameplay_replacement") is not True:
        failures.append("live kick replacement flag is false")
    if live.get("human_review", {}).get("selected") != "K1_SIDE_LEFT":
        failures.append("K1 human-selection receipt is missing")
    if len(live.get("bones", [])) != 50 or "knife" in live.get("bones", []):
        failures.append("live kick must contain 50 non-knife bones")
    if clip is None or review_clip is None:
        failures.append("selected kick clip is missing")
    else:
        expected = []
        for source_frame in review_clip["frames"]:
            frame = json.loads(json.dumps(source_frame))
            frame["rotation_wxyz"] = frame["rotation_wxyz"][:-1]
            expected.append(frame)
        if clip.get("frames") != expected:
            failures.append("live kick frames differ from reviewed K1 poses")
        if float(clip.get("playback_speed_multiplier", 0.0)) != 1.5:
            failures.append("kick clip playback is not 1.5x")
        if int(clip.get("contact_frame", -1)) != 48:
            failures.append("kick contact frame is not 48")
    contract = live.get("gameplay_contract", {})
    if contract.get("playback_speed_multiplier") != 1.5:
        failures.append("kick gameplay speed is not 1.5x")
    if contract.get("contact_tick_20hz") != 11:
        failures.append("kick contact tick is not 11")
    if contract.get("damage") != 50.0 or contract.get("cooldown_ticks") != 50:
        failures.append("existing stomp balance changed during kick promotion")
    if contract.get("damage_and_cooldown_changed") is not False:
        failures.append("kick balance-change declaration differs")

    entity = (REPO / (
        "src/main/java/com/projectseele/entity/EvaUnit01Entity.java"
    )).read_text(encoding="utf-8")
    engine = (REPO / (
        "src/main/java/com/projectseele/client/render/EvaMotionEngineV2.java"
    )).read_text(encoding="utf-8")
    graph = (REPO / (
        "src/main/java/com/projectseele/client/render/EvaPoseGraph.java"
    )).read_text(encoding="utf-8")
    zh = (REPO / (
        "src/main/resources/assets/projectseele/lang/zh_cn.json"
    )).read_text(encoding="utf-8")
    code = {
        "entitySpeed1p5x": "KICK_PLAYBACK_SPEED = 1.5F" in entity,
        "serverSequence": (
            "DATA_KICK_SEQUENCE" in entity
            and "clientKickStartTick" in entity
        ),
        "contactDamage": (
            "pendingKickContactTicks" in entity
            and "resolveSideKickContact" in entity
        ),
        "bidirectionalBuffer": (
            "ordinaryAfterKickBufferTicks" in entity
            and "kickAfterOrdinaryBufferTicks" in entity
        ),
        "serverRootAuthority": (
            "EvaLiveCombatMotion.kick" in entity
            and "applyLiveCombatRootMotion(false)" in entity
        ),
        "liveDatabase": (
            "motion/eva_kick_side_left_v1.json" in engine
            and 'db.clip("kick_side_left")' in engine
        ),
        "poseGraphAction": 'return "kick_attack"' in graph,
        "keyBLabel": '"key.projectseele.stomp": "EVA：侧踹"' in zh,
    }
    failures.extend(
        f"runtime code contract missing: {name}"
        for name, passed in code.items() if not passed
    )
    report = {
        "schema": 1,
        "result": "PASS" if not failures else "FAIL",
        "automaticVisualApproval": False,
        "selectedKick": "K1_SIDE_LEFT",
        "playbackSpeedMultiplier": 1.5,
        "bones": len(live.get("bones", [])),
        "clips": len(live.get("clips", {})),
        "frames": len(clip.get("frames", [])) if clip else 0,
        "contactFrame": 48,
        "contactTick20Hz": contract.get("contact_tick_20hz"),
        "damage": contract.get("damage"),
        "cooldownTicks": contract.get("cooldown_ticks"),
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
