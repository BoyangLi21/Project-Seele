#!/usr/bin/env python3
"""Enclose S22's three EVA transfer berths in one grounded pressure shell.

R02 established the accepted rail datums, foot locks, shoulder galleries and
rear arresting wall, but its exposed crane hangers read as three freestanding
test towers.  This packet leaves those functional datums in place and gives
the interchange the massing of a TV-era NERV industrial building: one thick
roof, two end walls, two bay dividers and three full-height EVA openings.

The edit is confined to the external interchange.  C-22 track level, the
recovery lake, wet cages, launch silos and command interior are out of scope.
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
PACKET = "S22-CANONICAL-EVA-INTERCHANGE-PRESSURE-SHELL-R03"
BBOX = ((-183, -452, 122), (-150, -386, 180))

AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
R02 = {
    "minecraft:polished_deepslate", "minecraft:polished_blackstone",
    "minecraft:polished_basalt", "minecraft:smooth_stone",
    "minecraft:light_gray_concrete", "minecraft:gray_concrete",
    "minecraft:black_concrete", "minecraft:orange_concrete",
    "minecraft:yellow_concrete", "minecraft:purple_concrete",
    "minecraft:red_concrete", "minecraft:deepslate",
    "minecraft:sea_lantern", "projectseele:clear_glass",
}

EDGE = "minecraft:polished_blackstone"
STEEL = "minecraft:polished_deepslate"
CORE = "minecraft:deepslate"
PANEL = "minecraft:gray_concrete"
BLACK = "minecraft:black_concrete"
ORANGE = "minecraft:orange_concrete"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if not (BBOX[0][0] <= x <= BBOX[1][0]
            and BBOX[0][1] <= y <= BBOX[1][1]
            and BBOX[0][2] <= z <= BBOX[1][2]):
        raise RuntimeError(f"left EVA-interchange mask at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def shell_state(x: int, y: int, z: int) -> str:
    if y in (-397, -393) or x in (-183, -150):
        return EDGE
    if (x + z) % 17 == 0 and y == -396:
        return LIGHT
    return CORE if y <= -395 else STEEL


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Remove the thin exposed R02 crane rails/hangers only.  Functional foot
    # locks, transfer tracks, shoulder bridges and rear wall stay untouched.
    for centre in (135, 151, 167):
        for x in range(-180, -152):
            for y in range(-397, -393):
                for z in range(centre - 6, centre + 7):
                    if bare(world.get((x, y, z), "minecraft:air")) in R02:
                        put(desired, x, y, z, "minecraft:air",
                            "retire exposed R02 crane rack")
        for x in (-164, -157):
            for y in range(-417, -393):
                for z in (centre - 6, centre + 6):
                    if bare(world.get((x, y, z), "minecraft:air")) in R02:
                        put(desired, x, y, z, "minecraft:air",
                            "retire exposed R02 crane hanger")

    # One continuous five-block pressure roof.  Fifty-four clear blocks from
    # the transfer deck to its underside preserve the full 48-block EVA scale.
    for x in range(-183, -149):
        for y in range(-397, -392):
            for z in range(126, 177):
                put(desired, x, y, z, shell_state(x, y, z),
                    "shared EVA interchange pressure roof")

    # End walls and two thick bay dividers make the building read as one
    # grounded three-berth facility.  The openings remain 12/12/11 blocks
    # wide and 49 blocks high, aligned to the existing coloured rail lanes.
    wall_bands = ((126, 129), (142, 145), (158, 161), (173, 176))
    for z0, z1 in wall_bands:
        for x in range(-183, -149):
            for y in range(-451, -397):
                for z in range(z0, z1 + 1):
                    edge = (z in (z0, z1) or x in (-183, -150)
                            or y in (-451, -450, -399, -398))
                    state = EDGE if edge else (PANEL if x >= -154 else CORE)
                    if x == -150 and y in (-425, -424):
                        state = ORANGE
                    put(desired, x, y, z, state,
                        "EVA interchange grounded pressure pier")

    # Deep front lintel and sill frame.  Only the wall bands are solid at EVA
    # height; the three central apertures are explicitly kept open.
    openings = ((130, 141), (146, 157), (162, 172))
    for x in range(-153, -149):
        for z in range(126, 177):
            in_opening = any(a <= z <= b for a, b in openings)
            for y in range(-451, -397):
                frame = y in range(-451, -447) or y in range(-402, -397)
                if in_opening and not frame:
                    continue
                state = EDGE if x in (-153, -150) or frame else PANEL
                if y in (-425, -424) and not in_opening:
                    state = ORANGE
                put(desired, x, y, z, state,
                    "EVA interchange front pressure frame")

    # A sheltered inspection band ties the three shoulder bridges together
    # without placing a freestanding bridge in front of the EVA silhouettes.
    for x in range(-156, -149):
        for z in range(127, 176):
            put(desired, x, -421, z,
                LIGHT if z % 8 == 0 else STEEL,
                "shared EVA interchange inspection deck")
            put(desired, x, -420, z, STEEL,
                "shared EVA interchange inspection deck")
        put(desired, x, -419, 127, EDGE,
            "inspection deck end guard")
        put(desired, x, -419, 175, EDGE,
            "inspection deck end guard")
    for z in range(127, 176):
        if any(a <= z <= b for a, b in openings):
            put(desired, -150, -419, z,
                LIGHT if z % 8 == 0 else GLASS,
                "inspection deck clear EVA-side guard")

    # Three compact overhead service rails remain inside the new shell.
    for centre in (135, 151, 167):
        for x in range(-180, -153):
            for z in (centre - 4, centre + 4):
                put(desired, x, -400, z, STEEL,
                    "internal EVA service rail")
                put(desired, x, -399, z,
                    LIGHT if x % 8 == 0 else ORANGE,
                    "internal EVA service datum")

    changes: list[Change] = []
    collisions = []
    for position, (after, reason) in sorted(desired.items(), key=lambda i: i[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in AIR | R02:
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
    backup = Path("backups") / f"SEELE_S22_PRE_EVA_INTERCHANGE_R03_{stamp}"
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
    report = {
        "packet": PACKET,
        "writes": len(changes),
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes),
            max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes),
        ],
        "parts": dict(sorted(reasons.items())),
    }
    print(json.dumps(report, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
