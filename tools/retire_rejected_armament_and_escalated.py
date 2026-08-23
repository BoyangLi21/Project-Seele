#!/usr/bin/env python3
"""Remove the rejected armament tower and Escalated motor from R28.

The surface tower volume is restored voxel-for-voxel from the user's clean
Tokyo-3 reference.  The lone Escalated transit motor is restored to the
measured reinforced-deepslate row surrounding it.  No other coordinates are
touched; every affected region is copied before an atomic rewrite.
"""

from __future__ import annotations

from collections import defaultdict
import csv
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box

WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
REFERENCE = ROOT / "run/saves/SEELE_TOKYO3_REBUILT"
DIMENSION = "projectseele:geofront"
PACKET = "RETIRE-REJECTED-ARMAMENT-ESCALATED-R01"
LO = (14, 48, 286)
HI = (46, 112, 314)


def plan() -> list[Change]:
    current = read_box(WORLD, DIMENSION, LO, HI)
    clean = read_box(REFERENCE, DIMENSION, LO, HI)
    changes: list[Change] = []
    for position in sorted(set(current) | set(clean)):
        before = current.get(position, "minecraft:air")
        after = clean.get(position, "minecraft:air")
        if before != after:
            changes.append(Change(PACKET, *position, before, after,
                                  "exact_reference_restore",
                                  "retire_rejected_surface_armament_tower"))

    motor = (80, -443, 270)
    motor_before = read_box(WORLD, DIMENSION, motor, motor).get(
        motor, "minecraft:air")
    if motor_before.startswith("create:creative_motor"):
        changes.append(Change(PACKET, *motor, motor_before,
                              "minecraft:reinforced_deepslate",
                              "measured_row_restore",
                              "retire_escalated_transit_motor"))
    return sorted(changes, key=lambda change: (change.y, change.z, change.x))


def apply(changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"retired_armament_escalated_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True)
    region_dir = dimension_dir(WORLD, DIMENSION) / "region"
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)

    originals: dict[Path, bytes] = {}
    changed_paths: list[Path] = []
    try:
        for (rx, rz), chunk_changes in sorted(by_region.items()):
            path = region_dir / f"r.{rx}.{rz}.mca"
            originals[path] = path.read_bytes()
            shutil.copy2(path, backup / path.name)
            touched = {(c.x, c.y, c.z)
                       for values in chunk_changes.values() for c in values}
            atomic_replace(path, rewrite_region(
                path, chunk_changes, removable_block_entities=touched))
            changed_paths.append(path)
        actual = read_box(WORLD, DIMENSION, LO, HI)
        motor = (80, -443, 270)
        actual.update(read_box(WORLD, DIMENSION, motor, motor))
        failed = [change for change in changes
                  if actual.get((change.x, change.y, change.z), "minecraft:air")
                  != change.after]
        if failed:
            sample = failed[0]
            observed = actual.get((sample.x, sample.y, sample.z),
                                  "minecraft:air")
            raise RuntimeError(
                f"read-back failed for {len(failed)} cells; first="
                f"{(sample.x, sample.y, sample.z)} expected={sample.after} "
                f"actual={observed}")
    except Exception:
        for path in changed_paths:
            atomic_replace(path, originals[path])
        raise

    with (artifact / "block_diff.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x", "y", "z", "before", "after", "reason"))
        for change in changes:
            writer.writerow((change.x, change.y, change.z, change.before,
                             change.after, change.reason))
    receipt = {
        "status": "APPLIED_AND_EXACT_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "surface_box": [LO, HI],
        "world": str(WORLD),
    }
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return artifact


if __name__ == "__main__":
    planned = plan()
    print(f"planned={len(planned)}")
    print(apply(planned))
