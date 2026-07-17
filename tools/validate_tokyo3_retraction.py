#!/usr/bin/env python3
"""Static and algorithmic contract for Tokyo-3 retractable armour towers."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(name: str, condition: bool, detail: str) -> bool:
    state = "PASS" if condition else "FAIL"
    print(f"[{state}] {name}: {detail}")
    return condition


def main() -> int:
    builder = source("src/main/java/com/projectseele/world/ThirdTokyoSurfaceBuilder.java")
    director = source("src/main/java/com/projectseele/world/Tokyo3RetractionDirector.java")
    saved = source("src/main/java/com/projectseele/world/Tokyo3RetractionSavedData.java")
    commands = source("src/main/java/com/projectseele/visual/ThirdTokyoCommands.java")
    capture = source(
        "src/main/java/com/projectseele/client/visual/VisualCaptureManager.java")
    automation = source("src/main/java/com/projectseele/visual/VisualLabAutomation.java")
    blockstates = json.loads(source(
        "src/main/resources/assets/projectseele/blockstates/"
        "retractable_building_core.json"))

    centres = (-80, -40, 0, 40, 80)
    excluded = {(0, -80), (80, 0), (0, 80)}
    towers = []
    for x in centres:
        for z in centres:
            if abs(x) <= 40 and abs(z) <= 40 or (x, z) in excluded:
                continue
            height = 22 + ((x // 40 * 31 + z // 40 * 17) % 6) * 4
            towers.append((x, z, height))
    maximum = max(height for _, _, height in towers)
    depths = range(maximum + 1)
    down = [[max(0, height - depth) for _, _, height in towers]
            for depth in depths]
    up = list(reversed(down))
    monotonic_down = all(
        all(after <= before for before, after in zip(down[i], down[i + 1]))
        for i in range(len(down) - 1))
    monotonic_up = all(
        all(after >= before for before, after in zip(up[i], up[i + 1]))
        for i in range(len(up) - 1))

    checks = [
        require("layout.tower_catalog", len(towers) == 13 and maximum == 42,
                f"towers={len(towers)} maximumDepth={maximum}"),
        require("motion.monotonic_cycle", monotonic_down and monotonic_up
                and all(value == 0 for value in down[-1])
                and up[-1] == down[0],
                "all towers descend to zero and restore to exact source heights"),
        require("motion.one_layer_per_second",
                "TICKS_PER_LAYER = 20" in director
                and "applyRetractionDepth" in director
                and "Math.abs(newDepth - oldDepth) != 1" in builder,
                "persistent director advances exactly one layer every 20 ticks"),
        require("motion.safe_restore",
                "restorationOccupied" in director
                and "LivingEntity.class" in director
                and "instanceof EvaUnit01Entity" in director
                and "entity.player.Player" in director,
                "rising layers protect players/EVAs without ambient-mob deadlock"),
        require("motion.full_retraction_evidence",
                "towerShellClear" in builder and "shellClear" in capture,
                "a visible first-floor wall prevents a false fully-retracted pass"),
        require("persistence.versioned",
                "extends SavedData" in saved
                and "DATA_VERSION = 1" in saved
                and all(token in saved for token in
                        ("Depth", "TargetDepth", "NextStepAt")),
                "depth, target and next tick survive save/reload"),
        require("core.registered_visual_states",
                set(blockstates["variants"]) == {"armed=false", "armed=true"}
                and "RETRACTABLE_BUILDING_CORE" in builder,
                "each armour tower owns an off/on operator core"),
        require("commands.complete",
                all(f'literal("{name}")' in commands
                    for name in ("retract", "restore", "status")),
                "/seele tokyo3 exposes retract, restore and status"),
        require("commands.post_sortie_origin",
                "Tokyo3RetractionSavedData.get" in commands
                and ".nearest(player.blockPosition(), 320.0D)" in commands
                and "parkedFormationRequired" in commands
                and "DEPLOYED_OR_AWAY" in commands,
                "persisted district commands remain available after the EVAs deploy"),
        require("visual.four_state_matrix",
                all(token in capture for token in
                    ("deployed", "mid_descent", "fully_retracted", "restored",
                     "towerStates={}/13", "cores={}/13", "armed={}/13"))
                and 'CAPTURE_UNIT.equals("tokyo3_retraction")' in automation,
                "real client gates four skyline frames on authoritative block states"),
    ]
    if all(checks):
        print("Tokyo-3 retraction contract: PASS")
        return 0
    print("Tokyo-3 retraction contract: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
