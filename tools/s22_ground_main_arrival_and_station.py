#!/usr/bin/env python3
"""Ground S22's lake-to-HQ route and build a real lakeside terminal.

The first arrival packet established the route but left most of its landward
run on narrow piers.  The TV exterior setting instead reads as a depressed,
heavy civil installation.  This packet keeps the approved deck alignment,
adds a terrain-following retaining substructure on land, retains bridge piers
over water, and replaces the marker lake deck with a low enclosed terminal.
Everything remains west of the frozen HQ boundary at x=-64.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-CANONICAL-LAKE-TRANSIT-AND-STATION-R01"
BBOX = ((-234, -474, 104), (-65, -432, 224))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
FLUID = {"minecraft:water"}
NATURAL = {
    "minecraft:sand", "minecraft:gravel", "minecraft:clay",
    "minecraft:dirt", "minecraft:grass_block", "minecraft:stone",
    "minecraft:deepslate", "minecraft:snow", "minecraft:snow_block",
    "minecraft:tall_grass", "minecraft:short_grass",
    "minecraft:seagrass", "minecraft:tall_seagrass",
    "minecraft:kelp", "minecraft:kelp_plant",
    "minecraft:spruce_log", "minecraft:spruce_leaves",
}
OWNED = {
    "minecraft:polished_deepslate", "minecraft:polished_blackstone",
    "minecraft:light_gray_concrete", "minecraft:orange_concrete",
    "minecraft:yellow_concrete", "minecraft:purple_concrete",
    "minecraft:red_concrete", "minecraft:sea_lantern",
    "minecraft:polished_basalt", "minecraft:black_concrete",
    "minecraft:smooth_stone", "projectseele:clear_glass",
}
CORE = "minecraft:deepslate"
WALL = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
PIER = "minecraft:polished_basalt[axis=y]"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"
ORANGE = "minecraft:orange_concrete"
BLACK = "minecraft:black_concrete"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def route() -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    points.extend((x, 120) for x in range(-220, -99))
    points.extend((-100, z) for z in range(121, 211))
    points.extend((x, 210) for x in range(-99, -64))
    return points


def deck_y(index: int, count: int) -> int:
    return -461 + round(index * 17 / max(1, count - 1))


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if x >= -64:
        raise RuntimeError(f"crossed frozen HQ boundary at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def highest_ground(world, x: int, z: int, below: int) -> tuple[int, bool]:
    saw_water = False
    for y in range(below, BBOX[0][1] - 1, -1):
        state = bare(world.get((x, y, z), "minecraft:air"))
        if state in FLUID:
            saw_water = True
            continue
        if state not in AIR:
            return y, saw_water
    return BBOX[0][1], saw_water


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    points = route()

    # Retain the authored deck.  On dry land its full width receives a solid,
    # stepped embankment; in the lake it remains a bridge with 3x3 piers.
    for index, (cx, cz) in enumerate(points):
        deck = deck_y(index, len(points))
        east_west = index < 121 or index >= 211
        water_at_centre = bare(world.get((cx, -462, cz), "minecraft:air")) \
            == "minecraft:water"
        for offset in range(-4, 5):
            x = cx if east_west else cx + offset
            z = cz + offset if east_west else cz
            ground, saw_water = highest_ground(world, x, z, deck - 1)
            if not water_at_centre and not saw_water:
                for y in range(ground + 1, deck):
                    state = EDGE if abs(offset) == 4 and (deck - y) % 4 == 0 else CORE
                    put(desired, x, y, z, state,
                        "landward NERV arrival retaining embankment")

        if water_at_centre and index % 14 == 0:
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    x, z = cx + dx, cz + dz
                    ground, _ = highest_ground(world, x, z, deck - 1)
                    for y in range(ground + 1, deck):
                        put(desired, x, y, z, PIER,
                            "lake transit bridge 3x3 load-bearing pier")

    # Low lakeside terminal: the route enters at x=-220/z=120.  The terminal
    # is intentionally horizontal and modest against the cavern/HQ scale.
    x0, x1, z0, z1 = -232, -207, 106, 134
    floor, roof = -461, -452
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            ground, _ = highest_ground(world, x, z, floor - 1)
            for y in range(ground + 1, floor):
                put(desired, x, y, z, CORE,
                    "lake terminal solid foundation")
            put(desired, x, floor, z,
                LIGHT if (x + z) % 17 == 0 else WALL,
                "lake terminal concourse")
            edge = x in (x0, x1) or z in (z0, z1)
            if edge:
                for y in range(floor + 1, roof):
                    doorway = x == x1 and 116 <= z <= 124 and y <= floor + 4
                    lower_wall = y <= floor + 2
                    state = "minecraft:air" if doorway else (WALL if lower_wall else GLASS)
                    put(desired, x, y, z, state,
                        "lake terminal glazed perimeter")
            put(desired, x, roof, z,
                LIGHT if (x + z) % 19 == 0 else BLACK,
                "lake terminal low roof")

    # A restrained NERV band and two enclosed service cores give the station
    # a readable front without using coloured test-chart geometry.
    for z in range(z0, z1 + 1):
        put(desired, x0, floor + 3, z, ORANGE,
            "lake terminal NERV identity band")
    for x in range(-231, -227):
        for z in (*range(108, 113), *range(128, 133)):
            for y in range(floor + 1, roof):
                put(desired, x, y, z, WALL,
                    "lake terminal service core")

    allowed = AIR | FLUID | NATURAL | OWNED
    changes: list[Change] = []
    collisions = []
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:8])
        raise RuntimeError(f"collides with {len(collisions)} protected cells: {sample}")
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_LAKE_TRANSIT_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))
    lo = tuple(min(getattr(c, axis) for c in changes) for axis in ("x", "y", "z"))
    hi = tuple(max(getattr(c, axis) for c in changes) for axis in ("x", "y", "z"))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [c for c in changes if actual.get((c.x, c.y, c.z), "minecraft:air") != c.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED", "packet": PACKET,
        "writes": len(changes), "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes = design(world)
    reasons = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    print(json.dumps({"packet": PACKET, "writes": len(changes),
                      "parts": dict(sorted(reasons.items()))}, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
