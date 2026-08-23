#!/usr/bin/env python3
"""Rebuild S22's undersized exterior EVA interchange at EVA scale.

The first arrival packet proved the physical route, but its 26 x 15 marker
deck was smaller than a deployed Evangelion.  This packet replaces only that
known prototype and surrounding natural shore with a 71 x 51 heavy sortie
apron: three parallel berths, a load-bearing island, a pedestrian/service
connection to the lake-to-HQ avenue, and restrained NERV safety markings.

The reviewed HQ remains frozen: every write is west of x=-96.
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
PACKET = "S22-CANONICAL-GEOFRONT-EVA-SORTIE-APRON-R01"
BBOX = ((-182, -468, 122), (-96, -424, 180))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:water", "minecraft:sand", "minecraft:gravel",
    "minecraft:clay", "minecraft:dirt", "minecraft:grass_block",
    "minecraft:stone", "minecraft:deepslate", "minecraft:snow",
    "minecraft:snow_block", "minecraft:tall_grass",
    "minecraft:short_grass", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp", "minecraft:kelp_plant",
    "minecraft:spruce_log", "minecraft:spruce_leaves",
}
PROTOTYPE = {
    "minecraft:polished_deepslate", "minecraft:polished_blackstone",
    "minecraft:yellow_concrete", "minecraft:purple_concrete",
    "minecraft:red_concrete", "minecraft:sea_lantern",
    "projectseele:clear_glass", "minecraft:polished_basalt",
    "minecraft:light_gray_concrete",
}

FLOOR = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
RAIL = "minecraft:polished_basalt[axis=x]"
PAD = "minecraft:smooth_stone"
LIGHT = "minecraft:sea_lantern"
WHITE = "minecraft:light_gray_concrete"
YELLOW = "minecraft:yellow_concrete"
ORANGE = "minecraft:orange_concrete"
BLACK = "minecraft:black_concrete"
GLASS = "projectseele:clear_glass"
CORE = "minecraft:deepslate"

DECK_Y = -451
X0, X1 = -178, -108
Z0, Z1 = 126, 176
BAY_CENTRES = (135, 151, 167)


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def set_desired(
        desired: dict[tuple[int, int, int], tuple[str, str]],
        x: int, y: int, z: int, state: str, reason: str) -> None:
    if x >= -96:
        raise RuntimeError(f"packet crossed frozen east boundary at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def hazard(x: int) -> str:
    return YELLOW if (x // 3) % 2 == 0 else BLACK


def design(world: dict[tuple[int, int, int], str]) -> tuple[list[Change], int]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Remove the one-block safety glazing of the known 26 x 15 prototype.
    # Its floor is covered by the larger replacement below.
    for x in range(-130, -104):
        for z in range(136, 151):
            before = world.get((x, DECK_Y + 1, z), "minecraft:air")
            if bare(before) in PROTOTYPE:
                set_desired(desired, x, DECK_Y + 1, z,
                            "minecraft:air", "retire prototype apron trim")

    # Solid artificial island.  Each column stops at the deck; no forest of
    # thin piers remains beneath an EVA-scale load.
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            for y in range(-466, DECK_Y):
                edge = x in (X0, X1) or z in (Z0, Z1)
                state = EDGE if edge and (y - (-466)) % 5 == 0 else CORE
                set_desired(desired, x, y, z, state,
                            "EVA sortie apron load-bearing island")

    # Main deck and restrained safety edge.
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            edge = x in (X0, X1) or z in (Z0, Z1)
            state = EDGE if edge else FLOOR
            set_desired(desired, x, DECK_Y, z, state,
                        "EVA sortie apron deck")

    # Three 13-wide parallel berths.  The heavy rails carry the feet/transfer
    # cradles; markings remain narrow so the pad reads as machinery, not a
    # coloured test chart.
    for unit, centre in enumerate(BAY_CENTRES):
        for x in range(X0 + 5, X1 - 3):
            for dz in range(-5, 6):
                z = centre + dz
                if abs(dz) == 5:
                    state = hazard(x)
                    reason = f"EVA-{unit:02d} berth hazard edge"
                elif abs(dz) == 3:
                    state = RAIL
                    reason = f"EVA-{unit:02d} heavy transfer rail"
                elif dz == 0:
                    state = LIGHT if x % 12 == 0 else WHITE
                    reason = f"EVA-{unit:02d} berth centreline"
                else:
                    state = PAD
                    reason = f"EVA-{unit:02d} reinforced standing pad"
                set_desired(desired, x, DECK_Y, z, state, reason)

        # West mechanical stops and compact unit-colour identity plate.
        colour = (YELLOW, "minecraft:purple_concrete",
                  "minecraft:red_concrete")[unit]
        for x in range(X0 + 1, X0 + 5):
            for z in range(centre - 4, centre + 5):
                for y in range(DECK_Y + 1, DECK_Y + 5):
                    state = colour if y == DECK_Y + 3 else EDGE
                    set_desired(desired, x, y, z, state,
                                f"EVA-{unit:02d} arresting stop")

    # East-side personnel/service link meets the existing north-south avenue
    # at its measured y=-451 section without altering that avenue itself.
    for x in range(X1 + 1, -96):
        for z in range(146, 157):
            edge = z in (146, 156)
            state = EDGE if edge else (WHITE if z == 151 else FLOOR)
            set_desired(desired, x, DECK_Y, z, state,
                        "sortie apron to arrival-avenue link")
            if edge and x % 3 != 0:
                set_desired(desired, x, DECK_Y + 1, z, GLASS,
                            "sortie link safety glazing")

    # Four service pylons provide scale without spanning a fake low roof over
    # the 48-block EVA silhouette.
    for z in (127, 143, 159, 175):
        for x in (X0 + 2, X1 - 2):
            for y in range(DECK_Y + 1, DECK_Y + 24):
                state = ORANGE if y in (DECK_Y + 8, DECK_Y + 9) else EDGE
                set_desired(desired, x, y, z, state,
                            "EVA apron shoulder-height service pylon")
            for dx in (-1, 0, 1):
                set_desired(desired, x + dx, DECK_Y + 23, z, LIGHT,
                            "EVA apron service beacon")

    changes: list[Change] = []
    preserved = 0
    allowed = AIR | NATURAL | PROTOTYPE | {
        "minecraft:orange_concrete", "minecraft:black_concrete",
        "minecraft:smooth_stone",
    }
    for position, (after, reason) in sorted(desired.items(),
                                             key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            preserved += 1
            continue
        changes.append(Change(
            PACKET, *position, before, after, "replace", reason,
        ))
    return changes, preserved


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_EVA_APRON_{stamp}"
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

    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "frozenEastBoundary": "x >= -96 untouched",
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
    changes, preserved = design(world)
    reasons: dict[str, int] = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    report = {
        "packet": PACKET,
        "writes": len(changes),
        "preservedUnknownAuthoredCells": preserved,
        "bounds": [
            min(change.x for change in changes),
            min(change.y for change in changes),
            min(change.z for change in changes),
            max(change.x for change in changes),
            max(change.y for change in changes),
            max(change.z for change in changes),
        ],
        "parts": dict(sorted(reasons.items())),
    }
    print(json.dumps(report, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
