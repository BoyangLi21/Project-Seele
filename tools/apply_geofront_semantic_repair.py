#!/usr/bin/env python3
"""Apply three narrow, independently reported R28 GeoFront repairs.

1. Replace measured natural-stone shell needles with the existing skyweave.
2. Retire the artificial rectangular lake and carve an organic west lake.
3. Seal all space below the Terminal Dogma LCL lake with natural deepslate.

The pyramid, hangars, launch wells, command room and their air volumes are not
inside any write domain owned by this script.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

from apply_s20_approved_semantic_repairs import (
    Change,
    atomic_replace,
    rewrite_region,
)
from audit_geofront_semantic_targets import scan as audit_targets
from query_blocks import dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
SKYWEAVE = "projectseele:geofront_skyweave"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def organic_lake_factor(x: int, z: int) -> tuple[float, float]:
    cx, cz = -165.0, 150.0
    dx, dz = (x - cx) / 76.0, (z - cz) / 58.0
    theta = math.atan2(dz, dx)
    radius = math.sqrt(dx * dx + dz * dz)
    edge = (1.0 + 0.10 * math.sin(theta * 3.0 + 0.4) +
            0.055 * math.sin(theta * 7.0 - 0.9) +
            0.035 * math.cos(theta * 11.0 + 0.2))
    return radius, edge


def add_change(desired: dict, cells: dict, packet: str,
               position: tuple[int, int, int], after: str, reason: str):
    before = cells.get(position, "minecraft:air")
    if before == after:
        desired.pop(position, None)
        return
    desired[position] = Change(packet, *position, before, after,
                               "semantic_repair", reason)


def pillar_changes(world: Path) -> list[Change]:
    report = audit_targets(world)
    changes = []
    packet = "S21-GEOFRONT-SHELL-NEEDLES-R01"
    for needle in report["stoneNeedles"]:
        for y in range(needle["y0"], needle["y1"] + 1):
            changes.append(Change(
                packet, needle["x"], y, needle["z"],
                "minecraft:stone", SKYWEAVE, "semantic_repair",
                "measured_shell_stone_needle"))
    return changes


def lake_changes(world: Path) -> list[Change]:
    packet = "S21-GEOFRONT-WEST-LAKE-R01"
    lo, hi = (-245, -450, 85), (-30, -425, 220)
    cells = read_box(world, DIMENSION, lo, hi)
    desired: dict[tuple[int, int, int], Change] = {}
    road = {
        "minecraft:black_concrete", "minecraft:polished_deepslate",
        "minecraft:deepslate_tiles", "minecraft:deepslate_bricks",
        "minecraft:chiseled_polished_blackstone",
    }
    vegetation = {
        "minecraft:dark_oak_log", "minecraft:stripped_dark_oak_log",
        "minecraft:dark_oak_leaves", "minecraft:azalea_leaves",
        "minecraft:flowering_azalea_leaves", "minecraft:moss_block",
        "minecraft:grass", "minecraft:tall_grass", "minecraft:fern",
    }
    replaceable = {
        "minecraft:water", "minecraft:grass_block", "minecraft:dirt",
        "minecraft:stone", "minecraft:clay", "minecraft:gravel",
        "minecraft:sand", "minecraft:light_gray_concrete",
        "minecraft:sea_lantern", "minecraft:light",
    } | vegetation | AIR

    # The old pool was not only water: its regular raised grass squares and
    # dotted lamps are part of the same failed test construction.  Mark every
    # column within six blocks of its measured water footprint so those
    # artificial islands are flattened together with the pool.  Structural
    # black/deepslate road columns are excluded and remain as a causeway.
    old_water_columns = {
        (x, z) for (x, y, z), state in cells.items()
        if bare(state) == "minecraft:water" and -448 <= y <= -444
        and organic_lake_factor(x, z)[0] > organic_lake_factor(x, z)[1] + 0.075
    }
    old_affected_columns = set()
    for x, z in old_water_columns:
        for dx in range(-6, 7):
            for dz in range(-6, 7):
                if dx * dx + dz * dz <= 36:
                    old_affected_columns.add((x + dx, z + dz))
    road_columns = set()
    for x in range(lo[0], hi[0] + 1):
        for z in range(lo[2], hi[2] + 1):
            if any(bare(cells.get((x, y, z), "minecraft:air")) in road
                   for y in range(-450, -429)):
                road_columns.add((x, z))

    # Retire both rectangular legacy water components and their dotted rim.
    for position, state in cells.items():
        x, y, z = position
        name = bare(state)
        old_zone = -205 <= x <= -35 and 95 <= z <= 215
        if not old_zone:
            continue
        if name == "minecraft:water" and -448 <= y <= -444:
            replacement = ("minecraft:grass_block[snowy=false]"
                           if y == -444 else "minecraft:dirt")
            add_change(desired, cells, packet, position, replacement,
                       "retire_rectangular_lake")
        elif (name in {"minecraft:light_gray_concrete",
                       "minecraft:sea_lantern"} and -446 <= y <= -443):
            replacement = ("minecraft:grass_block[snowy=false]"
                           if y >= -444 else "minecraft:dirt")
            add_change(desired, cells, packet, position, replacement,
                       "remove_dotted_lake_rim")

    # Remove the raised square islands and their foliage.  The final lake pass
    # below writes water back only inside the organic shoreline; elsewhere the
    # retired test pool becomes continuous grassland at y=-444.
    for x, z in old_affected_columns:
        if not (-205 <= x <= -35 and 95 <= z <= 215):
            continue
        if (x, z) in road_columns:
            continue
        for y in range(-443, -429):
            name = bare(cells.get((x, y, z), "minecraft:air"))
            if name in replaceable:
                add_change(desired, cells, packet, (x, y, z),
                           "minecraft:air", "flatten_legacy_square_island")
        if bare(cells.get((x, -444, z), "minecraft:air")) in replaceable:
            add_change(desired, cells, packet, (x, -444, z),
                       "minecraft:grass_block[snowy=false]",
                       "restore_continuous_grassland")

    # Carve a farther-west organic lake. Existing roads remain as causeways.
    for x in range(-242, -87):
        for z in range(88, 213):
            radius, edge = organic_lake_factor(x, z)
            if radius > edge + 0.075:
                continue
            if radius <= edge:
                # A causeway may remain, but trees and foliage must not float
                # above it or survive as tiny islands in open water.
                for y in range(-443, -424):
                    if bare(cells.get((x, y, z), "minecraft:air")) in vegetation:
                        add_change(desired, cells, packet, (x, y, z),
                                   "minecraft:air", "clear_lake_vegetation")
            if (x, z) in road_columns:
                continue
            # Keep the lake inside the measured GeoFront cavity at this y.
            sphere_r = math.sqrt((x - 30) ** 2 + (-444 + 332) ** 2 +
                                 (z - 220) ** 2)
            if sphere_r > 316.0:
                continue
            if radius <= edge:
                depth = 2 + min(3, int(max(0.0, edge - radius) * 5.0))
                for y in range(-443, -429):
                    state = cells.get((x, y, z), "minecraft:air")
                    if bare(state) in replaceable:
                        add_change(desired, cells, packet, (x, y, z),
                                   "minecraft:air", "clear_lake_canopy")
                for offset in range(depth):
                    y = -444 - offset
                    state = cells.get((x, y, z), "minecraft:air")
                    if bare(state) in replaceable:
                        add_change(desired, cells, packet, (x, y, z),
                                   "minecraft:water[level=0]",
                                   "organic_lake_water")
                bottom_y = -444 - depth
                state = cells.get((x, bottom_y, z), "minecraft:air")
                if bare(state) in replaceable:
                    floor = ("minecraft:clay" if (x + z) % 5
                             else "minecraft:gravel")
                    add_change(desired, cells, packet, (x, bottom_y, z),
                               floor, "organic_lake_floor")
            else:
                state = cells.get((x, -444, z), "minecraft:air")
                if bare(state) in replaceable:
                    shore = ("minecraft:gravel" if (x * 3 + z) % 4
                             else "minecraft:clay")
                    add_change(desired, cells, packet, (x, -444, z),
                               shore, "organic_lake_shore")
    return list(desired.values())


def lcl_changes(world: Path) -> list[Change]:
    packet = "S21-TERMINAL-DOGMA-LCL-SEAL-R01"
    lo, hi = (-12, -672, 238), (72, -591, 327)
    cells = read_box(world, DIMENSION, lo, hi)
    desired: dict[tuple[int, int, int], Change] = {}
    for x in range(lo[0], hi[0] + 1):
        for z in range(lo[2], hi[2] + 1):
            ellipse = ((x - 30) / 42.0) ** 2 + ((z - 282) / 44.0) ** 2
            for y in range(lo[1], hi[1] + 1):
                state = cells.get((x, y, z), "minecraft:air")
                name = bare(state)
                leaking_lcl = name == "projectseele:lcl"
                inside_seal = ellipse <= 1.0
                orange_legacy = name in {
                    "minecraft:orange_concrete",
                    "minecraft:orange_stained_glass",
                    "minecraft:orange_terracotta",
                }
                if not (leaking_lcl or (inside_seal and
                        (name in AIR or orange_legacy))):
                    continue
                after = ("minecraft:deepslate" if y <= -600
                         else "minecraft:tuff")
                add_change(desired, cells, packet, (x, y, z), after,
                           "seal_below_lcl_lake")
    return list(desired.values())


def region_path(root: Path, rx: int, rz: int) -> Path:
    return root / "region" / f"r.{rx}.{rz}.mca"


def apply_packet(world: Path, changes: list[Change], artifact: Path):
    root = dimension_dir(world, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)
    stats = Counter()
    originals = {}
    replaced = []
    packet = changes[0].packet if changes else "EMPTY"
    packet_dir = artifact / packet
    packet_dir.mkdir(parents=True, exist_ok=True)
    try:
        for (rx, rz), selected in sorted(by_region.items()):
            path = region_path(root, rx, rz)
            before = path.read_bytes()
            grouped: dict[tuple[int, int], list[Change]] = defaultdict(list)
            for change in selected:
                grouped[(change.x >> 4, change.z >> 4)].append(change)
            transformed = rewrite_region(path, grouped)
            shutil.copy2(path, packet_dir / path.name)
            originals[path] = before
            atomic_replace(path, transformed)
            replaced.append(path)
            stats["regions"] += 1
            stats["blocks"] += len(selected)
    except Exception:
        for path in replaced:
            atomic_replace(path, originals[path])
        raise
    receipt = {
        "packet": packet,
        "blocks": stats["blocks"],
        "regions": stats["regions"],
        "regionBeforeSha256": {
            path.name: hashlib.sha256(data).hexdigest()
            for path, data in originals.items()
        },
    }
    (packet_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--only", choices={"pillars", "lake", "lcl"},
                        action="append",
                        help="plan/apply only the named independent packet")
    args = parser.parse_args()
    world = args.world.resolve()
    selected = set(args.only or ("pillars", "lake", "lcl"))
    builders = {
        "pillars": pillar_changes,
        "lake": lake_changes,
        "lcl": lcl_changes,
    }
    packets = [builders[name](world) for name in ("pillars", "lake", "lcl")
               if name in selected]
    plan = {packet[0].packet: len(packet) for packet in packets if packet}
    print(json.dumps({"world": str(world), "plan": plan}, indent=2))
    if not args.apply:
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s21_geofront_semantic_repair_{stamp}"
    artifact.mkdir(parents=True, exist_ok=False)
    receipts = [apply_packet(world, packet, artifact)
                for packet in packets if packet]
    (artifact / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_WITH_PACKET_REGION_BACKUPS",
        "world": str(world),
        "receipts": receipts,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"applied": True, "artifact": str(artifact),
                      "receipts": receipts}, indent=2))


if __name__ == "__main__":
    main()
