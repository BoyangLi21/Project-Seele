#!/usr/bin/env python3
"""Restore the original spruce shaft door at 24,-418,254."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import shutil
import time

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S43-RESTORE-ORIGINAL-SHAFT-DOOR-R01"
S41 = ROOT / "artifacts/s41_command_sliding_doors_20260821_211108"
S42 = ROOT / "artifacts/s42_sliding_door_buttons_20260821_212606"
MARKER = ".projectseele_command_sliding_doors_r01.json"


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def plan(world: Path) -> tuple[list[Change], dict]:
    receipt41 = json.loads((S41 / "receipt.json").read_text(encoding="utf-8"))
    receipt42 = json.loads((S42 / "receipt.json").read_text(encoding="utf-8"))
    door41 = next(door for door in receipt41["doors"] if door["id"] == 14)
    door42 = next(door for door in receipt42["doors"] if door["id"] == 14)

    s41_positions = {tuple(pos) for pos in door41["aperture"]}
    x, y, z = door41["lower"]
    s41_positions.update((x, y + 2, z + offset) for offset in (-1, 0, 1))
    s41_positions.update(tuple(pos) for pos in door41["buttons"])
    s42_positions = set()
    for button in door42["buttons"]:
        bx, by, bz = button
        s42_positions.add((bx, by, bz))
        s42_positions.add((x, by, bz))

    final = {}
    for row in csv_rows(S42 / "block_diff.csv"):
        pos = (int(row["x"]), int(row["y"]), int(row["z"]))
        if pos in s42_positions:
            final[pos] = row["before"]
    for row in csv_rows(S41 / "block_diff.csv"):
        pos = (int(row["x"]), int(row["y"]), int(row["z"]))
        if pos in s41_positions:
            final[pos] = row["before"]
    expected = s41_positions | s42_positions
    if set(final) != expected:
        raise RuntimeError(f"incomplete layered preimage: missing={expected-set(final)}")

    lo = (min(p[0] for p in expected), min(p[1] for p in expected),
          min(p[2] for p in expected))
    hi = (max(p[0] for p in expected), max(p[1] for p in expected),
          max(p[2] for p in expected))
    cells = read_box(world, DIMENSION, lo, hi, None)
    changes = [Change(
        PACKET, *pos, cells.get(pos, "minecraft:air"), after,
        "human_authorized_command_sliding_doors",
        "restore_original_single_spruce_shaft_door")
        for pos, after in sorted(final.items())
        if cells.get(pos, "minecraft:air") != after]

    marker = json.loads((world / MARKER).read_text(encoding="utf-8"))
    marker["doors"] = [door for door in marker["doors"]
                       if int(door["id"]) != 14]
    marker["excludedOriginalDoors"] = [{
        "lower": [24, -418, 254],
        "reason": "human_requested_original_shaft_door",
    }]
    marker["packet"] = PACKET
    return changes, marker


def apply(world: Path, changes: list[Change], marker: dict) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s43_restore_shaft_door_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    root = dimension_dir(world, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)
    region_reports = []
    for (rx, rz), selected in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        before = path.read_bytes()
        shutil.copy2(path, backup / path.name)
        grouped: dict[tuple[int, int], list[Change]] = defaultdict(list)
        for change in selected:
            grouped[(change.x >> 4, change.z >> 4)].append(change)
        try:
            atomic_replace(path, rewrite_region(path, grouped))
        except Exception:
            atomic_replace(path, before)
            raise
        region_reports.append({
            "region": path.name,
            "beforeSha256": hashlib.sha256(before).hexdigest(),
            "afterSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    marker["artifact"] = str(artifact.resolve())
    (world / MARKER).write_text(
        json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": 1,
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "restoredDoor": [24, -418, 254],
        "activeSlidingDoors": len(marker["doors"]),
        "regions": region_reports,
    }
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = args.world.resolve()
    changes, marker = plan(world)
    print(json.dumps({
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "restoredDoor": [24, -418, 254],
        "activeSlidingDoors": len(marker["doors"]),
    }, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes, marker))},
                         indent=2))


if __name__ == "__main__":
    main()
