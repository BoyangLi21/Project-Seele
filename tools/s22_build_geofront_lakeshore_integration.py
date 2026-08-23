#!/usr/bin/env python3
"""Ground S22's west arrival route in a canonical lake/HQ shoreline.

The R01 arrival spine proved the route, but its southern half still read as a
bridge suspended over an empty bowl.  This packet creates the missing shore:
an asymmetric planted bank east of the underground lake, a solid EVA
interchange island, and a terraced approach to the NERV west gate.  It never
writes at x >= -64, so the reviewed HQ and command room remain frozen.
"""

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


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-CANONICAL-GEOFRONT-LAKESHORE-R01"
BBOX = ((-152, -470, 122), (-65, -430, 236))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:water", "minecraft:sand", "minecraft:gravel",
    "minecraft:clay", "minecraft:dirt", "minecraft:grass_block",
    "minecraft:stone", "minecraft:snow", "minecraft:snow_block",
    "minecraft:tall_grass", "minecraft:short_grass",
    "minecraft:seagrass", "minecraft:tall_seagrass",
    "minecraft:kelp", "minecraft:kelp_plant",
}
DEEPSLATE = "minecraft:deepslate"
DIRT = "minecraft:dirt"
GRASS = "minecraft:grass_block[snowy=false]"
SAND = "minecraft:sand"
CLAY = "minecraft:clay"
RETAINING = "minecraft:polished_deepslate"
RETAINING_TRIM = "minecraft:polished_blackstone"
LIGHT = "minecraft:sea_lantern"
TRUNK = "minecraft:spruce_log[axis=y]"
LEAVES = "minecraft:spruce_leaves[distance=1,persistent=true,waterlogged=false]"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def set_desired(
        desired: dict[tuple[int, int, int], tuple[str, str]],
        x: int, y: int, z: int, state: str, reason: str) -> None:
    if x >= -64:
        raise RuntimeError(f"packet crossed frozen HQ boundary at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def west_edge(z: int) -> int:
    """Irregular shore: broad by the interchange, tighter at the HQ gate."""
    progress = (z - 122) / 114.0
    return -146 + round(20.0 * progress + 3.0 * math.sin(z / 13.0))


def terrain_top(x: int, z: int) -> int:
    west = west_edge(z)
    span = max(1, -65 - west)
    rise = round(17.0 * (x - west) / span)
    relief = round(1.4 * math.sin((x + 2 * z) / 23.0))
    return min(-444, -461 + rise + relief)


def arrival_route_cells() -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for x in range(-220, -99):
        for offset in range(-5, 6):
            cells.add((x, 120 + offset))
    for z in range(121, 211):
        for offset in range(-6, 7):
            cells.add((-100 + offset, z))
    for x in range(-99, -64):
        for offset in range(-6, 7):
            cells.add((x, 210 + offset))
    return cells


def add_tree(
        desired: dict[tuple[int, int, int], tuple[str, str]],
        world: dict[tuple[int, int, int], str],
        x: int, z: int, route: set[tuple[int, int]], height: int) -> None:
    if any((x + dx, z + dz) in route
           for dx in range(-4, 5) for dz in range(-4, 5)):
        return
    base = terrain_top(x, z) + 1
    if bare(world.get((x, base, z), "minecraft:air")) not in AIR:
        return
    for y in range(base, base + height):
        set_desired(desired, x, y, z, TRUNK,
                    "GeoFront west-forest tree")
    crown = base + height - 2
    for dy, radius in ((-1, 2), (0, 3), (1, 2), (2, 1)):
        y = crown + dy
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                if abs(dx) + abs(dz) > radius + 1 or (dx == 0 and dz == 0):
                    continue
                if bare(world.get((x + dx, y, z + dz),
                                  "minecraft:air")) in AIR:
                    set_desired(desired, x + dx, y, z + dz, LEAVES,
                                "GeoFront west-forest canopy")


def design(world: dict[tuple[int, int, int], str]) -> tuple[list[Change], int]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    route = arrival_route_cells()

    # A real bank beneath the route: stone core, soil, grass, and a two-block
    # beach transition.  Existing authored cells are never replaced.
    for z in range(122, 237):
        west = west_edge(z)
        for x in range(west, -64):
            top = terrain_top(x, z)
            shore_depth = x - west
            for y in range(-466, top + 1):
                if y == top:
                    state = SAND if shore_depth <= 2 else GRASS
                    reason = "canonical underground-lake shoreline"
                elif y >= top - 3:
                    state = CLAY if shore_depth <= 2 else DIRT
                    reason = "canonical shoreline soil"
                else:
                    state = DEEPSLATE
                    reason = "canonical shoreline load-bearing core"
                set_desired(desired, x, y, z, state, reason)

        # Retaining edge gives the artificial NERV shore a deliberate profile
        # rather than a raw dirt cliff.  Breaks every 16 blocks reveal sand.
        if z % 16 not in (0, 1, 2):
            for y in range(-466, terrain_top(west, z) + 1):
                set_desired(desired, west, y, z,
                            RETAINING if y % 4 else RETAINING_TRIM,
                            "NERV lake retaining wall")

    # The three-lane EVA interchange is an artificial island, not a forest of
    # thin legs.  Its deck from R01 remains untouched at y=-451.
    for x in range(-133, -101):
        for z in range(133, 154):
            for y in range(-466, -451):
                edge = x in (-133, -102) or z in (133, 153)
                state = RETAINING_TRIM if edge and y % 5 == 0 else RETAINING
                set_desired(desired, x, y, z, state,
                            "EVA interchange artificial island")

    # Low embedded path lights outline the lake-facing promenade without
    # producing another wall of luminous blocks.
    for z in range(128, 233, 12):
        x = west_edge(z) + 3
        y = terrain_top(x, z)
        set_desired(desired, x, y, z, LIGHT,
                    "lake promenade recessed light")

    # Sparse TV-style parkland west of HQ.  These fixed coordinates make the
    # packet deterministic and keep the centreline clear for vehicles.
    trees = [
        (-132, 164, 7), (-122, 177, 8), (-137, 190, 7),
        (-120, 203, 9), (-111, 221, 7), (-128, 229, 8),
        (-89, 137, 7), (-80, 151, 8), (-76, 170, 7),
        (-88, 188, 9), (-76, 198, 8), (-82, 228, 7),
    ]
    for x, z, height in trees:
        if x >= west_edge(z) + 5:
            add_tree(desired, world, x, z, route, height)

    changes: list[Change] = []
    preserved = 0
    for position, (after, reason) in sorted(desired.items(),
                                             key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        # This is additive landscape integration.  Any non-natural authored
        # cell wins, including every R01 route block and transplanted HQ cell.
        if bare(before) not in AIR | NATURAL:
            preserved += 1
            continue
        changes.append(Change(
            PACKET, *position, before, after, "replace", reason,
        ))
    return changes, preserved


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_LAKESHORE_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    for (region_x, region_z), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{region_x}.{region_z}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    lo = (min(change.x for change in changes),
          min(change.y for change in changes),
          min(change.z for change in changes))
    hi = (max(change.x for change in changes),
          max(change.y for change in changes),
          max(change.z for change in changes))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [change for change in changes
                if actual.get((change.x, change.y, change.z), "minecraft:air")
                != change.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")

    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "frozenHqBoundary": "x >= -64 untouched",
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
    changes, preserved = design(world)
    reasons: dict[str, int] = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    print(json.dumps({
        "packet": PACKET,
        "writes": len(changes),
        "preservedAuthoredCells": preserved,
        "bounds": [
            min(change.x for change in changes),
            min(change.y for change in changes),
            min(change.z for change in changes),
            max(change.x for change in changes),
            max(change.y for change in changes),
            max(change.z for change in changes),
        ],
        "parts": dict(sorted(reasons.items())),
    }, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
