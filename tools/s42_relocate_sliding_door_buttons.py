#!/usr/bin/env python3
"""Move S41 command-door buttons from lintels to the two side jambs."""

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
PACKET = "S42-SLIDING-DOOR-SIDE-BUTTONS-R01"
S41 = ROOT / "artifacts/s41_command_sliding_doors_20260821_211108"
MARKER = ".projectseele_command_sliding_doors_r01.json"


def preimage() -> dict[tuple[int, int, int], str]:
    result = {}
    with (S41 / "block_diff.csv").open(
            encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["reason"] == "install_sliding_door_button":
                result[(int(row["x"]), int(row["y"]),
                        int(row["z"]))] = row["before"]
    return result


def plan(world: Path) -> tuple[list[Change], list[dict]]:
    cells = read_box(world, DIMENSION, (-20, -445, 225),
                     (80, -400, 380), None)
    doors = json.loads((S41 / "receipt.json").read_text(
        encoding="utf-8"))["doors"]
    old_buttons = preimage()
    changes: dict[tuple[int, int, int], Change] = {}

    def add(pos: tuple[int, int, int], after: str, reason: str) -> None:
        before = cells.get(pos, "minecraft:air")
        if before != after:
            changes[pos] = Change(
                PACKET, *pos, before, after,
                "human_authorized_command_sliding_doors", reason)

    for pos, before in old_buttons.items():
        current = cells.get(pos, "minecraft:air")
        if not current.startswith("minecraft:stone_button["):
            raise RuntimeError(f"S41 lintel button changed at {pos}: {current}")
        add(pos, before, "remove_lintel_button")

    result = []
    used: set[tuple[int, int, int]] = set()
    for door in doors:
        x, y, z = map(int, door["lower"])
        facing = door["facing"]
        axis_x = door["axis"] == "x"
        wx, wz = ((1, 0) if axis_x else (0, 1))
        nx, nz = ((0, 1) if axis_x else (1, 0))
        front_sign = 1 if facing in {"south", "east"} else -1
        chosen = []
        for width_sign in (-1, 1):
            selection = None
            for distance in (2, 3, 4):
                for height, normal_sign in (
                        (1, front_sign), (1, -front_sign),
                        (0, front_sign), (0, -front_sign),
                        (2, front_sign), (2, -front_sign)):
                    pos = (x + wx * width_sign * distance
                           + nx * normal_sign,
                           y + height,
                           z + wz * width_sign * distance
                           + nz * normal_sign)
                    if (pos in used
                            or cells.get(pos, "minecraft:air") not in AIR):
                        continue
                    selection = (pos, height, normal_sign, distance)
                    break
                if selection is not None:
                    break
            if selection is None:
                raise RuntimeError(
                    f"door {door['id']} has no free side-button cell at "
                    f"width sign {width_sign}")
            pos, height, normal_sign, distance = selection
            support = (x + wx * width_sign * distance, y + height,
                       z + wz * width_sign * distance)
            add(support, "minecraft:iron_block", "install_silver_button_jamb")
            if nx:
                button_facing = "east" if normal_sign > 0 else "west"
            else:
                button_facing = "south" if normal_sign > 0 else "north"
            add(pos, "minecraft:stone_button[face=wall,facing="
                + button_facing + ",powered=false]",
                "install_left_right_door_button")
            used.add(pos)
            chosen.append(list(pos))
        result.append({**door, "buttons": chosen})

    return (sorted(changes.values(), key=lambda c: (c.y, c.z, c.x)),
            result)


def apply(world: Path, changes: list[Change], doors: list[dict]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s42_sliding_door_buttons_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    root = dimension_dir(world, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)
    originals = {}
    replaced = []
    try:
        for (rx, rz), selected in sorted(by_region.items()):
            path = root / "region" / f"r.{rx}.{rz}.mca"
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

    for filename, reverse in (("block_diff.csv", False),
                              ("inverse_patch.csv", True)):
        with (artifact / filename).open("w", encoding="utf-8",
                                        newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("x", "y", "z", "before", "after", "reason"))
            for change in changes:
                writer.writerow((change.x, change.y, change.z,
                                 change.after if reverse else change.before,
                                 change.before if reverse else change.after,
                                 change.reason))
    receipt = {
        "schema": 1,
        "status": "APPLIED_WITH_EXACT_REGION_BACKUP",
        "packet": PACKET,
        "world": str(world),
        "doors": doors,
        "blocks": len(changes),
        "reasons": dict(sorted(Counter(
            change.reason for change in changes).items())),
        "regionBeforeSha256": {
            path.name: hashlib.sha256(data).hexdigest()
            for path, data in originals.items()
        },
    }
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (world / MARKER).write_text(json.dumps({
        "schema": 2,
        "packet": PACKET,
        "doors": doors,
        "artifact": str(artifact.resolve()),
    }, indent=2) + "\n", encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = args.world.resolve()
    changes, doors = plan(world)
    summary = {
        "packet": PACKET,
        "world": str(world),
        "doorCount": len(doors),
        "buttons": sum(len(door["buttons"]) for door in doors),
        "blocks": len(changes),
        "buttonPositions": {str(door["id"]): door["buttons"]
                            for door in doors},
        "reasons": dict(sorted(Counter(
            change.reason for change in changes).items())),
    }
    print(json.dumps(summary, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes, doors))},
                         indent=2))


if __name__ == "__main__":
    main()
