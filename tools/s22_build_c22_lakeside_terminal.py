#!/usr/bin/env python3
"""Build the S22 C-22 lakeside personnel-train terminus.

The packet replaces only the temporary black lake box and the first part of
its accepted nine-block arrival deck.  It leaves the deep recovery basin,
EVA berths, HQ entrance and every command-room voxel outside its envelope.
The two tracks are real vanilla rails; the platforms, canopy and lake piers
are physical, walkable structure rather than scenery markers.
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
PACKET = "S22-C22-LAKESIDE-TERMINAL-R01"
BBOX = ((-236, -512, 102), (-118, -446, 138))

AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:water", "minecraft:bubble_column", "minecraft:sand", "minecraft:gravel",
    "minecraft:clay", "minecraft:dirt", "minecraft:grass_block",
    "minecraft:stone", "minecraft:deepslate", "minecraft:snow",
    "minecraft:snow_block", "minecraft:short_grass",
    "minecraft:tall_grass", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp",
    "minecraft:kelp_plant",
}
OWNED = {
    "minecraft:polished_deepslate", "minecraft:polished_blackstone",
    "minecraft:black_concrete", "minecraft:light_gray_concrete",
    "minecraft:white_concrete", "minecraft:blue_concrete",
    "minecraft:orange_concrete", "minecraft:sea_lantern",
    "minecraft:polished_basalt", "minecraft:smooth_stone",
    "minecraft:redstone_block", "minecraft:rail",
    "minecraft:powered_rail", "projectseele:clear_glass",
}

WALL = "minecraft:polished_deepslate"
EDGE = "minecraft:polished_blackstone"
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
    if x > -118 or z < 102 or z > 138:
        raise RuntimeError(f"left C-22 construction envelope at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def highest_bed(world, x: int, z: int) -> int:
    for y in range(-463, BBOX[0][1] - 1, -1):
        state = bare(world.get((x, y, z), "minecraft:air"))
        if state not in AIR and state != "minecraft:water":
            return y
    return BBOX[0][1]


def station_design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Remove only the temporary terminal superstructure.  The accepted route
    # and its foundation are rebuilt below as one coherent station deck.
    for x in range(-232, -184):
        for y in range(-460, -449):
            for z in range(106, 135):
                put(desired, x, y, z, "minecraft:air",
                    "retire temporary lake-terminal box")

    # A 25-block-wide load deck carries two rail lines and three platforms.
    # All walking surfaces and rail heads share y=-460.
    for x in range(-232, -184):
        for z in range(108, 133):
            put(desired, x, -462, z, WALL,
                "C-22 terminal lower structural deck")
            top = FLOOR
            if z in (108, 132) or x in (-232, -185):
                top = EDGE
            elif (x + z) % 23 == 0 and z not in (114, 126):
                top = LIGHT
            put(desired, x, -461, z, top,
                "C-22 terminal platform deck")

    # Two real east-west tracks. Powered sections use concealed redstone
    # support so a minecart can traverse them without decorative substitutes.
    for z in (114, 126):
        for x in range(-228, -189):
            powered = (x + 228) % 12 == 0
            if powered:
                put(desired, x, -461, z, "minecraft:redstone_block",
                    "C-22 concealed traction power")
                rail = "minecraft:powered_rail[shape=east_west]"
            else:
                rail = "minecraft:rail[shape=east_west]"
            put(desired, x, -460, z, rail, "C-22 physical rail line")

        # Heavy terminal stops at both ends keep this a secure NERV terminus.
        for x in (-230, -188):
            put(desired, x, -460, z, "minecraft:polished_basalt[axis=x]",
                "C-22 terminal buffer stop")

    # Platform-edge identity strips: white/blue TV-era railway language, with
    # NERV orange reserved for the central secure boarding threshold.
    for x in range(-230, -187):
        for z in (112, 116, 124, 128):
            put(desired, x, -460, z,
                WHITE if (x // 4) % 2 == 0 else BLUE,
                "C-22 platform safety band")
    for x in range(-228, -189):
        if x % 8 in (0, 1):
            put(desired, x, -460, 120, ORANGE,
                "C-22 secure central-platform marker")

    # Open, low production-art-style canopy.  It replaces the unreadable
    # solid black box with repeated structural bays and a translucent roof.
    frame_x = list(range(-232, -184, 8))
    if frame_x[-1] != -185:
        frame_x.append(-185)
    for x in frame_x:
        for z in (108, 132):
            for y in range(-460, -451):
                put(desired, x, y, z, PIER, "C-22 canopy column")
        for z in range(108, 133):
            put(desired, x, -451, z,
                LIGHT if z in (108, 120, 132) else WHITE,
                "C-22 canopy transverse frame")
    for x in range(-232, -184):
        for z in range(108, 133):
            edge = z in (108, 132)
            state = WHITE if edge or x in frame_x else GLASS
            put(desired, x, -450, z, state, "C-22 translucent canopy")

    # Glazed wind/safety screens do not close the station: openings remain at
    # both track ends and at every second structural bay.
    for x in range(-230, -187):
        if ((x + 230) // 8) % 2 == 0:
            continue
        for z in (108, 132):
            for y in range(-459, -452):
                put(desired, x, y, z, GLASS, "C-22 platform safety screen")

    # The existing route rises eastward.  A broad stepped passenger link
    # leaves the centre platform and lands on the accepted nine-wide route at
    # x=-119 without touching the adjacent EVA docking structure.
    for x in range(-184, -118):
        rise = min(5, (x + 184) // 13 + 1)
        floor_y = -461 + rise
        for z in range(117, 124):
            for y in range(-462, floor_y):
                put(desired, x, y, z, WALL,
                    "C-22 to EVA-interchange retaining core")
            put(desired, x, floor_y, z,
                LIGHT if z == 120 and x % 5 == 0 else FLOOR,
                "C-22 to EVA-interchange stepped concourse")
        for z in (116, 124):
            for y in range(floor_y, floor_y + 2):
                put(desired, x, y, z, EDGE,
                    "C-22 concourse guarded edge")

    # Physical lake-bed support.  Every sixteenth metre bay uses paired 3x3
    # piers, terminating on the measured sediment instead of in mid-water.
    for x in (-224, -208, -192):
        for centre_z in (110, 130):
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    px, pz = x + dx, centre_z + dz
                    bed = highest_bed(world, px, pz)
                    for y in range(bed + 1, -462):
                        put(desired, px, y, pz, PIER,
                            "C-22 lake-bed load pier")

    allowed = AIR | NATURAL | OWNED
    changes: list[Change] = []
    collisions: list[tuple[tuple[int, int, int], str]] = []
    for position, (after, reason) in sorted(desired.items(), key=lambda i: i[0][1]):
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
    backup = Path("backups") / f"SEELE_S22_PRE_C22_TERMINAL_{stamp}"
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
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes = station_design(world)
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
