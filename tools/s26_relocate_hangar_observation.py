#!/usr/bin/env python3
"""Relocate the R28 wet-cage observation programme without touching cages.

The approved edit has three independent masks:

* retire only the obsolete upper observation storey at y=-386..-373;
* add one rear upper gallery whose floor is the human anchor y=-371;
* add three narrow face bridges from the retained lower gallery.

Every changed cell records its measured old state and every touched region is
copied before atomic replacement.
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
PACKET = "S26-HANGAR-OBSERVATION-RELOCATION-R01"
AIR_STATE = "minecraft:air"
CENTRES = (-12, 30, 72)

OLD_X0, OLD_X1 = -22, 82
OLD_Z0, OLD_Z1 = 126, 140
OLD_Y0, OLD_Y1 = -386, -373

NEW_X0, NEW_X1 = -32, 92
NEW_Z0, NEW_Z1 = 188, 198
NEW_FLOOR_Y, NEW_ROOF_Y = -371, -363
SEPARATOR_Z = 187

BRIDGE_FLOOR_Y = -395
BRIDGE_Z0, BRIDGE_Z1 = 140, 148
REMOVABLE_BLOCK_ENTITIES = {
    (centre, -377, 132) for centre in CENTRES
}


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def add(changes: dict[tuple[int, int, int], Change], cells: dict,
        pos: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(pos, AIR_STATE)
    if before == after:
        return
    changes[pos] = Change(PACKET, *pos, before, after,
                          "human_authorized_hangar_edit", reason)


def expect_replaceable(cells: dict, pos: tuple[int, int, int],
                       allowed: set[str], label: str) -> None:
    state = cells.get(pos, AIR_STATE)
    if state not in allowed:
        raise RuntimeError(f"{label} occupied at {pos}: {state}")


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (NEW_X0, BRIDGE_FLOOR_Y, OLD_Z0),
                     (NEW_X1, NEW_ROOF_Y, NEW_Z1), None)
    changes: dict[tuple[int, int, int], Change] = {}

    for pos in REMOVABLE_BLOCK_ENTITIES:
        if cells.get(pos, AIR_STATE) != "minecraft:beacon":
            raise RuntimeError(
                f"retired observation beacon changed at {pos}: "
                f"{cells.get(pos, AIR_STATE)}")

    # The human retired this exact upper storey.  The lower gallery at y=-395
    # and the wet-cage pressure face south of z=140 are outside this mask.
    for x in range(OLD_X0, OLD_X1 + 1):
        for y in range(OLD_Y0, OLD_Y1 + 1):
            for z in range(OLD_Z0, OLD_Z1 + 1):
                add(changes, cells, (x, y, z), AIR_STATE,
                    "retire_old_upper_observation_storey")

    # A sealed upper rear gallery occupies the newly raised-roof band.  Its
    # only transparent wall is the pressure boundary facing the three cages.
    marker = {(-13, NEW_FLOOR_Y, 188), (-13, NEW_FLOOR_Y, 189)}
    for x in range(NEW_X0, NEW_X1 + 1):
        for z in range(NEW_Z0, NEW_Z1 + 1):
            floor = (x, NEW_FLOOR_Y, z)
            roof = (x, NEW_ROOF_Y, z)
            allowed_floor = {AIR_STATE}
            if floor in marker:
                allowed_floor.add("minecraft:reinforced_deepslate")
            expect_replaceable(cells, floor, allowed_floor,
                               "new gallery floor")
            expect_replaceable(cells, roof, {AIR_STATE},
                               "new gallery roof")
            floor_state = ("minecraft:sea_lantern"
                           if (x - NEW_X0) % 12 == 6 and z in (191, 195)
                           else "minecraft:polished_deepslate")
            roof_state = ("minecraft:sea_lantern"
                          if (x - NEW_X0) % 10 == 5 and z in (191, 195)
                          else "minecraft:reinforced_deepslate")
            add(changes, cells, floor, floor_state,
                "build_rear_observation_floor")
            add(changes, cells, roof, roof_state,
                "build_rear_observation_roof")

    for y in range(NEW_FLOOR_Y + 1, NEW_ROOF_Y):
        for x in range(NEW_X0, NEW_X1 + 1):
            for z in range(NEW_Z0, NEW_Z1 + 1):
                boundary = x in (NEW_X0, NEW_X1) or z == NEW_Z1
                pos = (x, y, z)
                expect_replaceable(cells, pos, {AIR_STATE},
                                   "new gallery wall/interior")
                if boundary:
                    add(changes, cells, pos,
                        "minecraft:reinforced_deepslate",
                        "build_rear_observation_outer_wall")

    # Replace only the interiors of the three measured z=187 cage walls.
    # Structural columns at each 41-block shell edge remain untouched.
    separator_allowed = {
        "minecraft:reinforced_deepslate",
        "minecraft:polished_blackstone_bricks",
        "minecraft:sea_lantern",
        "minecraft:air",
    }
    for centre in CENTRES:
        for x in range(centre - 18, centre + 19):
            for y in range(NEW_FLOOR_Y + 1, NEW_ROOF_Y):
                pos = (x, y, SEPARATOR_Z)
                expect_replaceable(cells, pos, separator_allowed,
                                   "rear pressure window")
                add(changes, cells, pos, "projectseele:clear_glass",
                    "build_rear_clear_glass_separator")

    # Three five-wide lower bridges terminate two blocks before the measured
    # front of each parked EVA head.  They inherit the retained y=-395 lower
    # gallery floor, so no invented stair/elevator connection is required.
    bridge_floor_allowed = {
        AIR_STATE,
        "minecraft:reinforced_deepslate",
        "minecraft:polished_blackstone_bricks",
        "minecraft:polished_deepslate",
        "minecraft:sea_lantern",
        "minecraft:light_gray_stained_glass",
        "projectseele:clear_glass",
    }
    opening_allowed = bridge_floor_allowed | {
        "minecraft:gray_stained_glass",
    }
    for centre in CENTRES:
        for x in range(centre - 2, centre + 3):
            for y in range(BRIDGE_FLOOR_Y + 1,
                           BRIDGE_FLOOR_Y + 4):
                pos = (x, y, BRIDGE_Z0)
                expect_replaceable(cells, pos, opening_allowed,
                                   "face bridge pressure opening")
                add(changes, cells, pos, AIR_STATE,
                    f"eva{CENTRES.index(centre):02d}_open_face_bridge")
            for z in range(BRIDGE_Z0, BRIDGE_Z1 + 1):
                pos = (x, BRIDGE_FLOOR_Y, z)
                expect_replaceable(cells, pos, bridge_floor_allowed,
                                   "face bridge floor")
                state = ("minecraft:sea_lantern"
                         if x == centre and z in (143, 147)
                         else "minecraft:polished_deepslate")
                add(changes, cells, pos, state,
                    f"eva{CENTRES.index(centre):02d}_face_bridge_floor")
        for side_x in (centre - 3, centre + 3):
            for z in range(BRIDGE_Z0 + 1, BRIDGE_Z1 + 1):
                pos = (side_x, BRIDGE_FLOOR_Y + 1, z)
                expect_replaceable(cells, pos, {AIR_STATE},
                                   "face bridge railing")
                add(changes, cells, pos, "projectseele:clear_glass",
                    f"eva{CENTRES.index(centre):02d}_face_bridge_railing")
        for x in range(centre - 2, centre + 3):
            pos = (x, BRIDGE_FLOOR_Y + 1, BRIDGE_Z1 + 1)
            expect_replaceable(cells, pos, {AIR_STATE},
                               "face bridge end rail")
            add(changes, cells, pos, "projectseele:clear_glass",
                f"eva{CENTRES.index(centre):02d}_face_bridge_end_rail")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s26_hangar_observation_{stamp}"
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
            atomic_replace(path, rewrite_region(
                path, grouped, REMOVABLE_BLOCK_ENTITIES))
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
