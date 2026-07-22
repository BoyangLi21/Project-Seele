#!/usr/bin/env python3
"""Static contract gate for the persistent EVA armament-rack loop."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def gate(label: str, condition: bool, detail: str) -> bool:
    if condition:
        print(f"[PASS] {label}")
        return True
    print(f"[FAIL] {label}: {detail}")
    return False


def main() -> int:
    blocks = read("src/main/java/com/projectseele/registry/ModBlocks.java")
    block_entities = read("src/main/java/com/projectseele/registry/ModBlockEntities.java")
    items = read("src/main/java/com/projectseele/registry/ModItems.java")
    rack = read("src/main/java/com/projectseele/world/EvaArmamentRackBlock.java")
    rack_entity = read("src/main/java/com/projectseele/world/EvaArmamentRackBlockEntity.java")
    eva = read("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    config = read("src/main/java/com/projectseele/config/SeeleConfig.java")
    integrated = read("src/main/java/com/projectseele/world/IntegratedNervMapBuilder.java")
    telemetry = read("src/main/java/com/projectseele/world/NervCommandTelemetry.java")
    commands = read("src/main/java/com/projectseele/visual/GeoFrontCommands.java")
    start = read("tools/start_test.bat")
    roadmap = read("docs/ROADMAP.md")
    docs = read("docs/EVA_ARMAMENT_RACK_TEST.md")

    expected_items = (
        "EVA_PROGRESSIVE_KNIFE",
        "EVA_PALLET_RIFLE",
        "EVA_POSITRON_CANNON",
        "EVA_N2_DEVICE",
        "LANCE_OF_LONGINUS",
    )
    results = [
        gate(
            "registry.block_entity",
            "EVA_ARMAMENT_RACK = BLOCKS.register" in blocks
            and "EVA_ARMAMENT_RACK = BLOCK_ENTITY_TYPES.register" in block_entities
            and "EVA_ARMAMENT_RACK = ITEMS.register" in items,
            "rack block, block entity, or BlockItem registration is missing",
        ),
        gate(
            "registry.armaments",
            all(name in items for name in expected_items),
            "one or more physical EVA armament items are not registered",
        ),
        gate(
            "inventory.persistent",
            "SLOT_COUNT = 5" in rack_entity
            and "ContainerHelper.saveAllItems" in rack_entity
            and "ContainerHelper.loadAllItems" in rack_entity
            and "NextSlot" in rack_entity,
            "five-slot inventory or persistent rotation cursor is missing",
        ),
        gate(
            "inventory.no_login_restock",
            "Called only when a map upgrade has placed a brand-new rack" in rack_entity
            and "if (newlyPlaced" in integrated,
            "empty player-used racks may be replenished on routine ensure",
        ),
        gate(
            "interaction.exchange",
            "findNearestEva" in rack
            and "takeNextArmament" in rack
            and "equipRackArmament" in rack
            and "unloadRackArmament" in rack
            and "Containers.dropContents" in rack,
            "nearest-EVA exchange, unload, or break-drop path is incomplete",
        ),
        gate(
            "interaction.safety",
            "canReceiveRackArmament" in eva
            and "horizontalDistanceSqr() < 0.01D" in eva
            and "isPilotControlLocked()" in eva
            and "isCrucified()" in eva,
            "moving, launching, berserk, unpowered, or crucified EVA safety gate is incomplete",
        ),
        gate(
            "eva.persistence",
            "SeeleWeapon" in eva
            and "SeeleArmamentMask" in eva
            and "DATA_ARMAMENT_MASK" in eva,
            "equipped weapon or physical loadout mask is not restart-safe",
        ),
        gate(
            "eva.strict_cycle",
            "requireRackLoadout" in config
            and ".define(\"requireRackLoadout\", false)" in config
            and "this.armamentAvailable(candidate)" in eva,
            "default-compatible strict rack mode or filtered R-key cycle is missing",
        ),
        gate(
            "command.telemetry",
            "armamentRackStock" in telemetry
            and '" / RACK "' in telemetry
            and "lowerArmamentRack(variant)" in telemetry,
            "NERV unit panels do not report the matching launch-bay rack stock",
        ),
        gate(
            "map.login_upgrade",
            "GeoFront login infrastructure gate" in commands
            and "IntegratedNervMapBuilder.prepareRuntime(current)" in commands,
            "existing connected saves do not receive bounded rack/pylon repair on login",
        ),
        gate(
            "map.schema_v17",
            "MAP_VERSION = 17" in integrated
            and integrated.count("ensureArmamentRacks(level);") == 3
            and "lowerArmamentRack" in integrated
            and "rack.stockStandardLoadout()" in integrated
            and "armamentRacksPresent(level)" in integrated,
            "three launch-bay racks are not part of map build/ensure/runtime audit",
        ),
        gate(
            "docs.manual_gate",
            "requireRackLoadout = false" in docs
            and "Shift+右键" in docs
            and "专用服务器" in docs
            and "2.4 🟨" in roadmap,
            "manual restart/multiplayer gate or roadmap status is missing",
        ),
        gate(
            "launcher.contract",
            "validate_eva_armament_contract.py" in start,
            "desktop launcher does not run the armament gate",
        ),
    ]

    json_paths = [
        ROOT / "src/main/resources/assets/projectseele/blockstates/eva_armament_rack.json",
        ROOT / "src/main/resources/assets/projectseele/models/block/eva_armament_rack.json",
        ROOT / "src/main/resources/assets/projectseele/models/item/eva_armament_rack.json",
        ROOT / "src/main/resources/assets/projectseele/models/item/eva_progressive_knife.json",
        ROOT / "src/main/resources/assets/projectseele/models/item/eva_pallet_rifle.json",
        ROOT / "src/main/resources/assets/projectseele/models/item/eva_positron_cannon.json",
        ROOT / "src/main/resources/assets/projectseele/models/item/eva_n2_device.json",
        ROOT / "src/main/resources/data/projectseele/loot_tables/blocks/eva_armament_rack.json",
    ]
    resources_valid = True
    try:
        for path in json_paths:
            json.loads(path.read_text(encoding="utf-8"))
        for locale in ("en_us", "zh_cn"):
            language = json.loads(read(
                f"src/main/resources/assets/projectseele/lang/{locale}.json"
            ))
            for key in (
                "block.projectseele.eva_armament_rack",
                "item.projectseele.eva_progressive_knife",
                "item.projectseele.eva_pallet_rifle",
                "item.projectseele.eva_positron_cannon",
                "item.projectseele.eva_n2_device",
                "msg.projectseele.armament_rack_equipped",
            ):
                if key not in language:
                    resources_valid = False
    except (OSError, UnicodeError, json.JSONDecodeError):
        resources_valid = False
    results.append(gate(
        "resources.complete",
        resources_valid,
        "rack block/item/loot JSON or bilingual names are invalid",
    ))

    passed = sum(results)
    print(f"\nEVA armament contract: {passed}/{len(results)} gates passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())