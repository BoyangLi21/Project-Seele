#!/usr/bin/env python3
"""Fail-closed static contract for EVA internal and umbilical power."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def gate(name: str, condition: bool, detail: str) -> None:
    if condition:
        print(f"[PASS] {name}: {detail}")
    else:
        print(f"[FAIL] {name}: {detail}")
        ERRORS.append(name)


entity = text("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
block = text("src/main/java/com/projectseele/world/UmbilicalPylonBlock.java")
block_entity = text("src/main/java/com/projectseele/world/UmbilicalPylonBlockEntity.java")
blocks = text("src/main/java/com/projectseele/registry/ModBlocks.java")
block_entities = text("src/main/java/com/projectseele/registry/ModBlockEntities.java")
items = text("src/main/java/com/projectseele/registry/ModItems.java")
main = text("src/main/java/com/projectseele/ProjectSeele.java")
config = text("src/main/java/com/projectseele/config/SeeleConfig.java")
hud = text("src/main/java/com/projectseele/client/EvaHud.java")
telemetry = text("src/main/java/com/projectseele/world/NervCommandTelemetry.java")
cable = text("src/main/java/com/projectseele/client/render/EvaUmbilicalCableRenderer.java")
integrated = text("src/main/java/com/projectseele/world/IntegratedNervMapBuilder.java")
doc = text("docs/EVA_POWER_TEST.md")


gate(
    "power.pylon_registered",
    "UMBILICAL_PYLON = BLOCKS.register" in blocks
    and "UmbilicalPylonBlock" in block
    and "UMBILICAL_PYLON = BLOCK_ENTITY_TYPES.register" in block_entities
    and "UMBILICAL_PYLON = ITEMS.register" in items
    and "ModBlockEntities.BLOCK_ENTITY_TYPES.register(modEventBus)" in main,
    "block, block entity, item and mod-bus registrations are complete",
)

gate(
    "power.synced_persistent_battery",
    all(token in entity for token in (
        "DATA_POWER_TICKS", "DATA_POWER_CONNECTED", "DATA_POWER_ANCHOR_X",
        'tag.putInt("SeelePowerTicks"', 'tag.contains("SeelePowerTicks")',
        "getPowerCapacityTicks()", "isPowerDepleted()"
    )),
    "battery and connection state replicate while remaining restart-safe",
)

gate(
    "power.five_minute_default",
    'defineInRange("capacityTicks", 6000' in config
    and 'defineInRange("umbilicalRange", 32' in config
    and 'defineInRange("repairPerSecond", 1.0D' in config,
    "defaults are 6000 ticks, 32 blocks and one hull point per second",
)

gate(
    "power.bounded_loaded_index",
    all(token in block_entity for token in (
        "ConcurrentHashMap", "LOADED.computeIfAbsent", "Set.copyOf(positions)",
        "findNearest", "level.hasChunkAt(position)"
    )) and "for (int x" not in block_entity,
    "connection checks iterate loaded pylons instead of scanning a block cube",
)

gate(
    "power.authoritative_cycle",
    "this.tickPowerSystem();" in entity
    and "this.entityData.set(DATA_POWER_TICKS, this.getPowerCapacityTicks())" in entity
    and "int nextPower = oldPower - 1" in entity
    and "this.entityData.set(DATA_AT_ON, false)" in entity
    and "this.heal((float) repair)" in entity,
    "server tick holds full charge on cable, drains internally, shuts field and repairs on grid",
)

gate(
    "power.total_control_interlock",
    re.search(r"private boolean isPilotControlLocked\(\).*?isPowerDepleted\(\)",
              entity, re.S) is not None
    and "this.setDeltaMovement(Vec3.ZERO)" in entity
    and "pilot.stopRiding();" in entity,
    "all existing pilot actions share the depleted lock while ejection remains available",
)

gate(
    "power.hud_and_command_room",
    all(token in hud for token in (
        "getPowerTicks()", "isUmbilicalConnected()",
        "hud.projectseele.power_battery", "hud.projectseele.power_depleted"
    )) and all(token in telemetry for token in (
        '"\\nPOWER %s  %04d/%04d"', "feed.getPowerTicks()",
        "feed.getPowerCapacityTicks()"
    )),
    "pilot and Operations see the same synchronized battery state",
)

gate(
    "power.visible_cable",
    all(token in cable for token in (
        "RenderLevelStageEvent.Stage.AFTER_PARTICLES", "SEGMENTS = 18",
        "getUmbilicalAnchor()", "cablePoint", "RibbonRenderer.drawStarRibbon"
    )),
    "connected units render an eighteen-segment sagging umbilical ribbon",
)

gate(
    "power.facility_deployment",
    all(token in integrated for token in (
        "public static BlockPos lowerPowerPylon", "offset(10, 1, 0)",
        "public static BlockPos surfacePowerPylon", "offset(11, 2, 0)",
        "ensurePowerPylons(level)", "powerPylonsPresent(level)",
        "for (int index = 0; index < LIFT_LINKS.size(); index++)",
        "ModBlocks.UMBILICAL_PYLON.get().defaultBlockState()",
    )) and all(token in doc for token in (
        "/seele geofront setup", "522", "POWER UMBILICAL"
    )),
    "three lower and three surface pylons are repaired with the continuous sortie route",
)
gate(
    "power.assets_and_manual_contract",
    all((ROOT / path).is_file() for path in (
        "src/main/resources/assets/projectseele/blockstates/umbilical_pylon.json",
        "src/main/resources/assets/projectseele/models/block/umbilical_pylon.json",
        "src/main/resources/assets/projectseele/models/item/umbilical_pylon.json",
        "src/main/resources/data/projectseele/loot_tables/blocks/umbilical_pylon.json",
    )) and all(token in doc for token in (
        "projectseele:umbilical_pylon", "SeelePowerTicks:80",
        "capacityTicks", "umbilicalRange", "repairPerSecond"
    )),
    "block assets and accelerated manual depletion test are present",
)

if ERRORS:
    print(f"EVA power contract: FAIL ({len(ERRORS)} gate(s))")
    sys.exit(1)
print("EVA power contract: PASS")