#!/usr/bin/env python3
"""Render and audit the NERV launch-silo contract without starting Minecraft.

The drawing is deliberately schematic.  Every dimension used by the preview is
read from the Java builder, command audit, launch state machine, or the shipped
Unit-01 entry-plug animation.  The JSON report is the machine-readable result;
the PNG is a human-readable top/section review sheet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
KIT_SOURCE = ROOT / "src/main/java/com/projectseele/item/NervConstructionKitItem.java"
INTEGRATED_SOURCE = ROOT / "src/main/java/com/projectseele/world/IntegratedNervMapBuilder.java"
COMMAND_SOURCE = ROOT / "src/main/java/com/projectseele/visual/LaunchSiloCommands.java"
ENTITY_SOURCE = ROOT / "src/main/java/com/projectseele/entity/EvaUnit01Entity.java"
RENDERER_SOURCE = ROOT / "src/main/java/com/projectseele/client/render/EvaUnit01Renderer.java"
GEO_SOURCE = ROOT / "src/main/resources/assets/projectseele/geo/eva_unit01.geo.json"
ANIMATION_SOURCE = ROOT / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json"
DEFAULT_OUTPUT = ROOT / "external-assets/work/launch-silo-preview"

INK = (224, 235, 242, 255)
MUTED = (126, 148, 161, 255)
GRID = (49, 64, 74, 255)
AIR = (11, 23, 31, 255)
WALL = (54, 64, 70, 255)
DECK = (102, 111, 117, 255)
GANTRY = (236, 191, 67, 255)
PLUG = (255, 137, 50, 255)
PATH = (255, 214, 91, 255)
UNIT00 = (232, 145, 54, 255)
UNIT01 = (150, 80, 220, 255)
UNIT02 = (223, 61, 58, 255)
PASS = (91, 218, 136, 255)
FAIL = (255, 78, 78, 255)


def fail(message: str) -> RuntimeError:
    return RuntimeError(f"launch-silo contract parse failed: {message}")


def source_text(path: Path) -> str:
    if not path.is_file():
        raise fail(f"missing source {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def one(pattern: str, text: str, label: str, flags: int = 0) -> re.Match[str]:
    matches = list(re.finditer(pattern, text, flags))
    if len(matches) != 1:
        raise fail(f"expected one {label}, found {len(matches)}")
    return matches[0]


def method_body(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise fail(f"method {signature}")
    brace = text.find("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:index]
    raise fail(f"unterminated method {signature}")


def java_number(text: str, name: str) -> float:
    match = one(
        rf"\b{name}\s*=\s*(-?\d+(?:\.\d+)?)(?:D|F)?\s*;",
        text,
        name,
    )
    return float(match.group(1))


def loop_range(text: str, variable: str, start: int, end: int, label: str) -> tuple[int, int]:
    pattern = rf"for\s*\(int\s+{re.escape(variable)}\s*=\s*({start});\s*{re.escape(variable)}\s*<=\s*({end});\s*{re.escape(variable)}\+\+\)"
    match = one(pattern, text, label)
    return int(match.group(1)), int(match.group(2))


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_bone(geo: dict[str, Any], name: str) -> dict[str, Any]:
    geometries = geo.get("minecraft:geometry", [])
    if len(geometries) != 1:
        raise fail("Unit-01 geo must contain exactly one geometry")
    matches = [bone for bone in geometries[0].get("bones", []) if bone.get("name") == name]
    if len(matches) != 1:
        raise fail(f"expected one {name} bone, found {len(matches)}")
    return matches[0]


@dataclass(frozen=True)
class SiloContract:
    bays: tuple[tuple[str, int, int], ...]
    shaft_y: tuple[int, int]
    shaft_outer_half: int
    permanent_bed_half: int
    moving_carrier_half: int
    bed_origin_offset: int
    surface_origin_offset: int
    shutter_origin_offset: int
    gantry_origin_offset: int
    gantry_x: tuple[int, int]
    gantry_z: tuple[int, int]
    ladder_origin_y: tuple[int, int]
    ladder_z: int
    audit_y: tuple[int, int]
    audit_x: tuple[int, int]
    audit_z: tuple[int, int]
    deploy_origin_y: float
    deploy_yaw: float
    board_bed_y: float
    board_bed_z: float
    unit_width: float
    unit_height: float
    entry_min_height: float
    entry_max_height: float
    entry_min_distance: float
    entry_max_distance: float
    entry_min_rear_dot: float
    launch_target: float
    ascent_ticks: int
    clear_ticks: int
    renderer_scale: float
    plug_pivot_y: float
    runtime_plug_height: float
    plug_animation_start_y: float
    plug_animation_end_y: float
    geo_origin_y: int
    tokyo_origin_y: int
    legacy_launch_target: float
    legacy_ascent_ticks: int
    same_dimension_primary: bool

    @property
    def bed_y(self) -> float:
        return 0.0

    @property
    def surface_y(self) -> float:
        return self.surface_origin_offset - self.bed_origin_offset

    @property
    def shutter_y(self) -> float:
        return self.shutter_origin_offset - self.bed_origin_offset

    @property
    def gantry_y(self) -> float:
        return self.gantry_origin_offset - self.bed_origin_offset

    @property
    def unit_base_y(self) -> float:
        return self.deploy_origin_y - self.bed_origin_offset

    @property
    def ladder_y(self) -> tuple[float, float]:
        return tuple(value - self.bed_origin_offset for value in self.ladder_origin_y)  # type: ignore[return-value]

    @property
    def plug_socket_world_y(self) -> float:
        return self.unit_base_y + self.runtime_plug_height

    @property
    def plug_start_world_y(self) -> float:
        return self.plug_socket_world_y + self.plug_animation_start_y * self.renderer_scale / 16.0

    @property
    def plug_end_world_y(self) -> float:
        return self.plug_socket_world_y + self.plug_animation_end_y * self.renderer_scale / 16.0


def parse_contract() -> SiloContract:
    kit = source_text(KIT_SOURCE)
    integrated = source_text(INTEGRATED_SOURCE)
    command = source_text(COMMAND_SOURCE)
    entity = source_text(ENTITY_SOURCE)
    renderer = source_text(RENDERER_SOURCE)
    shaft = method_body(kit, "private static void buildLaunchShaft")
    gantry = method_body(kit, "private static void buildEntryGantry")
    deploy = method_body(kit, "private static void deployUnit")
    audit = method_body(command, "private static SiloAudit inspectComplex")
    board = method_body(command, "static int board")
    moving_carrier = method_body(entity, "private void setMovingCarrierLayer")

    bay_matches = re.findall(
        r"BlockPos\s+unit(\d\d)Bay\s*=\s*origin(?:\.offset\((-?\d+),\s*0,\s*(-?\d+)\))?\s*;",
        kit,
    )
    if len(bay_matches) != 3:
        raise fail(f"expected three bay declarations, found {len(bay_matches)}")
    legacy_bays = tuple((variant, int(x or 0), int(z or 0))
                        for variant, x, z in bay_matches)

    deploy_calls = re.findall(r"deployUnit\(level,\s*unit(\d\d)Bay,\s*ModEntities\.EVA_UNIT(\d\d)", kit)
    if len(deploy_calls) != 3 or any(bay != entity_id for bay, entity_id in deploy_calls):
        raise fail("bay-to-variant deploy mapping")

    # The standalone construction kit remains a compact entry-plug test rig.
    # The release-facing preview is driven by the real, vertically integrated
    # Tokyo-3/GeoFront station markers instead.
    geo_match = one(
        r"GEOFRONT_ORIGIN\s*=\s*new BlockPos\((-?\d+),\s*(-?\d+),\s*(-?\d+)\)",
        integrated, "GeoFront origin")
    tokyo_match = one(
        r"TOKYO3_ORIGIN\s*=\s*new BlockPos\((-?\d+),\s*(-?\d+),\s*(-?\d+)\)",
        integrated, "Tokyo-3 origin")
    geo_origin = tuple(int(geo_match.group(index)) for index in range(1, 4))
    tokyo_origin = tuple(int(tokyo_match.group(index)) for index in range(1, 4))
    lift_initializer = one(r"LIFT_X\s*=\s*\{([^}]+)\}", integrated,
                           "integrated lift X").group(1)
    lift_values = tuple(int(value) for value in re.findall(
        r"-?\d+", lift_initializer))
    if len(lift_values) != 3:
        raise fail(f"expected three integrated lift X positions, found {lift_values}")
    lower_z = int(java_number(integrated, "LOWER_TERMINAL_Z"))
    lower_above = int(java_number(integrated, "LOWER_BED_ABOVE_ORIGIN"))
    surface_below = int(java_number(integrated, "SURFACE_BED_BELOW_ORIGIN"))
    lower_bed_y = geo_origin[1] + lower_above
    surface_bed_y = tokyo_origin[1] - surface_below
    ascent_distance = surface_bed_y - lower_bed_y
    bays = tuple((variant, x, geo_origin[2] + lower_z)
                 for (variant, _, _), x in zip(legacy_bays, lift_values))
    shaft_y = (lower_bed_y + 1, surface_bed_y)
    outer = int(java_number(integrated, "SHAFT_OUTER_RADIUS"))
    clear_half = int(java_number(integrated, "SHAFT_CLEAR_RADIUS"))
    carrier_loop = one(
        r"for\s*\(int x = (-?\d+); x <= (-?\d+); x\+\+\)\s*\{\s*"
        r"for\s*\(int z = (-?\d+); z <= (-?\d+); z\+\+\)\s*\{\s*"
        r"boolean rim = Math\.abs\(x\)",
        shaft,
        "carrier loops",
        re.S,
    )
    permanent_bed_half = max(abs(int(carrier_loop.group(1))), abs(int(carrier_loop.group(2))))
    moving_carrier_loop = one(
        r"for\s*\(int x = (-?\d+); x <= (-?\d+); x\+\+\)\s*\{\s*"
        r"for\s*\(int z = (-?\d+); z <= (-?\d+); z\+\+\)",
        moving_carrier,
        "moving carrier loops",
        re.S,
    )
    moving_ranges = tuple(int(moving_carrier_loop.group(index)) for index in range(1, 5))
    if moving_ranges[0] != moving_ranges[2] or moving_ranges[1] != moving_ranges[3]:
        raise fail(f"moving carrier is not square: {moving_ranges}")
    moving_carrier_half = max(abs(moving_ranges[0]), abs(moving_ranges[1]))
    bed_offset = int(one(r"centre\.offset\(0,\s*(-?\d+),\s*0\),\s*Blocks\.LODESTONE", shaft, "lodestone bed").group(1))
    shutter_offset = int(one(r"centre\.offset\(i,\s*(-?\d+),\s*-8\)", shaft, "surface shutter").group(1))

    gantry_origin = int(one(r"int gantryY = (-?\d+)\s*;", gantry, "gantry Y").group(1))
    ladder_match = one(r"for\s*\(int y = (-?\d+); y <= (-?\d+); y\+\+\).*?centre\.offset\(0, y, (\d+)\), ladder", gantry, "ladder contract", re.S)
    ladder_y = (int(ladder_match.group(1)), int(ladder_match.group(2)))
    ladder_z = int(ladder_match.group(3))
    gantry_path = one(r"for\s*\(int z = (-?\d+); z <= (-?\d+); z\+\+\)\s*\{\s*for\s*\(int x = (-?\d+); x <= (-?\d+); x\+\+\)", gantry, "catwalk loops", re.S)
    gantry_z = (int(gantry_path.group(1)), int(gantry_path.group(2)))
    gantry_x = (int(gantry_path.group(3)), int(gantry_path.group(4)))

    # Parse the old audit as a compatibility assertion, but expose the 11x11
    # continuous envelope in the report.
    one(r"for\s*\(int y = (\d+); y <= (\d+) && clear; y\+\+\)", audit, "legacy audit y")
    one(r"for\s*\(int x = (-?\d+); x <= (-?\d+) && clear; x\+\+\)", audit, "legacy audit x")
    one(r"for\s*\(int z = (-?\d+); z <= (-?\d+); z\+\+\)", audit, "legacy audit z")

    move = one(r"unit\.moveTo\(bay\.getX\(\) \+ 0\.5D, bay\.getY\(\) ([+-]) (\d+(?:\.\d+)?)D, bay\.getZ\(\) \+ 0\.5D,\s*launchYaw", deploy, "deployed Unit pose", re.S)
    launch_yaw = one(r"float\s+launchYaw\s*=\s*(\d+(?:\.\d+)?)F", deploy,
                     "deployed Unit yaw")
    deploy_y = float(move.group(2)) * (-1.0 if move.group(1) == "-" else 1.0)
    deploy_yaw = float(launch_yaw.group(1))
    board_match = one(r"bed\.getY\(\) \+ (\d+(?:\.\d+)?)D,\s*bed\.getZ\(\) \+ (\d+(?:\.\d+)?)D", board, "board teleport", re.S)

    scale = float(one(r"this\.withScale\((\d+(?:\.\d+)?)F\)", renderer, "renderer scale").group(1))
    geo = json.loads(source_text(GEO_SOURCE))
    entry_bone = find_bone(geo, "entry_plug")
    pivot = entry_bone.get("pivot")
    if not isinstance(pivot, list) or len(pivot) != 3:
        raise fail("entry_plug pivot")

    animations = json.loads(source_text(ANIMATION_SOURCE)).get("animations", {})
    activation = animations.get("animation.eva_unit01.activation", {})
    positions = activation.get("bones", {}).get("entry_plug", {}).get("position", {})
    if not isinstance(positions, dict) or len(positions) < 2:
        raise fail("entry_plug activation positions")
    ordered = sorted((float(time), value) for time, value in positions.items())
    if any(not isinstance(value, list) or len(value) != 3 for _, value in ordered):
        raise fail("entry_plug activation position vector")

    legacy_target = java_number(entity, "LAUNCH_TARGET_ABOVE_BED")
    legacy_ticks = int(java_number(entity, "LAUNCH_ASCENT_TICKS"))
    ascent_speed = java_number(entity, "CONTINUOUS_ASCENT_BLOCKS_PER_TICK")
    dynamic_ticks = max(legacy_ticks, math.ceil(ascent_distance / ascent_speed))
    complete = method_body(entity, "private boolean completeLinkedSortie()")
    same_start = complete.find("if (destination == sourceLevel)")
    legacy_start = complete.find("this.changeDimension(destination", same_start)
    same_branch = complete[same_start:legacy_start] \
        if 0 <= same_start < legacy_start else ""
    same_dimension_primary = bool(same_branch) \
        and "changeDimension" not in same_branch \
        and "this.setPos(arrival.x, arrival.y, arrival.z)" in same_branch

    return SiloContract(
        bays=bays,
        shaft_y=shaft_y,
        shaft_outer_half=outer,
        permanent_bed_half=permanent_bed_half,
        moving_carrier_half=moving_carrier_half,
        bed_origin_offset=bed_offset,
        surface_origin_offset=bed_offset + ascent_distance,
        shutter_origin_offset=bed_offset + ascent_distance,
        gantry_origin_offset=gantry_origin,
        gantry_x=gantry_x,
        gantry_z=gantry_z,
        ladder_origin_y=ladder_y,
        ladder_z=ladder_z,
        audit_y=(1, ascent_distance),
        audit_x=(-clear_half, clear_half),
        audit_z=(-clear_half, clear_half),
        deploy_origin_y=deploy_y,
        deploy_yaw=deploy_yaw,
        board_bed_y=float(board_match.group(1)),
        board_bed_z=float(board_match.group(2)),
        unit_width=java_number(entity, "NORMAL_WIDTH"),
        unit_height=java_number(entity, "NORMAL_HEIGHT"),
        entry_min_height=java_number(entity, "SILO_ENTRY_MIN_HEIGHT"),
        entry_max_height=java_number(entity, "SILO_ENTRY_MAX_HEIGHT"),
        entry_min_distance=java_number(entity, "SILO_ENTRY_MIN_DISTANCE"),
        entry_max_distance=java_number(entity, "SILO_ENTRY_MAX_DISTANCE"),
        entry_min_rear_dot=java_number(entity, "SILO_ENTRY_MIN_REAR_DOT"),
        launch_target=float(ascent_distance + 1),
        ascent_ticks=dynamic_ticks,
        clear_ticks=int(java_number(entity, "LAUNCH_CLEAR_TICKS")),
        renderer_scale=scale,
        plug_pivot_y=float(pivot[1]),
        runtime_plug_height=java_number(entity, "ENTRY_PLUG_HEIGHT_01"),
        plug_animation_start_y=float(ordered[0][1][1]),
        plug_animation_end_y=float(ordered[-1][1][1]),
        geo_origin_y=geo_origin[1],
        tokyo_origin_y=tokyo_origin[1],
        legacy_launch_target=legacy_target,
        legacy_ascent_ticks=legacy_ticks,
        same_dimension_primary=same_dimension_primary,
    )


def check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "observed": observed, "expected": expected}


def audit_contract(contract: SiloContract) -> dict[str, Any]:
    variants = [variant for variant, _, _ in contract.bays]
    bay_positions = [(x, z) for _, x, z in contract.bays]
    clear_width = contract.audit_x[1] - contract.audit_x[0] + 1
    clear_depth = contract.audit_z[1] - contract.audit_z[0] + 1
    clear_height = contract.audit_y[1] - contract.audit_y[0] + 1
    ladder_count = contract.ladder_y[1] - contract.ladder_y[0] + 1
    permanent_bed_width = contract.permanent_bed_half * 2 + 1
    moving_carrier_width = contract.moving_carrier_half * 2 + 1
    carrier_travel = contract.launch_target - 1.0
    player_relative_height = contract.board_bed_y - contract.unit_base_y
    board_distance = abs(contract.board_bed_z)
    yaw_radians = math.radians(contract.deploy_yaw)
    forward = (-math.sin(yaw_radians), math.cos(yaw_radians))
    rear = (-forward[0], -forward[1])
    board_dir = (0.0, 1.0 if contract.board_bed_z >= 0.0 else -1.0)
    rear_dot = board_dir[0] * rear[0] + board_dir[1] * rear[1]

    checks = [
        check("three_variants", variants == ["00", "01", "02"], variants, ["00", "01", "02"]),
        check("three_unique_beds", len(set(bay_positions)) == 3, bay_positions, "three unique bay centres"),
        check("bay_spacing", sorted(x for x, _ in bay_positions) == [-28, 0, 28], bay_positions, "x=-28,0,28"),
        check("integrated_world_heights", contract.geo_origin_y == -40 and contract.tokyo_origin_y == 248, {"geofront_origin_y": contract.geo_origin_y, "tokyo3_origin_y": contract.tokyo_origin_y}, {"geofront_origin_y": -40, "tokyo3_origin_y": 248}),
        check("shaft_shell", contract.shaft_outer_half == 7 and contract.shaft_y == (-38, 247), {"half": contract.shaft_outer_half, "world_y": contract.shaft_y}, {"half": 7, "world_y": [-38, 247]}),
        check("clearance_11x11", clear_width == 11 and clear_depth == 11, [clear_width, clear_depth], [11, 11]),
        check("clearance_286_high", clear_height == 286 and contract.audit_y == (1, 286), {"height": clear_height, "bed_relative_y": contract.audit_y}, {"height": 286, "bed_relative_y": [1, 286]}),
        check("eva_fits_clearance", contract.unit_width <= clear_width, contract.unit_width, f"<= {clear_width}"),
        check("permanent_bed_13x13", permanent_bed_width == 13, permanent_bed_width, 13),
        check("moving_carrier_11x11", moving_carrier_width == 11, moving_carrier_width, 11),
        check("high_dorsal_gantry", contract.gantry_y == 26 and contract.board_bed_y == 27, {"floor_y": contract.gantry_y, "boarding_y": contract.board_bed_y}, {"floor_y": 26, "boarding_y": 27}),
        check("ladder_24_blocks", ladder_count == 24 and contract.ladder_y == (4, 27), {"count": ladder_count, "bed_relative_y": contract.ladder_y}, {"count": 24, "bed_relative_y": [4, 27]}),
        check("entry_height_gate", contract.entry_min_height <= player_relative_height <= contract.entry_max_height, player_relative_height, [contract.entry_min_height, contract.entry_max_height]),
        check("entry_rear_sector", contract.entry_min_distance <= board_distance <= contract.entry_max_distance and rear_dot >= contract.entry_min_rear_dot, {"distance": board_distance, "rear_dot": round(rear_dot, 4)}, {"distance": [contract.entry_min_distance, contract.entry_max_distance], "rear_dot_min": contract.entry_min_rear_dot}),
        check("entry_socket_matches_gantry", 0.4 <= contract.plug_socket_world_y - contract.board_bed_y <= 2.2, {"socket_y": round(contract.plug_socket_world_y, 3), "boarding_feet_y": contract.board_bed_y}, "socket 0.4..2.2 blocks above boarding feet"),
        check("plug_descends_from_above", contract.plug_animation_start_y > contract.plug_animation_end_y and contract.plug_start_world_y > contract.plug_end_world_y, {"animation_y": [contract.plug_animation_start_y, contract.plug_animation_end_y], "world_y": [round(contract.plug_start_world_y, 3), round(contract.plug_end_world_y, 3)]}, "start above end"),
        check("plug_starts_above_gantry", contract.plug_start_world_y > contract.board_bed_y, round(contract.plug_start_world_y, 3), f"> {contract.board_bed_y}"),
        check("carrier_travel_286", abs(carrier_travel - 286.0) < 1.0e-6, carrier_travel, 286.0),
        check("launch_endpoint", contract.launch_target == 287.0 and contract.shutter_y == 286.0 and contract.launch_target > contract.shutter_y, {"eva_base_y": contract.launch_target, "surface_y": contract.surface_y, "shutter_y": contract.shutter_y}, {"eva_base_y": 287.0, "surface_y": 286.0, "above_shutter": True}),
        check("dynamic_ascent_143_ticks", contract.ascent_ticks == 143 and contract.legacy_ascent_ticks == 34, {"continuous_ticks": contract.ascent_ticks, "legacy_ticks": contract.legacy_ascent_ticks}, {"continuous_ticks": 143, "legacy_ticks": 34}),
        check("same_dimension_primary", contract.same_dimension_primary, contract.same_dimension_primary, True),
        check("surface_clear_timed", contract.clear_ticks > 0, contract.clear_ticks, "> 0"),
    ]
    return {
        "schema": 2,
        "status": "PASS" if all(item["pass"] for item in checks) else "FAIL",
        "contract": {
            "bays": [{"variant": variant, "x": x, "z": z} for variant, x, z in contract.bays],
            "bed_relative": {
                "bed_y": contract.bed_y,
                "surface_y": contract.surface_y,
                "shutter_y": contract.shutter_y,
                "gantry_floor_y": contract.gantry_y,
                "boarding_y": contract.board_bed_y,
                "unit_start_base_y": contract.unit_base_y,
                "launch_base_y": contract.launch_target,
            },
            "shaft": {
                "outer_half_width": contract.shaft_outer_half,
                "permanent_bed_half_width": contract.permanent_bed_half,
                "moving_carrier_half_width": contract.moving_carrier_half,
                "clearance_x": list(contract.audit_x),
                "clearance_y": list(contract.audit_y),
                "clearance_z": list(contract.audit_z),
            },
            "gantry": {
                "x": list(contract.gantry_x),
                "z": list(contract.gantry_z),
                "ladder_y": list(contract.ladder_y),
                "ladder_z": contract.ladder_z,
            },
            "entry_plug": {
                "renderer_scale": contract.renderer_scale,
                "pivot_model_y": contract.plug_pivot_y,
                "runtime_socket_height": contract.runtime_plug_height,
                "animation_model_y": [contract.plug_animation_start_y, contract.plug_animation_end_y],
                "world_path_y": [round(contract.plug_start_world_y, 4), round(contract.plug_end_world_y, 4)],
            },
            "launch": {
                "carrier_travel": carrier_travel,
                "continuous_ascent_ticks": contract.ascent_ticks,
                "legacy_target": contract.legacy_launch_target,
                "legacy_ascent_ticks": contract.legacy_ascent_ticks,
                "same_dimension_primary": contract.same_dimension_primary,
                "surface_clear_ticks": contract.clear_ticks,
            },
        },
        "checks": checks,
        "sources": {
            str(path.relative_to(ROOT)).replace("\\", "/"): file_hash(path)
            for path in (KIT_SOURCE, INTEGRATED_SOURCE, COMMAND_SOURCE,
                         ENTITY_SOURCE, RENDERER_SOURCE, GEO_SOURCE,
                         ANIMATION_SOURCE)
        },
        "limitations": [
            "Schematic geometry verifies authored coordinates and state-machine contracts, not Minecraft block rendering.",
            "Runtime collision, interpolation, particles, sounds, and perceived launch weight still require in-game review.",
        ],
    }


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def line_arrow(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill: tuple[int, ...], width: int = 4) -> None:
    draw.line(points, fill=fill, width=width)
    if len(points) < 2:
        return
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 13
    wing = 0.55
    tip = (x2, y2)
    left = (x2 - length * math.cos(angle - wing), y2 - length * math.sin(angle - wing))
    right = (x2 - length * math.cos(angle + wing), y2 - length * math.sin(angle + wing))
    draw.polygon([tip, left, right], fill=fill)


def render_preview(contract: SiloContract, report: dict[str, Any], output: Path) -> None:
    image = Image.new("RGBA", (1600, 1000), (7, 15, 22, 255))
    draw = ImageDraw.Draw(image)
    title = font(34, True)
    heading = font(24, True)
    body = font(18)
    small = font(15)
    tiny = font(13)

    draw.text((42, 28), "NERV CONTINUOUS THREE-SHAFT / OFFLINE CONTRACT PREVIEW", font=title, fill=INK)
    status_color = PASS if report["status"] == "PASS" else FAIL
    draw.rounded_rectangle((1330, 27, 1555, 75), 10, outline=status_color, width=3)
    draw.text((1398, 36), report["status"], font=heading, fill=status_color)
    draw.text((44, 78), "Tokyo-3 Y=248 and GeoFront Y=-40 share one dimension; coordinates are parsed from Java.", font=small, fill=MUTED)

    # Top view: the three actual bay centres and full shaft/clearance/gantry footprints.
    top_box = (40, 120, 940, 570)
    draw.rounded_rectangle(top_box, 10, fill=(9, 20, 28, 255), outline=GRID, width=2)
    draw.text((64, 140), "TOP VIEW — SURFACE APRON + THREE DORSAL GANTRIES", font=heading, fill=INK)
    # Fit the authored 89x69 apron inside this panel; keep X and Z scales
    # separate so the three-bay spacing remains immediately legible.
    sx, sz = 8.75, 5.45
    cx, cy = 490.0, 355.0

    def top(x: float, z: float) -> tuple[float, float]:
        return cx + x * sx, cy + z * sz

    # Apron is x -44..44, z -30..38.
    a0 = top(-44, -30)
    a1 = top(44, 38)
    draw.rectangle((a0[0], a0[1], a1[0], a1[1]), fill=(31, 38, 43, 255), outline=DECK, width=2)
    colors = {"00": UNIT00, "01": UNIT01, "02": UNIT02}
    for variant, bx, bz in contract.bays:
        color = colors[variant]
        shaft0 = top(bx - contract.shaft_outer_half, bz - contract.shaft_outer_half)
        shaft1 = top(bx + contract.shaft_outer_half, bz + contract.shaft_outer_half)
        draw.rectangle((shaft0[0], shaft0[1], shaft1[0], shaft1[1]), fill=AIR, outline=WALL, width=5)
        clear0 = top(bx + contract.audit_x[0], bz + contract.audit_z[0])
        clear1 = top(bx + contract.audit_x[1], bz + contract.audit_z[1])
        draw.rectangle((clear0[0], clear0[1], clear1[0], clear1[1]), outline=PATH, width=2)
        gantry0 = top(bx + contract.gantry_x[0], bz + contract.gantry_z[0])
        gantry1 = top(bx + contract.gantry_x[1], bz + contract.gantry_z[1])
        draw.rectangle((gantry0[0], gantry0[1], gantry1[0], gantry1[1]), fill=(121, 91, 23, 255), outline=GANTRY, width=2)
        unit_radius = contract.unit_width * sx / 2.0
        ux, uy = top(bx, bz)
        draw.ellipse((ux - unit_radius, uy - unit_radius * 0.34, ux + unit_radius, uy + unit_radius * 0.34), outline=color, width=4)
        draw.line((ux, uy, ux, uy - 30), fill=color, width=4)
        draw.text((ux - 32, shaft0[1] - 28), f"UNIT-{variant}", font=small, fill=color)
        draw.text((ux - 24, uy + 8), "BED", font=tiny, fill=INK)
        line_arrow(draw, [(ux, gantry1[1] - 4), (ux, uy + 8)], PLUG, 3)
    draw.text((65, 525), "yellow square = audited 11x11 clear envelope   gold = high rear catwalk   orange arrow = entry direction", font=small, fill=MUTED)

    # Section view normalized to bed Y=0.  It shows both the carrier and the actual plug bone path.
    sec_box = (970, 120, 1560, 830)
    draw.rounded_rectangle(sec_box, 10, fill=(9, 20, 28, 255), outline=GRID, width=2)
    draw.text((994, 140), "UNIT-01 CONTINUOUS SECTION — LOWER BED = 0", font=heading, fill=INK)
    y_min = -1.0
    y_max = max(contract.surface_y + 3.0, contract.plug_start_world_y + 2.0)
    px_per_y = 570.0 / (y_max - y_min)
    origin_y = 770.0

    def section(z: float, y: float) -> tuple[float, float]:
        return 1235.0 + z * 15.0, origin_y - (y - y_min) * px_per_y

    wall_left = section(-contract.shaft_outer_half, contract.shutter_y)
    wall_bottom = section(-contract.shaft_outer_half, 0)
    wall_right = section(contract.shaft_outer_half, contract.shutter_y)
    draw.rectangle((wall_left[0] - 15, wall_left[1], wall_bottom[0], wall_bottom[1]), fill=WALL)
    draw.rectangle((wall_right[0], wall_right[1], wall_right[0] + 15, wall_bottom[1]), fill=WALL)

    # Ground and shutter/deck planes.
    _, surface_py = section(0, contract.surface_y)
    _, shutter_py = section(0, contract.shutter_y)
    draw.line((990, surface_py, 1540, surface_py), fill=(102, 80, 53, 255), width=5)
    draw.text((995, surface_py - 28), f"GROUND +{contract.surface_y:.0f}", font=small, fill=INK)
    draw.line((1130, shutter_py, 1340, shutter_py), fill=DECK, width=8)
    draw.text((1348, shutter_py - 10), f"SHUTTER +{contract.shutter_y:.0f}", font=tiny, fill=MUTED)

    # Clear carrier envelope and parked platform.
    clear_l = section(contract.audit_z[0], contract.audit_y[1])
    clear_r = section(contract.audit_z[1], contract.audit_y[0])
    draw.rectangle((clear_l[0], clear_l[1], clear_r[0], clear_r[1]), outline=PATH, width=2)
    bed_l = section(-contract.permanent_bed_half, 0)
    bed_r = section(contract.permanent_bed_half, 0)
    draw.line((bed_l[0], bed_l[1], bed_r[0], bed_r[1]), fill=(94, 221, 227, 255), width=9)
    draw.text((1035, bed_l[1] + 9), "PERMANENT BED APRON 13x13", font=tiny, fill=(94, 221, 227, 255))

    # EVA at the bed and dashed endpoint silhouette.
    unit_left = section(-contract.unit_width / 2, contract.unit_base_y + contract.unit_height)
    unit_right = section(contract.unit_width / 2, contract.unit_base_y)
    draw.rounded_rectangle((unit_left[0], unit_left[1], unit_right[0], unit_right[1]), 18, outline=UNIT01, width=3)
    draw.text((unit_left[0] + 8, unit_left[1] + 12), "EVA", font=heading, fill=UNIT01)
    end_base = section(0, contract.launch_target)[1]
    draw.line((1125, end_base, 1345, end_base), fill=PASS, width=3)
    draw.text((1350, end_base - 10), f"EVA BASE +{contract.launch_target:.0f}", font=tiny, fill=PASS)

    # Carrier launch path.
    carrier_x = section(-5.6, 0)[0]
    line_arrow(draw, [(carrier_x, section(0, 0)[1] - 6), (carrier_x, section(0, contract.launch_target - 1)[1])], (94, 221, 227, 255), 5)
    draw.text((carrier_x - 105, section(0, contract.surface_y * 0.5)[1] - 18),
              f"{contract.surface_y:.0f} BLOCK\nCARRIER TRAVEL\n{contract.ascent_ticks} TICKS",
              font=small, fill=(94, 221, 227, 255), align="center")
    carrier_probe_y = contract.surface_y * 0.5
    carrier_l = section(-contract.moving_carrier_half, carrier_probe_y)
    carrier_r = section(contract.moving_carrier_half, carrier_probe_y)
    draw.line((carrier_l[0], carrier_l[1], carrier_r[0], carrier_r[1]), fill=(94, 221, 227, 255), width=6)
    draw.text((carrier_r[0] + 8, carrier_r[1] - 8), "MOVING 11x11", font=tiny, fill=(94, 221, 227, 255))

    # High rear gantry, ladder and boarding station.
    gy = section(0, contract.gantry_y)[1]
    gz0 = section(contract.gantry_z[0], contract.gantry_y)[0]
    gz1 = section(contract.gantry_z[1], contract.gantry_y)[0]
    draw.line((gz0, gy, gz1, gy), fill=GANTRY, width=10)
    ladder_x = section(contract.ladder_z, 0)[0]
    ly0 = section(0, contract.ladder_y[0])[1]
    ly1 = section(0, contract.ladder_y[1])[1]
    draw.line((ladder_x, ly0, ladder_x, ly1), fill=GANTRY, width=5)
    for y in range(int(contract.ladder_y[0]), int(contract.ladder_y[1]) + 1, 2):
        py = section(0, y)[1]
        draw.line((ladder_x - 8, py, ladder_x + 8, py), fill=GANTRY, width=2)
    board_x, board_y = section(contract.board_bed_z, contract.board_bed_y)
    draw.ellipse((board_x - 7, board_y - 7, board_x + 7, board_y + 7), fill=GANTRY)
    draw.text((1350, gy + 8), f"DORSAL GANTRY +{contract.gantry_y:.0f}\nBOARD +{contract.board_bed_y:.0f}", font=tiny, fill=GANTRY)

    # Entry plug path from its animation, located at the dorsal side.
    plug_z = 2.5
    start = section(plug_z, contract.plug_start_world_y)
    end = section(plug_z, contract.plug_end_world_y)
    draw.rounded_rectangle((start[0] - 8, start[1] - 20, start[0] + 8, start[1] + 20), 5, outline=PLUG, width=3)
    line_arrow(draw, [start, end], PLUG, 5)
    draw.text((1030, 205), f"ENTRY PLUG PATH\n+{contract.plug_start_world_y:.1f} -> +{contract.plug_end_world_y:.1f}", font=small, fill=PLUG)

    # Check summary footer.
    passed = sum(1 for item in report["checks"] if item["pass"])
    total = len(report["checks"])
    draw.rounded_rectangle((40, 600, 940, 950), 10, fill=(9, 20, 28, 255), outline=GRID, width=2)
    draw.text((64, 620), f"STRICT CONTRACT GATES — {passed}/{total}", font=heading, fill=status_color)
    for index, item in enumerate(report["checks"]):
        column = index // 8
        row = index % 8
        x = 66 + column * 290
        y = 667 + row * 34
        color = PASS if item["pass"] else FAIL
        draw.text((x, y), "PASS" if item["pass"] else "FAIL", font=tiny, fill=color)
        draw.text((x + 48, y), item["name"], font=small, fill=INK)
    draw.text((990, 860), "Offline only: this sheet proves coordinate/state contracts,", font=small, fill=MUTED)
    draw.text((990, 885), "not final Minecraft lighting, collision, timing feel, or animation quality.", font=small, fill=MUTED)
    draw.text((990, 925), "PNG and JSON share the same parsed contract.", font=small, fill=INK)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=95)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT / "launch_silo_preview.png")
    parser.add_argument("--report", type=Path, default=DEFAULT_OUTPUT / "launch_silo_preview.json")
    parser.add_argument("--strict", action="store_true", help="return non-zero when any contract gate fails")
    args = parser.parse_args()

    contract = parse_contract()
    report = audit_contract(contract)
    render_preview(contract, report, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"launch silo preview: {report['status']}")
    print(f"png: {args.output}")
    print(f"json: {args.report}")
    failed = [item["name"] for item in report["checks"] if not item["pass"]]
    if failed:
        print("failed gates: " + ", ".join(failed))
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
