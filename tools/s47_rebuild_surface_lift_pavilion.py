#!/usr/bin/env python3
"""Apply the approved R28 surface lift pavilion material and gate revision."""

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
PACKET = "S47-SURFACE-LIFT-PAVILION-R01"
LO = (114, 79, 265)
HI = (136, 89, 281)


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION, LO, HI, None)
    targets: dict[tuple[int, int, int], tuple[str, str]] = {}
    for pos, state in cells.items():
        if state.startswith("minecraft:gray_stained_glass"):
            targets[pos] = ("minecraft:black_concrete",
                            "replace_pavilion_glass_with_black_shell")
        elif state == "minecraft:orange_concrete":
            targets[pos] = ("minecraft:red_concrete",
                            "replace_orange_pavilion_accent_with_red")

    # Human-declared 5x4 west entrance at x=116, centred on z=273.
    for y in range(81, 85):
        for z in range(271, 276):
            targets[(116, y, z)] = (
                    "minecraft:barrier", "surface_staff_gate_collision")

    return [Change(PACKET, *pos, cells.get(pos, "minecraft:air"), after,
                   "human_authorized_surface_lift_pavilion", reason)
            for pos, (after, reason) in sorted(targets.items())
            if cells.get(pos, "minecraft:air") != after]


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s47_surface_lift_pavilion_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    root = dimension_dir(world, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)
    reports = []
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
        reports.append({
            "region": path.name,
            "beforeSha256": hashlib.sha256(before).hexdigest(),
            "afterSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    with (artifact / "block_diff.csv").open(
            "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x", "y", "z", "before", "after", "reason"))
        for change in changes:
            writer.writerow((change.x, change.y, change.z, change.before,
                             change.after, change.reason))
    receipt = {
        "schema": 1, "packet": PACKET, "world": str(world),
        "bbox": [list(LO), list(HI)], "blocks": len(changes),
        "gate": {"planeX": 116, "walkY": 81,
                 "zRange": [271, 275], "width": 5, "height": 4},
        "regions": reports,
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
    result = {"packet": PACKET, "world": str(world), "blocks": len(changes)}
    if args.apply:
        result.update(applied=True, artifact=str(apply(world, changes)))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
