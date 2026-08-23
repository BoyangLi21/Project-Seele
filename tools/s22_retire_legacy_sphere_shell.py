#!/usr/bin/env python3
"""Retire the displaced 320-block S20 sphere shell from coastal S22.

S22 uses a 1,800-block shallow dome centred on the coastal facility datum.
The copied S20 shell is a separate, displaced sphere centred at z=220.  Its
remaining static-weave voxels sit wholly in the old radius band and visually
cut the expanded GeoFront in half.  This packet removes only those exact
weave voxels; every other block, block entity and authored structure is left
untouched.  Touched region files are copied before the first write.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from inspect_map_assets import decode_modern_section, iter_chunks, palette_name
from query_blocks import dimension_dir


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-RETIRE-DISPLACED-LEGACY-SPHERE-R01"
SOURCE = "projectseele:geofront_skyweave"
TARGET = "minecraft:air"
CENTRE = (30, -332, 220)
RADIUS = 320
BAND = 4
EXPECTED = 104_453


def collect() -> list[Change]:
    root = dimension_dir(WORLD, DIMENSION)
    min_x = (CENTRE[0] - RADIUS - BAND) >> 4
    max_x = (CENTRE[0] + RADIUS + BAND) >> 4
    min_z = (CENTRE[2] - RADIUS - BAND) >> 4
    max_z = (CENTRE[2] + RADIUS + BAND) >> 4
    inner_sq = (RADIUS - BAND) ** 2
    outer_sq = (RADIUS + BAND) ** 2
    changes: list[Change] = []

    for chunk_x, chunk_z, chunk in iter_chunks(
            root, (min_x, max_x, min_z, max_z)):
        base_x, base_z = chunk_x * 16, chunk_z * 16
        for section in chunk.get("sections", []):
            base_y = int(section.get("Y", 0)) * 16
            if (base_y > CENTRE[1] + RADIUS + BAND
                    or base_y + 15 < CENTRE[1] - RADIUS - BAND):
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            source_indices = [
                index for index, entry in enumerate(palette)
                if palette_name(entry) == SOURCE
            ]
            for palette_index in source_indices:
                offsets = np.flatnonzero(indices == palette_index)
                if not offsets.size:
                    continue
                xs = base_x + (offsets & 15)
                zs = base_z + ((offsets >> 4) & 15)
                ys = base_y + (offsets >> 8)
                radius_sq = ((xs - CENTRE[0]) ** 2
                             + (ys - CENTRE[1]) ** 2
                             + (zs - CENTRE[2]) ** 2)
                mask = (radius_sq >= inner_sq) & (radius_sq <= outer_sq)
                for x, y, z in zip(xs[mask], ys[mask], zs[mask]):
                    changes.append(Change(
                        PACKET, int(x), int(y), int(z), SOURCE, TARGET,
                        "replace", "retire displaced S20 sphere shell"))
    changes.sort(key=lambda c: (c.y, c.z, c.x))
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_LEGACY_SHELL_RETIRE_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    remaining = collect()
    if remaining:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(
            f"read-back found {len(remaining)} legacy shell voxels; restored")

    receipt = {
        "status": "APPLIED_AND_TARGETED_RESCAN_VERIFIED",
        "packet": PACKET,
        "source": SOURCE,
        "target": TARGET,
        "writes": len(changes),
        "legacySphereCentre": list(CENTRE),
        "legacySphereRadius": RADIUS,
        "regionsBeforeSha256": hashes,
    }
    (backup / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes = collect()
    report = {
        "packet": PACKET,
        "writes": len(changes),
        "expected": EXPECTED,
        "precondition": "PASS" if len(changes) == EXPECTED else "FAIL",
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes),
            min(c.z for c in changes), max(c.x for c in changes),
            max(c.y for c in changes), max(c.z for c in changes),
        ] if changes else None,
    }
    print(json.dumps(report, indent=2))
    if len(changes) != EXPECTED:
        raise RuntimeError(
            f"legacy shell precondition changed: {len(changes)} != {EXPECTED}")
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
