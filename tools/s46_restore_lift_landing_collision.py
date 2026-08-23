#!/usr/bin/env python3
"""Remove the broken barrier takeover from the exact R28 lift door planes."""

from __future__ import annotations

import argparse
from collections import defaultdict
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
PACKET = "S46-RESTORE-LIFT-LANDING-COLLISION-R01"

# centre x/y/z, exit; only exact generated door planes are touched.
LANDINGS = [
    (12, -566, 253, "south"), (12, -448, 253, "south"),
    (12, -423, 253, "south"), (12, -419, 253, "south"),
    (12, -409, 253, "south"),
    (94, -418, 241, "west"), (94, -394, 241, "north"),
    (93, -442, 204, "south"), (93, -394, 204, "south"),
    (93, -370, 204, "north"),
    (130, -442, 273, "west"), (130, 81, 273, "west"),
    (28, -388, 321, "north"), (28, -340, 321, "north"),
]

DIRECTIONS = {
    "north": (0, -1), "south": (0, 1),
    "west": (-1, 0), "east": (1, 0),
}


def positions() -> dict[tuple[int, int, int], str]:
    result: dict[tuple[int, int, int], str] = {}
    for cx, cy, cz, exit_name in LANDINGS:
        dx, dz = DIRECTIONS[exit_name]
        # Clockwise lateral vector in Minecraft's horizontal plane.
        lx, lz = -dz, dx
        state = ("projectseele:clear_glass"
                 if cx == 93 and cz == 204 and cy in (-442, -370)
                 else "minecraft:gray_stained_glass")
        px, pz = cx + dx * 4, cz + dz * 4
        for side in range(-2, 3):
            for dy in range(3):
                result[(px + lx * side, cy + dy, pz + lz * side)] = state
    return result


def plan(world: Path) -> list[Change]:
    expected = positions()
    lo = tuple(min(p[index] for p in expected) for index in range(3))
    hi = tuple(max(p[index] for p in expected) for index in range(3))
    cells = read_box(world, DIMENSION, lo, hi, None)
    return [Change(
        PACKET, *pos, cells.get(pos, "minecraft:air"), after,
        "lift_sliding_door_repair",
        "restore_legacy_lift_collision_owner")
        for pos, after in sorted(expected.items())
        if cells.get(pos, "minecraft:air") == "minecraft:barrier"]


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s46_restore_lift_collision_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    root = dimension_dir(world, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)
    regions = []
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
        regions.append({
            "region": path.name,
            "beforeSha256": hashlib.sha256(before).hexdigest(),
            "afterSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    (artifact / "receipt.json").write_text(json.dumps({
        "schema": 1, "packet": PACKET, "world": str(world),
        "restoredBarrierCells": len(changes), "regions": regions,
    }, indent=2) + "\n", encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = args.world.resolve()
    changes = plan(world)
    result = {"packet": PACKET, "world": str(world),
              "restoredBarrierCells": len(changes)}
    if args.apply:
        result.update(applied=True, artifact=str(apply(world, changes)))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
