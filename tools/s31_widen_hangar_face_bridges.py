#!/usr/bin/env python3
"""Widen the three approved lower EVA face bridges and reseal their glazing."""

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
PACKET = "S31-WIDE-EVA-FACE-BRIDGES-R01"
AIR = "minecraft:air"
AIR_STATES = {AIR, "minecraft:void_air", "minecraft:cave_air"}
CENTRES = (-12, 30, 72)
FLOOR_Y = -395
ENTRY_Z = 140
INTERIOR_END_Z = 149
GLASS_END_Z = 150
HALF_INTERIOR = 5
SIDE_X = 6
GLASS_BOTTOM_Y = -394
GLASS_TOP_Y = -386


def add(changes: dict[tuple[int, int, int], Change], cells: dict,
        pos: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(pos, AIR)
    if before == after or (after == AIR and before in AIR_STATES):
        return
    changes[pos] = Change(PACKET, *pos, before, after,
                          "human_authorized_hangar_bridge_revision", reason)


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (CENTRES[0] - SIDE_X, FLOOR_Y, ENTRY_Z),
                     (CENTRES[-1] + SIDE_X, GLASS_TOP_Y + 1,
                      GLASS_END_Z), None)
    changes: dict[tuple[int, int, int], Change] = {}

    for index, centre in enumerate(CENTRES):
        unit = f"eva{index:02d}"

        # Remove the former five-wide handrail from the new eleven-wide walk
        # lane.  This exact prism is the bridge interior authorised by the
        # user; no cage wall, LCL vessel or upper observation room is touched.
        for x in range(centre - HALF_INTERIOR,
                       centre + HALF_INTERIOR + 1):
            for z in range(ENTRY_Z, INTERIOR_END_Z + 1):
                for y in range(FLOOR_Y + 1, GLASS_TOP_Y + 1):
                    add(changes, cells, (x, y, z), AIR,
                        f"{unit}_clear_widened_walk_lane")

        # Eleven clear walking cells plus a one-block structural sill on each
        # side.  The centre lighting repeats the retained S26 bridge rhythm.
        for x in range(centre - HALF_INTERIOR,
                       centre + HALF_INTERIOR + 1):
            for z in range(ENTRY_Z, INTERIOR_END_Z + 1):
                state = ("minecraft:sea_lantern"
                         if x == centre and z in (143, 147)
                         else "minecraft:polished_deepslate")
                add(changes, cells, (x, FLOOR_Y, z), state,
                    f"{unit}_wide_bridge_floor")

        for side in (-SIDE_X, SIDE_X):
            x = centre + side
            for z in range(ENTRY_Z, GLASS_END_Z + 1):
                sill = ("minecraft:sea_lantern"
                        if z in (143, 147) else
                        "minecraft:polished_blackstone_bricks")
                add(changes, cells, (x, FLOOR_Y, z), sill,
                    f"{unit}_continuous_side_sill")
                for y in range(GLASS_BOTTOM_Y, GLASS_TOP_Y + 1):
                    add(changes, cells, (x, y, z),
                        "projectseele:clear_glass",
                        f"{unit}_continuous_side_glass")

        # The front is one uninterrupted panoramic pressure pane.  Both
        # corner columns are owned by the side pass above, eliminating the
        # one-block holes visible in the former bridge corners.
        for x in range(centre - HALF_INTERIOR,
                       centre + HALF_INTERIOR + 1):
            add(changes, cells, (x, FLOOR_Y, GLASS_END_Z),
                "minecraft:polished_blackstone_bricks",
                f"{unit}_front_sill")
            for y in range(GLASS_BOTTOM_Y, GLASS_TOP_Y + 1):
                add(changes, cells, (x, y, GLASS_END_Z),
                    "projectseele:clear_glass",
                    f"{unit}_panoramic_front_glass")

        # Reopen the full eleven-wide connection through the retained gallery
        # plane.  Side glazing at centre±6 seals the two outer edges.
        for x in range(centre - HALF_INTERIOR,
                       centre + HALF_INTERIOR + 1):
            for y in range(GLASS_BOTTOM_Y, GLASS_TOP_Y + 1):
                add(changes, cells, (x, y, ENTRY_Z), AIR,
                    f"{unit}_wide_gallery_opening")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s31_wide_face_bridges_{stamp}"
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
    print(json.dumps({
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "reasons": dict(sorted(Counter(c.reason for c in changes).items())),
    }, indent=2))
    if args.apply:
        print(json.dumps({
            "applied": True,
            "artifact": str(apply(world, changes)),
        }, indent=2))


if __name__ == "__main__":
    main()
