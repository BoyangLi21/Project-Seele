#!/usr/bin/env python3
"""Replace S22's flooded legacy Terminal Dogma with a vertical seal cathedral.

The packet is deliberately confined to the legacy Terminal-Dogma chamber.
It preserves the existing Central-Dogma shaft and its upper route, clears the
runaway LCL at observation height, and reconnects the shaft through a sealed
quarantine vestibule.  R28 and the accepted command interior are untouched.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
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


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-CANONICAL-TERMINAL-DOGMA-R01"
BBOX = ((-12, -620, 246), (72, -528, 344))

AIR = "minecraft:air"
WALL = "minecraft:deepslate_bricks"
RIB = "minecraft:polished_basalt[axis=y]"
TRIM = "minecraft:deepslate_tiles"
FLOOR = "minecraft:polished_blackstone"
STRUCTURE = "minecraft:reinforced_deepslate"
LIGHT = "minecraft:sea_lantern"
INVISIBLE_LIGHT = "minecraft:light[level=15,waterlogged=false]"
RED = "minecraft:redstone_block"
RED_GLASS = "minecraft:red_stained_glass"
LCL = "projectseele:lcl[level=0]"

OLD_OWNED = {
    "minecraft:deepslate_bricks", "minecraft:polished_basalt",
    "minecraft:deepslate_tiles", "minecraft:redstone_block",
    "minecraft:orange_concrete", "minecraft:polished_blackstone",
    "minecraft:red_stained_glass", "minecraft:reinforced_deepslate",
    "minecraft:light_gray_concrete", "minecraft:sea_lantern",
    "minecraft:iron_block", "minecraft:iron_bars",
    "minecraft:polished_deepslate", "minecraft:light",
    "minecraft:red_concrete", "minecraft:redstone_lamp",
    "minecraft:black_concrete", "minecraft:shroomlight",
    "minecraft:ladder", "minecraft:lodestone", "minecraft:calcite",
    "minecraft:magenta_concrete", "minecraft:netherite_block",
    "minecraft:gray_stained_glass", "projectseele:lcl",
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def ellipsoid(x: int, y: int, z: int,
              cx: int, cy: int, cz: int,
              rx: float, ry: float, rz: float) -> float:
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if not (BBOX[0][0] <= x <= BBOX[1][0]
            and BBOX[0][1] <= y <= BBOX[1][1]
            and BBOX[0][2] <= z <= BBOX[1][2]):
        raise RuntimeError(f"write escaped Terminal Dogma envelope: {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def fill(desired, x0, y0, z0, x1, y1, z1, state, reason) -> None:
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                put(desired, x, y, z, state, reason)


def floor_strip(desired, x0, x1, z0, z1, y, reason) -> None:
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            state = LIGHT if (x * 7 + z * 11) % 17 == 0 else FLOOR
            put(desired, x, y, z, state, reason)


def rail_x(desired, x0, x1, y, z, reason) -> None:
    state = "minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]"
    for x in range(x0, x1 + 1):
        put(desired, x, y, z, state, reason)


def rail_z(desired, x, y, z0, z1, reason) -> None:
    state = "minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]"
    for z in range(z0, z1 + 1):
        put(desired, x, y, z, state, reason)


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Retire only the legacy ellipsoid and its escaped LCL.  Unknown blocks
    # remain a hard collision instead of silently becoming part of the room.
    for (x, y, z), state in world.items():
        old_shell = ellipsoid(x, y, z, 30, -566, 296, 38, 30, 46) <= 1.08
        escaped_lcl = bare(state) == "projectseele:lcl"
        if (old_shell or escaped_lcl) and bare(state) in OLD_OWNED:
            put(desired, x, y, z, AIR, "retire flooded legacy chamber")

    # Tall containment shell: the vertical span is now 88 blocks instead of
    # the old 60-block oval room.  Ribs are regular, sparse and structural.
    cx, cy, cz = 30, -574, 296
    rx, ry, rz = 40, 44, 48
    for x in range(cx - rx, cx + rx + 1):
        for y in range(cy - ry, cy + ry + 1):
            for z in range(cz - rz, cz + rz + 1):
                distance = ellipsoid(x, y, z, cx, cy, cz, rx, ry, rz)
                if distance > 1.0:
                    continue
                if distance < 0.90:
                    put(desired, x, y, z, AIR, "terminal dogma cathedral void")
                    continue
                angle = math.atan2(z - cz, x - cx)
                vertical_rib = int((angle + math.pi) / (math.pi / 12)) % 3 == 0
                horizontal_rib = (y - (cy - ry)) % 9 <= 1
                state = RIB if horizontal_rib else (TRIM if vertical_rib else WALL)
                put(desired, x, y, z, state, "terminal dogma pressure shell")

    # LCL is a bounded seal lake at the bottom, never an atmospheric ceiling.
    lake_cz = 289
    for x in range(0, 61):
        for z in range(256, 323):
            d = ((x - 30) / 27.0) ** 2 + ((z - lake_cz) / 31.0) ** 2
            if d <= 1.0:
                put(desired, x, -613, z,
                    LIGHT if (x * 17 + z * 29) % 23 == 0
                    else "minecraft:orange_concrete",
                    "terminal dogma LCL lake bed")
                for y in range(-612, -602):
                    put(desired, x, y, z, LCL,
                        "terminal dogma bounded LCL lake")
            elif d <= 1.18:
                put(desired, x, -602, z,
                    LIGHT if (x + z) % 9 == 0 else STRUCTURE,
                    "terminal dogma LCL containment rim")

    # Pure-red crucifix, facing the observation bridge.  The existing Lilith
    # entity remains in front of it at the authored S22 specimen anchor.
    fill(desired, 26, -609, 268, 34, -541, 271, RED,
         "terminal dogma red crucifix vertical")
    fill(desired, 4, -581, 268, 56, -568, 271, RED,
         "terminal dogma red crucifix horizontal")
    fill(desired, 26, -609, 272, 34, -541, 272, RED_GLASS,
         "terminal dogma crucifix luminous face")
    fill(desired, 4, -581, 272, 56, -568, 272, RED_GLASS,
         "terminal dogma crucifix luminous face")
    for y in range(-607, -542, 5):
        put(desired, 30, y, 270, "minecraft:shroomlight",
            "terminal dogma crucifix concealed light")
    for x in range(6, 55, 5):
        put(desired, x, -574, 270, "minecraft:shroomlight",
            "terminal dogma crucifix concealed light")

    # High observation route: a south bridge and a U-shaped perimeter gallery
    # read as a deliberate processional axis rather than a floating slab.
    floor_strip(desired, 24, 36, 311, 337, -567,
                "terminal dogma axial observation bridge")
    floor_strip(desired, -2, 62, 328, 337, -567,
                "terminal dogma south observation gallery")
    floor_strip(desired, -2, 5, 278, 327, -567,
                "terminal dogma west observation gallery")
    floor_strip(desired, 55, 62, 278, 327, -567,
                "terminal dogma east observation gallery")
    rail_x(desired, -2, 23, -566, 327,
           "terminal dogma observation rail")
    rail_x(desired, 37, 62, -566, 327,
           "terminal dogma observation rail")
    rail_z(desired, 6, -566, 278, 310,
           "terminal dogma observation rail")
    rail_z(desired, 54, -566, 278, 310,
           "terminal dogma observation rail")
    rail_x(desired, -2, 62, -566, 338,
           "terminal dogma outer observation rail")
    rail_z(desired, -3, -566, 278, 337,
           "terminal dogma outer observation rail")
    rail_z(desired, 63, -566, 278, 337,
           "terminal dogma outer observation rail")

    # East quarantine vestibule joins the existing Central-Dogma shaft at
    # x=72,z=273 without moving or rebuilding that shaft.
    floor_strip(desired, 55, 70, 269, 277, -567,
                "terminal dogma quarantine approach")
    for x in range(55, 71):
        for z in range(269, 278):
            for y in range(-566, -560):
                boundary = z in (269, 277)
                if boundary:
                    state = RED_GLASS if -565 <= y <= -562 else STRUCTURE
                    put(desired, x, y, z, state,
                        "terminal dogma quarantine wall")
                else:
                    put(desired, x, y, z, AIR,
                        "terminal dogma quarantine clear route")
            put(desired, x, -559, z,
                LIGHT if (x + z) % 6 == 0 else STRUCTURE,
                "terminal dogma quarantine ceiling")
    for gate_x in (55, 62, 70):
        for y in range(-566, -560):
            for z in range(269, 278):
                aperture = 271 <= z <= 275 and y <= -561
                put(desired, gate_x, y, z, AIR if aperture else (
                    "minecraft:red_concrete" if y in (-564, -563) else
                    "minecraft:iron_block"),
                    "terminal dogma quarantine pressure frame")

    # Physical descent to the LCL service rim.  The wall-backed ladder is
    # intentionally placed on the east gallery, outside Lilith's silhouette.
    for y in range(-601, -566):
        put(desired, 64, y, 322, "minecraft:black_concrete",
            "terminal dogma lower service shaft backing")
        put(desired, 63, y, 322,
            "minecraft:ladder[facing=west,waterlogged=false]",
            "terminal dogma lower service ladder")
    floor_strip(desired, 55, 63, 316, 327, -602,
                "terminal dogma lower service landing")
    rail_x(desired, 55, 63, -601, 315,
           "terminal dogma lower service rail")
    rail_z(desired, 54, -601, 316, 327,
           "terminal dogma lower service rail")

    # Sparse invisible illumination reveals the red cross and white Lilith
    # without turning the chamber into a uniformly lit orange room.
    for x in range(0, 61, 6):
        for y in (-603, -591, -579, -567, -555, -543):
            for z in (276, 316):
                put(desired, x, y, z, INVISIBLE_LIGHT,
                    "terminal dogma controlled scene lighting")

    # S22 structural witnesses.  Runtime code recognises this dedicated
    # revision and will no longer regenerate the legacy flooded chamber.
    put(desired, 64, -569, 304, "minecraft:netherite_block",
        "S22 terminal dogma revision marker")
    put(desired, 63, -569, 304, "minecraft:magenta_concrete",
        "S22 terminal dogma revision marker")
    put(desired, 65, -569, 304, "minecraft:lodestone",
        "S22 terminal dogma revision marker")
    put(desired, 30, -567, 330, "minecraft:lodestone",
        "terminal dogma observation datum")
    put(desired, 30, -602, 296, LCL,
        "terminal dogma bounded LCL audit datum")
    put(desired, 30, -574, 268, RED,
        "terminal dogma crucifix audit datum")

    changes: list[Change] = []
    collisions = []
    allowed = OLD_OWNED | {
        "minecraft:air", "minecraft:void_air", "minecraft:cave_air",
        "minecraft:stone", "minecraft:deepslate",
    }
    for position, (after, reason) in sorted(desired.items(),
                                             key=lambda item: item[0][1]):
        before = world.get(position, AIR)
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after,
                              "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:16])
        raise RuntimeError(
            f"collides with {len(collisions)} protected cells: {sample}")
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_TERMINAL_DOGMA_R01_{stamp}"
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
        raise RuntimeError(f"read-back failed for {len(failures)} cells")
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
    report = {
        "packet": PACKET,
        "writes": len(changes),
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes),
            min(c.z for c in changes), max(c.x for c in changes),
            max(c.y for c in changes), max(c.z for c in changes),
        ],
        "parts": dict(sorted(parts.items())),
    }
    print(json.dumps(report, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
