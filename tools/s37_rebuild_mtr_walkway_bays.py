#!/usr/bin/env python3
"""Lower the MTR walkways into the floor and align three runs to the EVA bays."""

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
PACKET = "S37-MTR-THREE-EVA-BAY-WALKWAYS-R01"
SEGMENTS = ((-30, 6, "EVA-00"), (12, 48, "EVA-01"), (54, 90, "EVA-02"))
LANES = (
    (189, "east", "left"),
    (190, "east", "right"),
    (195, "west", "right"),
    (196, "west", "left"),
)
STEP_Y = -371
SIDE_Y = -370
RETIRED_SIDE_Y = -369
OLD_X_MIN = 45
OLD_X_MAX = 84


def orientation(x: int, x_min: int, x_max: int, facing: str) -> str:
    if facing == "east":
        if x == x_min:
            return "landing_bottom"
        if x == x_max:
            return "landing_top"
    else:
        if x == x_max:
            return "landing_bottom"
        if x == x_min:
            return "landing_top"
    return "flat"


def state(block: str, x: int, x_min: int, x_max: int,
          facing: str, side: str) -> str:
    properties = [f"facing={facing}",
                  f"orientation={orientation(x, x_min, x_max, facing)}",
                  f"side={side}"]
    if block == "escalator_step":
        properties = ["direction=true", *properties, "status=true"]
    return f"mtr:{block}[{','.join(properties)}]"


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (SEGMENTS[0][0], STEP_Y, min(z for z, _, _ in LANES)),
                     (SEGMENTS[-1][1], RETIRED_SIDE_Y,
                      max(z for z, _, _ in LANES)), None)
    changes: dict[tuple[int, int, int], Change] = {}

    def add(pos: tuple[int, int, int], before: str, after: str,
            reason: str) -> None:
        if before == after:
            return
        changes[pos] = Change(PACKET, *pos, before, after,
                              "human_authorized_three_bay_walkway",
                              reason)

    # Remove every raised block from the first one-piece trial. The original
    # floor beneath it remains untouched until the new recessed step replaces
    # that exact floor cell below.
    for x in range(OLD_X_MIN, OLD_X_MAX + 1):
        for z, _, _ in LANES:
            old_step = cells.get((x, SIDE_Y, z), "minecraft:air")
            old_side = cells.get((x, RETIRED_SIDE_Y, z), "minecraft:air")
            if not old_step.startswith("mtr:escalator_step["):
                raise RuntimeError(f"old raised step changed at {(x, SIDE_Y, z)}: {old_step}")
            if not old_side.startswith("mtr:escalator_side["):
                raise RuntimeError(f"old raised side changed at {(x, RETIRED_SIDE_Y, z)}: {old_side}")
            add((x, SIDE_Y, z), old_step, "minecraft:air",
                "retire_raised_trial_step")
            add((x, RETIRED_SIDE_Y, z), old_side, "minecraft:air",
                "retire_raised_trial_side")

    for x_min, x_max, bay in SEGMENTS:
        for x in range(x_min, x_max + 1):
            for z, facing, side in LANES:
                floor_pos = (x, STEP_Y, z)
                side_pos = (x, SIDE_Y, z)
                floor = cells.get(floor_pos, "minecraft:air")
                if floor not in {"minecraft:polished_deepslate",
                                 "minecraft:sea_lantern"}:
                    raise RuntimeError(f"{bay} floor changed at {floor_pos}: {floor}")
                old_side = cells.get(side_pos, "minecraft:air")
                if old_side != "minecraft:air" and not old_side.startswith(
                        "mtr:escalator_step["):
                    raise RuntimeError(f"{bay} side cell occupied at {side_pos}: {old_side}")
                add(floor_pos, floor,
                    state("escalator_step", x, x_min, x_max, facing, side),
                    f"{bay.lower()}_recessed_step")
                add(side_pos, old_side,
                    state("escalator_side", x, x_min, x_max, facing, side),
                    f"{bay.lower()}_handrail")

    return sorted(changes.values(), key=lambda change: (change.y, change.z, change.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s37_mtr_three_bays_{stamp}"
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
        "segments": SEGMENTS,
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
    print(json.dumps({"packet": PACKET, "world": str(world),
                      "blocks": len(changes), "segments": SEGMENTS,
                      "stepY": STEP_Y, "sideY": SIDE_Y}, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
