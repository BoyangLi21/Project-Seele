#!/usr/bin/env python3
"""Rebuild the exposed C-22 canopy as a grounded TV-era NERV terminal.

R01 proved the two physical rail lines and the east passenger connection, but
its white open frame reads as a temporary exhibition rack.  R02 stays inside
the same accepted lakeside envelope: it preserves the track datums and east
concourse, replaces the canopy with a low dark pressure shell, and lands the
outer walls on the measured lake bed.  EVA berths, recovery basin, HQ and
command interior are outside the edit mask.
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
PACKET = "S22-C22-LAKESIDE-TERMINAL-R02"
BBOX = ((-242, -512, 101), (-118, -446, 139))

AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:water", "minecraft:bubble_column", "minecraft:sand",
    "minecraft:gravel", "minecraft:clay", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:stone", "minecraft:deepslate",
    "minecraft:snow", "minecraft:snow_block", "minecraft:short_grass",
    "minecraft:tall_grass", "minecraft:seagrass", "minecraft:tall_seagrass",
    "minecraft:kelp", "minecraft:kelp_plant",
}
OWNED = {
    "minecraft:polished_deepslate", "minecraft:polished_blackstone",
    "minecraft:black_concrete", "minecraft:gray_concrete",
    "minecraft:light_gray_concrete", "minecraft:white_concrete",
    "minecraft:blue_concrete", "minecraft:orange_concrete",
    "minecraft:sea_lantern", "minecraft:polished_basalt",
    "minecraft:smooth_stone", "minecraft:redstone_block",
    "minecraft:rail", "minecraft:powered_rail",
    "projectseele:clear_glass",
}

WALL = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
BLACK = "minecraft:black_concrete"
PANEL = "minecraft:gray_concrete"
FLOOR = "minecraft:smooth_stone"
LIGHT = "minecraft:sea_lantern"
PIER = "minecraft:polished_basalt[axis=y]"
GLASS = "projectseele:clear_glass"
WHITE = "minecraft:white_concrete"
BLUE = "minecraft:blue_concrete"
ORANGE = "minecraft:orange_concrete"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if not (-242 <= x <= -185 and 101 <= z <= 139):
        raise RuntimeError(f"left R02 terminal envelope at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def lake_bed(world, x: int, z: int) -> int:
    for y in range(-463, -513, -1):
        state = bare(world.get((x, y, z), "minecraft:air"))
        if state not in AIR and state != "minecraft:water":
            return y
    return -512


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Remove exactly the R01 station body, leaving the accepted east concourse
    # (x >= -184) and every surrounding lake/recovery cell outside the mask.
    for x in range(-232, -184):
        for y in range(-462, -448):
            for z in range(106, 135):
                if bare(world.get((x, y, z), "minecraft:air")) in OWNED:
                    put(desired, x, y, z, "minecraft:air",
                        "retire exposed C-22 R01 canopy")

    # The new terminal is a low pressure vessel rather than a frame floating
    # on water.  A continuous lower hull and periodic lake-bed piers provide a
    # readable load path without filling the entire lake beneath it.
    for x in range(-234, -184):
        for z in range(107, 134):
            put(desired, x, -463, z, WALL,
                "C-22 continuous lower pressure hull")
            deck = EDGE if z in (107, 133) or x in (-234, -185) else FLOOR
            if (x + z) % 29 == 0 and z not in (114, 126):
                deck = LIGHT
            put(desired, x, -462, z, deck, "C-22 grounded station deck")

    for x in (-232, -216, -200, -186):
        for centre_z in (109, 131):
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    px, pz = x + dx, centre_z + dz
                    bed = lake_bed(world, px, pz)
                    for y in range(bed + 1, -463):
                        put(desired, px, y, pz, PIER,
                            "C-22 lake-bed structural pier")

    # Two physical tracks and three platforms keep the accepted rail datum.
    for z in (114, 126):
        for x in range(-231, -188):
            powered = (x + 231) % 13 == 0
            if powered:
                put(desired, x, -462, z, "minecraft:redstone_block",
                    "C-22 concealed rail power")
                rail = "minecraft:powered_rail[shape=east_west]"
            else:
                rail = "minecraft:rail[shape=east_west]"
            put(desired, x, -461, z, rail, "C-22 physical rail line")
        for x in (-232, -187):
            put(desired, x, -461, z, "minecraft:polished_basalt[axis=x]",
                "C-22 terminal buffer")

    for x in range(-232, -186):
        for z in (112, 116, 124, 128):
            put(desired, x, -461, z,
                WHITE if ((x + 232) // 4) % 2 == 0 else BLUE,
                "C-22 platform safety stripe")
        if x % 9 in (0, 1):
            put(desired, x, -461, 120, ORANGE,
                "C-22 secure boarding marker")

    # Low ribbed shell: dark structural roof, clear continuous side ribbons
    # and one restrained orange datum.  The ends remain visually substantial
    # while both tracks and the east passenger throat stay open.
    for x in range(-234, -184):
        bay_rib = (x + 234) % 8 == 0 or x in (-234, -185)
        for z in (107, 133):
            for y in range(-461, -451):
                if y in (-461, -460) or bay_rib:
                    state = WALL
                elif y == -457:
                    state = ORANGE
                elif -459 <= y <= -453:
                    state = GLASS
                else:
                    state = EDGE
                put(desired, x, y, z, state, "C-22 pressure side wall")

        for z in range(107, 134):
            roof_state = LIGHT if (bay_rib and z in (107, 120, 133)) else (
                EDGE if bay_rib or z in (107, 133) else BLACK)
            put(desired, x, -451, z, roof_state, "C-22 low ribbed roof")
            if bay_rib:
                put(desired, x, -452, z,
                    LIGHT if z in (112, 120, 128) else PANEL,
                    "C-22 interior transverse service rib")

    # A chamfered west end gives the terminus a deliberate bunker profile.
    # Track openings remain three blocks wide and seven blocks high.
    for x in range(-242, -233):
        inset = (-233 - x) // 2
        z0, z1 = 107 + inset, 133 - inset
        for z in range(z0, z1 + 1):
            put(desired, x, -463, z, WALL, "C-22 west bunker foundation")
            put(desired, x, -462, z, EDGE, "C-22 west bunker deck")
            put(desired, x, -451 + inset // 2, z,
                LIGHT if z in (114, 120, 126) else BLACK,
                "C-22 chamfered west bunker roof")
        for z in (z0, z1):
            for y in range(-461, -451 + inset // 2):
                put(desired, x, y, z,
                    ORANGE if y == -457 else WALL,
                    "C-22 chamfered west bunker wall")

    # Close the west facade around the two rail bores; the station is a real
    # terminus, not an endless open canopy.
    for z in range(111, 130):
        for y in range(-461, -451):
            rail_bore = ((112 <= z <= 116) or (124 <= z <= 128)) and y <= -454
            state = "minecraft:air" if rail_bore else (
                ORANGE if y == -457 else (GLASS if -459 <= y <= -454 else EDGE))
            put(desired, -234, y, z, state, "C-22 west terminal facade")

    allowed = AIR | NATURAL | OWNED
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
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:12])
        raise RuntimeError(f"protected collision count={len(collisions)} sample={sample}")
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_C22_TERMINAL_R02_{stamp}"
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
