#!/usr/bin/env python3
"""Fail closed when the GeoFront dimension, map or visual matrix drifts."""

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


def main() -> int:
    dimension_type = json.loads(text(
        "src/main/resources/data/projectseele/dimension_type/geofront.json"))
    dimension = json.loads(text(
        "src/main/resources/data/projectseele/dimension/geofront.json"))
    builder = text("src/main/java/com/projectseele/world/GeoFrontBuilder.java")
    operations = text(
        "src/main/java/com/projectseele/world/NervOperationsCentreBuilder.java")
    commands = text("src/main/java/com/projectseele/visual/GeoFrontCommands.java")
    automation = text("src/main/java/com/projectseele/visual/VisualLabAutomation.java")
    capture = text(
        "src/main/java/com/projectseele/client/visual/VisualCaptureManager.java")
    entity = text("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    sortie_packet = text(
        "src/main/java/com/projectseele/network/ClientboundGeoFrontSortieCapturePacket.java")
    network = text("src/main/java/com/projectseele/network/SeeleNetwork.java")
    tokyo_commands = text(
        "src/main/java/com/projectseele/visual/ThirdTokyoCommands.java")

    minimum = dimension_type.get("min_y")
    height = dimension_type.get("height")
    layers = dimension.get("generator", {}).get("settings", {}).get("layers", [])
    checks = [
        gate("dimension.vertical_contract",
             isinstance(minimum, int) and minimum % 16 == 0
             and isinstance(height, int) and height % 16 == 0
             and minimum + height <= 320,
             f"min_y={minimum} height={height}"),
        gate("dimension.void_generator",
             dimension.get("type") == "projectseele:geofront"
             and dimension.get("generator", {}).get("type") == "minecraft:flat"
             and layers == [{"block": "minecraft:bedrock", "height": 1}],
             "one bedrock layer leaves deterministic clean-room construction space"),
        gate("dimension.cavern_semantics",
             dimension_type.get("has_skylight") is False
             and dimension_type.get("has_ceiling") is True
             and dimension_type.get("fixed_time") == 6000,
             "fixed underground lighting and ceiling semantics"),
        gate("map.original_landmarks",
             all(token in builder for token in (
                 "CAVERN_RADIUS = 112", "buildLclLake", "buildNervPyramid",
                 "buildEvaLiftTerminals", "buildArtificialSun",
                 "buildObservationDeck")),
             "cavern, lake, pyramid, three lifts, sun and deck are procedural"),
        gate("map.runtime_audit",
             all(token in builder for token in (
                 "floor", "wall", "lake", "pyramid", "sun", "lifts == 3",
                 "gantries == 3", "bridge", "observation")),
             "all critical landmarks have server-side block evidence"),
        gate("map.nerv_operations",
             "NervOperationsCentreBuilder.build" in builder
             and all(token in operations for token in (
                 "buildLowerConcourse", "buildOperationsHall",
                 "buildAccessStairs", "buildLiftTransit", "OperationsAudit",
                 "consoles == 3", "transitLinks == 3",
                 "hasConnectedLowerRoutes", "walkable")),
             "playable entrance, tactical hall, stairs, consoles and three lift corridors are audited"),
        gate("commands.round_trip",
             all(f'literal("{name}")' in commands for name in
                 ("setup", "enter", "surface", "audit", "operations", "overview"))
             and all(token in commands for token in
                     ("RETURN_DIMENSION", "RETURN_X", "RETURN_Y", "RETURN_Z")),
             "entry saves an exact cross-dimension return position"),
        gate("sortie.three_way_link",
             all(token in commands for token in (
                 'literal("link")', 'literal("sortie_audit")',
                 "setSortieDestination", "transferUnpilotedTo",
                 "rollbackLinks", "linked == 3", "validDestinations == 3"))
             and all(token in builder for token in (
                 "buildLiftGantry", "clearLiftCorridor", "LIFT_X")),
             "Unit-00/01/02 map to reachable terminals with rollback and audits"),
        gate("sortie.persistent_safe_transfer",
             all(token in entity for token in (
                 "SeeleSortieDimension", "SeeleSortieBed",
                 "SeeleSortieParkingBed", "tickSortieParkingLock",
                 "completeLinkedSortie", "isSortieShaftClear",
                 "directTeleporter", "pilot.stopRiding()",
                 "pilot.startRiding(relocated, true)",
                 "setSurfaceCarrierAt(destination, destinationBed, true)",
                 "clearMovingCarrierBelowSurface"))
             and "setSortieParkingBed" in commands,
             "destination and frozen underground parking survive saves; shaft, carrier and pilot hand-off are gated"),
        gate("visual.five_views",
             all(token in capture for token in (
                 "cavern_overview", "nerv_pyramid", "lcl_lake",
                 "lift_terminals", "nerv_operations",
                 "GeoFront visual evidence"))
             and 'CAPTURE_UNIT.equals("geofront")' in automation,
             "real client captures and audits four cavern views plus the NERV operations hall"),
        gate("visual.cross_dimension_sortie",
             all(token in capture for token in (
                 "three_units_ready", "entry_plug_locked", "ascent_mid",
                 "tokyo3_surface_arrival", "GeoFrontSortieSession"))
             and 'CAPTURE_UNIT.equals("geofront_sortie")' in automation
             and all(token in sortie_packet for token in (
                 "startGeoFrontSortie", "readVarInt", "readBlockPos"))
             and all(token in commands for token in (
                 "VISUAL_SORTIE_UNITS", "pruneVisualSortieDuplicates"))
             and "this.origin.getY() + 10.0D" in capture
             and "auditVisualCapture" in tokyo_commands
             and "geoFrontSortieSurfaceAudited" in automation,
             "four height-gated frames follow the same UUID-audited piloted EVA into Tokyo-3"),
        gate("network.protocol",
             'PROTOCOL_VERSION = "10"' in network
             and "ClientboundGeoFrontCapturePacket.class" in network
             and "ClientboundGeoFrontSortieCapturePacket.class" in network,
             "GeoFront map and sortie capture are registered on protocol v10"),
    ]
    if all(checks):
        print("GeoFront contract: PASS")
        return 0
    print("GeoFront contract: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
