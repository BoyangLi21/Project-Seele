#!/usr/bin/env python3
"""Raise the three approved R28 wet-cage roofs by exactly ten blocks.

Only the measured 41x55 roof sheets, their four boundary walls, and the three
legacy closed gate interiors are touched.  Every changed region is copied
before atomic replacement and every voxel records its exact old state.
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
PACKET = "S25-HANGAR-ROOF-UP10-R01"
CENTRES = (-12, 30, 72)
Z0, Z1 = 133, 187
OLD_ROOF_Y, NEW_ROOF_Y = -373, -363
WALL_SOURCE_Y = -374
AIR_STATE = "minecraft:air"
ROOF_PALETTE = {"minecraft:reinforced_deepslate", "minecraft:sea_lantern"}


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def add(changes: dict[tuple[int, int, int], Change], cells: dict,
        pos: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(pos, AIR_STATE)
    if before == after:
        return
    changes[pos] = Change(PACKET, *pos, before, after,
                          "human_authorized_hangar_edit", reason)


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (-32, -445, Z0),
                     (92, NEW_ROOF_Y, Z1), None)
    changes: dict[tuple[int, int, int], Change] = {}
    for variant, cx in enumerate(CENTRES):
        # Destination must be genuinely empty; do not overwrite later human
        # work or another authored facility above the cage.
        occupied = []
        for x in range(cx - 20, cx + 21):
            for z in range(Z0, Z1 + 1):
                state = cells.get((x, NEW_ROOF_Y, z), AIR_STATE)
                if state not in AIR:
                    occupied.append((x, NEW_ROOF_Y, z, state))
        if occupied:
            raise RuntimeError(
                f"EVA-{variant:02d} roof destination occupied: {occupied[:8]}")

        for x in range(cx - 20, cx + 21):
            for z in range(Z0, Z1 + 1):
                source = cells.get((x, OLD_ROOF_Y, z), AIR_STATE)
                if source not in ROOF_PALETTE:
                    raise RuntimeError(
                        f"unexpected roof state EVA-{variant:02d} "
                        f"at {(x, OLD_ROOF_Y, z)}: {source}")
                add(changes, cells, (x, OLD_ROOF_Y, z), AIR_STATE,
                    f"eva{variant:02d}_clear_old_roof")
                add(changes, cells, (x, NEW_ROOF_Y, z), source,
                    f"eva{variant:02d}_move_roof_up_10")

        boundary = set()
        for z in range(Z0, Z1 + 1):
            boundary.add((cx - 20, z))
            boundary.add((cx + 20, z))
        for x in range(cx - 20, cx + 21):
            boundary.add((x, Z0))
            boundary.add((x, Z1))
        for x, z in sorted(boundary):
            wall = cells.get((x, WALL_SOURCE_Y, z), AIR_STATE)
            if wall in AIR:
                raise RuntimeError(
                    f"missing wall source EVA-{variant:02d} at "
                    f"{(x, WALL_SOURCE_Y, z)}")
            for y in range(OLD_ROOF_Y, NEW_ROOF_Y):
                add(changes, cells, (x, y, z), wall,
                    f"eva{variant:02d}_extend_boundary_to_new_roof")

        # Preserve the iron pressure frame.  Replace only visible interior
        # leaves with barrier collision; the new entity supplies animated
        # left/right armour and the split NERV emblem.
        gate_z = 187
        for dx in range(-16, 17):
            for y in range(-442, -377):
                pos = (cx + dx, y, gate_z)
                current = cells.get(pos, AIR_STATE)
                if current not in AIR and current != "minecraft:barrier":
                    add(changes, cells, pos, "minecraft:barrier",
                        f"eva{variant:02d}_invisible_gate_collision")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s25_hangar_roof_up10_{stamp}"
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
    summary = {
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "reasons": dict(sorted(Counter(c.reason for c in changes).items())),
    }
    print(json.dumps(summary, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
