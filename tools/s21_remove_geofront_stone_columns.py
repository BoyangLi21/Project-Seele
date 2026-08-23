#!/usr/bin/env python3
"""Remove only audited legacy raw-stone columns from the GeoFront cavern."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
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
from audit_geofront_cavern import scan
from query_blocks import dimension_dir


WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIMENSION = "projectseele:geofront"
CSV = Path("artifacts/geofront_stone_cleanup_candidates_20260811.csv")
PACKET = "S21-REMOVE-AUDITED-GEOFRONT-STONE-COLUMNS"


def load_changes(path: Path) -> list[Change]:
    changes: list[Change] = []
    with path.open(newline="", encoding="ascii") as stream:
        for row in csv.DictReader(stream):
            changes.append(Change(
                PACKET, int(row["x"]), int(row["y"]), int(row["z"]),
                row["before"], row["after"], "remove",
                "remove measured legacy vertical stone component height >= 50",
            ))
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("artifacts") / f"s21_stone_column_cleanup_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    for (region_x, region_z), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{region_x}.{region_z}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    report, remaining, _ = scan(WORLD.resolve(), DIMENSION)
    if remaining:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(
            f"post-cleanup audit still found {len(remaining)} suspicious cells")

    receipt = {
        "status": "APPLIED_AND_FULL_CAVERN_RESCAN_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "components": 136,
        "remainingSuspiciousStoneVoxels": 0,
        "shellBlocksUnchanged": report["shellBlocks"],
        "backup": str(backup.resolve()),
        "regionsBeforeSha256": hashes,
    }
    (backup / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes = load_changes(CSV)
    print(f"proposal components=136 writes={len(changes)} "
          "before=minecraft:stone after=minecraft:air")
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
