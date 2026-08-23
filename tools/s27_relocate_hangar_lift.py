#!/usr/bin/env python3
"""Relocate the R28 compact-cage lift and its lower personnel branch.

The human anchors identify the old/new south walls.  Their measured centres
are (108,*,192) and (89,*,204).  The lower landing remains at walk y=-442;
the new observation floor is a block at y=-371, hence its walk y is -370.
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
PACKET = "S27-HANGAR-LIFT-X89-Z204-R03"
AIR_STATE = "minecraft:air"

OLD_SHAFT = (104, -443, 188, 112, -390, 196)
OLD_BRANCH = (104, -443, 197, 112, -438, 270)
BRANCH_DX = -19

NEW_CX, NEW_CZ = 89, 204
NEW_X0, NEW_X1 = 85, 93
NEW_Z0, NEW_Z1 = 200, 208
NEW_Y0, NEW_Y1 = -443, -363
LOWER_WALK_Y = -442
UPPER_FLOOR_Y = -371
UPPER_WALK_Y = -370
HANGAR_CENTRES = (-12, 30, 72)


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
                          "human_authorized_lift_relocation", reason)


def moving_elevator(state: str) -> bool:
    return state.split("[", 1)[0].startswith("movingelevators:")


def same_non_air(left: str, right: str) -> str | None:
    if left == right and left not in AIR:
        return left
    return None


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (-32, -444, 125), (135, -363, 276), None)
    changes: dict[tuple[int, int, int], Change] = {}

    # Copy the complete 73-block branch west by nineteen blocks.  Air is part
    # of the corridor contract: it clears the exact seven-wide headspace, but
    # no cell outside this measured tube is touched.
    for x in range(OLD_BRANCH[0], OLD_BRANCH[3] + 1):
        for y in range(OLD_BRANCH[1], OLD_BRANCH[4] + 1):
            for z in range(OLD_BRANCH[2], OLD_BRANCH[5] + 1):
                source = cells.get((x, y, z), AIR_STATE)
                after = AIR_STATE if moving_elevator(source) else source
                add(changes, cells, (x + BRANCH_DX, y, z), after,
                    "move_compact_cage_branch_west_19")

    # Remove the old branch while preserving any orthogonal route that crosses
    # the tube.  Equal non-air states immediately west/east are measured proof
    # of a through-route; those states are continued across the retired tube.
    for x in range(OLD_BRANCH[0], OLD_BRANCH[3] + 1):
        for y in range(OLD_BRANCH[1], OLD_BRANCH[4] + 1):
            for z in range(OLD_BRANCH[2], OLD_BRANCH[5] + 1):
                source = cells.get((x, y, z), AIR_STATE)
                if moving_elevator(source):
                    continue
                crossing = same_non_air(
                    cells.get((OLD_BRANCH[0] - 1, y, z), AIR_STATE),
                    cells.get((OLD_BRANCH[3] + 1, y, z), AIR_STATE))
                add(changes, cells, (x, y, z),
                    crossing or AIR_STATE,
                    "retire_old_compact_cage_branch")

    # The old free-standing shaft becomes empty cavern.  Moving Elevators
    # controllers/panels are deliberately left for the live Java migration,
    # which removes them only after their dependency group is stationary.
    for x in range(OLD_SHAFT[0], OLD_SHAFT[3] + 1):
        for y in range(OLD_SHAFT[1], OLD_SHAFT[4] + 1):
            for z in range(OLD_SHAFT[2], OLD_SHAFT[5] + 1):
                state = cells.get((x, y, z), AIR_STATE)
                if not moving_elevator(state):
                    add(changes, cells, (x, y, z), AIR_STATE,
                        "retire_old_compact_cage_shaft")

    # Retire the old y=-395 east vestibule which otherwise terminates in air
    # after the shaft moves.  The retained gallery ends at x=82 and is outside
    # these two masks.
    for x in range(83, 109):
        for y in range(-395, -390):
            for z in range(127, 132):
                state = cells.get((x, y, z), AIR_STATE)
                if not moving_elevator(state):
                    add(changes, cells, (x, y, z), AIR_STATE,
                        "retire_old_upper_lift_catwalk")
    for x in range(106, 111):
        for y in range(-395, -390):
            for z in range(132, 188):
                state = cells.get((x, y, z), AIR_STATE)
                if not moving_elevator(state):
                    add(changes, cells, (x, y, z), AIR_STATE,
                        "retire_old_upper_lift_catwalk")

    # Rebuild the new continuous shaft.  Its west wall is the side nearest the
    # EVA-02/launch plant and is clear glass between structural corner posts.
    for x in range(NEW_X0, NEW_X1 + 1):
        for y in range(NEW_Y0, NEW_Y1 + 1):
            for z in range(NEW_Z0, NEW_Z1 + 1):
                pos = (x, y, z)
                if y == NEW_Y0:
                    state = ("minecraft:sea_lantern"
                             if (x == NEW_CX and z == NEW_CZ)
                             else "minecraft:polished_deepslate")
                elif y == NEW_Y1:
                    state = ("minecraft:sea_lantern"
                             if x == NEW_CX or z == NEW_CZ
                             else "minecraft:reinforced_deepslate")
                else:
                    boundary = x in (NEW_X0, NEW_X1) \
                        or z in (NEW_Z0, NEW_Z1)
                    lower_door = (z == NEW_Z1
                                  and NEW_CX - 2 <= x <= NEW_CX + 2
                                  and LOWER_WALK_Y <= y <= LOWER_WALK_Y + 2)
                    upper_door = (z == NEW_Z0
                                  and NEW_CX - 2 <= x <= NEW_CX + 2
                                  and UPPER_WALK_Y <= y <= UPPER_WALK_Y + 2)
                    if lower_door or upper_door:
                        state = "minecraft:gray_stained_glass"
                    elif not boundary:
                        state = AIR_STATE
                    elif (x == NEW_X0 and NEW_Z0 < z < NEW_Z1):
                        state = "projectseele:clear_glass"
                    elif ((x in (NEW_X0, NEW_X1)
                           and z in (NEW_Z0, NEW_Z1))
                          or (y - NEW_Y0) % 14 == 0):
                        state = "minecraft:sea_lantern"
                    else:
                        state = "minecraft:reinforced_deepslate"
                add(changes, cells, pos, state,
                    "build_x89_z204_clear_view_lift_shaft")

    # Two-block north vestibule joins the upper door to the user-approved rear
    # observation hall at (89,-371,198).  Its floor remains exactly y=-371.
    for x in range(NEW_CX - 2, NEW_CX + 3):
        for z in range(198, NEW_Z0 + 1):
            add(changes, cells, (x, UPPER_FLOOR_Y, z),
                "minecraft:polished_deepslate",
                "connect_lift_to_rear_observation")
            add(changes, cells, (x, NEW_Y1, z),
                "minecraft:reinforced_deepslate",
                "connect_lift_to_rear_observation")
        for y in range(UPPER_WALK_Y, UPPER_WALK_Y + 3):
            add(changes, cells, (x, y, 198), AIR_STATE,
                "open_rear_observation_lift_door")
            add(changes, cells, (x, y, NEW_Z0),
                "minecraft:gray_stained_glass",
                "build_upper_landing_door")
    for side_x in (NEW_CX - 3, NEW_CX + 3):
        for y in range(UPPER_WALK_Y, NEW_Y1):
            for z in range(198, NEW_Z0 + 1):
                add(changes, cells, (side_x, y, z),
                    "projectseele:clear_glass",
                    "glaze_upper_lift_vestibule")

    # S26 retired the obsolete upper room, but its deletion mask also crossed
    # the three wet-cage pressure shells at z=133 and four shared structural
    # ribs.  Restore only those measured shell planes; z=126..132 remains air,
    # so the rejected observation room itself cannot return.
    accents = {
        -12: "minecraft:orange_concrete",
        30: "minecraft:purple_concrete",
        72: "minecraft:red_concrete",
    }
    for centre in HANGAR_CENTRES:
        accent = accents[centre]
        for x in range(centre - 18, centre + 19):
            relative_x = x - centre
            for y in range(-386, -377):
                mullion = relative_x % 6 == 0 or y == -378
                lamp = mullion and (relative_x % 12 == 0
                                    or (y + 405) % 9 == 0)
                state = ("minecraft:sea_lantern" if lamp
                         else accent if mullion and relative_x % 12 == 6
                         else "minecraft:polished_blackstone_bricks"
                         if mullion else "projectseele:clear_glass")
                add(changes, cells, (x, y, 133), state,
                    "restore_wet_cage_front_pressure_shell")
        for side_x in (centre - 20, centre + 20):
            for z in range(134, 141):
                for y in range(-386, -372):
                    state = ("minecraft:sea_lantern"
                             if y in (-384, -378)
                             else "minecraft:polished_blackstone_bricks")
                    add(changes, cells, (side_x, y, z), state,
                        "restore_wet_cage_shared_rib")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s27_hangar_lift_{stamp}"
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
