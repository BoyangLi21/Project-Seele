#!/usr/bin/env python3
"""Refine S22's NERV main entrance inside its already-authored envelope.

The TV exterior decision sheet makes the entrance a small wedge attached to
the headquarters mass.  This packet preserves the accepted y=-444 floor and
the west/east thresholds, but replaces the oversized black stair roof with a
lower light-grey pavilion, a narrow NERV band and glazed side clerestories.
No cell east of x=-65 or outside the existing entrance footprint is touched.
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
PACKET = "S22-NERV-MAIN-ENTRANCE-PAVILION-R03"
REJECTED = "visual review rejected R03; authoritative region was restored"
BBOX = ((-105, -451, 192), (-65, -426, 233))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
ALLOWED = AIR | {
    "minecraft:deepslate", "minecraft:stone", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:polished_deepslate",
    "minecraft:polished_blackstone", "minecraft:black_concrete",
    "minecraft:light_gray_concrete", "minecraft:white_concrete",
    "minecraft:orange_concrete", "minecraft:sea_lantern",
    "minecraft:polished_basalt", "minecraft:smooth_stone",
    "minecraft:iron_door", "minecraft:stone_button",
    "projectseele:clear_glass",
}
WALL = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
LIGHT_GREY = "minecraft:light_gray_concrete"
WHITE = "minecraft:white_concrete"
ORANGE = "minecraft:orange_concrete"
BLACK = "minecraft:black_concrete"
GLASS = "projectseele:clear_glass"
LIGHT = "minecraft:sea_lantern"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if x < -105 or x > -65 or z < 192 or z > 233:
        raise RuntimeError(f"left existing entrance envelope at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Retire the previous pavilion only above its accepted load floor.
    for x in range(-104, -64):
        for y in range(-443, -426):
            for z in range(193, 233):
                before = bare(world.get((x, y, z), "minecraft:air"))
                if before in ALLOWED:
                    put(desired, x, y, z, "minecraft:air",
                        "retire oversized entrance superstructure")

    # Compact front hall: 17 wide, 14 deep and seven clear blocks high.
    for x in range(-104, -89):
        half = 8
        for z in range(210 - half, 211 + half):
            put(desired, x, -444, z,
                LIGHT if z == 210 and x in (-102, -96, -90) else WALL,
                "main entrance retained walking floor")
        for z in (202, 218):
            for y in range(-443, -435):
                state = ORANGE if y == -440 else (GLASS if y >= -439 else WALL)
                put(desired, x, y, z, state, "main entrance glazed side wall")
        for z in range(202, 219):
            state = LIGHT if z in (206, 210, 214) else LIGHT_GREY
            put(desired, x, -435, z, state, "main entrance low roof")

    # Small west facade.  The central five-block portal stays physically open
    # so this remains a real route, not a decorative sealed front.
    for y in range(-443, -434):
        for z in range(201, 220):
            opening = -443 <= y <= -438 and 207 <= z <= 213
            if opening:
                state = "minecraft:air"
            elif y == -440:
                state = ORANGE
            elif y >= -438 and 204 <= z <= 216:
                state = GLASS
            else:
                state = EDGE
            put(desired, -104, y, z, state, "NERV main entrance compact facade")
    for z in range(205, 216):
        put(desired, -105, -437, z, WHITE, "main entrance projecting canopy")
    for z in range(207, 214):
        put(desired, -105, -444, z,
            LIGHT if z in (207, 213) else WALL,
            "main entrance exterior threshold")

    # A restrained rising connector embeds the pavilion into the much larger
    # HQ wall.  Its roof rises only five blocks over 24 blocks of run.
    for x in range(-89, -64):
        progress = (x + 89) / 24.0
        half = 8 + round(4 * progress)
        roof = -435 + round(5 * progress)
        z0, z1 = 210 - half, 210 + half
        for z in range(z0, z1 + 1):
            put(desired, x, -444, z,
                LIGHT if z == 210 and x % 6 == 0 else WALL,
                "main entrance HQ connector floor")
        for y in range(-443, roof):
            for z in range(z0 + 1, z1):
                put(desired, x, y, z, "minecraft:air",
                    "main entrance HQ connector clearance")
        for z in (z0, z1):
            for y in range(-443, roof + 1):
                if y == -440:
                    state = ORANGE
                elif roof - 2 <= y < roof:
                    state = GLASS
                else:
                    state = WALL
                put(desired, x, y, z, state,
                    "main entrance HQ connector side")
        for z in range(z0, z1 + 1):
            state = LIGHT if z == 210 and x % 6 == 0 else LIGHT_GREY
            put(desired, x, roof, z, state, "main entrance rising light roof")

    # The frozen HQ begins at x=-64.  Keep a 7x6 opening at x=-65 while
    # finishing the surrounding facade; no command/HQ interior cell is read
    # as construction permission.
    for y in range(-443, -429):
        for z in range(196, 225):
            opening = y <= -438 and 207 <= z <= 213
            if opening:
                state = "minecraft:air"
            elif y == -440:
                state = ORANGE
            elif y >= -436 and 202 <= z <= 218:
                state = GLASS
            else:
                state = WALL
            put(desired, -65, y, z, state, "main entrance HQ interface facade")

    changes: list[Change] = []
    collisions = []
    for position, (after, reason) in sorted(desired.items(), key=lambda i: i[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in ALLOWED:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:10])
        raise RuntimeError(f"protected collision count={len(collisions)} sample={sample}")
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_MAIN_ENTRANCE_R03_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))
    lo = tuple(min(getattr(c, a) for c in changes) for a in ("x", "y", "z"))
    hi = tuple(max(getattr(c, a) for c in changes) for a in ("x", "y", "z"))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failed = [c for c in changes
              if actual.get((c.x, c.y, c.z), "minecraft:air") != c.after]
    if failed:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed cells={len(failed)}")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "frozenBoundary": "x >= -64 untouched",
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        raise SystemExit(REJECTED)
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes = design(world)
    parts = defaultdict(int)
    for change in changes:
        parts[change.reason] += 1
    print(json.dumps({
        "packet": PACKET,
        "writes": len(changes),
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes),
            max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes),
        ],
        "parts": dict(sorted(parts.items())),
    }, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
