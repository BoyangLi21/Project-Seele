#!/usr/bin/env python3
"""Refine S22's west GeoFront landscape without touching reviewed facilities.

The first lakeshore packet used a nearly linear height field and therefore
read as parallel Minecraft terraces.  This packet replaces only natural
terrain and the packet's own spruce trees with an asymmetric lake bank made
from broad hills, shallow swales and deterministic small-scale relief.  Every
engineered block wins, the EVA apron is excluded, and x >= -64 remains frozen.
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
PACKET = "S22-CANONICAL-GEOFRONT-WEST-LANDSCAPE-R02"
BBOX = ((-152, -470, 122), (-65, -426, 238))
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:water", "minecraft:sand", "minecraft:gravel", "minecraft:clay",
    "minecraft:dirt", "minecraft:grass_block", "minecraft:stone",
    "minecraft:deepslate", "minecraft:snow", "minecraft:snow_block",
    "minecraft:tall_grass", "minecraft:short_grass", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp", "minecraft:kelp_plant",
}
OWN_TREES = {"minecraft:spruce_log", "minecraft:spruce_leaves"}
DEEPSLATE = "minecraft:deepslate"
DIRT = "minecraft:dirt"
GRASS = "minecraft:grass_block[snowy=false]"
SAND = "minecraft:sand"
CLAY = "minecraft:clay"
TRUNK = "minecraft:spruce_log[axis=y]"
LEAVES = "minecraft:spruce_leaves[distance=1,persistent=true,waterlogged=false]"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def hash_noise(x: int, z: int) -> float:
    """Stable value in [-1, 1], independent of Python's randomized hash."""
    value = (x * 0x1F123BB5) ^ (z * 0x5F356495) ^ 0x2C1B3C6D
    value = (value ^ (value >> 16)) * 0x45D9F3B
    value = (value ^ (value >> 16)) & 0xFFFFFFFF
    return (value / 0x7FFFFFFF) - 1.0


def gaussian(x: int, z: int, cx: float, cz: float, sx: float, sz: float) -> float:
    return math.exp(-(((x - cx) / sx) ** 2 + ((z - cz) / sz) ** 2))


def west_edge(z: int) -> int:
    progress = (z - 122) / 116.0
    return -147 + round(20.0 * progress + 5.0 * math.sin(z / 15.0))


def target_top(x: int, z: int) -> int:
    west = west_edge(z)
    span = max(1, -65 - west)
    t = max(0.0, min(1.0, (x - west) / span))
    smooth = t * t * (3.0 - 2.0 * t)
    height = -462.0 + 13.0 * smooth
    height += 7.0 * gaussian(x, z, -84, 184, 22, 34)
    height += 4.5 * gaussian(x, z, -119, 220, 25, 28)
    height += 3.0 * gaussian(x, z, -91, 139, 20, 22)
    height -= 4.0 * gaussian(x, z, -105, 167, 17, 24)
    height += 1.3 * math.sin((x + 2.3 * z) / 17.0)
    height += 0.8 * math.sin((2.1 * x - z) / 11.0)
    height += 0.9 * hash_noise(x // 3, z // 3)
    # The ceremonial gate forecourt must meet the existing y=-444 terrace.
    if x >= -82 and 194 <= z <= 226:
        blend = min(1.0, (x + 82) / 12.0)
        height = height * (1.0 - blend) + (-445.0) * blend
    return min(-444, max(-462, round(height)))


def in_eva_apron(x: int, z: int) -> bool:
    return -180 <= x <= -96 and 124 <= z <= 178


def route_clearance(x: int, z: int) -> bool:
    if 118 <= z <= 152 and x <= -98:
        return True
    if -108 <= x <= -92 and 118 <= z <= 214:
        return True
    if -102 <= x <= -63 and 204 <= z <= 216:
        return True
    return False


def set_desired(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if x >= -64:
        raise RuntimeError(f"crossed frozen HQ boundary at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def add_tree(desired, world, x: int, z: int, height: int) -> None:
    base = target_top(x, z) + 1
    if route_clearance(x, z) or in_eva_apron(x, z):
        return
    for y in range(base, base + height):
        if bare(world.get((x, y, z), "minecraft:air")) in AIR | NATURAL | OWN_TREES:
            set_desired(desired, x, y, z, TRUNK, "asymmetric GeoFront forest")
    crown = base + height - 2
    for dy, radius in ((-1, 2), (0, 3), (1, 2), (2, 1)):
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                if abs(dx) + abs(dz) > radius + 1 or (dx == 0 and dz == 0):
                    continue
                pos = (x + dx, crown + dy, z + dz)
                if bare(world.get(pos, "minecraft:air")) in AIR | NATURAL | OWN_TREES:
                    set_desired(desired, *pos, LEAVES, "asymmetric GeoFront forest canopy")


def design(world: dict[tuple[int, int, int], str]) -> tuple[list[Change], int]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    preserved = 0

    # Remove only the first packet's natural field and trees, then rebuild the
    # same columns with irregular relief.  Engineered routes and HQ cells are
    # never cleared or replaced.
    for z in range(122, 239):
        west = west_edge(z)
        for x in range(west, -64):
            if in_eva_apron(x, z) or route_clearance(x, z):
                continue
            top = target_top(x, z)
            for y in range(-469, -425):
                before = world.get((x, y, z), "minecraft:air")
                material = bare(before)
                if y <= top:
                    depth = top - y
                    if depth == 0:
                        state = SAND if x - west <= 2 else GRASS
                    elif depth <= 3:
                        state = CLAY if x - west <= 2 else DIRT
                    else:
                        state = DEEPSLATE
                    set_desired(desired, x, y, z, state, "irregular canonical lake bank")
                elif material in NATURAL | OWN_TREES:
                    set_desired(desired, x, y, z, "minecraft:air", "remove linear terrace relief")

    trees = [
        (-137, 186, 8), (-128, 205, 9), (-122, 229, 8),
        (-113, 193, 10), (-102, 225, 8), (-91, 184, 9),
        (-79, 154, 8), (-75, 178, 10), (-84, 232, 8),
        (-69, 134, 7), (-130, 157, 7), (-96, 145, 8),
    ]
    for x, z, height in trees:
        add_tree(desired, world, x, z, height)

    changes: list[Change] = []
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        allowed = AIR | NATURAL | OWN_TREES
        if bare(before) not in allowed:
            preserved += 1
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    return changes, preserved


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_WEST_LANDSCAPE_{stamp}"
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
        "writes": len(changes), "frozenHqBoundary": "x >= -64 untouched",
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes, preserved = design(world)
    print(json.dumps({
        "packet": PACKET, "writes": len(changes),
        "preservedEngineeredCells": preserved,
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes),
            max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes),
        ],
    }, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
