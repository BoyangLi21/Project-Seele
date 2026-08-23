#!/usr/bin/env python3
"""Remove measured one-column stone needles protruding into the R28 cavern."""

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
    Change, atomic_replace, rewrite_region,
)
from audit_geofront_cavern import scan
from query_blocks import dimension_dir


WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIMENSION = "projectseele:geofront"
PACKET = "S21-REMOVE-MEASURED-EDGE-STONE-PILLARS"
ROOT = Path("artifacts/r28_cavern_cleanup_r02_20260811")
CSV_FILES = (ROOT / "pillar_candidates.csv",
             ROOT / "legacy_floor_candidates.csv")


def load() -> list[Change]:
    unique: dict[tuple[int, int, int], Change] = {}
    for path in CSV_FILES:
        with path.open(newline="", encoding="ascii") as stream:
            for row in csv.DictReader(stream):
                key = (int(row["x"]), int(row["y"]), int(row["z"]))
                unique[key] = Change(
                    PACKET, *key, row["before"], "minecraft:air", "replace",
                    "remove measured thin raw-stone cavern intrusion",
                )
    return list(unique.values())


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    grouped = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        grouped[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("artifacts") / f"s21_edge_pillar_cleanup_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    originals = {}
    hashes = {}
    replaced = []
    try:
        for (rx, rz), chunks in sorted(grouped.items()):
            path = root / "region" / f"r.{rx}.{rz}.mca"
            originals[path] = path.read_bytes()
            hashes[path.name] = hashlib.sha256(originals[path]).hexdigest()
            shutil.copy2(path, backup / path.name)
            atomic_replace(path, rewrite_region(path, chunks))
            replaced.append(path)
        report, suspicious, legacy = scan(WORLD.resolve(), DIMENSION)
        if suspicious or legacy:
            raise RuntimeError(
                f"pillar read-back failed: suspicious={len(suspicious)} "
                f"legacy={len(legacy)}")
    except Exception:
        for path in replaced:
            atomic_replace(path, originals[path])
        raise
    receipt = {
        "status": "APPLIED_AND_FULL_RESCAN_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "remainingSuspiciousStoneVoxels": report["suspiciousStoneVoxels"],
        "remainingLegacyFloorVoxels": report["legacyFloorColumnVoxels"],
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
    changes = load()
    print(json.dumps({"writes": len(changes)}, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
