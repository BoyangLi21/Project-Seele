#!/usr/bin/env python3
"""Install the reversible left-running MTR walkway trial in the S20 hangar corridor."""

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
PACKET = "S36-MTR-LEFT-TRAFFIC-WALKWAYS-R01"
X_MIN = 45
X_MAX = 84
STEP_Y = -370
SIDE_Y = -369

# Eastbound traffic keeps north/left; westbound traffic keeps south/left.
LANES = (
    (189, "east", "left"),
    (190, "east", "right"),
    (195, "west", "right"),
    (196, "west", "left"),
)


def orientation(x: int, facing: str) -> str:
    if facing == "east":
        if x == X_MIN:
            return "landing_bottom"
        if x == X_MAX:
            return "landing_top"
    else:
        if x == X_MAX:
            return "landing_bottom"
        if x == X_MIN:
            return "landing_top"
    return "flat"


def state(block: str, x: int, facing: str, side: str) -> str:
    properties = [f"facing={facing}", f"orientation={orientation(x, facing)}",
                  f"side={side}"]
    if block == "escalator_step":
        properties = ["direction=true", *properties, "status=true"]
    return f"mtr:{block}[{','.join(properties)}]"


def plan(world: Path) -> list[Change]:
    cells = read_box(world, DIMENSION,
                     (X_MIN, STEP_Y - 1, min(z for z, _, _ in LANES)),
                     (X_MAX, SIDE_Y, max(z for z, _, _ in LANES)), None)
    changes: list[Change] = []
    for x in range(X_MIN, X_MAX + 1):
        for z, facing, side in LANES:
            floor = cells.get((x, STEP_Y - 1, z), "minecraft:air")
            if floor not in {"minecraft:polished_deepslate",
                             "minecraft:sea_lantern"}:
                raise RuntimeError(f"unsupported floor at {(x, STEP_Y - 1, z)}: {floor}")
            for y, block in ((STEP_Y, "escalator_step"),
                             (SIDE_Y, "escalator_side")):
                before = cells.get((x, y, z), "minecraft:air")
                if before != "minecraft:air":
                    raise RuntimeError(f"walkway cell is not air at {(x, y, z)}: {before}")
                changes.append(Change(
                    PACKET, x, y, z, before, state(block, x, facing, side),
                    "human_authorized_mtr_walkway_trial",
                    "left_traffic_preserve_authored_floor"))
    return sorted(changes, key=lambda change: (change.y, change.z, change.x))


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s36_mtr_walkways_{stamp}"
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

    with (artifact / "block_diff.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x", "y", "z", "before", "after", "reason"))
        for change in changes:
            writer.writerow((change.x, change.y, change.z, change.before,
                             change.after, change.reason))
    with (artifact / "inverse_patch.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x", "y", "z", "before", "after"))
        for change in changes:
            writer.writerow((change.x, change.y, change.z,
                             change.after, change.before))

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
    print(json.dumps({"packet": PACKET, "world": str(world),
                      "blocks": len(changes), "x": [X_MIN, X_MAX],
                      "lanes": LANES}, indent=2))
    if args.apply:
        print(json.dumps({"applied": True,
                          "artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
