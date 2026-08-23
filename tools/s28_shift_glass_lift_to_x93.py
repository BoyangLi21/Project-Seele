#!/usr/bin/env python3
"""Shift the human-rebuilt hangar lift four blocks east without repainting it.

The current saved voxels are the source of truth.  Only the measured 9x9
shaft, its 9-wide lower branch and the short upper vestibule are owned here.
Moving Elevators block entities remain in place for the live Java migration.
"""

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
from query_blocks import AIR, dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S28-GLASS-LIFT-X93-Z204-R01"
AIR_STATE = "minecraft:air"
DX = 4

SOURCE_SHAFT = (85, -443, 200, 93, -363, 208)
SOURCE_BRANCH = (85, -443, 209, 93, -438, 270)
NEW_X0, NEW_X1 = 89, 97
NEW_Z0, NEW_Z1 = 200, 208
NEW_CX, NEW_CZ = 93, 204


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def moving_elevator(state: str) -> bool:
    return state.split("[", 1)[0].startswith("movingelevators:")


def add(changes: dict[tuple[int, int, int], Change], cells: dict,
        pos: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(pos, AIR_STATE)
    if before == after:
        return
    changes[pos] = Change(PACKET, *pos, before, after,
                          "human_authorized_lift_shift", reason)


def copy_shifted_box(changes: dict, cells: dict, box: tuple[int, ...],
                     reason: str) -> None:
    x0, y0, z0, x1, y1, z1 = box
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                source = cells.get((x, y, z), AIR_STATE)
                after = AIR_STATE if moving_elevator(source) else source
                add(changes, cells, (x + DX, y, z), after, reason)


def clear_retired_west_strip(changes: dict, cells: dict,
                             box: tuple[int, ...], reason: str) -> None:
    x0, y0, z0, _x1, y1, z1 = box
    for x in range(x0, x0 + DX):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                state = cells.get((x, y, z), AIR_STATE)
                if not moving_elevator(state):
                    add(changes, cells, (x, y, z), AIR_STATE, reason)


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (78, -444, 194), (105, -360, 276), None)
    changes: dict[tuple[int, int, int], Change] = {}

    copy_shifted_box(changes, cells, SOURCE_BRANCH,
                     "shift_lower_branch_east_4")
    copy_shifted_box(changes, cells, SOURCE_SHAFT,
                     "shift_lift_shaft_east_4")
    clear_retired_west_strip(changes, cells, SOURCE_BRANCH,
                             "retire_old_branch_west_strip")
    clear_retired_west_strip(changes, cells, SOURCE_SHAFT,
                             "retire_old_shaft_west_strip")

    # Four transparent shaft walls.  The two landing-door masks use the same
    # clear glass while closed; the runtime removes them only at the floor
    # where the physical cabin is present.
    for y in range(-442, -363):
        for x in range(NEW_X0, NEW_X1 + 1):
            for z in range(NEW_Z0, NEW_Z1 + 1):
                if x in (NEW_X0, NEW_X1) or z in (NEW_Z0, NEW_Z1):
                    add(changes, cells, (x, y, z),
                        "projectseele:clear_glass",
                        "four_sided_clear_glass_shaft")

    # Re-centre the upper handoff on x=93.  The broad observation floor at
    # z=198 is human-authored and is only opened at this exact five-wide door.
    for x in range(NEW_CX - 2, NEW_CX + 3):
        for z in range(198, NEW_Z0 + 1):
            add(changes, cells, (x, -371, z),
                "minecraft:polished_deepslate",
                "recenter_upper_observation_link")
            add(changes, cells, (x, -363, z),
                "minecraft:reinforced_deepslate",
                "recenter_upper_observation_link")
        for y in range(-370, -367):
            add(changes, cells, (x, y, 198), AIR_STATE,
                "open_x93_observation_door")
            add(changes, cells, (x, y, NEW_Z0),
                "projectseele:clear_glass",
                "x93_upper_clear_glass_landing_door")
    for side_x in (NEW_CX - 3, NEW_CX + 3):
        for y in range(-370, -363):
            for z in range(198, NEW_Z0 + 1):
                add(changes, cells, (side_x, y, z),
                    "projectseele:clear_glass",
                    "x93_upper_clear_glass_vestibule")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s28_glass_lift_x93_{stamp}"
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
