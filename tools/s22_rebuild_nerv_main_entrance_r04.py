#!/usr/bin/env python3
"""Rebuild S22 NERV's main entrance as a compact depressed pavilion.

The rejected long wedge is removed cell-for-cell inside its known envelope.
The replacement follows the TV exterior relationship: a small main entrance
embedded in the much larger square HQ interface, preceded by a sunken paved
forecourt.  The command interior and every cell east of x=-65 stay frozen.
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
PACKET = "S22-CANONICAL-NERV-MAIN-ENTRANCE-R04"
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
    "minecraft:light_gray_concrete", "minecraft:gray_concrete",
    "minecraft:black_concrete", "minecraft:orange_concrete",
    "minecraft:sea_lantern", "minecraft:polished_basalt",
    "projectseele:clear_glass", "minecraft:iron_door",
    "minecraft:stone_button",
}

WALL = "minecraft:polished_deepslate"
TRIM = "minecraft:polished_blackstone"
BLACK = "minecraft:black_concrete"
ORANGE = "minecraft:orange_concrete"
WHITE = "minecraft:light_gray_concrete"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if x > -65:
        raise RuntimeError(f"crossed frozen HQ boundary at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Remove the former wedge only where it used this project's known exterior
    # palette.  Natural terrain and unknown authored cells are not cleared.
    for x in range(-104, -64):
        for y in range(-443, -425):
            for z in range(190, 233):
                if bare(world.get((x, y, z), "minecraft:air")) in OWNED:
                    put(desired, x, y, z, "minecraft:air",
                        "retire oversized entrance wedge")

    # Re-landscape the exposed footprint as a deliberate low forecourt.  The
    # established lake-to-HQ centreline at z=210 remains hard surfaced.
    for x in range(-104, -88):
        half = 15 - max(0, (-96 - x) // 3)
        for z in range(210 - half, 211 + half):
            route = 204 <= z <= 216
            for y in range(-449, -444):
                put(desired, x, y, z,
                    "minecraft:deepslate" if y < -446 else "minecraft:dirt",
                    "main entrance landscaped foundation")
            put(desired, x, -444, z,
                WALL if route else "minecraft:grass_block",
                "main entrance landscaped forecourt")
            if route and z == 210 and x % 5 == 0:
                put(desired, x, -444, z, LIGHT,
                    "main entrance route lighting")

    # Square depressed forecourt, intentionally wider than the pavilion but
    # far smaller than the HQ mass.  Low retaining walls frame rather than
    # roof over the approach.
    for x in range(-92, -87):
        for z in range(198, 223):
            for y in range(-449, -444):
                put(desired, x, y, z, "minecraft:deepslate",
                    "main entrance forecourt foundation")
            edge = z in (198, 222)
            put(desired, x, -444, z, TRIM if edge else WALL,
                "main entrance depressed forecourt")
            if edge:
                put(desired, x, -443, z,
                    LIGHT if x in (-92, -88) else TRIM,
                    "main entrance forecourt retaining wall")

    # Compact low pavilion embedded into the west edge of the HQ.  The roof
    # steps only three blocks, preserving the small-entrance / huge-HQ scale
    # contrast shown in the finalized exterior setting drawing.
    for x in range(-88, -64):
        for z in range(201, 220):
            for y in range(-450, -444):
                put(desired, x, y, z, "minecraft:deepslate",
                    "main entrance pavilion foundation")
            put(desired, x, -444, z,
                LIGHT if z == 210 and x % 6 == 0 else WALL,
                "main entrance pavilion floor")
            for y in range(-443, -436):
                for zz in (201, 202, 218, 219):
                    state = ORANGE if y == -440 else WALL
                    if y in (-439, -438) and -84 <= x <= -70:
                        state = GLASS
                    put(desired, x, y, zz, state,
                        "main entrance pavilion side wall")

    # West and east portal frames.  Both are nine blocks wide and six blocks
    # high, exactly aligned with the arrival centreline.
    for x in (-88, -65):
        for y in range(-443, -435):
            for z in range(201, 220):
                opening = -443 <= y <= -438 and 206 <= z <= 214
                state = "minecraft:air" if opening else (
                    ORANGE if y == -440 else WALL)
                put(desired, x, y, z, state,
                    "NERV main entrance portal frame")
        for z in range(204, 217):
            put(desired, x, -436, z, TRIM,
                "NERV main entrance portal lintel")

    # The interior is an uncluttered vestibule, not a long corridor guess.
    for x in range(-87, -65):
        for y in range(-443, -436):
            for z in range(203, 218):
                put(desired, x, y, z, "minecraft:air",
                    "main entrance clear vestibule")

    # Three-step roof cap, with a narrow central clear strip instead of the
    # rejected full-width black slabs.
    roof_steps = (
        (-88, -65, 201, 219, -436),
        (-84, -65, 203, 217, -435),
        (-80, -65, 205, 215, -434),
    )
    for x0, x1, z0, z1, y in roof_steps:
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                state = GLASS if z in (209, 210, 211) and x % 4 != 0 else (
                    ORANGE if x == x0 else BLACK)
                put(desired, x, y, z, state,
                    "main entrance compact stepped roof")

    changes: list[Change] = []
    collisions = []
    allowed = AIR | NATURAL | OWNED
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:12])
        raise RuntimeError(f"collides with {len(collisions)} protected cells: {sample}")
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_MAIN_ENTRANCE_R04_{stamp}"
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
    failures = [c for c in changes
                if actual.get((c.x, c.y, c.z), "minecraft:air") != c.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "frozenHqBoundary": "x > -65 untouched",
        "regionsBeforeSha256": hashes,
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
    print(json.dumps({
        "packet": PACKET,
        "writes": len(changes),
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes),
            max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes),
        ],
        "parts": dict(sorted(reasons.items())),
    }, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
