#!/usr/bin/env python3
"""Install the four measured R28 MTR corridor edits requested on 2026-08-21."""

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
PACKET = "S39-REQUESTED-MTR-CORRIDOR-LINKS-R01"
S37_DIFF = ROOT / "artifacts/s37_mtr_three_bays_20260821_000141/block_diff.csv"
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
FLOOR = {"minecraft:polished_deepslate", "minecraft:sea_lantern"}
B_SEGMENTS = ((-30, 6, "EVA-00"), (12, 48, "EVA-01"),
              (54, 87, "EVA-02"))


def orientation(value: int, minimum: int, maximum: int,
                facing: str) -> str:
    forward = facing in {"east", "south"}
    if value == minimum:
        return "landing_bottom" if forward else "landing_top"
    if value == maximum:
        return "landing_top" if forward else "landing_bottom"
    return "flat"


def mtr_state(block: str, *, facing: str, orientation_value: str,
              side: str, direction: bool = True) -> str:
    properties = [f"facing={facing}",
                  f"orientation={orientation_value}", f"side={side}"]
    if block == "escalator_step":
        properties = [f"direction={str(direction).lower()}",
                      *properties, "status=true"]
    return f"mtr:{block}[{','.join(properties)}]"


def s37_floor_before() -> dict[tuple[int, int, int], str]:
    result: dict[tuple[int, int, int], str] = {}
    with S37_DIFF.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            pos = (int(row["x"]), int(row["y"]), int(row["z"]))
            if pos[1] == -371 and pos[2] in (189, 196):
                result[pos] = row["before"]
    return result


