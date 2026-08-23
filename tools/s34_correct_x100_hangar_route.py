#!/usr/bin/env python3
"""Restore EVA-02 cage wall and finish the human x100 straight route."""

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
PACKET = "S34-X100-STRAIGHT-HANGAR-ROUTE-R01"
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
                          "human_authorized_x100_route", reason)


def wall_state(z: int, y: int) -> str:
    if y in (HEAD_Y0, HEAD_Y1):
        return TRIM
    return FRAME if (z - 139) % 6 == 0 else GLASS


def restore_wrong_s33_spur(changes: dict, cells: dict) -> None:
    candidates = sorted(ROOT.glob(
        "artifacts/s33_b49_interchange_*/block_diff.csv"))
    source = None
    for path in reversed(candidates):
        rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
        if any(row["reason"] == "open_hangar_vestibule_port"
               for row in rows):
            source = (path, rows)
            break
    if source is None:
        raise RuntimeError("authoritative S33 interchange receipt is missing")

    retired = {
        "hangar_vestibule_floor",
        "hangar_vestibule_roof",
        "hangar_vestibule_wall",
        "hangar_vestibule_east_wall",
        "open_hangar_vestibule_port",
    }
    for row in source[1]:
        if row["reason"] not in retired:
            continue
        pos = (int(row["x"]), int(row["y"]), int(row["z"]))
        # The world is authoritative: restore only untouched S33 output and
        # leave any later human edit in place.
        if cells.get(pos, AIR) == row["after"]:
            add(changes, cells, pos, row["before"],
                "restore_eva02_cage_and_retire_wrong_spur")


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (89, FLOOR_Y, 139), (104, -386, 214), None)
    changes: dict[tuple[int, int, int], Change] = {}
    restore_wrong_s33_spur(changes, cells)

    # Follow the human floor exactly: six blocks wide at x=98..103 and
    # perfectly straight from z=139 to z=214.  The north end enters the
    # existing hangar access floor; the south end opens into the new B-49
    # compact-lift interchange.
    for x in range(98, 104):
        for z in range(139, 215):
            state = (LIGHT if x in (100, 101)
                     and (z - 141) % 8 == 0 else FLOOR)
            add(changes, cells, (x, FLOOR_Y, z), state,
                "x100_straight_corridor_floor")

    for x in range(99, 103):
        for z in range(140, 214):
            for y in range(HEAD_Y0, HEAD_Y1 + 1):
                add(changes, cells, (x, y, z), AIR,
                    "x100_straight_corridor_clearance")

    for x in (98, 103):
        for z in range(140, 214):
            if x == 98 and 204 <= z <= 210:
                for y in range(HEAD_Y0, HEAD_Y1 + 1):
                    add(changes, cells, (x, y, z), AIR,
                        "retain_compact_lift_interchange_opening")
                continue
            for y in range(HEAD_Y0, HEAD_Y1 + 1):
                add(changes, cells, (x, y, z), wall_state(z, y),
                    "x100_straight_corridor_wall")

    for x in range(98, 104):
        for z in range(140, 214):
            state = (LIGHT if x in (100, 101)
                     and (z - 145) % 8 == 0 else FRAME)
            add(changes, cells, (x, ROOF_Y, z), state,
                "x100_straight_corridor_roof")

    # Open ends with full-width headers.  No westward hole is created in the
    # EVA-02 cage; the corridor meets the already-authored floor at z=139.
    for z in (139, 214):
        for x in range(99, 103):
            for y in range(HEAD_Y0, HEAD_Y1 + 1):
                add(changes, cells, (x, y, z), AIR,
                    "x100_straight_corridor_open_end")
        for x in range(98, 104):
            add(changes, cells, (x, ROOF_Y, z),
                LIGHT if x in (100, 101) else FRAME,
                "x100_straight_corridor_header")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def region_path(root: Path, rx: int, rz: int) -> Path:
    path = root / "region" / f"r.{rx}.{rz}.mca"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s34_x100_route_{stamp}"
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
