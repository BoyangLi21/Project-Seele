#!/usr/bin/env python3
"""Restore three opaque x93/z204 lift-shaft walls; retain x=89 glazing."""

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
from query_blocks import dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S29-X93-LIFT-THREE-OPAQUE-WALLS-R01"
AIR_STATE = "minecraft:air"
CX = 93


def add(changes: dict[tuple[int, int, int], Change], cells: dict,
        pos: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(pos, AIR_STATE)
    if before != after:
        changes[pos] = Change(PACKET, *pos, before, after,
                              "human_authorized_lift_wall_revision", reason)


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (89, -442, 200), (97, -364, 208), None)
    changes: dict[tuple[int, int, int], Change] = {}
    wall = "minecraft:reinforced_deepslate"
    glass = "projectseele:clear_glass"
    for y in range(-442, -363):
        # x=89 is the sole launch-plant observation wall.
        for z in range(200, 209):
            add(changes, cells, (89, y, z), glass,
                "retain_x89_launch_view_glass")
            add(changes, cells, (97, y, z), wall,
                "restore_east_opaque_wall")
        for x in range(90, 98):
            lower_door = -442 <= y <= -440 and 91 <= x <= 95
            upper_door = -370 <= y <= -368 and 91 <= x <= 95
            add(changes, cells, (x, y, 200),
                glass if upper_door else wall,
                "restore_north_wall_with_upper_door")
            add(changes, cells, (x, y, 208),
                glass if lower_door else wall,
                "restore_south_wall_with_lower_door")
    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s29_lift_walls_{stamp}"
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
        "reasons": dict(sorted(Counter(c.reason for c in changes).items())),
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
        "reasons": dict(sorted(Counter(c.reason for c in changes).items())),
    }, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
