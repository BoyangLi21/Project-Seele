#!/usr/bin/env python3
"""Clear measured natural-terrain intrusions from the three R28 EVA shafts."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIMENSION = "projectseele:geofront"
CENTRES = (-12, 30, 72)
CENTRE_Z = 220
CLEAR_RADIUS = 15
LOWER_Y = -442
SURFACE_BED_Y = 79
EXIT_TOP_Y = 161
PACKET = "S24-CLEAR-THREE-EVA-LAUNCH-SHAFTS"

# This packet removes terrain that cannot be part of an authored mechanical
# shaft. It deliberately refuses to erase any facility block or unknown state.
NATURAL_INTRUSIONS = {
    "minecraft:dirt",
    "minecraft:grass_block",
    "minecraft:coarse_dirt",
    "minecraft:rooted_dirt",
    "minecraft:mud",
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def in_swept_height(y: int) -> bool:
    # Y=79 is the retained lodestone station bed. The moving EVA occupies the
    # shaft below it and the complete surface-exit headroom above it.
    return LOWER_Y <= y < SURFACE_BED_Y or SURFACE_BED_Y < y <= EXIT_TOP_Y


def scan() -> tuple[list[Change], dict[int, Counter[str]]]:
    world = read_box(
        WORLD,
        DIMENSION,
        (min(CENTRES) - CLEAR_RADIUS, LOWER_Y, CENTRE_Z - CLEAR_RADIUS),
        (max(CENTRES) + CLEAR_RADIUS, EXIT_TOP_Y, CENTRE_Z + CLEAR_RADIUS),
    )
    changes: list[Change] = []
    summary: dict[int, Counter[str]] = {variant: Counter() for variant in range(3)}
    for variant, centre_x in enumerate(CENTRES):
        for x in range(centre_x - CLEAR_RADIUS, centre_x + CLEAR_RADIUS + 1):
            for z in range(CENTRE_Z - CLEAR_RADIUS, CENTRE_Z + CLEAR_RADIUS + 1):
                for y in range(LOWER_Y, EXIT_TOP_Y + 1):
                    if not in_swept_height(y):
                        continue
                    state = world.get((x, y, z), "minecraft:air")
                    block = bare(state)
                    if block not in NATURAL_INTRUSIONS:
                        continue
                    changes.append(
                        Change(
                            PACKET,
                            x,
                            y,
                            z,
                            state,
                            "minecraft:air",
                            "replace",
                            f"remove terrain intrusion from EVA-0{variant} shaft",
                        )
                    )
                    summary[variant][block] += 1
    return changes, summary


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    grouped = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        grouped[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)

    backup = Path("artifacts") / (
        "s24_launch_shafts_" + time.strftime("%Y%m%d_%H%M%S")
    )
    backup.mkdir(parents=True, exist_ok=False)
    originals: dict[Path, bytes] = {}
    changed_paths: list[Path] = []
    before_hashes: dict[str, str] = {}
    try:
        for (region_x, region_z), chunk_changes in sorted(grouped.items()):
            path = root / "region" / f"r.{region_x}.{region_z}.mca"
            originals[path] = path.read_bytes()
            before_hashes[path.name] = hashlib.sha256(originals[path]).hexdigest()
            shutil.copy2(path, backup / path.name)
            atomic_replace(path, rewrite_region(path, chunk_changes))
            changed_paths.append(path)

        remaining, _ = scan()
        if remaining:
            raise RuntimeError(
                f"launch-shaft read-back failed: {len(remaining)} terrain cells remain"
            )
    except Exception:
        for path in changed_paths:
            atomic_replace(path, originals[path])
        raise

    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "centres": [[x, CENTRE_Z] for x in CENTRES],
        "clearRadius": CLEAR_RADIUS,
        "heightRanges": [[LOWER_Y, SURFACE_BED_Y - 1],
                         [SURFACE_BED_Y + 1, EXIT_TOP_Y]],
        "backup": str(backup.resolve()),
        "regionsBeforeSha256": before_hashes,
    }
    (backup / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii"
    )
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes, summary = scan()
    print(json.dumps({
        "writes": len(changes),
        "byUnit": {f"EVA-0{variant}": dict(counts)
                   for variant, counts in summary.items()},
    }, sort_keys=True))
    if args.apply and changes:
        print("backup=" + str(apply(changes)))


if __name__ == "__main__":
    main()
