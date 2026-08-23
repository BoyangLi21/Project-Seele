#!/usr/bin/env python3
"""Reshape the already-loaded S22 lake into the canonical irregular lake.

Future GeoFront chunks use this same shoreline equation.  This backfill acts
only on natural columns; any column containing authored infrastructure is
frozen in full so the terminal, bridge, piers, arrival road and EVA gantry are
not eroded by a cell-by-cell collision policy.
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
PACKET = "S22-CANONICAL-UNDERGROUND-LAKE-R01"
BBOX = ((-520, -478, -96), (-118, -426, 318))
CENTRE_X = 30
CENTRE_Z = 296
WATER_Y = -462
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:water", "minecraft:sand",
    "minecraft:gravel", "minecraft:clay", "minecraft:snow",
    "minecraft:snow_block", "minecraft:short_grass", "minecraft:tall_grass",
    "minecraft:oak_log", "minecraft:oak_leaves",
    "minecraft:spruce_log", "minecraft:spruce_leaves",
    "minecraft:seagrass", "minecraft:tall_seagrass", "minecraft:kelp",
    "minecraft:kelp_plant", "minecraft:sculk", "minecraft:sculk_vein",
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def shoreline_value(x: int, z: int) -> float:
    # Exact world-space form of GeoFrontBoundedChunkGenerator.canonicalLake.
    relative_x = x - CENTRE_X
    relative_z = z - CENTRE_Z
    dx = (relative_x + 310.0) / 320.0
    dz = (relative_z + 200.0) / 210.0
    return (dx * dx + dz * dz
            + 0.10 * math.sin((relative_x + relative_z) / 41.0)
            + 0.07 * math.cos((relative_x - relative_z) / 53.0))


def rolling_ground(x: int, z: int) -> int:
    rx = x - CENTRE_X
    rz = z - CENTRE_Z
    rolling = (5.0 * math.sin(rx / 173.0)
               + 4.0 * math.cos(rz / 211.0)
               + 3.0 * math.sin((rx + rz) / 97.0))
    return -466 + round(rolling)


def authored_column(world, x: int, z: int) -> bool:
    for y in range(BBOX[0][1], BBOX[1][1] + 1):
        state = bare(world.get((x, y, z), "minecraft:air"))
        if state not in AIR and state not in NATURAL:
            return True
    return False


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    desired[(x, y, z)] = (state, reason)


def reshape_column(desired, world, x: int, z: int) -> None:
    shore = shoreline_value(x, z)
    if shore < 1.0:
        # Deepest near the broad centre, shallower at the irregular edge.
        depth = 3 + round(max(0.0, 1.0 - shore) * 7.0)
        floor = WATER_Y - depth
        for y in range(-477, floor):
            if bare(world.get((x, y, z), "minecraft:air")) in AIR:
                put(desired, x, y, z, "minecraft:deepslate",
                    "underground lake load-bearing basin")
        for y in range(floor - 2, floor + 1):
            put(desired, x, y, z,
                "minecraft:clay" if (x * 7 + z * 11) % 17 == 0 else "minecraft:sand",
                "underground lake natural bed")
        for y in range(floor + 1, WATER_Y + 1):
            put(desired, x, y, z, "minecraft:water",
                "underground lake water body")
        for y in range(WATER_Y + 1, BBOX[1][1] + 1):
            if bare(world.get((x, y, z), "minecraft:air")) in NATURAL:
                put(desired, x, y, z, "minecraft:air",
                    "underground lake clear water headroom")
        return

    ground = rolling_ground(x, z)
    beach = shore < 1.14
    top = "minecraft:sand" if beach else "minecraft:grass_block"
    under = "minecraft:sand" if beach else "minecraft:dirt"
    for y in range(-474, ground - 3):
        if bare(world.get((x, y, z), "minecraft:air")) in AIR:
            put(desired, x, y, z, "minecraft:deepslate",
                "lake shore load-bearing terrain")
    for y in range(ground - 3, ground):
        put(desired, x, y, z, under, "lake shore soil")
    put(desired, x, ground, z, top, "irregular underground lake shore")
    for y in range(ground + 1, BBOX[1][1] + 1):
        if bare(world.get((x, y, z), "minecraft:air")) in NATURAL:
            put(desired, x, y, z, "minecraft:air", "clear retired rectangular lake")


def design(world: dict[tuple[int, int, int], str]):
    loaded_chunks = {(x >> 4, z >> 4) for x, _y, z in world}
    frozen = {
        (x, z)
        for x in range(BBOX[0][0], BBOX[1][0] + 1)
        for z in range(BBOX[0][2], BBOX[1][2] + 1)
        if (x >> 4, z >> 4) in loaded_chunks
        if authored_column(world, x, z)
    }
    desired = {}
    for x in range(BBOX[0][0], BBOX[1][0] + 1):
        for z in range(BBOX[0][2], BBOX[1][2] + 1):
            if ((x >> 4, z >> 4) in loaded_chunks
                    and (x, z) not in frozen):
                reshape_column(desired, world, x, z)

    changes = []
    collisions = []
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in AIR and bare(before) not in NATURAL:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    return changes, collisions, frozen, loaded_chunks


def apply(changes: list[Change], collisions: list[tuple]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_CANONICAL_LAKE_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))
    lo = (min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes))
    hi = (max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [c for c in changes if actual.get((c.x, c.y, c.z), "minecraft:air") != c.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED", "packet": PACKET,
        "writes": len(changes), "protectedCollisionsSkipped": len(collisions),
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes, collisions, frozen, loaded_chunks = design(world)
    reasons = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    print(json.dumps({
        "packet": PACKET, "writes": len(changes),
        "frozenAuthoredColumns": len(frozen),
        "loadedChunksBackfilled": len(loaded_chunks),
        "protectedCollisionsSkipped": len(collisions),
        "collisionSamples": [[list(pos), state] for pos, state in collisions[:20]],
        "bounds": [min(c.x for c in changes), min(c.y for c in changes),
                   min(c.z for c in changes), max(c.x for c in changes),
                   max(c.y for c in changes), max(c.z for c in changes)],
        "parts": dict(sorted(reasons.items())),
    }, indent=2))
    if args.apply:
        print(f"backup={apply(changes, collisions)}")


if __name__ == "__main__":
    main()
