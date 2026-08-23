#!/usr/bin/env python3
"""Replace S22 apron marker poles with an EVA-scale docking gantry.

The finalized 1994 NERV exterior drawing gives the EVA docking position its
own vertical silhouette.  This packet keeps the reviewed three-berth deck and
transfer rails, removes only its known temporary light poles, and builds one
continuous west-side mechanical spine with three open cradles.  It never
touches the hangars, launch plant, observation level or command complex.
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
PACKET = "S22-CANONICAL-EVA-DOCKING-GANTRY-R01"
BBOX = ((-184, -454, 122), (-96, -384, 180))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
OWNED = {
    "minecraft:polished_deepslate", "minecraft:polished_blackstone",
    "minecraft:polished_basalt", "minecraft:smooth_stone",
    "minecraft:light_gray_concrete", "minecraft:orange_concrete",
    "minecraft:yellow_concrete", "minecraft:purple_concrete",
    "minecraft:red_concrete", "minecraft:black_concrete",
    "minecraft:sea_lantern", "projectseele:clear_glass",
}
EDGE = "minecraft:polished_blackstone"
STEEL = "minecraft:polished_deepslate"
CORE = "minecraft:deepslate"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"
ORANGE = "minecraft:orange_concrete"
DECK_Y = -451
BAYS = (135, 151, 167)
COLOURS = ("minecraft:yellow_concrete", "minecraft:purple_concrete",
           "minecraft:red_concrete")


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if x >= -96:
        raise RuntimeError(f"crossed frozen facility boundary at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Remove the eight known prototype marker poles and their 3-wide lamps.
    for z in (127, 143, 159, 175):
        for x in (-176, -110):
            for y in range(DECK_Y + 1, DECK_Y + 24):
                before = bare(world.get((x, y, z), "minecraft:air"))
                if before in OWNED:
                    put(desired, x, y, z, "minecraft:air",
                        "retire temporary EVA apron marker pole")
            for dx in (-1, 0, 1):
                before = bare(world.get((x + dx, DECK_Y + 23, z),
                                        "minecraft:air"))
                if before in OWNED:
                    put(desired, x + dx, DECK_Y + 23, z, "minecraft:air",
                        "retire temporary EVA apron beacon")

    # Continuous load-bearing western spine.  Vertical ribs frame each bay
    # but the east face remains open for the transfer rails and EVA body.
    for x in range(-184, -178):
        for z in range(126, 177):
            for y in range(DECK_Y + 1, -388):
                rib = any(abs(z - centre) in (6, 7) for centre in BAYS)
                top_beam = y >= -394
                base = y <= DECK_Y + 5
                if rib or top_beam or base:
                    state = ORANGE if y in (-424, -423) else (CORE if x < -181 else STEEL)
                    put(desired, x, y, z, state,
                        "EVA docking gantry structural spine")

    for unit, centre in enumerate(BAYS):
        colour = COLOURS[unit]

        # Rear arresting cradle and shoulder-height service arms.  A 13-wide
        # clear pocket remains between the uprights for the 48-block EVA.
        for z in range(centre - 6, centre + 7):
            for y in range(DECK_Y + 1, DECK_Y + 8):
                for x in range(-181, -176):
                    edge = z in (centre - 6, centre + 6)
                    state = colour if y == DECK_Y + 6 else (EDGE if edge else STEEL)
                    put(desired, x, y, z, state,
                        f"EVA-{unit:02d} docking heel cradle")

        for z in (centre - 6, centre + 6):
            for x in range(-181, -167):
                for y in range(-424, -418):
                    shell = y in (-424, -418) or x in (-181, -167)
                    state = EDGE if shell else STEEL
                    put(desired, x, y, z, state,
                        f"EVA-{unit:02d} docking shoulder clamp")

        # Glazed shoulder observation booth behind each berth, reached from
        # the common service gallery rather than floating beside the EVA.
        for x in range(-183, -177):
            for z in range(centre - 4, centre + 5):
                for y in range(-414, -407):
                    edge = x in (-183, -177) or z in (centre - 4, centre + 4)
                    state = GLASS if edge and y not in (-414, -407) else STEEL
                    put(desired, x, y, z, state,
                        f"EVA-{unit:02d} docking observation booth")
        for z in range(centre - 3, centre + 4):
            put(desired, -177, -410, z, colour,
                f"EVA-{unit:02d} docking identity panel")

    # One common high service gallery and restrained lighting, establishing
    # scale without placing a roof across the EVA berths.
    for z in range(126, 177):
        for x in range(-183, -176):
            put(desired, x, -405, z,
                LIGHT if z % 9 == 0 and x == -179 else STEEL,
                "EVA docking high service gallery")
        for y in range(-404, -400):
            put(desired, -176, y, z,
                GLASS if z % 3 != 0 else EDGE,
                "EVA docking high gallery safety screen")

    allowed = AIR | OWNED | {"minecraft:deepslate"}
    changes: list[Change] = []
    collisions = []
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:8])
        raise RuntimeError(f"collides with {len(collisions)} protected cells: {sample}")
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_EVA_DOCKING_{stamp}"
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
        "writes": len(changes), "regionsBeforeSha256": hashes,
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
    print(json.dumps({"packet": PACKET, "writes": len(changes),
                      "parts": dict(sorted(reasons.items()))}, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
