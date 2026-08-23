#!/usr/bin/env python3
"""Reverse the x12 lift's B-158 landing and join it to Terminal Dogma.

The packet is deliberately limited to the retired north landing and one
five-block-wide L-shaped pressure corridor.  It does not touch the Lilith
chamber, the observation deck, or either adjacent laboratory volume.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import csv
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S21-TERMINAL-DOGMA-ACCESS-R03"
BOX = ((-8, -568, 245), (17, -561, 266))
AIR = "minecraft:air"
FLOOR = "minecraft:polished_blackstone"
LIGHT = "minecraft:sea_lantern"
WALL = "minecraft:deepslate_bricks"
TRIM = "minecraft:deepslate_tiles"
ACCENT = "minecraft:orange_concrete"


def put(desired: dict, current: dict, position: tuple[int, int, int],
        state: str, reason: str) -> None:
    before = current.get(position, AIR)
    if before == state:
        return
    desired[position] = Change(
        PACKET, *position, before, state, "bounded_authored_edit", reason)


def corridor_cells() -> set[tuple[int, int]]:
    # Five blocks wide at both handoffs: the lift threshold is x=10..14 and
    # the existing western deck spans z=256..268.
    south_leg = {(x, z) for x in range(10, 15) for z in range(256, 264)}
    west_leg = {(x, z) for x in range(-4, 15) for z in range(259, 264)}
    return south_leg | west_leg


def design(current: dict) -> list[Change]:
    desired: dict[tuple[int, int, int], Change] = {}

    # Seal the retired north-facing landing.  Its old threshold may remain as
    # a maintenance ledge, but there is no false door or call button.
    for x in range(9, 16):
        put(desired, current, (x, -567, 249),
            FLOOR if x != 12 else LIGHT, "seal retired north landing floor")
        for y in range(-566, -561):
            put(desired, current, (x, y, 249),
                TRIM if y == -562 else WALL,
                "seal retired north landing wall")
    for position in ((15, -565, 248), (15, -564, 248)):
        put(desired, current, position, AIR,
            "remove retired north landing controls")

    interior = corridor_cells()
    for x, z in interior:
        floor = LIGHT if (x * 5 + z * 3) % 17 == 0 else FLOOR
        put(desired, current, (x, -567, z), floor,
            "terminal dogma access floor")
        for y in range(-566, -561):
            put(desired, current, (x, y, z), AIR,
                "terminal dogma access clear volume")
        put(desired, current, (x, -561, z), TRIM,
            "terminal dogma access ceiling")

    # Boundary is derived from the union, so the turn cannot create a sealed
    # corner.  Leave the lift mouth (north) and existing deck mouth (west)
    # completely open.
    for x, z in interior:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if (nx, nz) in interior:
                continue
            lift_mouth = nz == 255 and 10 <= nx <= 14
            dogma_mouth = nx == -5 and 259 <= nz <= 263
            if lift_mouth or dogma_mouth:
                continue
            for y in range(-566, -561):
                put(desired, current, (nx, y, nz),
                    ACCENT if y == -564 else WALL,
                    "terminal dogma access pressure wall")

    changes = sorted(desired.values(), key=lambda c: (c.y, c.z, c.x))
    verify_route(current, changes)
    return changes


def verify_route(current: dict, changes: list[Change]) -> None:
    proposed = dict(current)
    for change in changes:
        proposed[(change.x, change.y, change.z)] = change.after

    def air(position: tuple[int, int, int]) -> bool:
        return proposed.get(position, AIR).split("[", 1)[0] in {
            "minecraft:air", "minecraft:cave_air", "minecraft:void_air"
        }

    def walkable(position: tuple[int, int, int]) -> bool:
        x, y, z = position
        return (not air((x, y - 1, z)) and air((x, y, z))
                and air((x, y + 1, z)))

    start = (12, -566, 256)
    goal = (-4, -566, 263)
    queue = deque([start])
    seen = {start}
    while queue:
        here = queue.popleft()
        if here == goal:
            return
        x, y, z = here
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y, z + dz)
            if nxt not in seen and walkable(nxt):
                seen.add(nxt)
                queue.append(nxt)
    raise RuntimeError(f"B-158 route remains disconnected: {start} -> {goal}")


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s21_terminal_dogma_access_r03_{stamp}"
    artifact.mkdir(parents=True)
    region_dir = dimension_dir(world, DIMENSION) / "region"
    before_dir = artifact / "region_before"
    before_dir.mkdir()
    touched = sorted({(change.x >> 9, change.z >> 9) for change in changes})
    for rx, rz in touched:
        source = region_dir / f"r.{rx}.{rz}.mca"
        if source.exists():
            shutil.copy2(source, before_dir / source.name)

    with (artifact / "block_diff.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("x", "y", "z", "before", "after", "reason"))
        for change in changes:
            writer.writerow((change.x, change.y, change.z,
                             change.before, change.after, change.reason))

    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = {}
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region.setdefault(region, {}).setdefault(chunk, []).append(change)
    for (rx, rz), region_changes in by_region.items():
        source = region_dir / f"r.{rx}.{rz}.mca"
        atomic_replace(source, rewrite_region(source, region_changes))

    (artifact / "receipt.json").write_text(json.dumps({
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "backup": str(before_dir),
    }, indent=2), encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = args.world.resolve()
    current = read_box(world, DIMENSION, BOX[0], BOX[1])
    changes = design(current)
    print(json.dumps({
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "reasons": dict(Counter(c.reason for c in changes)),
    }, indent=2))
    if args.apply:
        print(json.dumps({"artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
