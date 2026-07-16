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
    commands = text("src/main/java/com/projectseele/visual/GeoFrontCommands.java")
    automation = text("src/main/java/com/projectseele/visual/VisualLabAutomation.java")
    capture = text(
        "src/main/java/com/projectseele/client/visual/VisualCaptureManager.java")
    network = text("src/main/java/com/projectseele/network/SeeleNetwork.java")

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
                 "bridge", "observation")),
             "all critical landmarks have server-side block evidence"),
        gate("commands.round_trip",
             all(f'literal("{name}")' in commands for name in
                 ("setup", "enter", "surface", "audit", "overview"))
             and all(token in commands for token in
                     ("RETURN_DIMENSION", "RETURN_X", "RETURN_Y", "RETURN_Z")),
             "entry saves an exact cross-dimension return position"),
        gate("visual.four_views",
             all(token in capture for token in (
                 "cavern_overview", "nerv_pyramid", "lcl_lake",
                 "lift_terminals", "GeoFront visual evidence"))
             and 'CAPTURE_UNIT.equals("geofront")' in automation,
             "real client captures and audits four cavern views"),
        gate("network.protocol",
             'PROTOCOL_VERSION = "9"' in network
             and "ClientboundGeoFrontCapturePacket.class" in network,
             "GeoFront capture is registered on protocol v9"),
    ]
    if all(checks):
        print("GeoFront contract: PASS")
        return 0
    print("GeoFront contract: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
