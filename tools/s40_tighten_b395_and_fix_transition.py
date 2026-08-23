#!/usr/bin/env python3
"""Tighten the B395 walks and repair the reversed upper transition."""

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
from s39_install_requested_mtr_links import mtr_state, orientation


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S40-TIGHTEN-B395-AND-REPAIR-TRANSITION-R01"
S39_DIFF = ROOT / "artifacts/s39_requested_mtr_links_20260821_202611/block_diff.csv"
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
FLOOR = {"minecraft:polished_deepslate", "minecraft:sea_lantern"}


def previous_states() -> dict[tuple[int, int, int], str]:
    result = {}
    with S39_DIFF.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["reason"].startswith(("eastbound_long_hall_",
                                         "westbound_long_hall_")):
                result[(int(row["x"]), int(row["y"]),
                        int(row["z"]))] = row["before"]
    return result


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION, (-35, -395, 127),
                     (102, -394, 138), None)
    cells.update(read_box(world, DIMENSION, (56, -443, 274),
                          (56, -442, 275), None))
    old = previous_states()
    changes: dict[tuple[int, int, int], Change] = {}
    old_lanes = (127, 128, 137, 138)
    walk_x = [x for x in range(-35, 103)
              if all(cells.get((x, -395, z), "").startswith(
                     "mtr:escalator_step[") for z in old_lanes)]
    if not walk_x or walk_x != list(range(walk_x[0], walk_x[-1] + 1)):
        raise RuntimeError(f"B395 current walkway is not one run: {walk_x}")

    def add(pos: tuple[int, int, int], after: str, reason: str) -> None:
        before = cells.get(pos, "minecraft:air")
        if before != after:
            changes[pos] = Change(
                PACKET, *pos, before, after,
                "human_authorized_mtr_corridor_links", reason)

    # The long hall's former outer lanes are restored from the exact S39
    # preimage, never guessed from a repeating floor pattern.
    for x in walk_x:
        for z in old_lanes:
            step_pos = (x, -395, z)
            side_pos = (x, -394, z)
            if not cells.get(step_pos, "").startswith(
                    "mtr:escalator_step["):
                raise RuntimeError(f"old B395 step changed at {step_pos}")
            if not cells.get(side_pos, "").startswith(
                    "mtr:escalator_side["):
                raise RuntimeError(f"old B395 side changed at {side_pos}")
            if old.get(step_pos) not in FLOOR or old.get(side_pos) not in AIR:
                raise RuntimeError(f"missing exact S39 preimage at {step_pos}")
            add(step_pos, old[step_pos], "restore_wide_lane_floor")
            add(side_pos, old[side_pos], "remove_wide_lane_handrail")

        east_o = orientation(x, walk_x[0], walk_x[-1], "east")
        west_o = orientation(x, walk_x[0], walk_x[-1], "west")
        for z, facing, side, o, reason in (
                (130, "east", "left", east_o, "eastbound_tight"),
                (131, "east", "right", east_o, "eastbound_tight"),
                (134, "west", "right", west_o, "westbound_tight"),
                (135, "west", "left", west_o, "westbound_tight")):
            step_pos = (x, -395, z)
            side_pos = (x, -394, z)
            if cells.get(step_pos, "minecraft:air") not in FLOOR:
                raise RuntimeError(
                    f"new B395 floor changed at {step_pos}: "
                    f"{cells.get(step_pos)}")
            if cells.get(side_pos, "minecraft:air") not in AIR:
                raise RuntimeError(
                    f"new B395 clearance changed at {side_pos}: "
                    f"{cells.get(side_pos)}")
            add(step_pos, mtr_state(
                "escalator_step", facing=facing, orientation_value=o,
                side=side), reason + "_step")
            add(side_pos, mtr_state(
                "escalator_side", facing=facing, orientation_value=o,
                side=side), reason + "_handrail")

    # Reversed equivalent of the original east-facing transition_top.  The
    # west-facing flat run keeps direction=true, while transition_bottom makes
    # its west edge meet the lower east-facing slope at x=55.
    for z, side in ((274, "right"), (275, "left")):
        step_pos = (56, -443, z)
        side_pos = (56, -442, z)
        if not cells.get(step_pos, "").startswith("mtr:escalator_step["):
            raise RuntimeError(f"broken transition changed at {step_pos}")
        if not cells.get(side_pos, "").startswith("mtr:escalator_side["):
            raise RuntimeError(f"broken transition side changed at {side_pos}")
        add(step_pos, mtr_state(
            "escalator_step", facing="west",
            orientation_value="transition_bottom", side=side),
            "connect_upper_transition_to_lower_slope")
        add(side_pos, mtr_state(
            "escalator_side", facing="west",
            orientation_value="transition_bottom", side=side),
            "connect_transition_handrail")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s40_tighten_b395_{stamp}"
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

    for name, reverse in (("block_diff.csv", False),
                          ("inverse_patch.csv", True)):
        with (artifact / name).open("w", encoding="utf-8",
                                    newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("x", "y", "z", "before", "after", "reason"))
            for change in changes:
                writer.writerow((change.x, change.y, change.z,
                                 change.after if reverse else change.before,
                                 change.before if reverse else change.after,
                                 change.reason))
    receipt = {
        "status": "APPLIED_WITH_EXACT_REGION_BACKUP",
        "packet": PACKET,
        "world": str(world),
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
        "reasons": dict(sorted(Counter(
            change.reason for change in changes).items())),
    }, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
