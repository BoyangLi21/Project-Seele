#!/usr/bin/env python3
"""Convert the three EVA face bridges into open platforms and restore glazing."""

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
PACKET = "S32-OPEN-EVA-OBSERVATION-PLATFORMS-R01"
AIR = "minecraft:air"
AIR_STATES = {AIR, "minecraft:void_air", "minecraft:cave_air"}
CENTRES = (-12, 30, 72)
FLOOR_Y = -395
ENTRY_Z = 140
PLATFORM_END_Z = 151
RAIL_Z = 152
HALF_PLATFORM = 7
RAIL_X = 8
WINDOW_Z = 133
WINDOW_Y0 = -394
WINDOW_Y1 = -386


def add(changes: dict[tuple[int, int, int], Change], cells: dict,
        pos: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(pos, AIR)
    if before == after or (after == AIR and before in AIR_STATES):
        return
    changes[pos] = Change(PACKET, *pos, before, after,
                          "human_authorized_hangar_platform_revision", reason)


def bars(*, north: bool = False, south: bool = False,
         east: bool = False, west: bool = False) -> str:
    return ("minecraft:iron_bars["
            f"east={'true' if east else 'false'},"
            f"north={'true' if north else 'false'},"
            f"south={'true' if south else 'false'},"
            "waterlogged=false,"
            f"west={'true' if west else 'false'}]")


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (CENTRES[0] - 19, FLOOR_Y, WINDOW_Z),
                     (CENTRES[-1] + 19, WINDOW_Y1, RAIL_Z), None)
    changes: dict[tuple[int, int, int], Change] = {}

    for index, centre in enumerate(CENTRES):
        unit = f"eva{index:02d}"

        # Retire the mistaken glass U-shaped bridge from S31.  The platform
        # must read as one open operator deck, not a glazed pedestrian tube.
        for x in range(centre - HALF_PLATFORM,
                       centre + HALF_PLATFORM + 1):
            for z in range(ENTRY_Z, PLATFORM_END_Z + 1):
                for y in range(FLOOR_Y + 1, WINDOW_Y1 + 1):
                    add(changes, cells, (x, y, z), AIR,
                        f"{unit}_open_platform_headroom")
        for x in (centre - 6, centre + 6):
            for z in range(ENTRY_Z, 151):
                for y in range(FLOOR_Y + 1, WINDOW_Y1 + 1):
                    add(changes, cells, (x, y, z), AIR,
                        f"{unit}_retire_s31_side_glass")
        for x in range(centre - 5, centre + 6):
            for y in range(FLOOR_Y + 1, WINDOW_Y1 + 1):
                add(changes, cells, (x, y, 150), AIR,
                    f"{unit}_retire_s31_front_glass")

        # Fifteen-by-twelve uninterrupted deck: this is now a platform, not a
        # narrow bridge.  The outer sill closes every former floor-edge gap.
        for x in range(centre - HALF_PLATFORM,
                       centre + HALF_PLATFORM + 1):
            for z in range(ENTRY_Z, PLATFORM_END_Z + 1):
                state = ("minecraft:sea_lantern"
                         if x == centre and z in (143, 147, 151)
                         else "minecraft:polished_deepslate")
                add(changes, cells, (x, FLOOR_Y, z), state,
                    f"{unit}_observation_platform_floor")
        for side_x in (centre - RAIL_X, centre + RAIL_X):
            for z in range(ENTRY_Z, RAIL_Z + 1):
                add(changes, cells, (side_x, FLOOR_Y, z),
                    "minecraft:polished_blackstone_bricks",
                    f"{unit}_platform_side_sill")
        for x in range(centre - HALF_PLATFORM,
                       centre + HALF_PLATFORM + 1):
            add(changes, cells, (x, FLOOR_Y, RAIL_Z),
                "minecraft:polished_blackstone_bricks",
                f"{unit}_platform_front_sill")

        # One-block industrial guard only.  The EVA-facing edge is iron bars;
        # both side runs meet its corners with explicit connected states.
        for z in range(ENTRY_Z, RAIL_Z + 1):
            left = bars(south=z < RAIL_Z, north=z > ENTRY_Z,
                        east=z == RAIL_Z)
            right = bars(south=z < RAIL_Z, north=z > ENTRY_Z,
                         west=z == RAIL_Z)
            add(changes, cells, (centre - RAIL_X, FLOOR_Y + 1, z),
                left, f"{unit}_left_iron_guard")
            add(changes, cells, (centre + RAIL_X, FLOOR_Y + 1, z),
                right, f"{unit}_right_iron_guard")
        for x in range(centre - HALF_PLATFORM,
                       centre + HALF_PLATFORM + 1):
            add(changes, cells, (x, FLOOR_Y + 1, RAIL_Z),
                bars(east=x < centre + HALF_PLATFORM,
                     west=x > centre - HALF_PLATFORM),
                f"{unit}_eva_facing_iron_guard")

        # Restore the glass the user removed from the *hangar observation
        # side*, not from the platform.  Each bay uses its measured 39-block
        # interior; the three reinforced inter-bay ribs remain untouched.
        for x in range(centre - 19, centre + 20):
            for y in range(WINDOW_Y0, WINDOW_Y1 + 1):
                add(changes, cells, (x, y, WINDOW_Z),
                    "projectseele:clear_glass",
                    f"{unit}_full_observation_side_glass")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s32_observation_platforms_{stamp}"
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
