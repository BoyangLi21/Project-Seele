#!/usr/bin/env python3
"""Build the TV-era nine-block ceiling-city service lattice in S22.

The production GeoFront section and period terminology describe a broad flat
roof carrying nine Tokyo-3 accommodation blocks.  This packet adds only their
underside structural grid and inspection lighting.  The interiors of all nine
cells stay open, so generated and imported Tokyo-3 buildings retain their full
vertical travel shafts.  The three EVA launch shafts are also outside every
beam line.  No existing non-air voxel is replaced.
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
PACKET = "S22-TV-CEILING-CITY-NINE-BLOCK-LATTICE-R01"

# Three 120x120 accommodation blocks per axis.  Boundaries lie between the
# 40-block Tokyo-3 tower grid, rather than across a moving building centre.
GRID_X = (-150, -30, 90, 210)
GRID_Z = (40, 160, 280, 400)
BBOX = ((-156, 20, 34), (216, 53, 406))

AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
BEAM = "minecraft:deepslate_tiles"
EDGE = "minecraft:polished_blackstone"
PANEL = "minecraft:black_concrete"
ORANGE = "minecraft:orange_concrete"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if not (BBOX[0][0] <= x <= BBOX[1][0]
            and BBOX[0][1] <= y <= BBOX[1][1]
            and BBOX[0][2] <= z <= BBOX[1][2]):
        raise RuntimeError(f"left ceiling-city envelope at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def near_launch_shaft(x: int, z: int) -> bool:
    # S22 physical launch shafts: centres x=-12,30,72 and z=220, outer radius
    # 17.  Preserve two extra blocks for service shape updates.
    return z in range(201, 240) and any(abs(x - cx) <= 19 for cx in (-12, 30, 72))


def beam_top(world, x: int, z: int) -> int:
    """Return the air cell immediately below the measured roof underside.

    The central ceiling-city wells are intentionally open in S22; those use
    the flat production datum y=51.  Everywhere else the beam follows the
    first real roof voxel rather than cutting into it.
    """
    for y in range(42, 54):
        if bare(world.get((x, y, z), "minecraft:air")) not in AIR:
            return y - 1
    return 51


def design(world: dict[tuple[int, int, int], str]):
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Four north-south and four east-west mega-beams divide the roof into the
    # nine canonical accommodation blocks.  A five-wide lower flange makes
    # the scale readable from the park floor 500 blocks below.
    for gx in GRID_X:
        for x in range(gx - 2, gx + 3):
            for z in range(GRID_Z[0], GRID_Z[-1] + 1):
                if near_launch_shaft(x, z):
                    continue
                top = beam_top(world, x, z)
                for y in range(top - 3, top + 1):
                    edge = x in (gx - 2, gx + 2) or y in (top - 3, top)
                    state = EDGE if edge else BEAM
                    if y == top - 3 and x == gx and (z - GRID_Z[0]) % 16 == 0:
                        state = LIGHT
                    put(desired, x, y, z, state,
                        "ceiling-city north-south mega-beam")

    for gz in GRID_Z:
        for z in range(gz - 2, gz + 3):
            for x in range(GRID_X[0], GRID_X[-1] + 1):
                if near_launch_shaft(x, z):
                    continue
                top = beam_top(world, x, z)
                for y in range(top - 3, top + 1):
                    edge = z in (gz - 2, gz + 2) or y in (top - 3, top)
                    state = EDGE if edge else BEAM
                    if y == top - 3 and z == gz and (x - GRID_X[0]) % 16 == 0:
                        state = LIGHT
                    put(desired, x, y, z, state,
                        "ceiling-city east-west mega-beam")

    # Nine cells receive only shallow edge reflectors; their central 104x104
    # area remains completely open for the actual descending city blocks.
    for ix in range(3):
        for iz in range(3):
            x0, x1 = GRID_X[ix], GRID_X[ix + 1]
            z0, z1 = GRID_Z[iz], GRID_Z[iz + 1]
            block_id = iz * 3 + ix + 1
            for x in range(x0 + 7, x1 - 6):
                for z in list(range(z0 + 7, z0 + 11)) + list(range(z1 - 10, z1 - 6)):
                    if near_launch_shaft(x, z):
                        continue
                    state = LIGHT if (x - x0) % 18 == 0 else GLASS
                    put(desired, x, beam_top(world, x, z) - 2, z, state,
                        f"ceiling accommodation block {block_id} reflector")
            for z in range(z0 + 11, z1 - 10):
                for x in list(range(x0 + 7, x0 + 11)) + list(range(x1 - 10, x1 - 6)):
                    if near_launch_shaft(x, z):
                        continue
                    state = LIGHT if (z - z0) % 18 == 0 else GLASS
                    put(desired, x, beam_top(world, x, z) - 2, z, state,
                        f"ceiling accommodation block {block_id} reflector")

            # Compact identity bars at the northwest edge, visible from below
            # without inventing signage or filling the moving block volume.
            for n in range(block_id):
                for x in range(x0 + 14 + n * 3, x0 + 16 + n * 3):
                    for z in range(z0 + 14, z0 + 20):
                        put(desired, x, beam_top(world, x, z) - 4, z, ORANGE,
                            f"ceiling accommodation block {block_id} datum")

    # Intersection nodes hang below the lattice as service hubs.  They are
    # not columns to the floor and therefore do not recreate the retired
    # random stone pillars.
    for gx in GRID_X:
        for gz in GRID_Z:
            for x in range(gx - 5, gx + 6):
                for z in range(gz - 5, gz + 6):
                    if near_launch_shaft(x, z):
                        continue
                    ring = max(abs(x - gx), abs(z - gz)) >= 4
                    put(desired, x, beam_top(world, x, z) - 4, z,
                        EDGE if ring else PANEL,
                        "ceiling-city interchange node")
            for x, z in ((gx - 4, gz - 4), (gx - 4, gz + 4),
                         (gx + 4, gz - 4), (gx + 4, gz + 4)):
                top = beam_top(world, x, z) - 4
                for y in range(top - 7, top):
                    put(desired, x, y, z,
                        LIGHT if y == top - 7 else BEAM,
                        "ceiling-city short suspension pylon")

    changes: list[Change] = []
    protected = []
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in AIR:
            protected.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    return changes, protected


def apply(changes: list[Change], protected: list[tuple]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_CEILING_CITY_{stamp}"
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
        "protectedExistingCellsSkipped": len(protected),
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes, protected = design(world)
    parts = defaultdict(int)
    for change in changes:
        parts[change.reason] += 1
    report = {
        "packet": PACKET,
        "writes": len(changes),
        "protectedExistingCellsSkipped": len(protected),
        "protectedSamples": [[list(pos), state] for pos, state in protected[:16]],
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes),
            max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes),
        ],
        "parts": dict(sorted(parts.items())),
    }
    print(json.dumps(report, indent=2))
    if args.apply:
        print(f"backup={apply(changes, protected)}")


if __name__ == "__main__":
    main()
