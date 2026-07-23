#!/usr/bin/env python3
"""Fail-closed contract for the canonical NERV EVA hangar logistics loop."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def method_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        return ""
    brace = source.find("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    return ""


def main() -> int:
    hangar = read("src/main/java/com/projectseele/world/EvaHangarBuilder.java")
    data = read("src/main/java/com/projectseele/world/EvaFleetSavedData.java")
    logistics = read("src/main/java/com/projectseele/world/EvaLogisticsDirector.java")
    surface_console = read(
        "src/main/java/com/projectseele/world/Tokyo3RecoveryConsole.java")
    operations_console = read(
        "src/main/java/com/projectseele/world/NervOperationsConsole.java")
    entity = read("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    events = read("src/main/java/com/projectseele/GameEvents.java")
    commands = read("src/main/java/com/projectseele/visual/EvaLogisticsCommands.java")
    integrated = read("src/main/java/com/projectseele/world/IntegratedNervMapBuilder.java")
    launcher = read("tools/start_test.bat")
    automation = read(
        "src/main/java/com/projectseele/visual/VisualLabAutomation.java")
    capture = read(
        "src/main/java/com/projectseele/client/visual/VisualCaptureManager.java")
    visual_validator = read("tools/validate_visual_capture_run.py")
    carrier_visuals = read(
        "src/main/java/com/projectseele/world/NervCarrierVisuals.java")
    carrier_entity = read(
        "src/main/java/com/projectseele/entity/NervCarrierPlatformEntity.java")
    carrier_renderer = read(
        "src/main/java/com/projectseele/client/render/NervCarrierPlatformRenderer.java")
    registry = read("src/main/java/com/projectseele/registry/ModEntities.java")
    client_events = read("src/main/java/com/projectseele/client/ClientEvents.java")

    reset = method_body(logistics, "public static EvaUnit01Entity forceReset")
    hangar_controls = method_body(
        logistics, "private static void handleHangarControl")
    horizontal_transport = method_body(
        logistics, "private static void tickHorizontal")
    canonical_before_add = reset.find("EvaFleetSavedData.get(server).put") \
        < reset.find("level.addFreshEntity(replacement)")
    checks = [
        ("hangar.three_wet_cages", all(token in hangar for token in (
            "for (int variant = 0; variant < 3; variant++)",
            "buildChamber", "buildShoulderCatwalk", "buildObservationGallery",
            "LCL_SHOULDER_LAYERS = 22", "ModFluids.LCL_SOURCE",
            "Dedicated shell receipts",
            "bed.offset(-HALF_WIDTH, CHAMBER_HEIGHT, 0)",
            "bed.offset(HALF_WIDTH, CHAMBER_HEIGHT, 0)",
            "controls == 6", "galleries == 3", "walkableRoutes == 3"))),
        ("hangar.walkable_rear_boarding", all(token in hangar for token in (
            "CATWALK_FLOOR_ABOVE_BED = 24",
            "REAR_CROSS_Z_FROM_BED = -12",
            "REAR_BOARDING_Z_FROM_BED = -6",
            "buildBoardingConnector", "isBoardingRouteWalkable",
            "floorY != origin.getY() + GALLERY_Y",
            "Direction.UP", "Blocks.IRON_BARS"))),
        ("hangar.physical_rail_route", all(token in hangar for token in (
            "buildTransportTunnel", "setCarrier", "restoreStaticCarrier",
            "IntegratedNervMapBuilder.lowerLiftBed(variant)",
            "Blocks.LODESTONE"))),
        ("fleet.persistent_state_machine", all(token in data for token in (
            "SavedData", "canonicalId", "PARKED", "DRAINING", "TO_SILO",
            "SILO_READY", "DEPLOYED", "DESCENDING", "TO_HANGAR", "FILLING",
            "setDirty()"))),
        ("fleet.no_teleport_logistics", all(token in logistics for token in (
            "FLUID_LAYER_TICKS = 4", "HORIZONTAL_TRANSFER_TICKS = 160",
            "VERTICAL_BLOCKS_PER_TICK = 2.0D", "tickHorizontal", "tickDescent",
            "moveOnNervCarrier", "setLclLayer"))
            and "changeDimension" not in logistics
            and "teleportTo" not in method_body(logistics,
                                                  "private static void tickUnit")),
        ("fleet.surface_command_recovery", all(token in logistics for token in (
            "RECOVERY_MAX_SPEED_SQR", "must be motionless",
            "Tokyo3RecoveryConsole.controlPosition", "requestRecovery"))
            and "AUTO_RECOVERY" not in logistics
            and all(token in surface_console for token in (
                "Surface command post", "CONTROL_COUNT = 3",
                "controlPosition", "position.below(2)",
                "Blocks.POLISHED_BLACKSTONE", "EVA-%02d\\nRECOVERY"))),
        ("fleet.hangar_status_read_only", all(
            token in hangar_controls for token in (
                "requestPrepare", "Status snapshot = status",
                "[NERV HANGAR STATUS]", "ChatFormatting.AQUA"))
            and "requestRecovery" not in hangar_controls),
        ("fleet.world_global_singleton", all(token in logistics for token in (
            "validateCanonical", "server.getAllLevels()",
            "level.getAllEntities()", "duplicate.discard()",
            "Repairing missing PARKED canonical", "createParkedCanonical"))
            and "claimIfAbsent" in data
            and canonical_before_add
            and all(token in events for token in (
                "EntityJoinLevelEvent", "EvaLogisticsDirector.validateCanonical",
                "event.setCanceled(true)"))),
        ("fleet.entity_interlock", all(token in entity for token in (
            "DATA_NERV_LOGISTICS_LOCKED", "SeeleNervLogisticsLocked",
            "isNervLogisticsLocked", "setNervLogisticsLocked",
            "EvaHangarBuilder.isHangarBed", "moveOnNervCarrier",
            "prepareForNervRecovery", "armPreparedLaunch"))),
        ("fleet.operator_commands", all(token in commands for token in (
            'Commands.literal("eva")', 'Commands.literal("status")',
            'Commands.literal("prepare")', 'Commands.literal("reset")',
            'Commands.literal("hangar")', 'Commands.literal("recovery_control")',
            "forceReset(level, variant)", "requestPrepare"))
            and 'Commands.literal("recover")' not in commands
            and "requestRecovery" not in commands),
        ("fleet.map_v18_upgrade", all(token in integrated for token in (
            "MAP_VERSION = 18", "EvaHangarBuilder.build(level, GEOFRONT_ORIGIN)",
            "EvaHangarBuilder.ensure(level, GEOFRONT_ORIGIN)",
            "Tokyo3RecoveryConsole.build(level, TOKYO3_ORIGIN)",
            "Tokyo3RecoveryConsole.ensure(level, TOKYO3_ORIGIN)",
            "repairInterruptedCityRestoration"))),
        ("controls.supported_platforms", all(token in operations_console for token in (
            "buildControlPlatform", "Continuous supported dais",
            "BlockPos support = base.below()",
            "Blocks.POLISHED_BLACKSTONE_BRICK_STAIRS"))
            and all(token in surface_console for token in (
                "continuous dais", "supports == CONTROL_COUNT"))),
        ("hangar.shaft_safe_transport", all(token in hangar for token in (
            "int shaftPortalZ = destinationZ",
            "IntegratedNervMapBuilder.SHAFT_OUTER_RADIUS",
            "if (z > shaftPortalZ)",
            "rail. A tunnel roof here used to cap all three shafts"))
            and all(token in integrated for token in (
                "auditedCarrierDoor", "carrierPortalBottom",
                "southWall || auditedGantryDoor || auditedCarrierDoor"))),
        ("fleet.low_overhead_visual_carrier", all(
            token in horizontal_transport for token in (
                "NervCarrierVisuals.update", "NervCarrierVisuals.remove",
                "restoreStaticCarrier"))
            and "EvaHangarBuilder.moveCarrier" not in horizontal_transport
            and all(token in carrier_visuals for token in (
                "PLATFORM_BY_EVA", "NERV_CARRIER_PLATFORM",
                "moveControlled", "resetRuntime"))
            and all(token in carrier_entity for token in (
                "CONTROL_TIMEOUT_TICKS", "ticksWithoutControl",
                "this.discard()", "this.noPhysics = true"))
            and "NERV_CARRIER_PLATFORM" in registry
            and ".noSave()" in registry
            and "NervCarrierPlatformRenderer" in client_events
            and "renderSingleBlock" in carrier_renderer),
        ("fleet.mod_owned_chunk_tickets", all(token in logistics for token in (
            "ForgeChunkManager.forceChunk", "ROUTE_TICKET_STATE",
            "logistics route tickets", "maintainDormantLaunch",
            "tickDormantNervLaunch", "LAST_ENTITY_TICK"))
            and "setChunkForced" not in logistics
            and "getForcedChunks" not in logistics),
        ("fleet.full_runtime_cycle_gate", all(token in automation for token in (
            "TrainingPilotDirector.start", "EntryPlugDirector.hasBoardedPilot",
            "EvaLogisticsDirector.requestPrepare", "SILO_READY",
            "releaseLaunchFromCommand", "EvaLogisticsDirector.requestRecovery", "DESCENDING",
            "TO_HANGAR", "FILLING", "PARKED",
            "VISUAL GEOFRONT LOGISTICS CYCLE VALID"))
            and all(token in capture for token in (
                "recovery_descent", "wet_cage_return",
                "TIMEOUT_TICKS = 2400"))
            and all(token in visual_validator for token in (
                '"geofront_sortie": 7',
                "VISUAL GEOFRONT LOGISTICS CYCLE VALID"))),
        ("fleet.launcher_gate", "validate_eva_logistics_contract.py" in launcher),
    ]

    passed = 0
    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        passed += int(bool(ok))
    print(f"\nEVA logistics contract: {passed}/{len(checks)} gates passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
