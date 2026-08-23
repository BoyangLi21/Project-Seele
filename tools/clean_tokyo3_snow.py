#!/usr/bin/env python3
"""Remove only measured snow layers from the authored Tokyo-3 footprint."""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from inspect_map_assets import decode_modern_section, iter_chunks, palette_state
from query_blocks import dimension_dir

WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIMENSION = "projectseele:geofront"
BOUNDS = (-194, 60, -4, 254, 319, 444)
PACKET = "S24-CLEAR-TOKYO3-SNOW-LAYERS"

def scan() -> list[Change]:
    root = dimension_dir(WORLD, DIMENSION)
    x0, y0, z0, x1, y1, z1 = BOUNDS
    changes = []
    for cx, cz, chunk in iter_chunks(root, (x0 >> 4, x1 >> 4, z0 >> 4, z1 >> 4)):
        bx, bz = cx * 16, cz * 16
        for section in chunk.get("sections", []):
            by = int(section.get("Y", 0)) * 16
            if by > y1 or by + 15 < y0:
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            states = [palette_state(entry) for entry in palette]
            snow_blocks = {
                "minecraft:snow",
                "minecraft:snow_block",
                "minecraft:powder_snow",
            }
            snow_indices = {i for i, state in enumerate(states)
                            if state.split("[", 1)[0] in snow_blocks}
            if not snow_indices:
                continue
            for offset, index in enumerate(indices):
                if index not in snow_indices:
                    continue
                x = bx + (offset & 15)
                z = bz + ((offset >> 4) & 15)
                y = by + (offset >> 8)
                if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1:
                    changes.append(Change(PACKET, x, y, z, states[index],
                                          "minecraft:air", "replace",
                                          "remove existing Tokyo-3 snow"))
    return changes

def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    grouped = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        grouped[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    backup = Path("artifacts") / ("s24_tokyo3_snow_" + time.strftime("%Y%m%d_%H%M%S"))
    backup.mkdir(parents=True)
    originals = {}
    changed_paths = []
    before_hash = {}
    try:
        for (rx, rz), chunks in sorted(grouped.items()):
            path = root / "region" / f"r.{rx}.{rz}.mca"
            originals[path] = path.read_bytes()
            before_hash[path.name] = hashlib.sha256(originals[path]).hexdigest()
            shutil.copy2(path, backup / path.name)
            atomic_replace(path, rewrite_region(path, chunks))
            changed_paths.append(path)
        remaining = scan()
        if remaining:
            raise RuntimeError(f"snow read-back failed: {len(remaining)} remain")
    except Exception:
        for path in changed_paths:
            atomic_replace(path, originals[path])
        raise
    receipt = {"status": "APPLIED_AND_READ_BACK_VERIFIED",
               "changedSnowLayers": len(changes),
               "backup": str(backup.resolve()),
               "regionsBeforeSha256": before_hash}
    (backup / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return backup

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes = scan()
    print(json.dumps({"snowLayers": len(changes), "bounds": BOUNDS}))
    if args.apply and changes:
        print("backup=" + str(apply(changes)))

if __name__ == "__main__":
    main()