def plan(world: Path) -> list[Change]:
    a = read_box(world, DIMENSION, (61, -443, 271),
                 (125, -442, 275), None)
    b = read_box(world, DIMENSION, (-30, -371, 189),
                 (87, -370, 196), None)
    cd = read_box(world, DIMENSION, (-36, -395, 125),
                  (105, -389, 222), None)
    current = {**a, **b, **cd}
    changes: dict[tuple[int, int, int], Change] = {}

    def add(pos: tuple[int, int, int], after: str, reason: str) -> None:
        before = current.get(pos, "minecraft:air")
        if before == after:
            return
        changes[pos] = Change(PACKET, *pos, before, after,
                              "human_authorized_mtr_corridor_links", reason)

    def require_floor(pos: tuple[int, int, int], label: str) -> None:
        state = current.get(pos, "minecraft:air")
        if state not in FLOOR:
            raise RuntimeError(f"{label} floor changed at {pos}: {state}")

    def require_air(pos: tuple[int, int, int], label: str) -> None:
        state = current.get(pos, "minecraft:air")
        if state not in AIR:
            raise RuntimeError(f"{label} clearance changed at {pos}: {state}")

    # A — continue the existing paired incline across the measured long hall
    # to the glass vestibule before the physical lift at 130,-442,269.
    for x in range(61, 126):
        o = orientation(x, 61, 125, "east")
        for z, side, direction in (
                (271, "left", True), (272, "right", True),
                (274, "left", False), (275, "right", False)):
            require_floor((x, -443, z), "lift-link walkway")
            require_air((x, -442, z), "lift-link handrail")
            add((x, -443, z), mtr_state(
                "escalator_step", facing="east", orientation_value=o,
                side=side, direction=direction),
                "extend_walkway_to_personnel_lift")
            add((x, -442, z), mtr_state(
                "escalator_side", facing="east", orientation_value=o,
                side=side), "extend_walkway_handrail")

    # B — move both two-wide EVA-gallery runs inward by exactly one block.
    original_floor = s37_floor_before()
    for x_min, x_max, bay in B_SEGMENTS:
        for x in range(x_min, x_max + 1):
            east_o = orientation(x, x_min, x_max, "east")
            west_o = orientation(x, x_min, x_max, "west")
            for z in (189, 190, 195, 196):
                step = current.get((x, -371, z), "minecraft:air")
                side = current.get((x, -370, z), "minecraft:air")
                if not step.startswith("mtr:escalator_step["):
                    raise RuntimeError(
                        f"{bay} current step changed at {(x, -371, z)}: {step}")
                if not side.startswith("mtr:escalator_side["):
                    raise RuntimeError(
                        f"{bay} current side changed at {(x, -370, z)}: {side}")
            for z in (191, 194):
                require_floor((x, -371, z), f"{bay} inward lane")
                require_air((x, -370, z), f"{bay} inward handrail")

            for retired_z in (189, 196):
                before_floor = original_floor.get((x, -371, retired_z))
                if before_floor not in FLOOR:
                    raise RuntimeError(
                        f"missing exact S37 floor for {(x, -371, retired_z)}")
                add((x, -371, retired_z), before_floor,
                    f"{bay.lower()}_restore_outer_floor")
                add((x, -370, retired_z), "minecraft:air",
                    f"{bay.lower()}_remove_outer_handrail")

            for z, side in ((190, "left"), (191, "right")):
                add((x, -371, z), mtr_state(
                    "escalator_step", facing="east",
                    orientation_value=east_o, side=side),
                    f"{bay.lower()}_east_lane_inward")
                add((x, -370, z), mtr_state(
                    "escalator_side", facing="east",
                    orientation_value=east_o, side=side),
                    f"{bay.lower()}_east_handrail_inward")
            for z, side in ((194, "right"), (195, "left")):
                add((x, -371, z), mtr_state(
                    "escalator_step", facing="west",
                    orientation_value=west_o, side=side),
                    f"{bay.lower()}_west_lane_inward")
                add((x, -370, z), mtr_state(
                    "escalator_side", facing="west",
                    orientation_value=west_o, side=side),
                    f"{bay.lower()}_west_handrail_inward")

    # C — extend the x=98..103 north/south passage two blocks east.  Keep the
    # floor and roof, move only the measured wall skin from x=103 to x=105.
    for z in range(141, 223):
        for x in (104, 105):
            require_air((x, -395, z), "east passage floor extension")
            add((x, -395, z), "minecraft:polished_deepslate",
                "extend_north_south_passage_floor_east")
        for y in range(-394, -389):
            wall = current.get((103, y, z), "minecraft:air")
            if wall not in {"minecraft:polished_blackstone_bricks",
                            "projectseele:clear_glass",
                            "minecraft:reinforced_deepslate"}:
                raise RuntimeError(
                    f"east passage wall changed at {(103, y, z)}: {wall}")
            require_air((105, y, z), "east passage wall target")
            add((103, y, z), "minecraft:air",
                "open_old_east_wall_plane")
            add((105, y, z), wall, "move_east_wall_two_blocks")
        if current.get((103, -389, z)) != "minecraft:reinforced_deepslate":
            raise RuntimeError(f"east passage roof changed at {(103, -389, z)}")
        for x in (104, 105):
            require_air((x, -389, z), "east passage roof extension")
            add((x, -389, z), "minecraft:reinforced_deepslate",
                "extend_north_south_passage_roof_east")

        # z=222 is the measured end wall; the moving walks stop one block
        # before it while the shell extension still closes that final plane.
        if z == 222:
            continue
        north_o = orientation(z, 141, 221, "north")
        south_o = orientation(z, 141, 221, "south")
        for x, side in ((99, "left"), (100, "right")):
            require_floor((x, -395, z), "northbound passage lane")
            require_air((x, -394, z), "northbound passage handrail")
            add((x, -395, z), mtr_state(
                "escalator_step", facing="north",
                orientation_value=north_o, side=side),
                "northbound_passage_step")
            add((x, -394, z), mtr_state(
                "escalator_side", facing="north",
                orientation_value=north_o, side=side),
                "northbound_passage_handrail")
        for x, side in ((103, "right"), (104, "left")):
            if x == 103:
                require_floor((x, -395, z), "southbound passage lane")
            add((x, -395, z), mtr_state(
                "escalator_step", facing="south",
                orientation_value=south_o, side=side),
                "southbound_passage_step")
            add((x, -394, z), mtr_state(
                "escalator_side", facing="south",
                orientation_value=south_o, side=side),
                "southbound_passage_handrail")

    # D — two left-traffic pairs along the complete x=-35..102 hall.  The
    # selected z lanes were measured as uninterrupted polished floor with
    # empty headroom and avoid the coloured EVA bay markers at z=136.
    for x in range(-35, 103):
        east_o = orientation(x, -35, 102, "east")
        west_o = orientation(x, -35, 102, "west")
        for z, facing, side, o, reason in (
                (127, "east", "left", east_o, "eastbound_long_hall"),
                (128, "east", "right", east_o, "eastbound_long_hall"),
                (137, "west", "right", west_o, "westbound_long_hall"),
                (138, "west", "left", west_o, "westbound_long_hall")):
            require_floor((x, -395, z), reason)
            require_air((x, -394, z), reason + " handrail")
            add((x, -395, z), mtr_state(
                "escalator_step", facing=facing, orientation_value=o,
                side=side), reason + "_step")
            add((x, -394, z), mtr_state(
                "escalator_side", facing=facing, orientation_value=o,
                side=side), reason + "_handrail")

    return sorted(changes.values(), key=lambda c: (c.y, c.z, c.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s39_requested_mtr_links_{stamp}"
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
    summary = {
        "packet": PACKET,
        "world": str(world),
        "blocks": len(changes),
        "reasons": dict(sorted(Counter(
            change.reason for change in changes).items())),
    }
    print(json.dumps(summary, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
