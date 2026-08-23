#!/usr/bin/env python3
"""Refine the installed R28 Terminal Dogma without rebuilding its shell/lake.

The R04 pressure ellipsoid and LCL basin remain authoritative.  This packet
removes the retired x=72 stone shaft from inside the chamber, moves the red
crucifix to the south wall, and builds a north-facing arrival/viewing axis so
the B-158 approach reads Lilith immediately.  Exact region backups and read-
back verification make the edit reversible.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import csv
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


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S21-TERMINAL-DOGMA-R05"
BBOX = ((-12, -620, 246), (77, -528, 344))
AIR = "minecraft:air"
FLOOR = "minecraft:polished_blackstone"
TRIM = "minecraft:deepslate_tiles"
STRUCTURE = "minecraft:reinforced_deepslate"
LIGHT = "minecraft:sea_lantern"
RED = "minecraft:redstone_block"
RED_GLASS = "minecraft:red_stained_glass"
SHROOMLIGHT = "minecraft:shroomlight"
AIR_NAMES = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
RETIRED_SHAFT = {"minecraft:stone", "minecraft:tuff", "minecraft:deepslate"}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def ellipsoid(x: int, y: int, z: int) -> float:
    return ((x - 30) / 40.0) ** 2 + ((y + 574) / 44.0) ** 2 \
        + ((z - 296) / 48.0) ** 2


def put(desired: dict[tuple[int, int, int], Change], current: dict,
        position: tuple[int, int, int], after: str, reason: str,
        allowed: set[str] | None = None) -> None:
    before = current.get(position, AIR)
    if before == after:
        return
    if allowed is not None and bare(before) not in allowed:
        return
    desired[position] = Change(PACKET, *position, before, after,
                               "bounded_authored_edit", reason)


def fill(desired: dict, current: dict,
         lo: tuple[int, int, int], hi: tuple[int, int, int],
         state: str, reason: str, allowed: set[str] | None = None) -> None:
    for x in range(lo[0], hi[0] + 1):
        for y in range(lo[1], hi[1] + 1):
            for z in range(lo[2], hi[2] + 1):
                put(desired, current, (x, y, z), state, reason, allowed)


def floor_strip(desired: dict, current: dict,
                x0: int, x1: int, z0: int, z1: int, y: int,
                reason: str) -> None:
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            put(desired, current, (x, y, z),
                LIGHT if (x * 7 + z * 11) % 23 == 0 else FLOOR, reason)
            for clear_y in range(y + 1, y + 5):
                put(desired, current, (x, clear_y, z), AIR,
                    reason + " clear")


def rail_x(desired: dict, current: dict,
           x0: int, x1: int, y: int, z: int, reason: str) -> None:
    state = "minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]"
    for x in range(x0, x1 + 1):
        put(desired, current, (x, y, z), state, reason)


def rail_z(desired: dict, current: dict,
           x: int, y: int, z0: int, z1: int, reason: str) -> None:
    state = "minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]"
    for z in range(z0, z1 + 1):
        put(desired, current, (x, y, z), state, reason)


def plan(world: Path) -> list[Change]:
    current = read_box(world, DIMENSION, BBOX[0], BBOX[1])
    desired: dict[tuple[int, int, int], Change] = {}

    # Remove only natural backfill from the retired x=72 shaft where that box
    # lies inside the R04 chamber.  Authored floor/deck cells are not candidates.
    for x in range(67, 78):
        for y in range(-581, -466):
            for z in range(268, 279):
                position = (x, y, z)
                put(desired, current, position, AIR,
                    "clear_retired_x72_stone_backfill",
                    RETIRED_SHAFT)

    # Fully retire the old north-wall red crucifix and exposed light core.
    old_cross = {RED, RED_GLASS, SHROOMLIGHT}
    for x in range(8, 53):
        for y in range(-586, -542):
            for z in range(269, 275):
                put(desired, current, (x, y, z), AIR,
                    "retire_north_wall_crucifix", old_cross)

    # South-wall crucifix, luminous face toward the north/B-158 arrival.
    fill(desired, current, (26, -585, 320), (34, -544, 322), RED,
         "south_wall_crucifix_vertical")
    fill(desired, current, (9, -563, 320), (51, -555, 322), RED,
         "south_wall_crucifix_horizontal")
    fill(desired, current, (26, -585, 319), (34, -544, 319), RED_GLASS,
         "south_wall_crucifix_luminous_face")
    fill(desired, current, (9, -563, 319), (51, -555, 319), RED_GLASS,
         "south_wall_crucifix_luminous_face")
    for y in range(-584, -543, 4):
        put(desired, current, (30, y, 321), SHROOMLIGHT,
            "south_wall_crucifix_concealed_light")
    for x in range(10, 51, 4):
        put(desired, current, (x, -559, 321), SHROOMLIGHT,
            "south_wall_crucifix_concealed_light")

    # A broad frontal platform replaces the old bridge that ran through the
    # new cross.  Both perimeter galleries feed it; the centre remains a clear
    # processional sightline from north to south.
    floor_strip(desired, current, 8, 52, 278, 306, -567,
                "Terminal Dogma north frontal gallery")
    # West arrival handoff from Heaven's Door into the broad frontal gallery.
    floor_strip(desired, current, -2, 8, 278, 286, -567,
                "Terminal Dogma west arrival handoff")
    floor_strip(desired, current, 24, 36, 307, 313, -567,
                "Terminal Dogma short axial dais")
    rail_x(desired, current, 8, 23, -566, 307,
           "Terminal Dogma frontal gallery rail")
    rail_x(desired, current, 37, 52, -566, 307,
           "Terminal Dogma frontal gallery rail")
    rail_z(desired, current, 7, -566, 287, 306,
           "Terminal Dogma frontal gallery rail")
    rail_z(desired, current, 53, -566, 286, 306,
           "Terminal Dogma frontal gallery rail")

    # Retire the old axial bridge south of the new dais, but preserve the
    # actual south perimeter gallery at z=328..337.
    for x in range(24, 37):
        for z in range(314, 328):
            for y in range(-567, -562):
                position = (x, y, z)
                if y == -567 or bare(current.get(position, AIR)) in {
                        "minecraft:iron_bars"}:
                    put(desired, current, position, AIR,
                        "retire_cross_conflicting_axial_bridge")

    # Runtime witnesses agree with the Java R28 south-wall audit.
    put(desired, current, (30, -558, 321), RED,
        "Terminal Dogma runtime witness")
    put(desired, current, (50, -558, 319), RED_GLASS,
        "Terminal Dogma runtime witness")
    put(desired, current, (30, -567, 300), "minecraft:lodestone",
        "Terminal Dogma frontal witness")

    changes = sorted(desired.values(), key=lambda c: (c.y, c.z, c.x))
    verify(current, changes)
    return changes


def verify(current: dict, changes: list[Change]) -> None:
    proposed = dict(current)
    for change in changes:
        proposed[(change.x, change.y, change.z)] = change.after

    def air(position: tuple[int, int, int]) -> bool:
        return bare(proposed.get(position, AIR)) in AIR_NAMES

    def walkable(position: tuple[int, int, int]) -> bool:
        x, y, z = position
        return (not air((x, y - 1, z)) and air((x, y, z))
                and air((x, y + 1, z)))

    start = (-4, -566, 263)
    goal = (30, -566, 300)
    queue = deque([start])
    seen = {start}
    bounds = (-8, 68, 250, 318)
    while queue:
        here = queue.popleft()
        if here == goal:
            break
        x, y, z = here
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y, z + dz)
            if (bounds[0] <= nxt[0] <= bounds[1]
                    and bounds[2] <= nxt[2] <= bounds[3]
                    and nxt not in seen and walkable(nxt)):
                seen.add(nxt)
                queue.append(nxt)
    else:
        raise RuntimeError(f"B-158 cannot reach frontal gallery: {start}->{goal}")
    required = {
        (30, -558, 321): "minecraft:redstone_block",
        (50, -558, 319): "minecraft:red_stained_glass",
        (30, -567, 300): "minecraft:lodestone",
        (30, -583, 296): "projectseele:lcl",
    }
    for position, expected in required.items():
        actual = bare(proposed.get(position, AIR))
        if actual != expected:
            raise RuntimeError(f"witness {position}: {actual} != {expected}")
    if any(bare(proposed.get((30, -558, z), AIR)) in old
           for z in range(270, 274)
           for old in ({RED, RED_GLASS, SHROOMLIGHT},)):
        raise RuntimeError("old north-wall cross still has a central witness")


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s21_terminal_dogma_r05_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    region_dir = dimension_dir(world, DIMENSION) / "region"
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    originals: dict[Path, bytes] = {}
    changed: list[Path] = []
    try:
        for (rx, rz), chunk_changes in sorted(by_region.items()):
            path = region_dir / f"r.{rx}.{rz}.mca"
            originals[path] = path.read_bytes()
            shutil.copy2(path, backup / path.name)
            atomic_replace(path, rewrite_region(path, chunk_changes))
            changed.append(path)
        lo = tuple(min(getattr(c, axis) for c in changes)
                   for axis in ("x", "y", "z"))
        hi = tuple(max(getattr(c, axis) for c in changes)
                   for axis in ("x", "y", "z"))
        actual = read_box(world, DIMENSION, lo, hi)
        failures = [c for c in changes
                    if actual.get((c.x, c.y, c.z), AIR) != c.after]
        if failures:
            raise RuntimeError(f"read-back failed for {len(failures)} cells")
    except Exception:
        for path in changed:
            atomic_replace(path, originals[path])
        raise
    with (artifact / "block_diff.csv").open(
            "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x", "y", "z", "before", "after", "reason"))
        for change in changes:
            writer.writerow((change.x, change.y, change.z, change.before,
                             change.after, change.reason))
    receipt = {
        "status": "APPLIED_AND_EXACT_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "reasons": dict(Counter(c.reason for c in changes)),
        "regionsBeforeSha256": {
            path.name: hashlib.sha256(data).hexdigest()
            for path, data in originals.items()
        },
    }
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = args.world.resolve()
    changes = plan(world)
    print(json.dumps({
        "packet": PACKET,
        "writes": len(changes),
        "reasons": dict(Counter(c.reason for c in changes)),
    }, indent=2))
    if args.apply:
        print(json.dumps({"artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
