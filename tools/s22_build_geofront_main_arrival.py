#!/usr/bin/env python3
"""Build S22's first canonical GeoFront exterior arrival spine.

The packet stays west of x=-64, outside the transplanted HQ authority volume.
It joins the generated underground lake to the existing HQ west terrace and
reserves a three-lane EVA interchange apron.  Preview is the default; --apply
backs up every touched region and performs an exact read-back.
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

from apply_s20_approved_semantic_repairs import (
    Change,
    atomic_replace,
    rewrite_region,
)
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-CANONICAL-GEOFRONT-MAIN-ARRIVAL-R01"
BBOX = ((-232, -482, 108), (-65, -435, 222))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:water", "minecraft:sand", "minecraft:gravel",
    "minecraft:clay", "minecraft:dirt", "minecraft:grass_block",
    "minecraft:stone", "minecraft:snow", "minecraft:tall_grass",
    "minecraft:short_grass", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp", "minecraft:kelp_plant",
}
FLOOR = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
GLASS = "projectseele:clear_glass"
LIGHT = "minecraft:sea_lantern"
STRIPE = "minecraft:light_gray_concrete"
ORANGE = "minecraft:orange_concrete"
PIER = "minecraft:polished_basalt[axis=y]"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def centreline() -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    points.extend((x, 120) for x in range(-220, -99))
    points.extend((-100, z) for z in range(121, 211))
    points.extend((x, 210) for x in range(-99, -64))
    return points


def deck_y(index: int, count: int) -> int:
    return -461 + round(index * 17 / max(1, count - 1))


def set_desired(
        desired: dict[tuple[int, int, int], tuple[str, str]],
        x: int, y: int, z: int, state: str, reason: str) -> None:
    if x >= -64:
        raise RuntimeError(f"packet crossed frozen HQ boundary at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def platform(
        desired: dict[tuple[int, int, int], tuple[str, str]],
        x0: int, x1: int, z0: int, z1: int, y: int,
        reason: str, lanes: bool = False) -> None:
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            state = EDGE if edge else FLOOR
            if lanes and not edge:
                if z in (z0 + 4, z0 + 8, z0 + 12):
                    state = {
                        z0 + 4: "minecraft:yellow_concrete",
                        z0 + 8: "minecraft:purple_concrete",
                        z0 + 12: "minecraft:red_concrete",
                    }[z]
            if not edge and (x + z) % 13 == 0:
                state = LIGHT
            set_desired(desired, x, y, z, state, reason)
            if edge and (x + z) % 4 != 0:
                set_desired(desired, x, y + 1, z, GLASS,
                            reason + " / safety glazing")


def support_column(
        desired: dict[tuple[int, int, int], tuple[str, str]],
        world: dict[tuple[int, int, int], str],
        x: int, deck: int, z: int, reason: str) -> None:
    for y in range(deck - 1, BBOX[0][1] - 1, -1):
        before = world.get((x, y, z), "minecraft:air")
        if bare(before) not in AIR | NATURAL:
            break
        if bare(before) not in AIR and bare(before) != "minecraft:water":
            break
        set_desired(desired, x, y, z, PIER, reason)


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    route = centreline()

    # Seven-block open avenue.  One-block rises are separated by at least
    # twelve horizontal blocks, so vanilla step-up remains natural.
    for index, (x, z) in enumerate(route):
        y = deck_y(index, len(route))
        east_west = index < 121 or index >= 211
        for offset in range(-3, 4):
            px = x if east_west else x + offset
            pz = z + offset if east_west else z
            state = STRIPE if offset == 0 else FLOOR
            if offset == 0 and index % 12 == 0:
                state = LIGHT
            set_desired(desired, px, y, pz, state,
                        "lake-to-HQ main arrival avenue")
        for side in (-4, 4):
            # Open the west rail only where the dedicated EVA interchange
            # spur meets this avenue; every other edge remains protected.
            if (not east_west and side == -4
                    and 138 <= z <= 148):
                continue
            px = x if east_west else x + side
            pz = z + side if east_west else z
            set_desired(desired, px, y, pz, EDGE,
                        "main avenue structural edge")
            if index % 4 != 0:
                set_desired(desired, px, y + 1, pz, GLASS,
                            "main avenue safety glazing")
        if index % 16 == 0:
            support_column(desired, world, x, y, z,
                           "main avenue load-bearing pier")

    # Lake arrival deck sits one block above canonical water level.
    platform(desired, -230, -212, 110, 130, -461,
             "underground-lake arrival station")
    for x, z in ((-228, 112), (-228, 128), (-214, 112), (-214, 128)):
        support_column(desired, world, x, -461, z,
                       "lake station load-bearing pier")

    # Three coloured lanes reserve the future EVA/personnel/mechanical split.
    platform(desired, -130, -105, 136, 150, -451,
             "EVA interchange apron", lanes=True)
    for x in range(-104, -102):
        for z in range(140, 147):
            set_desired(desired, x, -451, z, FLOOR,
                        "EVA interchange pedestrian spur")
    for x, z in ((-128, 138), (-128, 148), (-107, 138), (-107, 148)):
        support_column(desired, world, x, -451, z,
                       "EVA interchange load-bearing pier")

    # Monumental forecourt stops one block before the frozen HQ authority and
    # meets the existing y=-444 west terrace without replacing it.
    platform(desired, -78, -65, 200, 220, -444,
             "NERV HQ west main-gate forecourt")
    for z in (201, 219):
        for y in range(-443, -435):
            set_desired(desired, -65, y, z,
                        ORANGE if y in (-440, -439) else EDGE,
                        "NERV HQ main-gate arch")
    for z in range(201, 220):
        set_desired(desired, -65, -435, z, EDGE,
                    "NERV HQ main-gate lintel")

    changes: list[Change] = []
    collisions: list[tuple[tuple[int, int, int], str, str]] = []
    for position, (after, reason) in sorted(desired.items(),
                                             key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in AIR | NATURAL:
            collisions.append((position, before, after))
            continue
        changes.append(Change(
            PACKET, *position, before, after, "replace", reason,
        ))
    if collisions:
        sample = ", ".join(
            f"{position}:{before}" for position, before, _ in collisions[:8])
        raise RuntimeError(
            f"proposal collides with {len(collisions)} authored cells: {sample}")
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
    backup = Path("backups") / f"SEELE_S22_PRE_MAIN_ARRIVAL_{stamp}"
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

    counts: dict[str, int] = defaultdict(int)
    for change in changes:
        counts[change.reason] += 1
    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "frozenHqBoundary": "x >= -64 untouched",
        "parts": dict(sorted(counts.items())),
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
    reasons: dict[str, int] = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    print(json.dumps({
        "packet": PACKET,
        "writes": len(changes),
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
