#!/usr/bin/env python3
"""Audit 20 Hz server-authoritative root deltas for live combat clips."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
BLOCKS_PER_SOURCE_METRE = 112.0 * 5.0 / 16.0


def sample(frames: list[dict], progress: float) -> list[float]:
    position = max(0.0, min(1.0, progress)) * (len(frames) - 1)
    first = int(math.floor(position))
    second = min(len(frames) - 1, first + 1)
    amount = position - first
    return [
        frames[first]["root_m"][axis]
        + (frames[second]["root_m"][axis]
           - frames[first]["root_m"][axis]) * amount
        for axis in range(3)
    ]


def audit_clip(name: str, clip: dict, synchronization_gain: float,
               root_clip: dict | None = None) -> dict:
    frames = clip["frames"]
    root_frames = (root_clip or clip)["frames"]
    speed = float(clip["playback_speed_multiplier"]) * synchronization_gain
    duration_ticks = (len(frames) - 1) / 60.0 / speed * 20.0
    ticks = max(1, math.ceil(duration_ticks))
    previous = sample(root_frames, 0.0)
    maximum = 0.0
    total = 0.0
    for tick in range(1, ticks + 1):
        current = sample(root_frames, min(1.0, tick / duration_ticks))
        dx = (current[0] - previous[0]) * BLOCKS_PER_SOURCE_METRE
        dz = -(current[2] - previous[2]) * BLOCKS_PER_SOURCE_METRE
        distance = math.hypot(dx, dz)
        maximum = max(maximum, distance)
        total += distance
        previous = current
    net = sample(root_frames, 1.0)
    start = sample(root_frames, 0.0)
    return {
        "clip": name,
        "effectivePlaybackSpeed": speed,
        "durationTicks": duration_ticks,
        "sampledServerTicks": ticks,
        "maximumHorizontalDeltaBlocksPerTick": maximum,
        "pathLengthBlocks": total,
        "netRightBlocks": (net[0] - start[0]) * BLOCKS_PER_SOURCE_METRE,
        "netForwardBlocks": -(net[2] - start[2]) * BLOCKS_PER_SOURCE_METRE,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ordinary", required=True, type=Path)
    parser.add_argument("--kick", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    ordinary = json.loads(args.ordinary.read_text(encoding="utf-8"))
    kick = json.loads(args.kick.read_text(encoding="utf-8"))
    rows = []
    for gain in (1.0, 1.25):
        for name, clip in ordinary["clips"].items():
            root_clip = (ordinary["clips"][
                "ordinary_attack_group_c_stage_1"]
                if name == "ordinary_attack_group_c_stage_1_loop"
                else clip)
            rows.append(audit_clip(name, clip, gain, root_clip))
        rows.append(audit_clip(
            "kick_side_left", kick["clips"]["kick_side_left"], gain
        ))
    maximum = max(
        row["maximumHorizontalDeltaBlocksPerTick"] for row in rows
    )
    failures = []
    if maximum > 6.0:
        failures.append(
            f"server root delta {maximum:.5f} blocks/tick exceeds 6.0"
        )
    entity = (REPO / (
        "src/main/java/com/projectseele/entity/EvaUnit01Entity.java"
    )).read_text(encoding="utf-8")
    loader = (REPO / (
        "src/main/java/com/projectseele/entity/EvaLiveCombatMotion.java"
    )).read_text(encoding="utf-8")
    project = (REPO / (
        "src/main/java/com/projectseele/ProjectSeele.java"
    )).read_text(encoding="utf-8")
    code = {
        "commonSideLoader": "getResourceAsStream" in loader,
        "startupPreload": "EvaLiveCombatMotion.preload()" in project,
        "ordinaryRootCurve": "EvaLiveCombatMotion.ordinary" in entity,
        "kickRootCurve": "EvaLiveCombatMotion.kick" in entity,
        "serverMoveAuthority": "this.move(MoverType.SELF, movement)" in entity,
        "sixBlockSafetyGate": (
            "movement.horizontalDistanceSqr() <= 36.0D" in entity
        ),
    }
    failures.extend(
        f"server root code contract missing: {name}"
        for name, passed in code.items() if not passed
    )
    report = {
        "schema": 1,
        "result": "PASS" if not failures else "FAIL",
        "automaticVisualApproval": False,
        "blocksPerSourceMetre": BLOCKS_PER_SOURCE_METRE,
        "maximumSynchronizationGain": 1.25,
        "maximumHorizontalDeltaBlocksPerTick": maximum,
        "clips": rows,
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
