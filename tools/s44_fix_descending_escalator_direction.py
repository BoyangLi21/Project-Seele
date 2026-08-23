#!/usr/bin/env python3
"""Correct the two reversed upper transition cells seen from 56,-443,285."""

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
PACKET = "S44-FIX-DESCENDING-ESCALATOR-DIRECTION-R01"


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION, (56, -443, 274),
                     (56, -443, 275), None)
    changes = []
    for z, side in ((274, "left"), (275, "right")):
        pos = (56, -443, z)
        before = cells.get(pos, "minecraft:air")
        expected = ("mtr:escalator_step[direction=true,facing=east,"
                    f"orientation=transition_top,side={side},status=true]")
        if before != expected:
            raise RuntimeError(f"transition changed at {pos}: {before}")
        after = ("mtr:escalator_step[direction=false,facing=east,"
                 f"orientation=transition_top,side={side},status=true]")
        changes.append(Change(
            PACKET, *pos, before, after,
            "human_authorized_mtr_corridor_links",
            "match_upper_transition_to_descending_slope"))
    return changes


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s44_escalator_direction_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    root = dimension_dir(world, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)
    reports = []
    for (rx, rz), selected in by_region.items():
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
    receipt = {"schema": 1, "packet": PACKET, "world": str(world),
               "blocks": len(changes), "regions": reports}
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
    print(json.dumps({"packet": PACKET, "world": str(world),
                      "blocks": len(changes)}, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
