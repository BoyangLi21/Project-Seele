#!/usr/bin/env python3
"""Rebuild the R28 freshwater lake west of the authored diagonal road."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import (
    Change,
    atomic_replace,
    rewrite_region,
)
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIMENSION = "projectseele:geofront"
PACKET = "S21-SEALED-NATURAL-LAKE-R03"
CENTRE_X = -188
CENTRE_Z = 157
# The road is the lake's eastern shore, not a causeway through its centre.
# Expansion therefore goes only west into the undeveloped landscape.
RADIUS_X = 78
RADIUS_Z = 61
BBOX = ((-270, -466, 70), (-30, -420, 235))
NATURAL = {
    "minecraft:air", "minecraft:void_air", "minecraft:cave_air",
    "minecraft:water", "minecraft:stone", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:sand", "minecraft:clay",
    "minecraft:gravel",
}
PROTECTION_EXEMPT = {
    "projectseele:geofront_skyweave",
    "ars_nouveau:sky_block",
}
VEGETATION = {
    "minecraft:dark_oak_log", "minecraft:stripped_dark_oak_log",
    "minecraft:dark_oak_leaves", "minecraft:azalea_leaves",
    "minecraft:flowering_azalea_leaves", "minecraft:moss_block",
    "minecraft:grass", "minecraft:tall_grass", "minecraft:fern",
}
LIGHTING = {"minecraft:light", "minecraft:sea_lantern"}
ROAD = {
    "minecraft:light_gray_concrete", "minecraft:black_concrete",
    "minecraft:polished_deepslate", "minecraft:deepslate_tiles",
    "minecraft:deepslate_bricks",
    "minecraft:chiseled_polished_blackstone",
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def lake_factor(x: int, z: int) -> tuple[float, float]:
    dx = (x - CENTRE_X) / RADIUS_X
    dz = (z - CENTRE_Z) / RADIUS_Z
    radius = (dx * dx + dz * dz) ** 0.5
    angle = math.atan2(dz, dx)
    edge = (1.0 + 0.055 * math.sin(angle * 3.0 + 0.35)
            + 0.035 * math.sin(angle * 7.0 - 0.8)
            + 0.020 * math.cos(angle * 11.0 + 0.1))
    return radius, edge


def natural_ground(y: int, x: int, z: int, shore: bool) -> str:
    if -466 <= y <= -447:
        return "minecraft:stone"
    if y in (-446, -445):
        return "minecraft:dirt"
    if y == -444:
        if shore:
            pattern = (x * 31 + z * 17) % 11
            if pattern in (0, 1):
                return "minecraft:gravel"
            if pattern == 2:
                return "minecraft:clay"
        return "minecraft:grass_block[snowy=false]"
    return "minecraft:air"


def desired_state(x: int, y: int, z: int,
                  road_west_edge: int | None) -> str:
    radius, edge = lake_factor(x, z)
    sphere = ((x - 30) ** 2 + (-444 + 332) ** 2
              + (z - 220) ** 2) ** 0.5
    west_of_road = road_west_edge is None or x <= road_west_edge - 5
    inside = radius <= edge and west_of_road and sphere <= 315.0
    shore = (radius <= edge + 0.105 and west_of_road
             and sphere <= 317.0)
    if inside:
        if -466 <= y <= -450:
            return "minecraft:stone"
        if y == -449:
            return ("minecraft:gravel"
                    if (x * 19 + z * 23) % 19 == 0
                    else "minecraft:clay")
        if -448 <= y <= -444:
            return "minecraft:water[level=0]"
        return "minecraft:air"
    if shore:
        return natural_ground(y, x, z, True)
    return natural_ground(y, x, z, False)


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    changes: list[Change] = []
    # Any column containing an authored/structural block, plus a two-block
    # buffer, belongs to the existing facility.  This prevents the expanded
    # water body from occupying hangar, pyramid or service-road air space.
    authored = {(x, z) for (x, _, z), state in world.items()
                if bare(state) not in NATURAL
                and bare(state) not in VEGETATION
                and bare(state) not in LIGHTING
                and bare(state) not in PROTECTION_EXEMPT}
    protected = {(x + dx, z + dz) for x, z in authored
                 for dx in range(-2, 3) for dz in range(-2, 3)}
    road_columns: dict[int, list[int]] = defaultdict(list)
    for (x, _, z), state in world.items():
        if bare(state) in ROAD and -180 <= x <= -60:
            road_columns[z].append(x)
    road_west_edge = {z: min(xs) for z, xs in road_columns.items()}

    for (x, y, z), before in world.items():
        name = bare(before)
        edge_x = road_west_edge.get(z)
        radius, organic_edge = lake_factor(x, z)
        sphere = ((x - 30) ** 2 + (-444 + 332) ** 2
                  + (z - 220) ** 2) ** 0.5
        inside_water = (radius <= organic_edge
                        and (edge_x is None or x <= edge_x - 5)
                        and sphere <= 315.0)
        if name in VEGETATION:
            if inside_water and y >= -443:
                changes.append(Change(
                    PACKET, x, y, z, before, "minecraft:air", "replace",
                    "clear vegetation from lake water",
                ))
            continue
        if name in LIGHTING:
            if inside_water:
                after = desired_state(x, y, z, edge_x)
                if before != after:
                    changes.append(Change(
                        PACKET, x, y, z, before, after, "replace",
                        "remove legacy dotted lake light",
                    ))
            continue
        if name not in NATURAL:
            continue
        # Protected facility columns are deliberately dry.  Rebuilding their
        # natural substrate also removes water left by the rejected symmetric
        # lake without touching any authored block in the column.
        after = (natural_ground(y, x, z, False)
                 if (x, z) in protected
                 else desired_state(x, y, z, edge_x))
        if before == after:
            continue
        changes.append(Change(
            PACKET, x, y, z, before, after, "replace",
            "sealed natural lake basin/source water/shoreline",
        ))
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("artifacts") / f"s21_natural_lake_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    for (region_x, region_z), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{region_x}.{region_z}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    actual = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    falling = sum(bare(state) == "minecraft:water"
                  and state != "minecraft:water[level=0]"
                  for state in actual.values())
    deep_water = sum(bare(state) == "minecraft:water" and y < -449
                     for (_, y, _), state in actual.items())
    road_water = 0
    road_columns = {(x, z) for (x, _, z), state in actual.items()
                    if bare(state) in ROAD}
    water_columns = {(x, z) for (x, y, z), state in actual.items()
                     if y == -444 and bare(state) == "minecraft:water"}
    for x, z in road_columns:
        if any((x + dx, z + dz) in water_columns
               for dx in range(-2, 3) for dz in range(-2, 3)):
            road_water += 1
    if falling or deep_water or road_water:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(
            f"lake read-back failed: falling={falling} deep={deep_water} "
            f"roadWater={road_water}")

    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "fallingWaterRemaining": falling,
        "waterBelowBedRemaining": deep_water,
        "roadColumnsWithinTwoBlocksOfWater": road_water,
        "backup": str(backup.resolve()),
        "regionsBeforeSha256": hashes,
    }
    (backup / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes = design(world)
    print(json.dumps({
        "writes": len(changes),
        "waterSources": sum(change.after == "minecraft:water[level=0]"
                            for change in changes),
        "removedFallingWater": sum(
            bare(change.before) == "minecraft:water"
            and change.before != "minecraft:water[level=0]"
            and change.after != "minecraft:water[level=0]"
            for change in changes),
    }, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
