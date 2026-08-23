#!/usr/bin/env python3
"""Remove the three redundant Y=79 Tokyo-3 carrier slabs from R28."""

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
PACKET = "S48-REMOVE-REDUNDANT-SURFACE-CARRIER-Y79-R01"
CENTRES = (-12, 30, 72)
CENTRE_Z = 220
Y = 79
RADIUS = 14
EXPECTED = {
    "minecraft:light_gray_concrete",
    "minecraft:iron_block",
    "minecraft:lodestone",
}


def plan(world: Path) -> list[Change]:
    cells = read_box(
        world,
        DIMENSION,
        (CENTRES[0] - RADIUS, Y, CENTRE_Z - RADIUS),
        (CENTRES[-1] + RADIUS, Y, CENTRE_Z + RADIUS),
        None,
    )
    changes: list[Change] = []
    for centre_x in CENTRES:
        for x in range(centre_x - RADIUS, centre_x + RADIUS + 1):
            for z in range(CENTRE_Z - RADIUS, CENTRE_Z + RADIUS + 1):
                before = cells.get((x, Y, z), "minecraft:air")
                if before not in EXPECTED:
                    raise RuntimeError(
                        f"unexpected Y=79 hatch state at {(x, Y, z)}: {before}"
                    )
                changes.append(Change(
                    PACKET, x, Y, z, before, "minecraft:air",
                    "remove_redundant_surface_carrier_layer",
                    "retain_y80_animated_nerv_hatch_only",
                ))
    return sorted(changes, key=lambda change: (change.y, change.z, change.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s48_surface_carrier_y79_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    dimension = dimension_dir(world, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)

    originals: dict[Path, bytes] = {}
    replaced: list[Path] = []
    try:
        for (rx, rz), selected in sorted(by_region.items()):
            path = dimension / "region" / f"r.{rx}.{rz}.mca"
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
        "before": dict(sorted(Counter(c.before for c in changes).items())),
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
        "before": dict(sorted(Counter(c.before for c in changes).items())),
    }
    print(json.dumps(summary, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
