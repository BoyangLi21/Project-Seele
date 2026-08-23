#!/usr/bin/env python3
"""Build the measured upper-pyramid Commander Ikari office in R28.

The packet owns only the human-authored 51x51 floor at y=-330 and the exact
existing stepped shell above it.  It never infers or expands the pyramid:
shell glass is a material substitution on measured non-air perimeter cells.
Every write carries the full decoded before-state and each touched region is
copied beside the receipt before atomic replacement.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
DIMENSION = "projectseele:geofront"
PACKET = "S21-COMMANDER-OFFICE-R01"
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
CLEAR_GLASS = "projectseele:clear_glass"


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def add(desired: dict[tuple[int, int, int], Change], cells: dict,
        position: tuple[int, int, int], after: str, reason: str) -> None:
    before = cells.get(position, "minecraft:air")
    if before == after:
        desired.pop(position, None)
        return
    desired[position] = Change(
        PACKET, *position, before, after, "authored_office", reason)


def fill(desired: dict, cells: dict,
         lo: tuple[int, int, int], hi: tuple[int, int, int],
         state: str, reason: str) -> None:
    for x in range(lo[0], hi[0] + 1):
        for y in range(lo[1], hi[1] + 1):
            for z in range(lo[2], hi[2] + 1):
                add(desired, cells, (x, y, z), state, reason)


def frame_wall(desired: dict, cells: dict, z: int,
               x0: int, x1: int, y0: int, y1: int,
               reason: str) -> None:
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            border = x in (x0, x1) or y in (y0, y1)
            state = ("minecraft:polished_blackstone" if border
                     else "minecraft:smooth_quartz")
            add(desired, cells, (x, y, z), state, reason)


def letter(desired: dict, cells: dict, x0: int, y_top: int, z: int,
           rows: tuple[str, ...]) -> None:
    for row, pattern in enumerate(rows):
        for column, value in enumerate(pattern):
            if value == "#":
                add(desired, cells, (x0 + column, y_top - row, z),
                    "minecraft:red_concrete", "original_nerv_wordmark")


def plan(world: Path) -> list[Change]:
    lo, hi = (5, -330, 302), (55, -291, 352)
    cells = read_box(world, DIMENSION, lo, hi)
    desired: dict[tuple[int, int, int], Change] = {}

    # Replace only the measured edge of each existing stepped course.  The
    # crown from y=-302 upward stays opaque and the footprint never expands.
    shell_materials = {
        "minecraft:polished_blackstone", "minecraft:black_concrete",
        "minecraft:orange_concrete", "minecraft:smooth_quartz",
        "minecraft:reinforced_deepslate",
    }
    for y in range(-329, -302):
        # Nearby invisible lights are not pyramid geometry and can extend the
        # layer bbox far outside the stepped course.  Derive each course only
        # from the measured shell palette.
        layer = [(position, state) for position, state in cells.items()
                 if position[1] == y and bare(state) in shell_materials]
        if not layer:
            raise RuntimeError(f"missing measured pyramid course y={y}")
        xs = [position[0] for position, _ in layer]
        zs = [position[2] for position, _ in layer]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)
        for position, state in layer:
            x, _, z = position
            if (x not in (min_x, max_x) and z not in (min_z, max_z)):
                continue
            add(desired, cells, position, CLEAR_GLASS,
                "preserve_stepped_shell_as_clear_glass")

    # The y=-322 test slab made the new level only seven blocks high.  Remove
    # its white interior, while the measured perimeter was already converted
    # above as part of the exact shell course.
    removed_slab = 0
    for x in range(11, 50):
        for z in range(308, 347):
            position = (x, -322, z)
            state = cells.get(position, "minecraft:air")
            if bare(state) == "minecraft:white_concrete":
                add(desired, cells, position, "minecraft:air",
                    "open_double_height_commander_hall")
                removed_slab += 1
            elif bare(state) not in AIR:
                raise RuntimeError(
                    f"authored object inside removable slab at {position}: {state}")
    if removed_slab != 1521:
        raise RuntimeError(
            f"expected 1521 white slab cells, measured {removed_slab}")

    # Close the single measured accidental pinhole in the new floor.
    add(desired, cells, (53, -330, 350), "minecraft:white_concrete",
        "close_single_floor_pinhole")

    # A dark axial inlay keeps the enormous room legible without turning it
    # into another command centre.
    for x in range(27, 34):
        for z in range(310, 345):
            if x in (27, 33):
                state = "minecraft:polished_blackstone"
            elif x == 30:
                state = "minecraft:red_concrete"
            else:
                state = "minecraft:black_concrete"
            add(desired, cells, (x, -330, z), state,
                "commander_axis_floor_inlay")

    # North: formal desk wall and an original block-built NERV wordmark.
    frame_wall(desired, cells, 311, 20, 40, -329, -315,
               "commander_north_feature_wall")
    glyphs = (
        (21, ("#..#", "##.#", "#.##", "#..#", "#..#")),
        (26, ("###", "#..", "##.", "#..", "###")),
        (30, ("###.", "#..#", "###.", "#.#.", "#..#")),
        (35, ("#...#", "#...#", ".#.#.", ".#.#.", "..#..")),
    )
    for x0, rows in glyphs:
        letter(desired, cells, x0, -319, 311, rows)

    # South: white Tree-of-Life plate.  The actual local image is rendered by
    # TreeOfLifeWallClient on the north-facing side of this wall.
    frame_wall(desired, cells, 340, 20, 40, -329, -315,
               "tree_of_life_feature_wall")

    # Commander desk: low black slab with quartz side pedestals.  Its high-back
    # chair sits on the room axis, facing south into the hall.
    desk_slab = "minecraft:polished_blackstone_slab[type=top,waterlogged=false]"
    fill(desired, cells, (24, -329, 315), (36, -329, 318), desk_slab,
         "commander_desk_surface")
    fill(desired, cells, (24, -329, 315), (25, -329, 318),
         "minecraft:smooth_quartz", "commander_desk_left_pedestal")
    fill(desired, cells, (35, -329, 315), (36, -329, 318),
         "minecraft:smooth_quartz", "commander_desk_right_pedestal")
    add(desired, cells, (30, -329, 313),
        "projectseele:command_seat_back[facing=south]",
        "commander_high_back")
    add(desired, cells, (30, -329, 314),
        "minecraft:dark_oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]",
        "commander_chair_seat")
    add(desired, cells, (23, -329, 314),
        "minecraft:dark_oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]",
        "deputy_chair")

    # Central conference table and restrained seating.  The table is long but
    # leaves clear circulation around both feature walls and the glass shell.
    fill(desired, cells, (28, -329, 322), (32, -329, 336), desk_slab,
         "conference_table_surface")
    for z in (324, 328, 332, 336):
        add(desired, cells, (26, -329, z),
            "minecraft:dark_oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]",
            "conference_chair_west")
        add(desired, cells, (34, -329, z),
            "minecraft:dark_oak_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]",
            "conference_chair_east")
    add(desired, cells, (30, -329, 338),
        "minecraft:dark_oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]",
        "conference_chair_south")
    add(desired, cells, (30, -329, 320),
        "minecraft:dark_oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]",
        "conference_chair_north")

    # Invisible, non-colliding light points replace a false luminous ceiling.
    for x in (18, 30, 42):
        for z in (317, 327, 337):
            add(desired, cells, (x, -323, z),
                "minecraft:light[level=14]", "office_indirect_light")

    return sorted(desired.values(), key=lambda c: (c.y, c.z, c.x))


def region_path(root: Path, rx: int, rz: int) -> Path:
    return root / "region" / f"r.{rx}.{rz}.mca"


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s21_commander_office_{stamp}"
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

    reason_counts = Counter(change.reason for change in changes)
    receipt = {
        "status": "APPLIED_WITH_EXACT_REGION_BACKUP",
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "bbox": [5, -330, 302, 55, -291, 352],
        "reasons": dict(sorted(reason_counts.items())),
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
        artifact = apply(world, changes)
        print(json.dumps({"applied": True, "artifact": str(artifact)},
                         indent=2))


if __name__ == "__main__":
    main()
