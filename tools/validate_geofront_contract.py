#!/usr/bin/env python3
"""Fail closed when the continuous Tokyo-3 / GeoFront map contract drifts."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def gate(name: str, condition: bool, detail: str) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return condition


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
                return source[brace + 1:index]
    return ""


def main() -> int:
    dimension_type = json.loads(text(
        "src/main/resources/data/projectseele/dimension_type/geofront.json"))
    dimension = json.loads(text(
        "src/main/resources/data/projectseele/dimension/geofront.json"))
    builder = text("src/main/java/com/projectseele/world/GeoFrontBuilder.java")
    integrated = text(
        "src/main/java/com/projectseele/world/IntegratedNervMapBuilder.java")
    tokyo3_landscape = text(
        "src/main/java/com/projectseele/world/Tokyo3LandscapeBuilder.java")
    geofront_landscape = text(
        "src/main/java/com/projectseele/world/GeoFrontLandscapeBuilder.java")
    operations = text(
        "src/main/java/com/projectseele/world/NervOperationsCentreBuilder.java")
    commands = text("src/main/java/com/projectseele/visual/GeoFrontCommands.java")
    automation = text("src/main/java/com/projectseele/visual/VisualLabAutomation.java")
    capture = text(
        "src/main/java/com/projectseele/client/visual/VisualCaptureManager.java")
    entity = text("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    fluids = text("src/main/java/com/projectseele/registry/ModFluids.java")
    lcl_type = text("src/main/java/com/projectseele/fluid/LclFluidType.java")
    lcl_events = text("src/main/java/com/projectseele/event/LclEvents.java")
    blocks = text("src/main/java/com/projectseele/registry/ModBlocks.java")
    sortie_packet = text(
        "src/main/java/com/projectseele/network/ClientboundGeoFrontSortieCapturePacket.java")
    network = text("src/main/java/com/projectseele/network/SeeleNetwork.java")

    minimum = dimension_type.get("min_y")
    height = dimension_type.get("height")
    layers = dimension.get("generator", {}).get("settings", {}).get("layers", [])
    complete_sortie = method_body(entity, "private boolean completeLinkedSortie()")
    same_dimension_start = complete_sortie.find("if (destination == sourceLevel)")
    legacy_transfer = complete_sortie.find("this.changeDimension(destination")
    same_dimension_branch = complete_sortie[
        same_dimension_start:legacy_transfer
    ] if 0 <= same_dimension_start < legacy_transfer else ""
    lcl_builder = method_body(builder, "private static void buildLclLake")

    checks = [
        gate("dimension.vertical_contract",
             isinstance(minimum, int) and minimum % 16 == 0
             and isinstance(height, int) and height % 16 == 0
             and minimum <= -64 and minimum + height == 320,
             f"min_y={minimum} height={height} supports GeoFront and Tokyo-3"),
        gate("dimension.clean_generator",
             dimension.get("type") == "projectseele:geofront"
             and dimension.get("generator", {}).get("type") == "minecraft:flat"
             and layers == [{"block": "minecraft:bedrock", "height": 1}],
             "one bedrock layer leaves deterministic full-height construction space"),
        gate("dimension.normal_surface_sky",
             dimension_type.get("has_skylight") is True
             and dimension_type.get("has_ceiling") is False
             and dimension_type.get("natural") is True
             and "fixed_time" not in dimension_type,
             "Tokyo-3 has a normal day/night sky; GeoFront darkness comes from geometry"),
        gate("map.sealed_cavern_dome",
             all(token in builder for token in (
                 "CAVERN_RADIUS = 112", "CAVERN_HEIGHT = 104",
                 "CAVERN_DOME_SPRING_Y = 48", "buildCavernWall",
                 "int domeRise = CAVERN_HEIGHT - CAVERN_DOME_SPRING_Y",
                 "int roofY = CAVERN_DOME_SPRING_Y",
                 "for (int thickness = 0; thickness <= 2; thickness++)",
                 "set(level, origin.offset(x, y, z), roof)")),
             "a three-layer calculated roof seals the underground cavern from the real sky"),
        gate("map.integrated_coordinates",
             all(token in integrated for token in (
                 "MAP_VERSION = 2",
                 "GEOFRONT_ORIGIN = new BlockPos(0, -40, 76)",
                 "TOKYO3_ORIGIN = new BlockPos(0, 248, 0)",
                 "LIFT_X = {-28, 0, 28}",
                 "LOWER_TERMINAL_Z = -76",
                 "LOWER_BED_ABOVE_ORIGIN = 1",
                 "SURFACE_BED_BELOW_ORIGIN = 1")),
             "lower beds are Y=-39, surface beds are Y=247, aligned at X=-28/0/28 Z=0"),
        gate("map.three_continuous_shafts",
             all(token in integrated for token in (
                 "SHAFT_OUTER_RADIUS = 7", "SHAFT_CLEAR_RADIUS = 5",
                 "buildContinuousShaft(level, link)",
                 "for (int y = bottomY; y <= topY; y++)",
                 "return this.surfaceBed.getY() - this.lowerBed.getY()",
                 "continuousShafts == LIFT_LINKS.size()",
                 "surfaceBeds == LIFT_LINKS.size()",
                 "clearExits == LIFT_LINKS.size()"))
             and "Launch travels the same 286-block shaft" in commands,
             "three audited 15x15 shells contain uninterrupted 11x11, 286-block routes"),
        gate("map.original_landmarks",
             all(token in builder for token in (
                 "buildLclLake", "buildNervPyramid", "buildEvaLiftTerminals",
                 "buildArtificialSun", "buildObservationDeck"))
             and "ThirdTokyoSurfaceBuilder.buildDistrict" in integrated
             and "GeoFrontBuilder.build" in integrated,
             "Tokyo-3 and the complete GeoFront landmark set are built before shafts are cut"),
        gate("map.playable_landscapes",
             all(token in integrated for token in (
                 "Tokyo3LandscapeBuilder.build(level, TOKYO3_ORIGIN)",
                 "GeoFrontLandscapeBuilder.build(level, GEOFRONT_ORIGIN)",
                 "tokyo3Landscape.valid()", "geoFrontLandscape.valid()"))
             and all(token in tokyo3_landscape for token in (
                 "buildOuterTerrainShell", "buildElevatedExpressway",
                 "buildRailwayAndStation", "buildLaunchSafetyDistrict",
                 "buildMunicipalFacilities", "LandscapeAudit"))
             and all(token in geofront_landscape for token in (
                 "buildLclShore", "buildPumpingStation",
                 "buildServiceRoad", "buildMaintenanceTerrace",
                 "buildBlastBunkers", "LandscapeAudit")),
             "both levels include audited terrain, transport, service and safety infrastructure"),
        gate("map.runtime_audit",
             all(token in integrated for token in (
                 "IntegratedAudit", "controlMarkers", "lowerBeds",
                 "surfaceBeds", "continuousShafts", "clearExits"))
             and all(token in builder for token in (
                 "floor", "wall", "lake", "pyramid", "sun", "lifts == 3",
                 "gantries == 3", "bridge", "observation")),
             "both maps, three station pairs and physical shaft exits have block evidence"),
        gate("lcl.dedicated_fluid",
             all(token in fluids for token in (
                 "DeferredRegister<FluidType>", "LCL_TYPE", "LCL_SOURCE",
                 "FLOWING_LCL", ".block(ModBlocks.LCL_BLOCK)"))
             and "LiquidBlock" in blocks and "LCL_BLOCK" in blocks
             and all(token in lcl_type for token in (
                 "extends FluidType", ".canSwim(true)", ".canDrown(false)",
                 "getTintColor", "modifyFogRender"))
             and "ModFluids.LCL_SOURCE.get().defaultFluidState()" in lcl_builder
             and "ORANGE_STAINED_GLASS" not in lcl_builder
             and all(token in lcl_events for token in (
                 "getFluidType() != ModFluids.LCL_TYPE.get()",
                 "living.setAirSupply(living.getMaxAirSupply())")),
             "the five-block lake is an orange, breathable, swimmable FluidType rather than glass/water replacement"),
        gate("map.nerv_operations",
             "NervOperationsCentreBuilder.build" in builder
             and all(token in operations for token in (
                 "buildLowerConcourse", "buildOperationsHall",
                 "buildAccessStairs", "buildLiftTransit", "OperationsAudit",
                 "consoles == 3", "transitLinks == 3",
                 "hasConnectedLowerRoutes", "walkable")),
             "playable entrance, tactical hall, stairs, consoles and lift corridors are audited"),
        gate("commands.connected_map",
             all(f'literal("{name}")' in commands for name in
                 ("setup", "enter", "link", "sortie_audit", "surface", "exit",
                  "audit", "operations", "overview"))
             and "IntegratedNervMapBuilder.ensure" in commands
             and "IntegratedNervMapBuilder.inspect" in commands,
             "developer camera shortcuts are separate from the physically linked EVA sortie"),
        gate("sortie.same_dimension_primary",
             all(token in commands for token in (
                 "ensureContinuousSortieUnits", "setSortieDestination(level.dimension(),",
                 "setSortieParkingBed(lift.lowerBed())", "no transfer occurs",
                 "no portal or EVA teleport"))
             and all(token in entity for token in (
                 "private boolean isContinuousSortie()",
                 "private double launchTargetY()",
                 "private int launchDeckY()",
                 "private int launchAscentTicks()",
                 "CONTINUOUS_ASCENT_BLOCKS_PER_TICK",
                 "isContinuousSortieShaftClear"))
             and same_dimension_start >= 0
             and "changeDimension" not in same_dimension_branch
             and "this.setPos(arrival.x, arrival.y, arrival.z)" in same_dimension_branch
             and legacy_transfer > same_dimension_start,
             "same-dimension branch completes first and never changes dimension; legacy transfer remains fallback only"),
        gate("sortie.dynamic_286_timing",
             all(token in entity for token in (
                 "return this.sortieDestinationBed.getY() + 1.0D",
                 "Mth.ceil(distance / CONTINUOUS_ASCENT_BLOCKS_PER_TICK)",
                 "int ascentTicks = this.launchAscentTicks()",
                 "double targetY = this.launchTargetY()"))
             and "ascentBlocks()" in integrated,
             "target height and ascent duration derive from the two real station markers (286/2=143 ticks)"),
        gate("visual.five_views",
             all(token in capture for token in (
                 "cavern_overview", "nerv_pyramid", "lcl_lake",
                 "lift_terminals", "nerv_operations",
                 "GeoFront visual evidence"))
             and 'CAPTURE_UNIT.equals("geofront")' in automation,
             "five fixed client views cover cavern landmarks and dedicated LCL"),
        gate("visual.same_dimension_sortie",
             all(token in capture for token in (
                 "three_units_ready", "entry_plug_locked", "ascent_mid",
                 "tokyo3_surface_arrival", "GeoFrontSortieSession",
                 "this.origin.getY() + 100.0D",
                 "this.origin.getY() + 240.0D",
                 "this.origin.getY() + 286.0D"))
             and 'CAPTURE_UNIT.equals("geofront_sortie")' in automation
             and all(token in sortie_packet for token in (
                 "startGeoFrontSortie", "readVarInt", "readBlockPos"))
             and "IntegratedNervMapBuilder.surfaceLiftBed(1)" in automation,
             "four height-gated frames follow one piloted EVA through the same-dimension shaft"),
        gate("network.protocol",
             'PROTOCOL_VERSION = "11"' in network
             and "ClientboundGeoFrontCapturePacket.class" in network
             and "ClientboundGeoFrontSortieCapturePacket.class" in network,
             "GeoFront map and sortie captures remain registered on protocol v11"),
    ]
    if all(checks):
        print("Continuous GeoFront contract: PASS")
        return 0
    print("Continuous GeoFront contract: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
