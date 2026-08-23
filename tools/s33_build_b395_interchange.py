#!/usr/bin/env python3
"""Compile the human-authored B-49 bridges into two finished corridors."""

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
PACKET = "S33-B49-HANGAR-INTERCHANGE-R01"
AIR = "minecraft:air"
AIR_STATES = {AIR, "minecraft:void_air", "minecraft:cave_air"}
FLOOR_Y = -395
HEAD_Y0, HEAD_Y1 = -394, -390
ROOF_Y = -389
FRAME = "minecraft:reinforced_deepslate"
TRIM = "minecraft:polished_blackstone_bricks"
FLOOR = "minecraft:polished_deepslate"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"


def add(changes: dict[tuple[int, int, int], Change], cells: dict,
        pos: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(pos, AIR)
    if before == after or (after == AIR and before in AIR_STATES):
        changes.pop(pos, None)
        return
    changes[pos] = Change(PACKET, *pos, before, after,
                          "human_authorized_b49_interchange", reason)


def wall_state(axis: int, y: int) -> str:
    if y in (HEAD_Y0, HEAD_Y1) or axis % 6 == 0:
        return TRIM if y in (HEAD_Y0, HEAD_Y1) else FRAME
    return GLASS


def fill_floor(changes: dict, cells: dict,
               x0: int, x1: int, z0: int, z1: int,
               lights: set[tuple[int, int]], reason: str) -> None:
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            add(changes, cells, (x, FLOOR_Y, z),
                LIGHT if (x, z) in lights else FLOOR, reason)


def clear_headroom(changes: dict, cells: dict,
                   x0: int, x1: int, z0: int, z1: int,
                   reason: str) -> None:
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(HEAD_Y0, HEAD_Y1 + 1):
                add(changes, cells, (x, y, z), AIR, reason)


def roof(changes: dict, cells: dict,
         x0: int, x1: int, z0: int, z1: int,
         light_cells: set[tuple[int, int]], reason: str) -> None:
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            add(changes, cells, (x, ROOF_Y, z),
                LIGHT if (x, z) in light_cells else FRAME, reason)


def retire_wrong_s32_glass(changes: dict, cells: dict) -> None:
    candidates = sorted(ROOT.glob(
        "artifacts/s32_observation_platforms_*/block_diff.csv"))
    if not candidates:
        raise RuntimeError("S32 observation-glass receipt is missing")
    receipt = candidates[-1]
    with receipt.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row["reason"].endswith("full_observation_side_glass"):
                continue
            pos = (int(row["x"]), int(row["y"]), int(row["z"]))
            # Preserve any later human edit.  Only our unchanged S32 glass is
            # eligible for exact restoration to its recorded previous state.
            if cells.get(pos, AIR) == row["after"]:
                add(changes, cells, pos, row["before"],
                    "retire_misplaced_s32_hangar_glass")


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (-31, FLOOR_Y, 133),
                     (105, -386, 244), None)
    changes: dict[tuple[int, int, int], Change] = {}

    retire_wrong_s32_glass(changes, cells)

    # Retire the former east-facing upper landing controls and the temporary
    # remote button in the middle of the human bridge.  Moving Elevators will
    # install one north-facing call at (97,-393,236) on first load.
    for pos in ((99, -393, 244), (98, -393, 244), (98, -392, 244),
                (99, -393, 224), (98, -393, 224), (98, -392, 224)):
        state = cells.get(pos, AIR).split("[", 1)[0]
        if (state in {"minecraft:polished_blackstone_button",
                      "minecraft:black_concrete",
                      "movingelevators:button_block",
                      "movingelevators:display_block"}):
            add(changes, cells, pos, AIR,
                "retire_superseded_elevator_control")

    # A. Six-wide interior between the two lifts, with structural sills,
    # restrained observation glazing and a continuous illuminated roof.
    fill_floor(changes, cells, 90, 97, 209, 237,
               {(93, z) for z in (215, 221, 227, 233)}
               | {(94, z) for z in (215, 221, 227, 233)},
               "interlift_corridor_floor")
    clear_headroom(changes, cells, 91, 96, 209, 236,
                   "interlift_corridor_clearance")
    for x in (90, 97):
        for z in range(209, 237):
            for y in range(HEAD_Y0, HEAD_Y1 + 1):
                add(changes, cells, (x, y, z), wall_state(z, y),
                    "interlift_corridor_wall")
    roof(changes, cells, 90, 97, 209, 236,
         {(93, z) for z in (214, 220, 226, 232)}
         | {(94, z) for z in (214, 220, 226, 232)},
         "interlift_corridor_roof")

    # B. Existing north-running bridge becomes a four-wide glazed service
    # corridor.  Its west wall opens for seven blocks into the compact-lift
    # interchange instead of cutting that lift off.
    fill_floor(changes, cells, 98, 103, 191, 214,
               {(100, z) for z in (195, 201, 207, 213)}
               | {(101, z) for z in (195, 201, 207, 213)},
               "hangar_link_corridor_floor")
    clear_headroom(changes, cells, 99, 102, 191, 214,
                   "hangar_link_corridor_clearance")
    for x in (98, 103):
        for z in range(191, 215):
            if x == 98 and 204 <= z <= 210:
                for y in range(HEAD_Y0, HEAD_Y1 + 1):
                    add(changes, cells, (x, y, z), AIR,
                        "hangar_link_interchange_opening")
                continue
            for y in range(HEAD_Y0, HEAD_Y1 + 1):
                add(changes, cells, (x, y, z), wall_state(z, y),
                    "hangar_link_corridor_wall")
    roof(changes, cells, 98, 103, 191, 214,
         {(100, z) for z in (194, 200, 206, 212)}
         | {(101, z) for z in (194, 200, 206, 212)},
         "hangar_link_corridor_roof")

    # Four-wide lateral opening from the new compact-lift threshold into the
    # hangar link.  The old x=97 shell line was the visible missing connection
    # at (101,-395,207); remove it only across this bounded interchange.
    fill_floor(changes, cells, 96, 99, 204, 210,
               {(98, 207)}, "compact_to_hangar_link_floor")
    clear_headroom(changes, cells, 96, 99, 204, 210,
                   "compact_to_hangar_link_opening")

    # C. A short west-facing vestibule closes the five-block floor gap and
    # opens the measured x=92 hangar wall.  The south wall retains a four-wide
    # opening into corridor B, forming one natural L rather than two bridges.
    fill_floor(changes, cells, 89, 103, 185, 190,
               {(x, 187) for x in (95, 99, 103)},
               "hangar_vestibule_floor")
    clear_headroom(changes, cells, 89, 102, 186, 189,
                   "hangar_vestibule_clearance")
    for z in (185, 190):
        for x in range(89, 104):
            if z == 190 and 99 <= x <= 102:
                continue
            for y in range(HEAD_Y0, HEAD_Y1 + 1):
                add(changes, cells, (x, y, z), wall_state(x, y),
                    "hangar_vestibule_wall")
    for z in range(185, 191):
        for y in range(HEAD_Y0, HEAD_Y1 + 1):
            add(changes, cells, (103, y, z), wall_state(z, y),
                "hangar_vestibule_east_wall")
    for z in range(186, 190):
        for y in range(HEAD_Y0, HEAD_Y1 + 1):
            for x in range(89, 93):
                add(changes, cells, (x, y, z), AIR,
                "open_hangar_vestibule_port")
    roof(changes, cells, 89, 103, 185, 190,
         {(x, 187) for x in (95, 99, 103)},
         "hangar_vestibule_roof")

    # D. Real middle stop for the x=93/z=204 lift.  Remove the human floor
    # only from the exact 5x5 moving-cage prism, retain the south threshold,
    # and give both lift ends a clean five-wide framed aperture.
    for x in range(91, 96):
        for z in range(202, 207):
            for y in range(FLOOR_Y, ROOF_Y + 1):
                add(changes, cells, (x, y, z), AIR,
                    "compact_lift_middle_cage_clearance")
    fill_floor(changes, cells, 90, 97, 207, 210,
               {(93, 209), (94, 209)},
               "compact_lift_middle_threshold")
    for x in range(91, 96):
        for y in range(HEAD_Y0, -391):
            add(changes, cells, (x, y, 208), AIR,
                "compact_lift_middle_doorway")
    for x in (90, 96):
        for y in range(HEAD_Y0, HEAD_Y1 + 1):
            add(changes, cells, (x, y, 208), FRAME,
                "compact_lift_middle_jamb")
    for x in range(90, 97):
        add(changes, cells, (x, ROOF_Y, 208),
            LIGHT if x == 93 else FRAME,
            "compact_lift_middle_header")

    for x in range(92, 97):
        for y in range(HEAD_Y0, -391):
            add(changes, cells, (x, y, 237), AIR,
                "observation_lift_north_doorway")
    for x in (91, 97):
        for y in range(HEAD_Y0, HEAD_Y1 + 1):
            add(changes, cells, (x, y, 237), FRAME,
                "observation_lift_north_jamb")
    for x in range(91, 98):
        add(changes, cells, (x, ROOF_Y, 237),
            LIGHT if x == 94 else FRAME,
            "observation_lift_north_header")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s33_b49_interchange_{stamp}"
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
    changes = plan(args.world.resolve())
    print(json.dumps({
        "packet": PACKET,
        "world": str(args.world.resolve()),
        "blocks": len(changes),
        "reasons": dict(sorted(Counter(c.reason for c in changes).items())),
    }, indent=2))
    if args.apply:
        print(json.dumps({
            "applied": True,
            "artifact": str(apply(args.world.resolve(), changes)),
        }, indent=2))


if __name__ == "__main__":
    main()
