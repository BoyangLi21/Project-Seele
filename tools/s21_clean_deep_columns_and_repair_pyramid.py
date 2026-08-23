#!/usr/bin/env python3
"""Remove measured deep GeoFront stone needles and repair crossed surfaces."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
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
from audit_geofront_cavern import scan
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIMENSION = "projectseele:geofront"
CSV = Path("artifacts/geofront_legacy_floor_columns_20260811.csv")
PACKET = "S21-CLEAN-DEEP-STONE-NEEDLES-AND-REPAIR-PYRAMID"

# Accepted R28 GeoFront origin and legacy pyramid envelope.
ORIGIN = (30, -444, 296)
SPHERE_CENTRE_XZ = (30, 220)
PYRAMID_BASE_Y = -22
PYRAMID_APEX_Y = 150
PYRAMID_BASE_HALF_X = 120
PYRAMID_BASE_HALF_Z = 120
PYRAMID_CENTRE_Z = 31


def java_int(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def java_round(value: float) -> int:
    return math.floor(value + 0.5)


def control_height(cell_x: int, cell_z: int) -> float:
    value = java_int(cell_x * 374761393 + cell_z * 668265263)
    value = java_int((value ^ ((value & 0xFFFFFFFF) >> 13))
                     * 1274126177)
    value = java_int(value ^ ((value & 0xFFFFFFFF) >> 16))
    return value % 2001 / 1000.0 - 1.0


def smooth_step(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def terrain_height(relative_x: int, relative_z: int) -> int:
    distance = int(math.sqrt(relative_x * relative_x
                             + relative_z * relative_z))
    if distance <= 170:
        return 0
    cell_x = math.floor(relative_x / 24)
    cell_z = math.floor(relative_z / 24)
    within_x = smooth_step((relative_x - cell_x * 24) / 24.0)
    within_z = smooth_step((relative_z - cell_z * 24) / 24.0)
    near = (control_height(cell_x, cell_z) * (1.0 - within_x)
            + control_height(cell_x + 1, cell_z) * within_x)
    far = (control_height(cell_x, cell_z + 1) * (1.0 - within_x)
           + control_height(cell_x + 1, cell_z + 1) * within_x)
    ramp = max(0.0, min(1.0, (distance - 170) / 40.0))
    return java_round((near * (1.0 - within_z) + far * within_z)
                      * 4.0 * ramp)


def stepped_half(relative_y: int) -> int:
    progress = max(0.0, min(
        1.0,
        (relative_y - PYRAMID_BASE_Y)
        / (PYRAMID_APEX_Y - PYRAMID_BASE_Y),
    ))
    return java_round(PYRAMID_BASE_HALF_X * (1.0 - progress))


def shell_material(relative_y: int) -> str:
    band = (relative_y - PYRAMID_BASE_Y) % 14
    if band <= 1:
        return "minecraft:orange_concrete"
    if relative_y > 72 and band <= 4:
        return "minecraft:smooth_quartz"
    return ("minecraft:black_concrete" if band % 4 <= 1
            else "minecraft:polished_blackstone")


def pyramid_expected(world_x: int, world_y: int, world_z: int) -> str | None:
    x = world_x - ORIGIN[0]
    y = world_y - ORIGIN[1]
    z = world_z - ORIGIN[2]
    if y == PYRAMID_BASE_Y:
        if (abs(x) <= PYRAMID_BASE_HALF_X
                and abs(z - PYRAMID_CENTRE_Z) <= PYRAMID_BASE_HALF_Z):
            return "minecraft:polished_deepslate"
        return None
    if y <= PYRAMID_BASE_Y or y > PYRAMID_APEX_Y:
        return None
    half = stepped_half(y)
    next_half = 0 if y == PYRAMID_APEX_Y else stepped_half(y + 1)
    centred_z = z - PYRAMID_CENTRE_Z
    if abs(x) > half or abs(centred_z) > half:
        return None
    if not (abs(x) >= next_half or abs(centred_z) >= next_half):
        return None
    if ((abs(x) == half and abs(centred_z) == half)
            or (x == 0 and abs(centred_z) == half)
            or (abs(x) == half and centred_z == 0)):
        return ("minecraft:orange_concrete"
                if x == 0 or centred_z == 0
                else "minecraft:black_concrete")
    return shell_material(y)


def terrain_expected(world_x: int, world_y: int, world_z: int) -> str | None:
    relative_x = world_x - SPHERE_CENTRE_XZ[0]
    relative_z = world_z - SPHERE_CENTRE_XZ[1]
    # The command-pyramid service island owns this complete footprint.
    pyramid_x = world_x - ORIGIN[0]
    pyramid_z = world_z - ORIGIN[2]
    if (abs(pyramid_x) <= PYRAMID_BASE_HALF_X + 14
            and PYRAMID_CENTRE_Z - PYRAMID_BASE_HALF_Z - 14
            <= pyramid_z
            <= PYRAMID_CENTRE_Z + PYRAMID_BASE_HALF_Z + 14):
        return None
    surface = ORIGIN[1] + terrain_height(relative_x, relative_z)
    if world_y == surface:
        return "minecraft:grass_block[snowy=false]"
    if world_y in (surface - 1, surface - 2):
        return "minecraft:dirt"
    low = min(ORIGIN[1] - 5, surface - 3)
    if low <= world_y <= surface - 3:
        return "minecraft:stone"
    return None


def load_changes(path: Path) -> list[Change]:
    changes: list[Change] = []
    with path.open(newline="", encoding="ascii") as stream:
        for row in csv.DictReader(stream):
            x, y, z = int(row["x"]), int(row["y"]), int(row["z"])
            after = pyramid_expected(x, y, z)
            reason = "repair crossed NERV pyramid shell"
            if after is None:
                after = terrain_expected(x, y, z)
                reason = ("restore authored four-layer terrain"
                          if after is not None
                          else "remove measured legacy deep stone needle")
            if after is None:
                after = "minecraft:air"
            if after == row["before"]:
                continue
            changes.append(Change(
                PACKET, x, y, z, row["before"], after, "replace", reason,
            ))
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("artifacts") / f"s21_deep_column_cleanup_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    for (region_x, region_z), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{region_x}.{region_z}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    report, _, remaining = scan(WORLD.resolve(), DIMENSION)
    if remaining:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(
            f"deep-column audit still found {len(remaining)} cells")

    receipt = {
        "status": "APPLIED_AND_FULL_RESCAN_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "air": sum(change.after == "minecraft:air" for change in changes),
        "terrainRepairs": sum("four-layer" in change.reason
                              for change in changes),
        "pyramidRepairs": sum("pyramid" in change.reason
                              for change in changes),
        "remainingLegacyFloorColumnVoxels":
            report["legacyFloorColumnVoxels"],
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
    changes = load_changes(CSV)
    print(json.dumps({
        "writes": len(changes),
        "air": sum(change.after == "minecraft:air" for change in changes),
        "terrainRepairs": sum("four-layer" in change.reason
                              for change in changes),
        "pyramidRepairs": sum("pyramid" in change.reason
                              for change in changes),
    }, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
