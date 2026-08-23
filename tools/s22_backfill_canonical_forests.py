#!/usr/bin/env python3
"""Backfill the canonical r4 forest masses into already-generated S22 chunks.

The chunk generator plants these trees in future chunks.  S22's central six
region files predate r4, so this one-shot packet applies the same deterministic
rule only where an exposed natural grass column and a completely empty canopy
already exist.  Authored facilities and the command-room volume are therefore
never cleared or overwritten.
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

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from inspect_map_assets import decode_modern_section, iter_chunks, palette_state
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-CANONICAL-FOREST-BACKFILL-R01"
CENTRE = (30, 220)
BOUNDS = (-480, 480, -256, 760)
MIN_Y = -480
MAX_Y = -400
AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
TRUNK = "minecraft:oak_log[axis=y]"
LEAVES = "minecraft:oak_leaves[distance=1,persistent=true,waterlogged=false]"


def gaussian(x: int, z: int, cx: float, cz: float, radius: float) -> float:
    dx = x - cx
    dz = z - cz
    return math.exp(-(dx * dx + dz * dz) / (radius * radius))


def density(relative_x: int, relative_z: int) -> float:
    north_west = gaussian(relative_x, relative_z, -650.0, 330.0, 560.0)
    south = gaussian(relative_x, relative_z, -160.0, 760.0, 520.0)
    east = gaussian(relative_x, relative_z, 720.0, 180.0, 520.0)
    campus = gaussian(relative_x, relative_z, 0.0, 0.0, 300.0)
    return max(0.0, min(1.0, max(north_west, south, east) - campus * 0.92))


def signed64(value: int) -> int:
    value &= (1 << 64) - 1
    return value - (1 << 64) if value >= (1 << 63) else value


def mix_coordinates(x: int, z: int) -> int:
    value = signed64(x * 341873128712) ^ signed64(z * 132897987541)
    value &= (1 << 64) - 1
    value ^= value >> 33
    value = (value * 0xFF51AFD7ED558CCD) & ((1 << 64) - 1)
    value ^= value >> 33
    value = (value * 0xC4CEB9FE1A85EC53) & ((1 << 64) - 1)
    value ^= value >> 33
    return signed64(value)


def chunk_states(chunk) -> dict[int, tuple[list[str], np.ndarray]]:
    result = {}
    for section in chunk.get("sections", []):
        section_y = int(section.get("Y", 0))
        base_y = section_y * 16
        if base_y > MAX_Y + 16 or base_y + 15 < MIN_Y:
            continue
        palette, indices = decode_modern_section(section)
        if not palette:
            continue
        result[section_y] = ([palette_state(entry) for entry in palette], indices)
    return result


def state_at(sections, local_x: int, y: int, local_z: int) -> str:
    section = sections.get(y >> 4)
    if section is None:
        return "minecraft:air"
    names, indices = section
    offset = ((y & 15) << 8) | (local_z << 4) | local_x
    return names[int(indices[offset])]


def design() -> tuple[list[Change], dict[str, int]]:
    root = dimension_dir(WORLD, DIMENSION)
    chunk_bounds = (BOUNDS[0] >> 4, BOUNDS[1] >> 4,
                    BOUNDS[2] >> 4, BOUNDS[3] >> 4)
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    counters = defaultdict(int)

    for chunk_x, chunk_z, chunk in iter_chunks(root, chunk_bounds):
        sections = chunk_states(chunk)
        if not sections:
            continue
        base_x, base_z = chunk_x * 16, chunk_z * 16
        for local_z in range(2, 14):
            world_z = base_z + local_z
            if not BOUNDS[2] <= world_z <= BOUNDS[3]:
                continue
            for local_x in range(2, 14):
                world_x = base_x + local_x
                if not BOUNDS[0] <= world_x <= BOUNDS[1]:
                    continue
                relative_x = world_x - CENTRE[0]
                relative_z = world_z - CENTRE[1]
                forest_density = density(relative_x, relative_z)
                if forest_density <= 0.0:
                    continue
                hash_value = mix_coordinates(world_x, world_z)
                if hash_value % 1000 >= round(forest_density * 11.0):
                    continue

                terrain_top = None
                for y in range(MAX_Y, MIN_Y - 1, -1):
                    if state_at(sections, local_x, y, local_z).split("[", 1)[0] \
                            == "minecraft:grass_block":
                        terrain_top = y
                        break
                if terrain_top is None:
                    continue

                trunk_height = 6 + ((hash_value >> 10) % 4)
                targets: list[tuple[int, int, int, str]] = []
                for y in range(terrain_top + 1, terrain_top + trunk_height + 1):
                    targets.append((local_x, y, local_z, TRUNK))
                crown_y = terrain_top + trunk_height
                for dy in range(-2, 2):
                    radius = 1 if dy == 1 else 2
                    for ox in range(-radius, radius + 1):
                        for oz in range(-radius, radius + 1):
                            if abs(ox) == radius and abs(oz) == radius and dy != -1:
                                continue
                            targets.append((local_x + ox, crown_y + dy,
                                            local_z + oz, LEAVES))

                # Every target is inside this chunk by the 2-block margin.
                # Existing vegetation, fixtures, buildings or another chosen
                # tree make the candidate fail closed.
                blocked = False
                for tx, ty, tz, _ in targets:
                    world_pos = (base_x + tx, ty, base_z + tz)
                    if world_pos in desired or state_at(sections, tx, ty, tz) not in AIR:
                        blocked = True
                        break
                if blocked:
                    counters["blockedCandidates"] += 1
                    continue
                for tx, ty, tz, after in targets:
                    desired[(base_x + tx, ty, base_z + tz)] = (
                        after, "canonical asymmetric GeoFront forest")
                counters["trees"] += 1

    changes = [Change(PACKET, x, y, z, "minecraft:air", after,
                      "replace", reason)
               for (x, y, z), (after, reason) in sorted(desired.items())]
    counters["writes"] = len(changes)
    return changes, dict(counters)


def apply(changes: list[Change], counters: dict[str, int]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_FOREST_BACKFILL_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    lo = (min(c.x for c in changes), min(c.y for c in changes),
          min(c.z for c in changes))
    hi = (max(c.x for c in changes), max(c.y for c in changes),
          max(c.z for c in changes))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [c for c in changes
                if actual.get((c.x, c.y, c.z), "minecraft:air") != c.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "bounds": list(BOUNDS),
        "counters": counters,
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes, counters = design()
    print(json.dumps({"packet": PACKET, **counters}, indent=2))
    if args.apply and changes:
        print(f"backup={apply(changes, counters)}")


if __name__ == "__main__":
    main()
