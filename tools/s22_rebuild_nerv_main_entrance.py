#!/usr/bin/env python3
"""Replace S22's temporary gate arch with an enclosed NERV main entrance.

The 1994-09-20 finalized NERV exterior setting marks the main entrance on the
forward edge of the headquarters complex, between the lake-side approach and
the main building.  This packet implements that relationship as a compact,
secure vestibule.  It replaces only the temporary S22 arch/forecourt and
natural terrain west of x=-64; the reviewed HQ and command room stay frozen.
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
PACKET = "S22-CANONICAL-NERV-MAIN-ENTRANCE-R02"
BBOX = ((-106, -452, 190), (-65, -426, 232))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:water", "minecraft:sand", "minecraft:gravel", "minecraft:clay",
    "minecraft:dirt", "minecraft:grass_block", "minecraft:stone",
    "minecraft:deepslate", "minecraft:snow", "minecraft:snow_block",
    "minecraft:tall_grass", "minecraft:short_grass", "minecraft:spruce_log",
    "minecraft:spruce_leaves",
}
OWNED = {
    "minecraft:polished_deepslate", "minecraft:polished_blackstone",
    "minecraft:light_gray_concrete", "minecraft:orange_concrete",
    "minecraft:sea_lantern", "minecraft:polished_basalt",
    "projectseele:clear_glass",
}
WALL = "minecraft:polished_deepslate"
TRIM = "minecraft:polished_blackstone"
BLACK = "minecraft:black_concrete"
ORANGE = "minecraft:orange_concrete"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"
DOOR = "minecraft:iron_door"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if x >= -64:
        raise RuntimeError(f"crossed frozen HQ boundary at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def fill(desired, x0, x1, y0, y1, z0, z1, state, reason) -> None:
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                put(desired, x, y, z, state, reason)


def design(world: dict[tuple[int, int, int], str]) -> tuple[list[Change], int]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # A tapered wedge rises into the much larger HQ shell.  The west end is a
    # human-scale portal; the east end is taller and wider, so it reads as an
    # embedded part of the headquarters instead of a free-standing black box.
    for x in range(-98, -64):
        progress = (x + 98) / 33.0
        half = 9 + round(5 * progress)
        roof = -437 + round(7 * progress)
        z0, z1 = 210 - half, 210 + half

        # Solid foundation and continuous walking floor.
        for z in range(z0, z1 + 1):
            for y in range(-450, -444):
                put(desired, x, y, z, "minecraft:deepslate",
                    "main entrance load-bearing wedge")
            put(desired, x, -444, z,
                LIGHT if z == 210 and x % 7 == 0 else WALL,
                "main entrance floor")

        # Clear only the wedge interior, then build two rising side walls and
        # its stepped roof.  Engineered cells outside this envelope are absent
        # from the desired mask and therefore untouched.
        for y in range(-443, roof):
            for z in range(z0 + 1, z1):
                put(desired, x, y, z, "minecraft:air",
                    "main entrance clear interior")
        for z in (z0, z1):
            for y in range(-443, roof + 1):
                if y == -440:
                    state = ORANGE
                elif roof - 3 <= y <= roof - 2 and x > -94:
                    state = GLASS
                else:
                    state = WALL
                put(desired, x, y, z, state, "main entrance tapered side wall")
        for z in range(z0, z1 + 1):
            put(desired, x, roof, z,
                LIGHT if z == 210 and x % 6 == 0 else BLACK,
                "main entrance rising roof")

    # West portal.  The setting drawing shows the entrance as a small element
    # against the mass of the HQ; the frame is deliberately broad but low.
    for y in range(-443, -436):
        for z in range(201, 220):
            opening = y <= -439 and 206 <= z <= 214
            put(desired, -98, y, z,
                "minecraft:air" if opening else
                (ORANGE if y == -440 else WALL),
                "NERV main entrance west facade")
    for z in range(204, 217):
        put(desired, -99, -438, z, TRIM, "main entrance portal lintel")
    for y in range(-443, -437):
        for z in (204, 216):
            put(desired, -99, y, z, TRIM, "main entrance portal jamb")
    for z in range(206, 215):
        put(desired, -99, -444, z,
            LIGHT if z in (206, 214) else WALL,
            "main entrance threshold")

    # Replace the temporary arch on the HQ interface with one continuous,
    # broad route.  x=-64 and everything east of it remain frozen.
    for y in range(-443, -429):
        for z in range(196, 225):
            opening = y <= -437 and 205 <= z <= 215
            put(desired, -65, y, z,
                "minecraft:air" if opening else
                (ORANGE if y == -440 else WALL),
                "main entrance HQ interface")

    # Forecourt is only as wide as the portal, with short retaining cheeks
    # that merge into the irregular lake bank instead of a giant rectangular
    # slab.
    for x in range(-104, -98):
        spread = 10 + (-99 - x)
        for z in range(210 - spread, 211 + spread):
            for y in range(-447, -444):
                put(desired, x, y, z, "minecraft:deepslate",
                    "main entrance forecourt foundation")
            put(desired, x, -444, z,
                LIGHT if z == 210 and x % 3 == 0 else WALL,
                "main entrance forecourt")
        for z in (210 - spread, 210 + spread):
            put(desired, x, -443, z, TRIM,
                "main entrance forecourt cheek")

    changes: list[Change] = []
    collisions = []
    allowed = AIR | NATURAL | OWNED | {
        "minecraft:black_concrete", "minecraft:iron_door", "minecraft:stone_button",
    }
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:10])
        raise RuntimeError(f"collides with {len(collisions)} protected cells: {sample}")
    return changes, len(collisions)


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_MAIN_ENTRANCE_{stamp}"
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
        "writes": len(changes), "frozenHqBoundary": "x >= -64 untouched",
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
    print(json.dumps({
        "packet": PACKET, "writes": len(changes), "collisions": collisions,
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes),
            max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes),
        ], "parts": dict(sorted(reasons.items())),
    }, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
