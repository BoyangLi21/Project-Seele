#!/usr/bin/env python3
"""Restore the three launch-well pylons and clarify existing carrier rails."""

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

from apply_s20_approved_semantic_repairs import (
    Change,
    atomic_replace,
    rewrite_region,
)
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIMENSION = "projectseele:geofront"
PACKET = "S21-RESTORE-LAUNCH-POWER-AND-HIGHLIGHT-CARRIER-RAILS"
CENTRES = (-12, 30, 72)
POWER = ((4, -442, 220), (46, -442, 220), (88, -442, 220))
RAIL_Y = -443
RAIL_Z_MIN = 133
RAIL_Z_MAX = 205


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    changes: list[Change] = []
    for x, y, z in POWER:
        before = world.get((x, y, z), "minecraft:air")
        if bare(before) == "projectseele:umbilical_pylon":
            continue
        if bare(before) != "minecraft:air":
            raise RuntimeError(
                f"launch pylon position {x},{y},{z} is {before}, expected air")
        changes.append(Change(
            PACKET, x, y, z, before, "projectseele:umbilical_pylon",
            "replace", "restore canonical launch-well external power",
        ))

    for centre_x in CENTRES:
        for rail_x in (centre_x - 5, centre_x + 5):
            for z in range(RAIL_Z_MIN, RAIL_Z_MAX + 1):
                position = (rail_x, RAIL_Y, z)
                before = world.get(position, "minecraft:air")
                if bare(before) != "minecraft:polished_basalt":
                    # A moving carrier or a human-authored edit owns this cell.
                    # It will receive the new rail pattern when the carrier
                    # next restores the floor; never overwrite it offline.
                    continue
                after = ("minecraft:sea_lantern"
                         if (z - 160) % 8 == 0
                         else "minecraft:iron_block")
                changes.append(Change(
                    PACKET, rail_x, RAIL_Y, z, before, after, "replace",
                    "high-contrast paired EVA carrier rail",
                ))
    return changes


def apply(world: dict[tuple[int, int, int], str],
          changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("artifacts") / f"s21_power_rails_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    before_hashes: dict[str, str] = {}
    for (region_x, region_z), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{region_x}.{region_z}.mca"
        before_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    lo = (min(change.x for change in changes),
          min(change.y for change in changes),
          min(change.z for change in changes))
    hi = (max(change.x for change in changes),
          max(change.y for change in changes),
          max(change.z for change in changes))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [change for change in changes
                if actual.get((change.x, change.y, change.z), "minecraft:air")
                != change.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")

    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "powerPylons": sum(1 for change in changes
                           if change.after == "projectseele:umbilical_pylon"),
        "railCells": sum(1 for change in changes
                         if change.reason.startswith("high-contrast")),
        "backup": str(backup.resolve()),
        "regionsBeforeSha256": before_hashes,
    }
    (backup / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION,
                     (min(CENTRES) - 6, RAIL_Y, RAIL_Z_MIN),
                     (max(CENTRES) + 16, -442, 220))
    changes = design(world)
    power = sum(1 for change in changes
                if change.after == "projectseele:umbilical_pylon")
    print(f"proposal writes={len(changes)} power={power} "
          f"rails={len(changes) - power}")
    if args.apply:
        print(f"backup={apply(world, changes)}")


if __name__ == "__main__":
    main()
