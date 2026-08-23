#!/usr/bin/env python3
"""Build the grounded U-shaped exterior transit spine around S22 NERV HQ.

The TV production plan puts the square, depressed HQ compound between the
lake/forest/hill landscape and the artificial-facilities sector.  S22 already
has each landmark, but only the west arrival and south/east stubs are linked.
This packet joins those accepted interfaces outside the frozen HQ rectangle.
It adds no rooms and never writes inside the command/HQ authority volume.
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
PACKET = "S22-CANONICAL-GEOFRONT-PERIMETER-TRANSIT-R01"
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:water", "minecraft:sand",
    "minecraft:gravel", "minecraft:clay", "minecraft:short_grass",
    "minecraft:tall_grass", "minecraft:sculk", "minecraft:sculk_vein",
    "minecraft:sculk_catalyst", "minecraft:redstone_ore",
    "minecraft:sculk_sensor", "minecraft:iron_ore", "minecraft:coal_ore",
    "minecraft:tuff", "minecraft:spruce_log", "minecraft:spruce_leaves",
}
ROAD_PALETTE = {
    "minecraft:smooth_stone", "minecraft:polished_deepslate",
    "minecraft:polished_blackstone", "minecraft:light_gray_concrete",
    "minecraft:sea_lantern", "projectseele:clear_glass",
}
FLOOR = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
CENTRE = "minecraft:light_gray_concrete"
LIGHT = "minecraft:sea_lantern"
SUBBASE = "minecraft:deepslate"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def frozen_hq(x: int, z: int) -> bool:
    return -67 <= x <= 159 and 193 <= z <= 400


def smooth_y(start: int, end: int, index: int, count: int) -> int:
    t = max(0.0, min(1.0, index / max(1, count)))
    eased = t * t * (3.0 - 2.0 * t)
    return round(start + (end - start) * eased)


def load_route_world() -> dict[tuple[int, int, int], str]:
    cells: dict[tuple[int, int, int], str] = {}
    for lo, hi in (
        ((-90, -480, 198), (-76, -420, 418)),
        ((-90, -480, 406), (178, -420, 422)),
        ((164, -480, 292), (178, -420, 422)),
    ):
        cells.update(read_box(WORLD, DIMENSION, lo, hi))
    return cells


def natural_top(world, x: int, z: int) -> int:
    for y in range(-420, -481, -1):
        material = bare(world.get((x, y, z), "minecraft:air"))
        if material in NATURAL and material != "minecraft:water":
            return y
    return -466


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if frozen_hq(x, z):
        raise RuntimeError(f"crossed frozen HQ at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def add_column(desired, world, x: int, z: int, floor_y: int,
               state: str, reason: str) -> None:
    top = natural_top(world, x, z)
    # Load-bearing approach: raised portions receive a compact full foundation;
    # cut portions remove natural terrain only, never authored infrastructure.
    for y in range(min(top + 1, floor_y - 2), floor_y):
        if y >= -480:
            put(desired, x, y, z, SUBBASE, reason + " / grounded sub-base")
    for y in range(floor_y + 1, min(-419, max(top + 1, floor_y + 5))):
        if bare(world.get((x, y, z), "minecraft:air")) in NATURAL:
            put(desired, x, y, z, "minecraft:air", reason + " / terrain clearance")
    put(desired, x, floor_y, z, state, reason)


def add_road_cross_section(desired, world, cx: int, cz: int, floor_y: int,
                           east_west: bool, index: int, reason: str) -> None:
    for offset in range(-4, 5):
        x = cx if east_west else cx + offset
        z = cz + offset if east_west else cz
        if abs(offset) == 4:
            state = EDGE
        elif offset == 0:
            state = LIGHT if index % 18 == 0 else CENTRE
        else:
            state = FLOOR
        add_column(desired, world, x, z, floor_y, state, reason)


def design(world: dict[tuple[int, int, int], str]):
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # West leg: accepted main-gate forecourt (-78..-65, y=-444) to the
    # south-hill datum.  Nine-block width stays outside the HQ authority.
    for index, z in enumerate(range(210, 415)):
        y = smooth_y(-444, -458, index, 204)
        add_road_cross_section(desired, world, -83, z, y, False, index,
                               "west NERV perimeter avenue")

    # South leg crosses the existing south-hill service road near x=30 and
    # remains below the frozen compound's z=400 boundary.
    for index, x in enumerate(range(-83, 171)):
        add_road_cross_section(desired, world, x, 414, -458, True, index,
                               "south NERV perimeter avenue")

    # East leg climbs back to the measured artificial-sector avenue at
    # x=160+, z=294..306, y=-444.
    for index, z in enumerate(range(300, 415)):
        y = smooth_y(-444, -458, index, 114)
        add_road_cross_section(desired, world, 170, z, y, False, index,
                               "east artificial-sector connector")

    # Three broad junction tables eliminate one-block seams at the corners
    # and at the existing south service-road crossing.
    junctions = [(-83, -458, 414), (170, -458, 414), (30, -458, 414)]
    for cx, y, cz in junctions:
        for x in range(cx - 5, cx + 6):
            for z in range(cz - 5, cz + 6):
                state = LIGHT if (x == cx or z == cz) and (x + z) % 7 == 0 else FLOOR
                add_column(desired, world, x, z, y, state,
                           "grounded perimeter transit junction")

    changes: list[Change] = []
    collisions: list[tuple[tuple[int, int, int], str, str]] = []
    allowed = AIR | NATURAL | ROAD_PALETTE
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before, reason))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    return changes, collisions


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    removable_natural_block_entities = {
        (change.x, change.y, change.z)
        for change in changes
        if bare(change.before) in {"minecraft:sculk_sensor", "minecraft:sculk_catalyst"}
    }
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_PERIMETER_TRANSIT_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(
            path, chunk_changes, removable_natural_block_entities))
    lo = (min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes))
    hi = (max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [c for c in changes if actual.get((c.x, c.y, c.z), "minecraft:air") != c.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = load_route_world()
    changes, collisions = design(world)
    report = {
        "packet": PACKET,
        "writes": len(changes),
        "protectedCollisions": len(collisions),
        "collisionSamples": collisions[:12],
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes),
            max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes),
        ],
    }
    print(json.dumps(report, indent=2))
    if collisions:
        raise SystemExit("protected collisions present; proposal not applied")
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
