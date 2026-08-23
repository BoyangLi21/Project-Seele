#!/usr/bin/env python3
"""Build the source-backed S22 Central Dogma B20 radial interchange.

This packet occupies the measured empty volume around the existing deep
pressure shaft.  It does not touch the command room, the passenger lift car
sweep, or speculative office space.  The only destructive edits are a
three-block-wide maintenance aperture through the north face of the audited
shaft shell; every other write must land in air.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
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
PACKET = "S22-CENTRAL-DOGMA-B20-RADIAL-R01"
BBOX = ((44, -510, 245), (100, -499, 301))

AIR = "minecraft:air"
FLOOR = "minecraft:polished_blackstone"
UNDERFLOOR = "minecraft:reinforced_deepslate"
TRIM = "minecraft:deepslate_tiles"
WALL = "minecraft:polished_deepslate"
GLASS = "projectseele:clear_glass"
LIGHT = "minecraft:sea_lantern"
ORANGE = "minecraft:orange_concrete"
RED_GLASS = "minecraft:red_stained_glass"

CX, CZ = 72, 273
FLOOR_Y = -507
WALK_Y = -506
CEILING_Y = -501

AIRLIKE = {
    "minecraft:air", "minecraft:void_air", "minecraft:cave_air"
}
BREACH = {
    (x, y, 268)
    for x in range(71, 74)
    for y in range(WALK_Y, -501)
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if not (BBOX[0][0] <= x <= BBOX[1][0]
            and BBOX[0][1] <= y <= BBOX[1][1]
            and BBOX[0][2] <= z <= BBOX[1][2]):
        raise RuntimeError(f"write escaped B20 envelope: {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def put_if_air(desired, world, x: int, y: int, z: int,
               state: str, reason: str) -> None:
    """Add structure only where the measured world is air-like."""
    if bare(world.get((x, y, z), AIR)) in AIRLIKE:
        put(desired, x, y, z, state, reason)


def radial_path() -> set[tuple[int, int]]:
    path: set[tuple[int, int]] = set()
    for x in range(CX - 25, CX + 26):
        for z in range(CZ - 25, CZ + 26):
            dx, dz = abs(x - CX), abs(z - CZ)
            metric = 2 * max(dx, dz) + min(dx, dz)
            ring = 36 <= metric <= 46
            east_west = dz <= 2 and 6 <= dx and metric <= 46
            north_south = dx <= 2 and 6 <= dz and metric <= 46
            if ring or east_west or north_south:
                path.add((x, z))
    # Threshold and ladder-foot bay remain outside the 5x5 car sweep.
    for x in range(71, 74):
        path.add((x, 267))
        path.add((x, 268))
        path.add((x, 269))
    # The ladder itself is a climbable cell, not horizontal floor space.
    path.discard((72, 269))
    return path


def design(world: dict[tuple[int, int, int], str]) -> tuple[list[Change], dict]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    path = radial_path()

    # Two-block structural deck and five-block clear circulation volume.
    for x, z in sorted(path):
        put_if_air(desired, world, x, FLOOR_Y - 1, z, UNDERFLOOR,
                   "B20 radial structural deck")
        floor = LIGHT if (x * 17 + z * 29) % 41 == 0 else FLOOR
        put_if_air(desired, world, x, FLOOR_Y, z, floor,
                   "B20 radial circulation floor")
        for y in range(WALK_Y, CEILING_Y):
            put(desired, x, y, z, AIR,
                "B20 radial clear headroom")
        ceiling = LIGHT if (x * 11 + z * 7) % 37 == 0 else TRIM
        put_if_air(desired, world, x, CEILING_Y, z, ceiling,
                   "B20 radial pressure ceiling")

    # Every exposed corridor edge is sealed.  Structural posts interrupt the
    # clear glazing on a regular rhythm without becoming free-standing rods.
    wall_cells: set[tuple[int, int]] = set()
    for x, z in path:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbour = (x + dx, z + dz)
            if neighbour not in path:
                wall_cells.add(neighbour)
    for x, z in sorted(wall_cells):
        for y in range(WALK_Y, CEILING_Y):
            post = ((x + z) % 6 == 0) or y in (WALK_Y, CEILING_Y - 1)
            put_if_air(desired, world, x, y, z, WALL if post else GLASS,
                       "B20 radial sealed perimeter")
        put_if_air(desired, world, x, FLOOR_Y, z, TRIM,
                   "B20 radial perimeter footing")
        put_if_air(desired, world, x, CEILING_Y, z, TRIM,
                   "B20 radial perimeter crown")

    # The north maintenance aperture uses the existing wall as its threshold.
    # It exposes the wall-backed ladder at z=269 but never enters the car sweep
    # beginning at z=271.
    for x, y, z in sorted(BREACH):
        put(desired, x, y, z, AIR,
            "B20 measured maintenance aperture")
    for x in (71, 73):
        put(desired, x, FLOOR_Y, 269, FLOOR,
            "B20 ladder-foot landing")
        put(desired, x, CEILING_Y, 269, TRIM,
            "B20 ladder-foot canopy")
    for x in (70, 74):
        for y in range(WALK_Y, CEILING_Y):
            put(desired, x, y, 269,
                WALL if y in (WALK_Y, CEILING_Y - 1) else GLASS,
                "B20 ladder-foot side screen")

    # Four sealed pressure gates advertise future radial routes without
    # claiming that unbuilt rooms already exist beyond them.
    gates = {
        "north": [(x, CZ - 25) for x in range(CX - 2, CX + 3)],
        "south": [(x, CZ + 25) for x in range(CX - 2, CX + 3)],
        "west": [(CX - 25, z) for z in range(CZ - 2, CZ + 3)],
        "east": [(CX + 25, z) for z in range(CZ - 2, CZ + 3)],
    }
    for name, cells in gates.items():
        for index, (x, z) in enumerate(cells):
            for y in range(WALK_Y, CEILING_Y):
                centre = 1 <= index <= 3 and y <= WALK_Y + 3
                state = RED_GLASS if centre else (ORANGE if y == WALK_Y + 2 else TRIM)
                put(desired, x, y, z, state,
                    f"B20 sealed {name} pressure gate")

    # Structural witness for runtime/world-version detection.
    put(desired, 96, FLOOR_Y, 272, "minecraft:lodestone",
        "B20 revision witness")
    put(desired, 96, FLOOR_Y, 273, "minecraft:magenta_concrete",
        "B20 revision witness")
    put(desired, 96, FLOOR_Y, 274, "minecraft:netherite_block",
        "B20 revision witness")

    changes: list[Change] = []
    collisions = []
    for position, (after, reason) in sorted(desired.items(),
                                             key=lambda item: item[0]):
        before = world.get(position, AIR)
        if before == after:
            continue
        allowed = bare(before) in AIRLIKE or position in BREACH
        # Preserve the existing shaft shell, ladder and lift car sweep unless
        # the coordinate is one of the measured aperture cells.
        if not allowed:
            collisions.append((position, before, reason))
            continue
        changes.append(Change(PACKET, *position, before, after,
                              "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}:{r}" for p, s, r in collisions[:12])
        raise RuntimeError(
            f"B20 proposal collides with {len(collisions)} protected cells: {sample}")

    # Gate 0: every authored walk cell must form one horizontal component.
    remaining = set(path)
    connected = set()
    queue = deque([next(iter(remaining))])
    while queue:
        node = queue.popleft()
        if node in connected or node not in remaining:
            continue
        connected.add(node)
        x, z = node
        queue.extend(((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)))
    if connected != remaining:
        raise RuntimeError(
            f"B20 path is disconnected: {len(connected)}/{len(remaining)}")

    # Gate 1: no desired wall or ceiling may occupy the declared path volume.
    for x, z in path:
        for y in range(WALK_Y, CEILING_Y):
            state = desired.get((x, y, z), (world.get((x, y, z), AIR), ""))[0]
            if bare(state) not in AIRLIKE:
                raise RuntimeError(f"B20 headroom blocked at {(x, y, z)}: {state}")

    report = {
        "packet": PACKET,
        "writes": len(changes),
        "pathCells": len(path),
        "connectedPathCells": len(connected),
        "protectedCollisions": 0,
        "intentionalShaftBreachCells": len(BREACH),
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes),
            min(c.z for c in changes), max(c.x for c in changes),
            max(c.y for c in changes), max(c.z for c in changes),
        ],
    }
    return changes, report


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_CENTRAL_DOGMA_B20_R01_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    lo = tuple(min(getattr(c, axis) for c in changes)
               for axis in ("x", "y", "z"))
    hi = tuple(max(getattr(c, axis) for c in changes)
               for axis in ("x", "y", "z"))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [c for c in changes
                if actual.get((c.x, c.y, c.z), AIR) != c.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"B20 read-back failed for {len(failures)} cells")
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
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes, report = design(world)
    parts = defaultdict(int)
    for change in changes:
        parts[change.reason] += 1
    report["parts"] = dict(sorted(parts.items()))
    print(json.dumps(report, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
