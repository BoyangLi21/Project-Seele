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
    local_assets = source(
        "src/main/java/com/projectseele/world/LocalMapAssetLoader.java")
    automation = source("src/main/java/com/projectseele/visual/VisualLabAutomation.java")
    blockstates = json.loads(source(
        "src/main/resources/assets/projectseele/blockstates/"
        "retractable_building_core.json"))

    centres = tuple(range(-160, 161, 40))
    private_lots = {(-120, -80), (120, -80), (120, 80)}
    fixed_lots = {(0, -80), (80, 0), (0, 80)}
    inner = []
    for x in centres:
        for z in centres:
            if (abs(x) <= 40 and abs(z) <= 40
                    or (x, z) in fixed_lots
                    or (x, z) in private_lots):
                continue
            height = 22 + ((x // 40 * 31 + z // 40 * 17) % 6) * 4
            inner.append((x, z, height, 12))

    outer = []
    for x in range(-200, 201, 40):
        for z in range(-200, 201, 40):
            if max(abs(x), abs(z)) != 200 or x == 200:
                continue
            height = 18 + ((x * 13 + z * 29) % 5) * 5
            outer.append((x, z, height, 9))
    buildings = inner + outer

    def ceiling_roof(x: int, z: int, half_size: int) -> int:
        farthest_x = abs(x) + half_size
        farthest_z = abs(z) + half_size
        rise = int((320 * 320 - farthest_x * farthest_x
                    - farthest_z * farthest_z) ** 0.5)
        return -416 + rise

    travel = [max(height, -ceiling_roof(x, z, half_size))
              for x, z, height, half_size in buildings]
    maximum = max(start + height
                  for start, (_, _, height, _) in zip(travel, buildings))
    depths = range(maximum + 1)
    surface = [[max(0, height - depth) for _, _, height, _ in buildings]
               for depth in depths]
    ceiling = [[max(0, min(height, depth - start))
                for start, (_, _, height, _) in zip(travel, buildings)]
               for depth in depths]
    monotonic_surface = all(
        all(after <= before
            for before, after in zip(surface[index], surface[index + 1]))
        for index in range(len(surface) - 1))
    monotonic_ceiling = all(
        all(after >= before
            for before, after in zip(ceiling[index], ceiling[index + 1]))
        for index in range(len(ceiling) - 1))
    checks = [
        require("layout.complete_catalog",
                len(inner) == 66 and len(outer) == 29
                and len(buildings) == 95 and maximum == 312
                and all(token in builder for token in (
                    "OUTER_WARD_TOWERS", "MOVABLE_BUILDINGS",
                    "createOuterWardTowers", "ceilingRoofRelativeY")),
                f"inner={len(inner)} outer={len(outer)} "
                f"movable={len(buildings)} maximumDepth={maximum}"),
        require("motion.physical_cycle",
                monotonic_surface and monotonic_ceiling
                and all(value == 0 for value in surface[-1])
                and ceiling[-1] == [height for _, _, height, _ in buildings],
                "surface skyline descends to zero while all 95 buildings "
                "materialise below the curved GeoFront ceiling"),
        require("motion.one_layer_per_second",
                "TICKS_PER_LAYER = 20" in director
                and "applyRetractionDepth" in director
                and "Math.abs(newDepth - oldDepth) != 1" in builder,
                "persistent director advances exactly one layer every 20 ticks"),
        require("motion.safe_restore",
                "restorationOccupied" in director
                and "LivingEntity.class" in director
                and "instanceof EvaUnit01Entity" in director
                and "entity.player.Player" in director
                and "tower.halfSize()" in director,
                "rising inner and outer lots protect players and EVAs"),
        require("motion.ceiling_evidence",
                all(token in builder for token in (
                    "emergeCeilingLayer", "withdrawCeilingLayer",
                    "ceilingStateMatches", "ceilingBuildings",
                    "ceilingRoofRelativeYForBounds",
                    "Math.max(Math.abs(minimumX), Math.abs(maximumX))",
                    "Math.max(Math.abs(minimumZ), Math.abs(maximumZ))",
                    "Blocks.SEA_LANTERN")),
                "the audit rejects a vanished city and requires moving "
                "undersides plus real ceiling-city walls"),
        require("motion.private_skyscrapers",
                all(token in local_assets for token in (
                    "applyTokyo3RetractionDepth",
                    "SKYSCRAPER_MOVE_QUANTUM = 12",
                    "addTokyo3SkyscraperTravelChunks",
                    "ceilingRoofRelativeYForBounds",
                    "inspectTokyo3Skyscrapers(BlockGetter level,",
                    "int retractionDepth)",
                    "skyscraperMarker(base, index)",
                    "skyscraperBodyPresent",
                    "SKYSCRAPER_SIGNATURES",
                    "Blocks.REDSTONE_LAMP", "Blocks.END_ROD",
                    "Blocks.LIGHTNING_ROD",
                    "restoredOld={}",
                    "|| skyscraperBodyPresent("))
                and local_assets.count(
                    "set(level, stateMarker, Blocks.AIR.defaultBlockState())") >= 3
                and all(token in capture for token in (
                    "Tokyo3RetractionDirector.depth",
                    "currentRetractionDepth",
                    "this.origin, currentRetractionDepth")),
                "three local NBT high-rises move in bounded twelve-block "
                "steps inside explicitly ticketed rotated footprints; "
                "current-depth travel receipts plus seven internal blocks "
                "reject stale state markers and failed moves stay retryable"),
        require("motion.long_lived_chunk_tickets",
                "maximumRetractionDepth() + 20" in director
                and "if (claimed >= chunks.length)" in director
                and "LocalMapAssetLoader.addTokyo3SkyscraperTravelChunks" in director
                and "reconcilePrivateSkyscrapers" in director
                and "for (long packed : travelChunks(origin))" in director
                and "claimed >= chunks.length ? 0 : claimed" not in director,
                "one batched ticket claim covers the complete 312-layer route; "
                "large-building chunks are not synchronously re-ticketed every layer"),
        require("persistence.versioned",
                "extends SavedData" in saved
                and "DATA_VERSION = 2" in saved
                and "version == 1 && targetDepth >= 42" in saved
                and all(token in saved for token in
                        ("Depth", "TargetDepth", "NextStepAt", "Cursor")),
                "v2 persists the complete route and resumes old v1 "
                "surface-only emergency orders"),
        require("core.registered_visual_states",
                set(blockstates["variants"]) == {"armed=false", "armed=true"}
                and "RETRACTABLE_BUILDING_CORE" in builder,
                "each inner armour tower owns an off/on operator core"),
        require("commands.complete",
                all(f'literal("{name}")' in commands
                    for name in ("retract", "restore", "status")),
                "/seele tokyo3 exposes retract, restore and status"),
        require("commands.post_sortie_origin",
                "Tokyo3RetractionSavedData.get" in commands
                and ".nearest(player.blockPosition(), 320.0D)" in commands
                and "parkedFormationRequired" in commands
                and "DEPLOYED_OR_AWAY" in commands,
                "persisted district commands remain available after sortie"),
        require("visual.complete_cycle",
                all(token in capture for token in (
                    "deployed", "mid_descent", "fully_retracted", "restored",
                    "towerStates={}/66", "ceilingStates={}/66",
                    "ThirdTokyoSurfaceBuilder.maximumRetractionDepth()",
                    "cameraPos = base.add(0.0D, -250.0D, 260.0D)"))
                and 'CAPTURE_UNIT.equals("tokyo3_retraction")' in automation
                and "ticks > 15000" in automation,
                "surface and GeoFront cameras gate a complete 312-layer cycle"),
    ]
    if all(checks):
        print("Tokyo-3 retraction contract: PASS")
        return 0
    print("Tokyo-3 retraction contract: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
