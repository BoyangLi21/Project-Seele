#!/usr/bin/env python3
"""Apply the approved office revision and Terminal Dogma access route.

The office revision restores the measured pyramid skin above y=-314, changes
only the remaining office glazing to directional one-way glass, builds an
unframed black NERV wall and white Tree wall, and copies the two
human-nominated chair styles.
The infrastructure revision retires two exact abandoned shaft footprints and
extends the existing x12/z253 lift down to a measured Terminal Dogma walkway.
Every touched region is copied before one atomic rewrite.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import csv
import hashlib
import json
from pathlib import Path
import shutil
import time

from apply_s20_approved_semantic_repairs import (
    Change,
    atomic_replace,
    rewrite_region,
)
from query_blocks import dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
PRE_OFFICE = ROOT / "backups/SEELE_R28_PRE_COMMANDER_OFFICE_20260811_212555"
DIMENSION = "projectseele:geofront"
PACKET = "S21-OFFICE-DOGMA-ACCESS-R02"
AIR_NAMES = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
AIR = "minecraft:air"
CLEAR_GLASS = "projectseele:clear_glass"
ONE_WAY = "projectseele:one_way_glass"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def add(desired: dict[tuple[int, int, int], Change], cells: dict,
        position: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(position, AIR)
    if before == after:
        desired.pop(position, None)
        return
    desired[position] = Change(
        PACKET, *position, before, after, "bounded_authored_edit", reason)


def fill(desired: dict, cells: dict, lo: tuple[int, int, int],
         hi: tuple[int, int, int], state: str, reason: str) -> None:
    for x in range(lo[0], hi[0] + 1):
        for y in range(lo[1], hi[1] + 1):
            for z in range(lo[2], hi[2] + 1):
                add(desired, cells, (x, y, z), state, reason)


def set_if_air(desired: dict, cells: dict,
               position: tuple[int, int, int], after: str,
               reason: str) -> None:
    if bare(cells.get(position, AIR)) in AIR_NAMES:
        add(desired, cells, position, after, reason)


def one_way_state(x: int, z: int) -> str:
    dx, dz = x - 30, z - 327
    if abs(dx) >= abs(dz):
        facing = "east" if dx > 0 else "west"
    else:
        facing = "south" if dz > 0 else "north"
    return f"{ONE_WAY}[facing={facing}]"


def chair(desired: dict, cells: dict, centre: tuple[int, int, int],
          facing: str, commander: bool, reason: str) -> None:
    x, y, z = centre
    vectors = {
        "north": ((0, 1), (-1, 0), (1, 0), "west", "east"),
        "south": ((0, -1), (-1, 0), (1, 0), "west", "east"),
        "east": ((-1, 0), (0, -1), (0, 1), "north", "south"),
        "west": ((1, 0), (0, -1), (0, 1), "north", "south"),
    }
    back, left, right, left_face, right_face = vectors[facing]
    wood = "mangrove" if commander else "dark_oak"
    stool = "red" if commander else "black"
    add(desired, cells, centre,
        f"another_furniture:{stool}_stool[low=false,waterlogged=false]",
        reason + "_seat")
    add(desired, cells, (x + left[0], y, z + left[1]),
        f"minecraft:{wood}_wall_sign[facing={left_face},waterlogged=false]",
        reason + "_left_arm")
    add(desired, cells, (x + right[0], y, z + right[1]),
        f"minecraft:{wood}_wall_sign[facing={right_face},waterlogged=false]",
        reason + "_right_arm")
    bx, bz = x + back[0], z + back[1]
    add(desired, cells, (bx, y, bz),
        f"projectseele:command_seat_back[facing={facing},half=lower]",
        reason + "_back_lower")
    add(desired, cells, (bx, y + 1, bz),
        f"projectseele:command_seat_back[facing={facing},half=upper]",
        reason + "_back_upper")
    if commander:
        add(desired, cells, (x, y + 1, z),
            f"minecraft:red_wall_banner[facing={facing}]",
            reason + "_commander_banner")


def plan_office(desired: dict, current: dict, original: dict) -> None:
    for position, state in current.items():
        if bare(state) != CLEAR_GLASS:
            continue
        x, y, z = position
        if y >= -314:
            before_office = original.get(position, AIR)
            if bare(before_office) in AIR_NAMES:
                raise RuntimeError(
                    f"cannot restore absent pyramid skin at {position}")
            add(desired, current, position, before_office,
                "restore_original_pyramid_skin_at_and_above_y_minus_314")
        else:
            add(desired, current, position, one_way_state(x, z),
                "commander_office_one_way_glazing")

    # Plain image planes: no frame, lettering or decorative trim.  The NERV
    # emblem is behind Ikari's chair on black; the Tree faces it on white.
    fill(desired, current, (20, -329, 311), (40, -315, 311),
         "minecraft:black_concrete", "pure_black_nerv_image_wall")
    fill(desired, current, (20, -329, 340), (40, -315, 340),
         "minecraft:white_concrete", "pure_white_tree_image_wall")

    chair(desired, current, (30, -329, 314), "south", True,
          "copied_ikari_red_command_seat")
    chair(desired, current, (23, -329, 314), "south", False,
          "copied_general_office_seat")
    for z in (324, 328, 332, 336):
        chair(desired, current, (26, -329, z), "east", False,
              "copied_conference_seat_west")
        chair(desired, current, (34, -329, z), "west", False,
              "copied_conference_seat_east")
    chair(desired, current, (30, -329, 338), "north", False,
          "copied_conference_seat_south")
    chair(desired, current, (30, -329, 320), "south", False,
          "copied_conference_seat_north")


def strata(y: int) -> str:
    if y <= -576:
        return "minecraft:deepslate"
    if y <= -512:
        return "minecraft:tuff"
    return "minecraft:stone"


def retire_shaft(desired: dict, cells: dict,
                 box: tuple[int, int, int, int, int, int],
                 reason: str) -> None:
    x0, y0, z0, x1, y1, z1 = box
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                after = strata(y) if y <= -467 else AIR
                add(desired, cells, (x, y, z), after, reason)


def build_dogma_route(desired: dict, cells: dict) -> None:
    # Extend the measured 7x7 shaft shell without altering its 5x5 car sweep.
    for y in range(-566, -450):
        for x in range(9, 16):
            for z in range(250, 257):
                perimeter = x in (9, 15) or z in (250, 256)
                if not perimeter:
                    continue
                if z == 250 and 10 <= x <= 14 and -566 <= y <= -564:
                    continue
                state = ("minecraft:sea_lantern"
                         if y % 12 == 0 and (x, z) in ((9, 253), (15, 253))
                         else "minecraft:reinforced_deepslate")
                set_if_air(desired, cells, (x, y, z), state,
                           "extend_x12_z253_pressure_shaft")

    floor = "minecraft:polished_deepslate"
    wall = "minecraft:deepslate_bricks"
    roof = "minecraft:black_concrete"

    # East-west pressure corridor, exactly aligned to the new north landing.
    for x in range(9, 66):
        for z in range(245, 250):
            set_if_air(desired, cells, (x, -567, z), floor,
                       "terminal_dogma_access_floor")
            set_if_air(desired, cells, (x, -561, z), roof,
                       "terminal_dogma_access_roof")
        for z in (244, 250):
            for y in range(-566, -561):
                if z == 250 and 10 <= x <= 14 and y <= -564:
                    continue
                if z == 250 and 63 <= x <= 65:
                    continue
                set_if_air(desired, cells, (x, y, z), wall,
                           "terminal_dogma_access_sidewall")

    # Three-wide south turn joins the existing x63..66 Terminal Dogma deck.
    for x in range(63, 66):
        for z in range(247, 257):
            set_if_air(desired, cells, (x, -567, z), floor,
                       "terminal_dogma_existing_deck_handoff")
            set_if_air(desired, cells, (x, -561, z), roof,
                       "terminal_dogma_existing_deck_handoff_roof")
    for x in (62, 66):
        for z in range(250, 256):
            for y in range(-566, -561):
                set_if_air(desired, cells, (x, y, z), wall,
                           "terminal_dogma_turn_sidewall")

    # Restrained guide lights; no signs or block entities are introduced.
    for x in range(18, 64, 9):
        set_if_air(desired, cells, (x, -561, 247),
                   "minecraft:sea_lantern", "terminal_dogma_route_light")


def connectivity_gate(desired: dict, cells: dict) -> None:
    def state(position: tuple[int, int, int]) -> str:
        change = desired.get(position)
        return change.after if change else cells.get(position, AIR)

    def walkable(x: int, z: int) -> bool:
        return (bare(state((x, -567, z))) not in AIR_NAMES
                and bare(state((x, -566, z))) in AIR_NAMES
                and bare(state((x, -565, z))) in AIR_NAMES)

    start, goal = (12, 247), (64, 256)
    queue = deque([start])
    seen = {start}
    while queue:
        x, z = queue.popleft()
        if (x, z) == goal:
            return
        for nxt in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if (7 <= nxt[0] <= 68 and 242 <= nxt[1] <= 260
                    and nxt not in seen and walkable(*nxt)):
                seen.add(nxt)
                queue.append(nxt)
    raise RuntimeError(
        "Terminal Dogma landing does not reach the existing deck")


def plan(world: Path) -> list[Change]:
    office_lo, office_hi = (5, -330, 302), (55, -291, 352)
    office = read_box(world, DIMENSION, office_lo, office_hi)
    original = read_box(PRE_OFFICE, DIMENSION, office_lo, office_hi)
    infra = read_box(world, DIMENSION,
                     (5, -581, 244), (98, -438, 320))
    desired: dict[tuple[int, int, int], Change] = {}
    plan_office(desired, office, original)
    retire_shaft(desired, infra, (90, -567, 312, 98, -459, 320),
                 "retire_abandoned_x98_z316_shaft")
    retire_shaft(desired, infra, (67, -581, 268, 77, -438, 278),
                 "retire_abandoned_x72_z273_shaft")
    build_dogma_route(desired, infra)
    connectivity_gate(desired, infra)
    return sorted(desired.values(), key=lambda c: (c.y, c.z, c.x))


def region_path(root: Path, rx: int, rz: int) -> Path:
    return root / "region" / f"r.{rx}.{rz}.mca"


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s21_office_dogma_access_{stamp}"
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
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
