#!/usr/bin/env python3
"""Build the canonical artificial-facilities sector east of S22 NERV HQ.

The TV GeoFront plan separates the lake/forest landscape from an artificial
sector.  This packet uses the measured east edge of the accepted HQ compound
as its only interface, then grounds a service avenue, two chamfered utility
plants and a roof-light/energy collector yard in existing natural terrain.
No command-room, pyramid, hangar, launch-bay or observation-volume coordinate
is inside this packet.
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
PACKET = "S22-CANONICAL-ARTIFICIAL-SECTOR-R01"
BBOX = ((158, -474, 238), (388, -408, 432))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:water", "minecraft:sand",
    "minecraft:gravel", "minecraft:clay", "minecraft:snow",
    "minecraft:snow_block", "minecraft:short_grass",
    "minecraft:tall_grass", "minecraft:oak_log", "minecraft:oak_leaves",
    "minecraft:spruce_log", "minecraft:spruce_leaves",
    "minecraft:sculk", "minecraft:sculk_vein", "minecraft:sculk_catalyst",
}
WALL = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
CORE = "minecraft:deepslate"
ROAD = "minecraft:smooth_stone"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"
ORANGE = "minecraft:orange_concrete"
BLACK = "minecraft:black_concrete"
REMOVABLE_NATURAL_BLOCK_ENTITIES = {
    # Measured in S22 before packet generation: a vanilla deep-dark catalyst,
    # not an authored NERV device.  It falls inside the power-plant interior.
    (293, -453, 322),
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def frozen_hq(x: int, z: int) -> bool:
    return -67 <= x <= 159 and 193 <= z <= 400


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if frozen_hq(x, z):
        raise RuntimeError(f"crossed frozen NERV compound at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def natural_top(world, x: int, z: int) -> int:
    for y in range(BBOX[1][1], BBOX[0][1] - 1, -1):
        state = bare(world.get((x, y, z), "minecraft:air"))
        if state in NATURAL and state != "minecraft:water":
            return y
    return -466


def road_height(x: int) -> int:
    progress = max(0.0, min(1.0, (x - 160) / 196.0))
    return -444 - round(11.0 * (progress * progress * (3.0 - 2.0 * progress)))


def add_grounded_deck(desired, world, x: int, z: int, y: int,
                      state: str, reason: str) -> None:
    ground = natural_top(world, x, z)
    for fill_y in range(ground + 1, y):
        put(desired, x, fill_y, z, CORE, reason + " foundation")
    for clear_y in range(y + 1, min(BBOX[1][1], ground + 1)):
        if bare(world.get((x, clear_y, z), "minecraft:air")) in NATURAL:
            put(desired, x, clear_y, z, "minecraft:air", reason + " cutting")
    put(desired, x, y, z, state, reason)


def add_service_avenue(desired, world) -> None:
    # The accepted compound edge is x=159.  A broad avenue continues east,
    # descends with the natural park floor and never becomes a floating line.
    for x in range(160, 357):
        deck_y = road_height(x)
        for z in range(294, 307):
            edge = z in (294, 306)
            state = EDGE if edge else (LIGHT if z == 300 and x % 17 == 0 else ROAD)
            add_grounded_deck(desired, world, x, z, deck_y, state,
                              "east artificial-sector service avenue")
        if x % 24 == 0:
            for z in (292, 308):
                ground = natural_top(world, x, z)
                for y in range(ground + 1, deck_y + 1):
                    put(desired, x, y, z, EDGE,
                        "service avenue retaining pier")
                put(desired, x, deck_y + 1, z, LIGHT,
                    "service avenue restrained marker light")


def chamfered_footprint(x: int, z: int, x0: int, x1: int,
                        z0: int, z1: int, cut: int = 3) -> bool:
    if not (x0 <= x <= x1 and z0 <= z <= z1):
        return False
    dx = min(x - x0, x1 - x)
    dz = min(z - z0, z1 - z)
    return dx + dz >= cut


def add_utility_plant(desired, world, name: str, x0: int, x1: int,
                      z0: int, z1: int, floor: int, height: int) -> None:
    roof = floor + height
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if not chamfered_footprint(x, z, x0, x1, z0, z1):
                continue
            ground = natural_top(world, x, z)
            for y in range(ground + 1, floor):
                put(desired, x, y, z, CORE, f"{name} grounded foundation")
            put(desired, x, floor, z,
                LIGHT if (x + z) % 19 == 0 else WALL,
                f"{name} service floor")
            boundary = (not chamfered_footprint(x - 1, z, x0, x1, z0, z1)
                        or not chamfered_footprint(x + 1, z, x0, x1, z0, z1)
                        or not chamfered_footprint(x, z - 1, x0, x1, z0, z1)
                        or not chamfered_footprint(x, z + 1, x0, x1, z0, z1))
            for y in range(floor + 1, roof):
                if boundary:
                    if y == floor + 3:
                        state = ORANGE
                    elif floor + 5 <= y <= roof - 3 and (x + z) % 4 != 0:
                        state = GLASS
                    else:
                        state = WALL
                    put(desired, x, y, z, state, f"{name} exterior shell")
                else:
                    before = bare(world.get((x, y, z), "minecraft:air"))
                    if before in NATURAL:
                        put(desired, x, y, z, "minecraft:air",
                            f"{name} clear interior")
            # Two-step roof, avoiding a featureless rectangular lid.
            roof_y = roof + (1 if (x - x0) % 12 in (0, 1) else 0)
            put(desired, x, roof_y, z,
                LIGHT if (x + z) % 23 == 0 else BLACK,
                f"{name} ribbed roof")

    # A secure three-wide door faces the service avenue.
    door_x = (x0 + x1) // 2
    for x in range(door_x - 1, door_x + 2):
        for y in range(floor + 1, floor + 5):
            put(desired, x, y, z0, "minecraft:air", f"{name} avenue entrance")
    for x in range(door_x - 2, door_x + 3):
        put(desired, x, floor + 5, z0, EDGE, f"{name} entrance lintel")


def add_collector_yard(desired, world) -> None:
    # Three grounded inclined collectors echo the setting drawing's roof-light
    # infrastructure without creating a second pyramid or a floating screen.
    for centre_z in (338, 365, 392):
        floor = max(natural_top(world, x, z)
                    for x in range(324, 363, 4)
                    for z in range(centre_z - 8, centre_z + 9, 4)) + 1
        for x in range(322, 365):
            for z in range(centre_z - 10, centre_z + 11):
                if x in (322, 364) or z in (centre_z - 10, centre_z + 10):
                    add_grounded_deck(desired, world, x, z, floor, EDGE,
                                      "collector yard grounded frame")
        for step in range(0, 15):
            x = 330 + step
            y = floor + 2 + step // 2
            for z in range(centre_z - 7, centre_z + 8):
                put(desired, x, y, z,
                    LIGHT if (z - centre_z) % 4 == 0 else GLASS,
                    "inclined GeoFront roof-light collector")
            for support_z in (centre_z - 7, centre_z + 7):
                for support_y in range(floor + 1, y):
                    put(desired, x, support_y, support_z, EDGE,
                        "collector triangular support")


def design(world: dict[tuple[int, int, int], str]) -> tuple[list[Change], list[tuple]]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    add_service_avenue(desired, world)
    add_utility_plant(desired, world, "NERV environmental plant",
                      218, 274, 244, 282, -454, 12)
    add_utility_plant(desired, world, "NERV power conditioning plant",
                      281, 337, 317, 357, -455, 14)
    add_collector_yard(desired, world)

    allowed = AIR | NATURAL | {
        "minecraft:smooth_stone", "minecraft:polished_deepslate",
        "minecraft:polished_blackstone", "minecraft:sea_lantern",
        "minecraft:orange_concrete", "minecraft:black_concrete",
        "projectseele:clear_glass",
    }
    collisions = []
    changes = []
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    return changes, collisions


def apply(changes: list[Change], collisions: list[tuple]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_ARTIFICIAL_SECTOR_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(
            path, chunk_changes, REMOVABLE_NATURAL_BLOCK_ENTITIES))
    lo = (min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes))
    hi = (max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [c for c in changes
                if actual.get((c.x, c.y, c.z), "minecraft:air") != c.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED", "packet": PACKET,
        "writes": len(changes), "protectedCollisionsSkipped": len(collisions),
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes, collisions = design(world)
    reasons = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    print(json.dumps({"packet": PACKET, "writes": len(changes),
                      "protectedCollisionsSkipped": len(collisions),
                      "collisionSamples": [
                          [list(position), state]
                          for position, state in collisions[:20]
                      ],
                      "bounds": [min(c.x for c in changes), min(c.y for c in changes),
                                 min(c.z for c in changes), max(c.x for c in changes),
                                 max(c.y for c in changes), max(c.z for c in changes)],
                      "parts": dict(sorted(reasons.items()))}, indent=2))
    if args.apply:
        print(f"backup={apply(changes, collisions)}")


if __name__ == "__main__":
    main()
