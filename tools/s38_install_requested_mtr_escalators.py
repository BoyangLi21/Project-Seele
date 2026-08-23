#!/usr/bin/env python3
"""Install the three user-requested MTR escalator/moving-walk pairs."""

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
PACKET = "S38-REQUESTED-MTR-ESCALATORS-R01"
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def mtr_state(block: str, *, facing: str, orientation: str,
              side: str, direction: bool = True) -> str:
    properties = [f"facing={facing}", f"orientation={orientation}", f"side={side}"]
    if block == "escalator_step":
        properties = [f"direction={str(direction).lower()}", *properties, "status=true"]
    return f"mtr:{block}[{','.join(properties)}]"


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION, (20, -451, 205), (100, -388, 278), None)
    changes: dict[tuple[int, int, int], Change] = {}

    def add(pos: tuple[int, int, int], after: str, reason: str) -> None:
        before = cells.get(pos, "minecraft:air")
        if before == after:
            return
        changes[pos] = Change(PACKET, *pos, before, after,
                              "human_authorized_mtr_escalators", reason)

    def require_air(pos: tuple[int, int, int], label: str) -> None:
        before = cells.get(pos, "minecraft:air")
        if before not in AIR:
            raise RuntimeError(f"{label} expected air at {pos}, found {before}")

    # A: long north/south corridor.  The east/southbound lane already existed
    # for z=212..223 and the human excavated its continuation to z=269.
    # Extend it without changing its axis, then add the west/northbound lane.
    for z in range(212, 270):
        south_orientation = "landing_bottom" if z == 212 else (
            "landing_top" if z == 269 else "flat")
        north_orientation = "landing_top" if z == 212 else (
            "landing_bottom" if z == 269 else "flat")

        # Facing south: east cell is left and west cell is right.
        for x, side in ((94, "right"), (95, "left")):
            step_pos = (x, -443, z)
            side_pos = (x, -442, z)
            old_step = cells.get(step_pos, "minecraft:air")
            old_side = cells.get(side_pos, "minecraft:air")
            if z <= 223:
                if not old_step.startswith("mtr:escalator_step["):
                    raise RuntimeError(f"existing south step changed at {step_pos}: {old_step}")
                if not old_side.startswith("mtr:escalator_side["):
                    raise RuntimeError(f"existing south side changed at {side_pos}: {old_side}")
            else:
                require_air(step_pos, "excavated south lane")
                require_air(side_pos, "south handrail clearance")
            add(step_pos, mtr_state("escalator_step", facing="south",
                                   orientation=south_orientation, side=side),
                "corridor_southbound_step")
            add(side_pos, mtr_state("escalator_side", facing="south",
                                   orientation=south_orientation, side=side),
                "corridor_southbound_handrail")

        # Facing north: west cell is left and east cell is right.
        for x, side in ((91, "left"), (92, "right")):
            step_pos = (x, -443, z)
            side_pos = (x, -442, z)
            old_step = cells.get(step_pos, "minecraft:air")
            if old_step not in {"minecraft:polished_deepslate",
                                "minecraft:polished_blackstone"}:
                raise RuntimeError(f"north lane floor changed at {step_pos}: {old_step}")
            require_air(side_pos, "north handrail clearance")
            add(step_pos, mtr_state("escalator_step", facing="north",
                                   orientation=north_orientation, side=side),
                "corridor_northbound_step")
            add(side_pos, mtr_state("escalator_side", facing="north",
                                   orientation=north_orientation, side=side),
                "corridor_northbound_handrail")

    # B: mirror the human-built east/up escalator at z=271..272.  The new
    # z=274..275 lane travels west/down and leaves the fixed z=273 stair intact.
    b_profile = (
        (50, -449, "landing_bottom"),
        (51, -448, "slope"),
        (52, -447, "slope"),
        (53, -446, "slope"),
        (54, -445, "slope"),
        (55, -444, "slope"),
        (56, -443, "transition_top"),
        (57, -443, "landing_top"),
    )
    for x, y, orientation in b_profile:
        for z, side in ((274, "left"), (275, "right")):
            step_pos = (x, y, z)
            side_pos = (x, y + 1, z)
            require_air(step_pos, "new west/down escalator")
            require_air(side_pos, "new west/down handrail")
            add(step_pos, mtr_state("escalator_step", facing="east",
                                   orientation=orientation, side=side,
                                   direction=False),
                "westbound_descending_step")
            add(side_pos, mtr_state("escalator_side", facing="east",
                                   orientation=orientation, side=side),
                "westbound_descending_handrail")

    # C: five-wide south-facing stair.  Preserve x=28 as the fixed centre
    # stair, use x=29..30 for south/up and x=26..27 for north/down.
    c_profile: list[tuple[int, int, str]] = [(258, -404, "landing_bottom")]
    c_profile.extend((z, -403 + (z - 259), "slope") for z in range(259, 272))
    c_profile.extend(((272, -390, "transition_top"),
                      (273, -390, "landing_top")))
    for z, y, orientation in c_profile:
        for x, side, direction, reason in (
                (26, "right", False, "northbound_descending"),
                (27, "left", False, "northbound_descending"),
                (29, "right", True, "southbound_ascending"),
                (30, "left", True, "southbound_ascending")):
            step_pos = (x, y, z)
            side_pos = (x, y + 1, z)
            old_step = cells.get(step_pos, "minecraft:air")
            if z in (258, 273):
                if old_step != "minecraft:red_concrete":
                    raise RuntimeError(f"stair landing changed at {step_pos}: {old_step}")
            elif not old_step.startswith("minecraft:polished_blackstone_stairs["):
                raise RuntimeError(f"stair flight changed at {step_pos}: {old_step}")
            require_air(side_pos, "centre-stair escalator handrail")
            add(step_pos, mtr_state("escalator_step", facing="south",
                                   orientation=orientation, side=side,
                                   direction=direction),
                f"{reason}_step")
            add(side_pos, mtr_state("escalator_side", facing="south",
                                   orientation=orientation, side=side),
                f"{reason}_handrail")

    return sorted(changes.values(), key=lambda change: (change.y, change.z, change.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s38_requested_mtr_escalators_{stamp}"
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

    for name, reverse in (("block_diff.csv", False), ("inverse_patch.csv", True)):
        with (artifact / name).open("w", encoding="utf-8", newline="") as stream:
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
        "reasons": dict(sorted(Counter(change.reason for change in changes).items())),
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
        "reasons": dict(sorted(Counter(change.reason for change in changes).items())),
    }
    print(json.dumps(summary, indent=2))
    if args.apply:
        print(json.dumps({"applied": True, "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
