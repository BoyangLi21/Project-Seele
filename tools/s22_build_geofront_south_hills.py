#!/usr/bin/env python3
"""Build the TV-setting-inspired south hill/forest sector in S22 GeoFront.

The canonical plan separates an irregular hill mass and forest from the lake,
HQ depression and east artificial sector.  This packet starts south of every
measured HQ component.  It reshapes natural columns only, runs one grounded
service road from the HQ edge into the park, and plants sparse broad-leaf
woods while preserving every authored column fail-closed.
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
PACKET = "S22-CANONICAL-SOUTH-HILLS-R01"
BBOX = ((-112, -474, 400), (252, -420, 686))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:water", "minecraft:sand",
    "minecraft:gravel", "minecraft:clay", "minecraft:snow",
    "minecraft:snow_block", "minecraft:short_grass",
    "minecraft:tall_grass", "minecraft:oak_log", "minecraft:oak_leaves",
    "minecraft:spruce_log", "minecraft:spruce_leaves",
    "minecraft:sculk", "minecraft:sculk_vein",
}
ROAD = "minecraft:smooth_stone"
ROAD_EDGE = "minecraft:polished_blackstone"
LIGHT = "minecraft:sea_lantern"
DIRT = "minecraft:dirt"
GRASS = "minecraft:grass_block"
STONE = "minecraft:deepslate"
LOG = "minecraft:oak_log"
LEAVES = "minecraft:oak_leaves"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def authored_column(world, x: int, z: int) -> bool:
    """Any non-natural voxel freezes the whole column, not merely one cell."""
    for y in range(BBOX[0][1], BBOX[1][1] + 1):
        state = bare(world.get((x, y, z), "minecraft:air"))
        if state not in AIR and state not in NATURAL:
            return True
    return False


def existing_natural_top(world, x: int, z: int) -> int:
    for y in range(BBOX[1][1], BBOX[0][1] - 1, -1):
        state = bare(world.get((x, y, z), "minecraft:air"))
        if state in NATURAL and state != "minecraft:water":
            return y
    return -466


def gaussian(x: float, z: float, cx: float, cz: float, radius: float) -> float:
    dx = x - cx
    dz = z - cz
    return math.exp(-(dx * dx + dz * dz) / (radius * radius))


def target_height(x: int, z: int) -> int:
    # Two overlapping, asymmetric hill masses; no circular bowl or flat wall.
    west = 15.0 * gaussian(x, z, -35.0, 570.0, 112.0)
    east = 20.0 * gaussian(x, z, 162.0, 605.0, 138.0)
    saddle = 5.0 * gaussian(x, z, 70.0, 535.0, 175.0)
    ripple = 1.8 * math.sin((x + z) / 37.0) + 1.2 * math.cos(x / 43.0)
    return -466 + round(west + east + saddle + ripple)


def road_centre_x(z: int) -> float:
    progress = max(0.0, min(1.0, (z - 432) / 224.0))
    return 30.0 + 72.0 * (progress * progress * (3.0 - 2.0 * progress))


def near_road(x: int, z: int, margin: int = 0) -> bool:
    return abs(x - road_centre_x(z)) <= 7 + margin


def mix(x: int, z: int) -> int:
    value = (x * 341873128712) ^ (z * 132897987541)
    value ^= value >> 33
    value *= 0xff51afd7ed558ccd
    value ^= value >> 33
    return value & ((1 << 64) - 1)


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    desired[(x, y, z)] = (state, reason)


def add_landscape(desired, world, frozen_columns: set[tuple[int, int]]) -> None:
    for x in range(BBOX[0][0], BBOX[1][0] + 1):
        for z in range(432, BBOX[1][2] + 1):
            if (x, z) in frozen_columns:
                continue
            current = existing_natural_top(world, x, z)
            target = target_height(x, z)
            # The packet raises/lowers at most the natural skin.  The deep
            # load-bearing mass below -470 is never touched.
            for y in range(max(-470, current + 1), target + 1):
                state = GRASS if y == target else (DIRT if y >= target - 3 else STONE)
                put(desired, x, y, z, state, "south hill natural fill")
            if current > target:
                for y in range(target + 1, current + 1):
                    if bare(world.get((x, y, z), "minecraft:air")) in NATURAL:
                        put(desired, x, y, z, "minecraft:air", "south hill natural cut")
            put(desired, x, target, z, GRASS, "south hill grass skin")
            for depth in range(1, 4):
                put(desired, x, target - depth, z, DIRT, "south hill soil")


def add_service_road(desired, world, frozen_columns: set[tuple[int, int]]) -> None:
    # The first station touches the measured HQ south edge at z=400; terrain
    # reshaping itself still begins at z=432, outside every HQ component.
    for z in range(401, 657):
        cx = round(road_centre_x(z))
        for x in range(cx - 7, cx + 8):
            if (x, z) in frozen_columns:
                continue
            y = target_height(x, z) + 1
            offset = abs(x - cx)
            state = ROAD_EDGE if offset == 7 else (LIGHT if offset == 0 and z % 19 == 0 else ROAD)
            put(desired, x, y, z, state, "grounded south service road")
            # A road replaces the turf directly under it, rather than hovering.
            put(desired, x, y - 1, z, STONE, "south road sub-base")


def add_tree(desired, x: int, z: int, ground: int, height: int) -> None:
    for y in range(ground + 1, ground + height + 1):
        put(desired, x, y, z, LOG, "south forest trunk")
    crown = ground + height
    for dy in range(-2, 2):
        radius = 1 if dy == 1 else 2
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                if abs(dx) == radius and abs(dz) == radius and dy != -1:
                    continue
                put(desired, x + dx, crown + dy, z + dz,
                    LEAVES, "south forest canopy")


def add_forests(desired, frozen_columns: set[tuple[int, int]]) -> None:
    for x in range(-96, 238, 7):
        for z in range(454, 678, 7):
            if near_road(x, z, 7):
                continue
            density = max(gaussian(x, z, -58, 548, 115),
                          gaussian(x, z, 190, 594, 128))
            if density < 0.22 or mix(x, z) % 1000 >= round(density * 410):
                continue
            if any((x + dx, z + dz) in frozen_columns
                   for dx in range(-2, 3) for dz in range(-2, 3)):
                continue
            add_tree(desired, x, z, target_height(x, z), 6 + mix(x, z) % 4)


def design(world: dict[tuple[int, int, int], str]):
    frozen_columns = {
        (x, z)
        for x in range(BBOX[0][0], BBOX[1][0] + 1)
        for z in range(BBOX[0][2], BBOX[1][2] + 1)
        if authored_column(world, x, z)
    }
    desired = {}
    add_landscape(desired, world, frozen_columns)
    add_service_road(desired, world, frozen_columns)
    add_forests(desired, frozen_columns)

    changes = []
    collisions = []
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in AIR and bare(before) not in NATURAL:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    return changes, collisions, frozen_columns


def apply(changes: list[Change], collisions: list[tuple]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_SOUTH_HILLS_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))
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
        "writes": len(changes), "protectedCollisionsSkipped": len(collisions),
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes, collisions, frozen = design(world)
    reasons = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    report = {
        "packet": PACKET, "writes": len(changes),
        "frozenAuthoredColumns": len(frozen),
        "protectedCollisionsSkipped": len(collisions),
        "collisionSamples": [[list(pos), state] for pos, state in collisions[:20]],
        "bounds": [min(c.x for c in changes), min(c.y for c in changes),
                   min(c.z for c in changes), max(c.x for c in changes),
                   max(c.y for c in changes), max(c.z for c in changes)],
        "parts": dict(sorted(reasons.items())),
    }
    print(json.dumps(report, indent=2))
    if args.apply:
        print(f"backup={apply(changes, collisions)}")


if __name__ == "__main__":
    main()
