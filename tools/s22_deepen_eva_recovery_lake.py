#!/usr/bin/env python3
"""Deepen S22's west lake into an EVA-scale recovery basin.

The TV production exterior keeps the underground lake and EVA docking
position adjacent but distinct.  This packet preserves every authored
infrastructure column, deepens only natural lake terrain, and adds a compact
patrol/entry-plug recovery pier connected to the existing lake terminal.
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
PACKET = "S22-CANONICAL-EVA-RECOVERY-LAKE-R01"
BBOX = ((-336, -512, 74), (-179, -450, 226))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:water", "minecraft:bubble_column", "minecraft:sand",
    "minecraft:gravel", "minecraft:clay", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:stone", "minecraft:deepslate",
    "minecraft:snow", "minecraft:snow_block", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp", "minecraft:kelp_plant",
    "minecraft:sculk", "minecraft:tuff",
}
WATER = "minecraft:water[level=0]"
DECK = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
PIER = "minecraft:polished_basalt[axis=y]"
LIGHT = "minecraft:sea_lantern"
CENTRE_X = -260
CENTRE_Z = 150
RADIUS_X = 76
RADIUS_Z = 62
WATER_Y = -462


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def radial(x: int, z: int) -> float:
    return math.sqrt(((x - CENTRE_X) / RADIUS_X) ** 2
                     + ((z - CENTRE_Z) / RADIUS_Z) ** 2)


def basin_bottom(x: int, z: int) -> int:
    distance = min(1.0, radial(x, z))
    depth = round(42.0 * (1.0 - distance) ** 1.35)
    return -466 - depth


def design(world: dict[tuple[int, int, int], str]) -> tuple[list[Change], int]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    frozen_columns = 0

    for x in range(CENTRE_X - RADIUS_X, CENTRE_X + RADIUS_X + 1):
        for z in range(CENTRE_Z - RADIUS_Z, CENTRE_Z + RADIUS_Z + 1):
            if radial(x, z) > 1.0:
                continue
            protected = any(
                bare(world.get((x, y, z), "minecraft:air"))
                not in AIR | NATURAL
                for y in range(-511, -449)
            )
            if protected:
                frozen_columns += 1
                continue
            bottom = basin_bottom(x, z)
            sediment = ("minecraft:clay" if (x + z) % 5
                        else "minecraft:gravel")
            desired[(x, bottom, z)] = (
                sediment, "EVA recovery basin sediment")
            for y in range(bottom + 1, WATER_Y + 1):
                desired[(x, y, z)] = (
                    WATER, "EVA-scale underground-lake water column")
            for y in range(WATER_Y + 1, -449):
                desired[(x, y, z)] = (
                    "minecraft:air", "EVA recovery basin open headroom")

    # Seven-wide pier joins the existing terminal at x=-230 without replacing
    # it.  The U-shaped end leaves a real water pocket for patrol craft and
    # entry-plug recovery rather than filling the basin with another platform.
    for x in range(-258, -232):
        for z in range(117, 124):
            edge = z in (117, 123)
            state = EDGE if edge else (LIGHT if x % 9 == 0 and z == 120
                                       else DECK)
            desired[(x, -461, z)] = (state, "lake recovery access pier")

    for x in range(-282, -258):
        for z in range(110, 131):
            hull = x <= -279 or z <= 112 or z >= 128
            if hull:
                state = EDGE if (x in (-282, -279) or z in (110, 130)) else DECK
                if (x + z) % 17 == 0:
                    state = LIGHT
                desired[(x, -461, z)] = (
                    state, "patrol and entry-plug recovery berth")

    support_points = [
        (-258, 118), (-258, 122), (-249, 118), (-249, 122),
        (-240, 118), (-240, 122), (-282, 111), (-282, 129),
        (-270, 111), (-270, 129), (-260, 111), (-260, 129),
    ]
    for x, z in support_points:
        for y in range(basin_bottom(x, z) + 1, -461):
            desired[(x, y, z)] = (PIER, "lake recovery pier footing")

    changes: list[Change] = []
    collisions: list[tuple[tuple[int, int, int], str]] = []
    for position, (after, reason) in sorted(
            desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if reason.startswith(("lake recovery", "patrol")) \
                and bare(before) not in AIR | NATURAL:
            collisions.append((position, before))
            continue
        changes.append(Change(
            PACKET, *position, before, after, "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:8])
        raise RuntimeError(
            f"recovery pier collides with {len(collisions)} authored cells: {sample}")
    return changes, frozen_columns


def apply(changes: list[Change], frozen_columns: int) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_EVA_RECOVERY_LAKE_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    for (region_x, region_z), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{region_x}.{region_z}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    lo = tuple(min(getattr(change, axis) for change in changes)
               for axis in ("x", "y", "z"))
    hi = tuple(max(getattr(change, axis) for change in changes)
               for axis in ("x", "y", "z"))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [change for change in changes
                if actual.get((change.x, change.y, change.z), "minecraft:air")
                != change.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")

    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "frozenAuthoredColumns": frozen_columns,
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes, frozen = design(world)
    reasons: dict[str, int] = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    print(json.dumps({
        "packet": PACKET,
        "writes": len(changes),
        "frozenAuthoredColumns": frozen,
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
        print(f"backup={apply(changes, frozen)}")


if __name__ == "__main__":
    main()
