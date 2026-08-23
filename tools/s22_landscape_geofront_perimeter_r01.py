#!/usr/bin/env python3
"""Blend S22's new HQ perimeter avenue into canonical park terrain.

Only natural terrain outside the reviewed HQ rectangle is reshaped.  Each
road edge receives a broad grass/dirt shoulder which eases back into the
measured existing terrain; authored columns are frozen wholesale.
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

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-CANONICAL-GEOFRONT-PERIMETER-LANDSCAPE-R01"
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:tuff",
    "minecraft:dirt", "minecraft:grass_block", "minecraft:water",
    "minecraft:sand", "minecraft:gravel", "minecraft:clay",
    "minecraft:short_grass", "minecraft:tall_grass", "minecraft:sculk",
    "minecraft:sculk_vein", "minecraft:sculk_sensor",
    "minecraft:sculk_catalyst", "minecraft:redstone_ore",
    "minecraft:iron_ore", "minecraft:coal_ore", "minecraft:spruce_log",
    "minecraft:spruce_leaves", "minecraft:oak_log", "minecraft:oak_leaves",
}
ROAD = {
    "minecraft:smooth_stone", "minecraft:polished_deepslate",
    "minecraft:polished_blackstone", "minecraft:light_gray_concrete",
    "minecraft:sea_lantern", "projectseele:clear_glass",
}
GRASS = "minecraft:grass_block[snowy=false]"
DIRT = "minecraft:dirt"
STONE = "minecraft:deepslate"
LOG = "minecraft:oak_log[axis=y]"
LEAVES = "minecraft:oak_leaves[distance=1,persistent=true,waterlogged=false]"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def smooth_y(start: int, end: int, index: int, count: int) -> int:
    t = max(0.0, min(1.0, index / max(1, count)))
    eased = t * t * (3.0 - 2.0 * t)
    return round(start + (end - start) * eased)


def road_y(leg: str, coordinate: int) -> int:
    if leg == "west":
        return smooth_y(-444, -458, coordinate - 210, 204)
    if leg == "east":
        return smooth_y(-444, -458, coordinate - 300, 114)
    return -458


def load_world():
    cells = {}
    for lo, hi in (
        ((-106, -480, 198), (-63, -418, 436)),
        ((-96, -480, 396), (192, -418, 436)),
        ((156, -480, 286), (192, -418, 436)),
    ):
        cells.update(read_box(WORLD, DIMENSION, lo, hi))
    return cells


def existing_top(world, x: int, z: int) -> int:
    for y in range(-418, -481, -1):
        material = bare(world.get((x, y, z), "minecraft:air"))
        if material in NATURAL and material not in {
                "minecraft:water", "minecraft:short_grass",
                "minecraft:tall_grass", "minecraft:oak_log",
                "minecraft:oak_leaves", "minecraft:spruce_log",
                "minecraft:spruce_leaves"}:
            return y
    return -466


def authored_column(world, x: int, z: int) -> bool:
    for y in range(-480, -417):
        material = bare(world.get((x, y, z), "minecraft:air"))
        # Roads and glazing are accepted authored infrastructure too; freeze
        # their complete columns instead of grading terrain through them.
        if material not in AIR | NATURAL:
            return True
    return False


def target_height(world, x: int, z: int, road_floor: int,
                  distance: int) -> int:
    outer = existing_top(world, x, z)
    t = max(0.0, min(1.0, (distance - 5) / 13.0))
    eased = t * t * (3.0 - 2.0 * t)
    return round((road_floor - 1) * (1.0 - eased) + outer * eased)


def landscape_column(desired, world, x: int, z: int, target: int,
                     reason: str) -> None:
    current = existing_top(world, x, z)
    for y in range(min(current, target) - 3, target + 1):
        if y < -480:
            continue
        depth = target - y
        state = GRASS if depth == 0 else (DIRT if depth <= 3 else STONE)
        desired[(x, y, z)] = (state, reason)
    if current > target:
        for y in range(target + 1, current + 10):
            material = bare(world.get((x, y, z), "minecraft:air"))
            if material in NATURAL:
                desired[(x, y, z)] = ("minecraft:air", reason + " / natural cut")


def add_tree(desired, world, x: int, z: int, ground: int) -> None:
    height = 6 + ((x * 31 + z * 17) & 3)
    targets = []
    for y in range(ground + 1, ground + height + 1):
        targets.append((x, y, z, LOG))
    crown = ground + height
    for dy, radius in ((-2, 2), (-1, 3), (0, 2), (1, 1)):
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                if abs(dx) + abs(dz) > radius + 1 or (dx == 0 and dz == 0):
                    continue
                targets.append((x + dx, crown + dy, z + dz, LEAVES))
    if any(bare(world.get((tx, ty, tz), "minecraft:air")) not in AIR | NATURAL
           for tx, ty, tz, _ in targets):
        return
    for tx, ty, tz, state in targets:
        desired[(tx, ty, tz)] = (state, "GeoFront perimeter forest belt")


def design(world):
    desired = {}
    frozen = 0

    # West leg shoulders.
    for z in range(210, 415):
        floor = road_y("west", z)
        for x in list(range(-101, -87)) + list(range(-78, -67)):
            if authored_column(world, x, z):
                frozen += 1
                continue
            distance = abs(x + 83)
            landscape_column(desired, world, x, z,
                             target_height(world, x, z, floor, distance),
                             "west perimeter planted embankment")

    # South leg shoulders; stop before the already frozen HQ face at z=400.
    for x in range(-83, 171):
        for z in list(range(401, 410)) + list(range(419, 433)):
            if authored_column(world, x, z):
                frozen += 1
                continue
            distance = abs(z - 414)
            landscape_column(desired, world, x, z,
                             target_height(world, x, z, -458, distance),
                             "south perimeter planted embankment")

    # East leg shoulders, outside x=159 HQ boundary.
    for z in range(300, 415):
        floor = road_y("east", z)
        for x in list(range(160, 166)) + list(range(175, 189)):
            if authored_column(world, x, z):
                frozen += 1
                continue
            distance = abs(x - 170)
            landscape_column(desired, world, x, z,
                             target_height(world, x, z, floor, distance),
                             "east perimeter planted embankment")

    # Sparse irregular outer tree line; none is placed on a road or against
    # the compound wall.
    for x, z in [
        (-99, 244), (-100, 286), (-98, 335), (-100, 382),
        (-60, 430), (-16, 431), (58, 431), (112, 430),
        (187, 331), (186, 369), (188, 404),
    ]:
        if not authored_column(world, x, z):
            add_tree(desired, world, x, z, existing_top(world, x, z))

    changes = []
    collisions = []
    allowed = AIR | NATURAL
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    return changes, collisions, frozen


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    removable = {
        (c.x, c.y, c.z) for c in changes
        if bare(c.before) in {"minecraft:sculk_sensor", "minecraft:sculk_catalyst"}
    }
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_PERIMETER_LANDSCAPE_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes, removable))
    lo = (min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes))
    hi = (max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes))
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
    world = load_world()
    changes, collisions, frozen = design(world)
    report = {
        "packet": PACKET, "writes": len(changes),
        "protectedCollisions": len(collisions),
        "frozenAuthoredColumns": frozen,
        "collisionSamples": collisions[:12],
    }
    print(json.dumps(report, indent=2))
    if collisions:
        raise SystemExit("protected collisions present; proposal not applied")
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
