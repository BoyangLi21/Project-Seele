#!/usr/bin/env python3
"""Restore cross-route cells accidentally removed by S27/S28 lift moves.

Only cells whose current state still equals the recorded deleted state qualify.
Both sides of the retired strip must currently be non-air at the same y/z,
which proves an orthogonal floor/roof/wall continues through the deletion.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import shutil
import time

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import AIR, dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S30-RESTORE-LAUNCH-FLOOR-CROSS-ROUTES-R01"
AIR_STATE = "minecraft:air"
SOURCES = (
    (ROOT / "artifacts/s27_hangar_lift_20260818_234827/block_diff.csv",
     {"retire_old_compact_cage_branch",
      "retire_old_compact_cage_shaft"}, 103, 113),
    (ROOT / "artifacts/s28_glass_lift_x93_20260819_152052/block_diff.csv",
     {"retire_old_branch_west_strip",
      "retire_old_shaft_west_strip"}, 84, 89),
)


def add(changes: dict[tuple[int, int, int], Change], cells: dict,
        pos: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(pos, AIR_STATE)
    if before != after:
        changes[pos] = Change(PACKET, *pos, before, after,
                              "measured_cross_route_restoration", reason)


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (80, -444, 185), (116, -363, 273), None)
    changes: dict[tuple[int, int, int], Change] = {}
    for path, reasons, west_x, east_x in SOURCES:
        with path.open("r", encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["reason"] not in reasons:
                    continue
                pos = (int(row["x"]), int(row["y"]), int(row["z"]))
                before = row["before"]
                after = row["after"]
                if before in AIR or after not in AIR:
                    continue
                if cells.get(pos, AIR_STATE) != after:
                    continue
                west = cells.get((west_x, pos[1], pos[2]), AIR_STATE)
                east = cells.get((east_x, pos[1], pos[2]), AIR_STATE)
                if west in AIR or east in AIR:
                    continue
                add(changes, cells, pos, before,
                    "restore_measured_launch_floor_or_pyramid_crossing")
    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s30_cross_routes_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    root = dimension_dir(world, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)
    originals: dict[Path, bytes] = {}
    replaced: list[Path] = []
    try:
        for (rx, rz), selected in sorted(by_region.items()):
            path = region_path(root, rx, rz)
            before = path.read_bytes()
            shutil.copy2(path, backup / path.name)
            originals[path] = before
            grouped: dict[tuple[int, int], list[Change]] = defaultdict(list)
            for change in selected:
                grouped[(change.x >> 4, change.z >> 4)].append(change)
            atomic_replace(path, rewrite_region(path, grouped))
            replaced.append(path)
    except Exception:
        for path in replaced:
            atomic_replace(path, originals[path])
        raise
    with (artifact / "block_diff.csv").open(
            "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x", "y", "z", "before", "after", "reason"))
        for change in changes:
            writer.writerow((change.x, change.y, change.z, change.before,
                             change.after, change.reason))
    receipt = {
        "status": "APPLIED_WITH_EXACT_REGION_BACKUP",
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "states": dict(sorted(Counter(c.after for c in changes).items())),
        "zBands": dict(sorted(Counter(str(c.z) for c in changes).items(),
                              key=lambda item: int(item[0]))),
        "regionBeforeSha256": {
            path.name: hashlib.sha256(data).hexdigest()
            for path, data in originals.items()
        },
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
    changes = plan(world)
    print(json.dumps({
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "states": dict(sorted(Counter(c.after for c in changes).items())),
        "zBands": dict(sorted(Counter(str(c.z) for c in changes).items(),
                              key=lambda item: int(item[0]))),
    }, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
