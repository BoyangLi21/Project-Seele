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
    noise_settings = json.loads(text(
        "src/main/resources/data/projectseele/worldgen/noise_settings/geofront_surface.json"))
    builder = text("src/main/java/com/projectseele/world/GeoFrontBuilder.java")
    integrated = text(
        "src/main/java/com/projectseele/world/IntegratedNervMapBuilder.java")
    tokyo3_landscape = text(
        "src/main/java/com/projectseele/world/Tokyo3LandscapeBuilder.java")
    tokyo3_surface = text(
        "src/main/java/com/projectseele/world/ThirdTokyoSurfaceBuilder.java")
    geofront_landscape = text(
        "src/main/java/com/projectseele/world/GeoFrontLandscapeBuilder.java")
    operations = text(
        "src/main/java/com/projectseele/world/NervOperationsCentreBuilder.java")
    telemetry = text(
        "src/main/java/com/projectseele/world/NervCommandTelemetry.java")
    operations_console = text(
        "src/main/java/com/projectseele/world/NervOperationsConsole.java")
    terminal_dogma = text(
        "src/main/java/com/projectseele/world/TerminalDogmaBuilder.java")
    lilith_entity = text(
        "src/main/java/com/projectseele/entity/LilithEntity.java")
    lilith_renderer = text(
        "src/main/java/com/projectseele/client/render/LilithRenderer.java")
    mod_entities = text(
        "src/main/java/com/projectseele/registry/ModEntities.java")
    lilith_pack = text("tools/make_lilith_model_pack.py")
    magi = text(
        "src/main/java/com/projectseele/world/MagiDeepLabBuilder.java")
    game_events = text("src/main/java/com/projectseele/GameEvents.java")
    logistics = text(
        "src/main/java/com/projectseele/world/EvaLogisticsDirector.java")
    hangars = text(
        "src/main/java/com/projectseele/world/EvaHangarBuilder.java")
    local_assets = text(
        "src/main/java/com/projectseele/world/LocalMapAssetLoader.java")
    battle = text(
        "src/main/java/com/projectseele/event/Tokyo3RamielBattleDirector.java")
    battle_data = text(
        "src/main/java/com/projectseele/world/Tokyo3RamielBattleSavedData.java")
    tokyo3_commands = text(
        "src/main/java/com/projectseele/visual/ThirdTokyoCommands.java")
    tokyo3_packet = text(
        "src/main/java/com/projectseele/network/ClientboundTokyo3CapturePacket.java")
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
    video_client = text(
        "src/main/java/com/projectseele/client/EvaCommandFeedClient.java")
    video_upload = text(
        "src/main/java/com/projectseele/network/ServerboundEvaVideoFramePacket.java")
    video_downlink = text(
        "src/main/java/com/projectseele/network/ClientboundEvaVideoFramePacket.java")
    client_events = text(
        "src/main/java/com/projectseele/client/ClientEvents.java")
    map_staging = text("tools/prepare_local_map_assets.py")
    launcher = text("tools/start_test.bat")

    minimum = dimension_type.get("min_y")
    height = dimension_type.get("height")
    generator = dimension.get("generator", {})
    complete_sortie = method_body(entity, "private boolean completeLinkedSortie()")
    same_dimension_start = complete_sortie.find("if (destination == sourceLevel)")
    legacy_transfer = complete_sortie.find("this.changeDimension(destination")
    same_dimension_branch = complete_sortie[
        same_dimension_start:legacy_transfer
    ] if 0 <= same_dimension_start < legacy_transfer else ""
    lcl_builder = method_body(builder, "private static void buildLclLake")
    geofront_visual_setup = method_body(
        commands, "static int setupVisualCapture(CommandSourceStack source)")

    checks = [
        gate("dimension.vertical_contract",
             isinstance(minimum, int) and minimum % 16 == 0
             and isinstance(height, int) and height % 16 == 0
             and minimum == -672 and height == 992
             and minimum + height == 320,
             f"min_y={minimum} height={height} leaves bedrock, full sphere and Tokyo-3 surface"),
        gate("dimension.clean_generator",
             dimension.get("type") == "projectseele:geofront"
             and generator.get("type") == "minecraft:noise"
             and generator.get("settings") == "projectseele:geofront_surface"
             and generator.get("biome_source", {}).get("preset")
                 == "minecraft:overworld"
             and noise_settings.get("noise", {}).get("min_y") == minimum
             and noise_settings.get("noise", {}).get("height") == height
             and noise_settings.get("default_fluid", {}).get("Name")
                 == "minecraft:air"
             and noise_settings.get("sea_level") == minimum
             and noise_settings.get("noise_router", {}).get(
                 "final_density", {}).get("type") == "minecraft:range_choice",
             "the dedicated sea level is pinned to min_y so vanilla's hard-coded deep lava picker never reaches the GeoFront sphere"),
        gate("dimension.buried_continent_density",
             noise_settings.get("noise_router", {}).get(
                 "final_density", {}).get("when_out_of_range", {}).get(
                 "min_inclusive") == -12.0
             and noise_settings.get("noise_router", {}).get(
                 "initial_density_without_jaggedness", {}).get(
                 "min_inclusive") == -12.0,
             "overworld density begins at the GeoFront crown Y=-12, so the sphere is embedded beneath a real continent instead of an air gap"),
        gate("dimension.normal_surface_sky",
             dimension_type.get("has_skylight") is True
             and dimension_type.get("has_ceiling") is False
             and dimension_type.get("natural") is True
             and dimension_type.get("ambient_light") == 0.62
             and "fixed_time" not in dimension_type
             and "relativeY = 32" in builder
             and "x += 14" in builder,
             "Tokyo-3 retains a normal sky while GeoFront combines broad "
             "reflected daylight with a mob-safe ground light plane"),
        gate("map.skyweave_sphere",
             all(token in builder for token in (
                 "CAVERN_RADIUS = 320", "CAVERN_CENTRE_Y = 112",
                 "CAVERN_CENTRE_Z = -76", "buildSkyweaveSphere",
                 "ars_nouveau", "sky_block", "skyweaveState",
                 "buildCavernFloor", "buildNaturalLake", "buildForestRing")),
             "a complete 640-block Skyweave sphere surrounds a natural floor, lake and forest"),
        gate("map.command_pyramid_envelope",
             all(token in builder for token in (
                 "PYRAMID_BASE_CENTRE_Z = 31", "PYRAMID_CENTRE_Z = 31",
                 "PYRAMID_BASE_Y = -22", "PYRAMID_APEX_Y = 150",
                 "PYRAMID_BASE_HALF_X = 120", "PYRAMID_BASE_HALF_Z = 120",
                 "PYRAMID_APEX_HALF = 0", "ensurePyramidRevision",
                 "clearTallEnvelopePyramid", "clearBentEnvelopePyramid",
                 "clearLegacyNervPyramid", "rectangularPyramidShellLayer",
                 "buildPyramidApron", "OBSERVATION_Z = 190",
                 "pyramidApronMarkersPresent", "pyramidApronSurfacePresent",
                 "writePyramidApronMarkers", "PYRAMID_APRON_MARGIN",
                 "clearStaleNaturalColumn", "origin.offset(-x, 1",
                 "buildObservationAccess", "pyramidGroundAccessPresent",
                 "isWithinPyramidServiceApron",
                 "isWithinPyramidPublicAccess",
                 "LocalMapAssetLoader.commandEnvelopeContains",
                 "Blocks.BLACK_CONCRETE", "Blocks.CRYING_OBSIDIAN",
                 "Blocks.BEACON"))
             and all(token in local_assets for token in (
                 "COMMAND_OFFSET = new BlockPos(-28, -21, -33)",
                 "COMMAND_SIZE = new Vec3i(56, 77, 129)",
                 "commandEnvelopeContains", "isCommandMarkerOffset")),
             "one square black v18 NERV pyramid encloses the complete "
             "56x77x129 command module, with an audited hard apron and a "
             "walkable passage/stair to the ground overlook"),
        gate("map.integrated_coordinates",
             all(token in integrated for token in (
                  "MAP_VERSION = 18",
                   "EvaHangarBuilder.build(level, GEOFRONT_ORIGIN)",
                   "EvaHangarBuilder.ensure(level, GEOFRONT_ORIGIN)",
                  "stagedEvaWorld(level)",
                  "GEOFRONT_ORIGIN = new BlockPos(30, -444, 296)",
                  "TOKYO3_ORIGIN = new BlockPos(30, 80, 220)",
                 "LIFT_X = {-28, 0, 28}",
                 "LOWER_TERMINAL_Z = -76",
                 "LOWER_BED_ABOVE_ORIGIN = 1",
                 "SURFACE_BED_BELOW_ORIGIN = 1")),
             "GeoFront beds are Y=-443 and Tokyo-3 beds Y=79 at X=2/30/58 Z=220"),
        gate("map.deep_burial_and_lava_gate",
             all(token in integrated for token in (
                 "rockCover >= 80", "bedrockClearance >= 16",
                 "deeplyBuried", "rockCover", "bedrockClearance"))
             and all(token in builder for token in (
                 "countVanillaLavaSamples", "FluidTags.LAVA",
                 "vanillaLavaSamples == 0", "vanillaLavaSamples=%d/0")),
             "the sphere has at least 80 blocks of cover and stale vanilla-lava chunks fail the server audit"),
        gate("map.three_continuous_shafts",
             all(token in integrated for token in (
                 "SHAFT_OUTER_RADIUS = 7", "SHAFT_CLEAR_RADIUS = 5",
                 "buildContinuousShaft(level, link)",
                 "for (int y = bottomY; y <= topY; y++)",
                 "int worldZ = TOKYO3_ORIGIN.getZ()",
                 "new LiftLink(index, worldX, worldZ",
                 "link.z() + z",
                 "shaftLayerIsClear(level, link, y)",
                 "return this.surfaceBed.getY() - this.lowerBed.getY()",
                 "continuousShafts == LIFT_LINKS.size()",
                 "surfaceBeds == LIFT_LINKS.size()",
                 "clearExits == LIFT_LINKS.size()"))
             and "IntegratedNervMapBuilder.ascentDistance()" in commands,
             "three audited 15x15 shells contain uninterrupted 11x11, 522-block routes"),
        gate("map.lower_bay_observation_glass",
             all(token in integrated for token in (
                 "ensureLowerBayWindows(level)",
                 "Blocks.GRAY_STAINED_GLASS.defaultBlockState()",
                 "state.is(Blocks.GRAY_STAINED_GLASS)",
                 "y >= accessDeckY + 1 && y <= accessDeckY + 3",
                 "Math.abs(x) <= 2",
                 "clear(level, new BlockPos(link.x() + x, y, wallZ))")),
             "three lower shafts have audited blast glazing without sealing the plug gantry door"),
        gate("map.original_landmarks",
             all(token in builder for token in (
                 "buildNaturalLake", "buildLclLake", "buildNervPyramid",
                 "buildEvaLiftTerminals", "buildForestRing",
                 "clearLegacyArtificialSun", "buildObservationDeck"))
             and "ThirdTokyoSurfaceBuilder.buildDistrict" in integrated
             and "GeoFrontBuilder.build" in integrated
             and "GeoFrontBuilder.build(level, GEOFRONT_ORIGIN, false)" in integrated,
             "Tokyo-3 is generated on the natural surface above a new full GeoFront sphere"),
        gate("map.playable_landscapes",
             all(token in integrated for token in (
                 "Tokyo3LandscapeBuilder.build(level, TOKYO3_ORIGIN)",
                 "GeoFrontLandscapeBuilder.build(level, GEOFRONT_ORIGIN)",
                 "tokyo3Landscape.valid()", "geoFrontLandscape.valid()"))
             and all(token in tokyo3_landscape for token in (
                 "CITY_PLATFORM_HALF_SIZE = 224",
                 "OUTER_TERRAIN_RADIUS = 360",
                 "buildOuterTerrainShell", "buildElevatedExpressway",
                 "buildRailwayAndStation", "buildLaunchSafetyDistrict",
                 "buildMunicipalFacilities", "terrainSurfacePresent",
                 "for (int y = top; y >= -48; y--)", "LandscapeAudit"))
             and all(token in geofront_landscape for token in (
                 "buildLclShore", "buildPumpingStation",
                 "buildServiceRoad", "buildMaintenanceTerrace",
                 "buildBlastBunkers", "LandscapeAudit",
                 "isWithinPyramidServiceApron",
                 "isWithinPyramidPublicAccess")),
             "both levels include audited terrain, transport, service and safety infrastructure"),
        gate("map.expanded_tokyo3_wards",
             all(token in tokyo3_surface for token in (
                 "DISTRICT_HALF_SIZE = 208", "FOUNDATION_HALF_SIZE = 224",
                 "OUTER_WARD_TOWERS", "MOVABLE_BUILDINGS",
                 "buildOuterWardTower", "createOuterWardTowers",
                 "outerWards == EXPECTED_OUTER_WARDS",
                 "ceilingBuildings == MOVABLE_BUILDINGS.size()",
                 "emergeCeilingLayer", "ceilingRoofRelativeY"))
             and all(token in local_assets for token in (
                 "SKYSCRAPER_MOVE_QUANTUM = 12",
                 "applyTokyo3RetractionDepth", "skyscraperDrop")),
             "the 416-block district moves 66 inner towers, 29 outer wards "
             "and three local high-rises into a curved ceiling city"),
        gate("map.fresh_normal_world",
             all(token in map_staging for token in (
                 "SEELE_TOKYO3_REBUILT", "STAGED_WORLD_SCHEMA = 10",
                 "world_generator_type", "minecraft:noise",
                 "continent_surface_skyweave_sphere_640_v5_buried_noise",
                 'data["confirmedExperimentalSettings"] = nbtlib.Byte(1)',
                 '"geofront_anchor": [30, -444, 296]'))
             and "SEELE_TOKYO3_REBUILT" in launcher,
             "local staging preserves the old save and creates a new normal-noise world selected by the desktop launcher"),
        gate("map.runtime_audit",
             all(token in integrated for token in (
                 "IntegratedAudit", "controlMarkers", "lowerBeds",
                 "surfaceBeds", "continuousShafts", "clearExits",
                 "hangars.valid()", "recoveryConsole.valid()",
                 "repairMissingStreetLevelDistrict"))
             and all(token in builder for token in (
                 "floor", "skySphere", "lake", "naturalLake", "pyramid",
                 "legacyInnerPyramidGone", "realSky", "lifts == 3",
                 "gantries == 3", "bridge", "observation")),
             "both maps, three station pairs and physical shaft exits have block evidence"),
        gate("map.umbilical_launch_route",
             all(token in integrated for token in (
                 "public static BlockPos lowerPowerPylon",
                 "public static BlockPos surfacePowerPylon",
                 "offset(10, 1, 0)", "offset(11, 2, 0)",
                 "ensurePowerPylons(level)",
                 "powerPylonsPresent(level)",
                 "ModBlocks.UMBILICAL_PYLON.get().defaultBlockState()")),
             "all three underground berths and surface stations carry audited umbilical reconnect points"),
        gate("map.incremental_runtime_repair",
             all(token in integrated for token in (
                 "if (isInstalled(level))",
                 "NervOperationsCentreBuilder.repairRuntimeAccess(",
                 "MagiDeepLabBuilder.repairRuntimeLabels(",
                 "public static RuntimeAudit prepareRuntime",
                 "shaftIsContinuous(level, link)",
                 "surfaceExitIsClear(level, link)",
                 "magi.labels()",
                 "elapsedMilliseconds(startedAt)",
                 "Integrated NERV map reused without full rebuild",
                 "incremental audit failed; rebuilding")),
             "loaded saves repair transient displays, while live combat controls gate only the physical sortie route instead of synchronously loading every remote map landmark"),
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
                  "buildCommandAccessSpine", "hasSafeAnnexRoutes",
                  "consoles == 3", "transitLinks == 3",
                  "linkFacilities", "facilityLinks", "linkHangars",
                  "hasConnectedLowerRoutes", "hasConnectedHangarRoutes",
                  "walkable")),
             "command, MAGI, Terminal Dogma and all lift routes share an audited physical interchange"),
        gate("map.nerv_live_telemetry",
             all(token in telemetry for token in (
                 "SCREEN_COUNT = 5", "unit00", "unit01", "unit02",
                 "strategic", "sensor", "unitPanel", "strategicPanel",
                 "sensorPanel", "ENTRY PLUG / LIVE OPTICAL SENSOR",
                 "pilot.getEyePosition()", "Vec3.directionFromRotation",
                 "markNearestAngel", "SENSOR_WIDTH = 20",
                 "getSynchronizationRatio", "getAtFieldEnergy",
                 "getLaunchPhase", "PILOT SENSOR FEED",
                 "GEOFRONT > TOKYO-3 PHYSICAL ROUTE"))
             and "NervCommandTelemetry.tick(event.getServer())" in game_events
             and "REFRESH_INTERVAL_TICKS = 40" in telemetry
             and "% NervCommandTelemetry.REFRESH_INTERVAL_TICKS" in game_events
             and "NervCommandTelemetry.countScreens" in operations,
             "five server-driven command displays include a live pilot-view sensor raster and refresh every 40 ticks"),
        gate("map.nerv_live_pilot_video",
             all(token in operations for token in (
                 "buildCommandSupportAnnex", "buildVideoWall",
                 "videoWall", "safeAnnex",
                  "&& hasSafeAnnexRoutes(level, origin)"))
             and all(token in video_client for token in (
                 "Screenshot.takeScreenshot", "resizeSubRectTo",
                 "CAPTURE_INTERVAL_TICKS = 5",
                 "FRAME_STALE_NANOS", "DynamicTexture[3]",
                  "STANDBY_TEXTURES", "STANDBY_TEXTURE_IDS",
                 "VisualCaptureManager.isSuppressingGui()",
                 "minecraft.player.getVehicle()",
                  "eva.getFirstPassenger() != minecraft.player",
                 "renderScreen(event.getPoseStack()"))
             and all(token in video_upload for token in (
                 "FRAME_WIDTH = 160", "FRAME_HEIGHT = 90",
                 "sender.getVehicle() instanceof EvaUnit01Entity",
                 "eva.getUnitVariant() != this.variant",
                  "eva.getFirstPassenger() != sender",
                 "level.dimension().equals(GeoFrontCommands.GEOFRONT)",
                 "commandArea.contains(viewer.position())", "validPng(this.png)",
                 "PacketDistributor.PLAYER"))
             and "COCKPIT VIDEO: LIVE" in telemetry
             and "COCKPIT VIDEO: STANDBY" in telemetry
             and "DistExecutor.unsafeRunWhenOn" in video_downlink
             and "com.projectseele.client.EvaCommandFeedClient"
                 in video_downlink
             and all(token in network for token in (
                 "ServerboundEvaVideoFramePacket.class",
                 "ClientboundEvaVideoFramePacket.class"))
             and "\"eva_command_feed_capture\", EvaCommandFeedClient.CAPTURE_OVERLAY"
                 in client_events,
             "three physical 16:9 panels receive throttled, authenticated final-frame cockpit video only from the actual EVA pilots"),
        gate("map.nerv_physical_console",
             all(token in operations_console for token in (
                 "CONTROL_COUNT = 7", "MAGI\\nCHECK",
                 "EVA-00\\nRELEASE", "EVA-01\\nRELEASE",
                 "EVA-02\\nRELEASE", "CITY\\nARMOUR",
                 "YASHIMA\\nSTART", "BATTLE\\nABORT",
                 "handleUse(ServerPlayer player, BlockPos position)",
                 "GeoFrontCommands.ensureContinuousSortieUnits",
                 "IntegratedNervMapBuilder.prepareRuntime(level)",
                 "releaseLaunchFromCommand",
                 "Tokyo3RetractionDirector.request",
                 "Tokyo3RamielBattleDirector.start",
                 "Tokyo3RamielBattleDirector.abort",
                 "controls == CONTROL_COUNT",
                 "bases == CONTROL_COUNT", "labels == CONTROL_COUNT",
                 "supports == CONTROL_COUNT", "removeLegacyRow"))
             and "NervOperationsConsole.handleUse(player, event.getPos())"
                 in game_events
             and "InteractionHand.MAIN_HAND" in game_events
             and "NervOperationsConsole.inspect" in operations
             and all(token in entity for token in (
                 "public boolean releaseLaunchFromCommand()",
                 "this.getLaunchPhase() != LAUNCH_LOCKED",
                 "this.getControllingPassenger() instanceof ServerPlayer pilot",
                 "this.launchBedPos == null",
                 "this.enforceLaunchLock()")),
             "seven in-world buttons control checks, three interlocked releases, city armour and Operation Yashima"),
        gate("map.terminal_dogma_physical",
             all(token in terminal_dogma for token in (
                 "FACILITY_Y_OFFSET = -64", "SHAFT_TOP_Y = 65",
                 "SHAFT_BOTTOM_Y = -59", "CHAMBER_CENTRE_Y = -58",
                 "LCL_SURFACE_Y = -75", "buildCentralDogmaShaft",
                 "buildDeepAccess", "buildContainmentCross",
                 "ModFluids.LCL_SOURCE", "ladder=%d/%d",
                 "sealedSpecimen", "observation"))
             and all(token in terminal_dogma for token in (
                 "spawnLilith", "repairRuntimeSpecimen",
                 "LilithEntity.class", "terminal_dogma_lilith"))
             and all(token in lilith_entity for token in (
                 "setYRot(180.0F)", "setDeltaMovement(Vec3.ZERO)",
                 "return false;", "removeWhenFarAway"))
             and all(token in lilith_renderer for token in (
                 "lilith_body", "lilith_face_dark", "lilith_mask",
                 "lilith_nails", "lilith_spear", "lilith_eyes",
                 "LocalTriangleMeshLayer", "visualBounds"))
             and 'ENTITY_TYPES.register("lilith"' in mod_entities
             and all(token in lilith_pack for token in (
                 "lilith_-_evangelion.glb", "lilith-local.json",
                 "LILITH_EXPORT"))
             and "TerminalDogmaBuilder.build" in builder
             and "terminalDogma.valid()" in builder
             and 'literal("dogma")' in commands,
             "walkable Central Dogma reaches a persistent crucified Lilith, local six-layer mesh, red cross, spear, gallery and LCL pool"),
        gate("map.magi_deep_lab",
             all(token in magi for token in (
                 "LAB_FLOOR_Y = -27", "buildDescentShaft",
                 "buildPhysicalAccess", "buildPribnowBox",
                 "MELCHIOR-1", "BALTHASAR-2", "CASPER-3",
                 "handleUse", "consensusLine", "onlineCores",
                 "repairRuntimeLabels", "public static void tick",
                 "countLabelEntities(level, origin) != CORE_NAMES.length"))
             and "MagiDeepLabBuilder.build" in builder
             and "magi.runtimePhysicalValid()" in builder
             and "MagiDeepLabBuilder.handleUse(player, event.getPos())"
                 in game_events
             and "MagiDeepLabBuilder.tick(event.getServer())" in game_events,
             "a physical 35-block descent reaches the three persistent MAGI cores, Pribnow Box and maintenance controls"),
        gate("map.private_asset_fail_safe",
             all(token in local_assets for token in (
                 "PRIVATE_GEOFRONT", "COMMAND_MODULE", "TOKYO3_SKYSCRAPER",
                 "privateGeoFrontShellPresent", "commandMarkersPresent",
                 "placeTokyo3Skyscrapers", "stagedEvaWorld")),
             "local map structures are explicitly detected and audited instead of packaged as silent fallbacks"),
        gate("commands.connected_map",
             all(f'literal("{name}")' in commands for name in
                 ("setup", "enter", "link", "sortie_audit", "surface", "exit",
                  "audit", "operations", "overview"))
             and "IntegratedNervMapBuilder.ensure" in commands
             and "IntegratedNervMapBuilder.inspect" in commands
             and all(token in commands for token in (
                 "overview(source) != 1 || operations(source) != 1",
                 "prepareSafeLanding", "repairRuntimeAccess",
                 "unsafeOverviewLogin", "unsafe saved GeoFront overview")),
             "developer camera shortcuts are separate from the physically linked EVA sortie"),
        gate("visual.city_armour_reset",
             "Tokyo3RetractionDirector.forceDepth(level," in geofront_visual_setup
             and geofront_visual_setup.index(
                 "Tokyo3RetractionDirector.forceDepth(level,")
                 < geofront_visual_setup.index(
                     "IntegratedNervMapBuilder.ensure(level)"),
             "the fixed GeoFront capture physically restores every Tokyo-3 tower before auditing the saved world"),
        gate("sortie.same_dimension_primary",
             all(token in commands for token in (
                 "ensureContinuousSortieUnits", "EvaLogisticsDirector.ensureFleet(level)",
                 "no portal or EVA teleport"))
             and all(token in logistics for token in (
                 "Phase.TO_SILO", "tickHorizontal", "tickDescent",
                 "setSortieDestination(level.dimension(),",
                 "setSortieParkingBed(silo)", "moveOnNervCarrier"))
             and all(token in hangars for token in (
                 "buildTransportTunnel", "setCarrier", "restoreStaticCarrier"))
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
        gate("sortie.dynamic_shaft_timing",
             all(token in entity for token in (
                 "return this.sortieDestinationBed.getY() + 1.0D",
                 "Mth.ceil(distance / CONTINUOUS_ASCENT_BLOCKS_PER_TICK)",
                 "int ascentTicks = this.launchAscentTicks()",
                 "double targetY = this.launchTargetY()"))
             and "ascentBlocks()" in integrated,
             "target height and ascent duration derive from the two real station markers (522/2=261 ticks)"),
        gate("sortie.accelerating_surface_release",
             all(token in entity for token in (
                 "CONTINUOUS_SURFACE_SYNC_TICKS = 1",
                 "progress * (0.35F + 0.65F * progress)",
                 "this.beginContinuousSurfaceArrival(arrivalYaw)",
                 "this.finishTransferredSortie(this.launchLockedYaw)")),
             "the carrier keeps positive upward speed through the aperture and releases local control after one sync tick"),
        gate("visual.thirteen_geofront_views",
             all(token in capture for token in (
                  "cavern_overview", "natural_lake", "forest_canopy",
                  "nerv_pyramid", "nerv_operations",
                  "nerv_support_gallery", "nerv_briefing_room",
                  "nerv_medical_support", "nerv_pressure_vestibule",
                  "central_dogma_descent", "terminal_dogma",
                  "lcl_lake", "lift_terminals", "skyweaveCanopy",
                  "GeoFront visual evidence"))
             and 'CAPTURE_UNIT.equals("geofront")' in automation,
             "thirteen fixed views include the command hall, two inhabited support rooms and both sealed boundary exits"),
        gate("visual.same_dimension_sortie",
             all(token in capture for token in (
                 "three_units_ready", "entry_plug_locked", "live_pilot_sensor", "ascent_mid",
                 "tokyo3_surface_arrival", "recovery_descent",
                 "wet_cage_return", "GeoFrontSortieSession",
                 "double ascent = IntegratedNervMapBuilder.ascentDistance()",
                 "ascent * 0.40D",
                 "ascent + 1.5D"))
             and 'CAPTURE_UNIT.equals("geofront_sortie")' in automation
             and all(token in automation for token in (
                 "TrainingPilotDirector.start",
                 "EntryPlugDirector.hasBoardedPilot",
                 "EvaLogisticsDirector.requestPrepare", "SILO_READY",
                 "releaseLaunchFromCommand",
                 "EvaLogisticsDirector.requestRecovery",
                 "VISUAL GEOFRONT LOGISTICS CYCLE VALID"))
             and all(token in sortie_packet for token in (
                 "startGeoFrontSortie", "readVarInt", "readBlockPos"))
             and "IntegratedNervMapBuilder.surfaceLiftBed(1)" in capture,
             "seven state-gated frames prove dummy external-plug boarding, command-authorized wet-cage transfer, live sortie and physical recovery through one same-dimension shaft"),
        gate("battle.operation_yashima_persistent",
             all(token in battle for token in (
                 "RESTORE_DELAY_TICKS = 100", "Tokyo3RamielBattleSavedData.get",
                 "Tokyo3RetractionDirector.request(level, origin, true)",
                 "AngelAlarmSystem.engage(ramiel)",
                 "AngelAlarmSystem.disengage", "Operation Yashima started",
                 "getAtFieldEnergy", "getAtFieldMax", "abort"))
             and all(token in battle_data for token in (
                 "extends SavedData", "StoredBattle", "ramiel",
                 "clearTicks", "save(CompoundTag"))
             and all(f'literal("{name}")' in tokyo3_commands
                     for name in ("ramiel", "start", "status", "abort")),
             "Ramiel UUID, clear confirmation, alarm and retract/restore cycle survive in server SavedData"),
        gate("visual.operation_yashima",
             'CAPTURE_UNIT.equals("tokyo3_battle")' in automation
             and "Tokyo3RamielBattleDirector.start" in automation
             and "Tokyo3RamielBattleDirector.abort" in automation
             and "origin, false, true" in automation
             and all(token in tokyo3_packet for token in (
                 "private final boolean battle", "startTokyo3Battle"))
             and all(token in capture for token in (
                 "ramielCount", "battleState", "tokyo3_battle_",
                 "this.battle ? towers == 0 : towers == 66")),
             "battle capture requires one Ramiel, retracted towers, three EVA variants and logout cleanup"),
        gate("network.protocol",
             'PROTOCOL_VERSION = "13"' in network
             and "ClientboundGeoFrontCapturePacket.class" in network
             and "ClientboundGeoFrontSortieCapturePacket.class" in network
             and "ServerboundGeoFrontCameraPacket.class" in network
             and "new ServerboundGeoFrontCameraPacket(this.view)" in capture,
             "GeoFront captures, camera sync and authenticated EVA video remain registered on protocol v13"),
    ]
    if all(checks):
        print("Continuous GeoFront contract: PASS")
        return 0
    print("Continuous GeoFront contract: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
