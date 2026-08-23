#!/usr/bin/env python3
"""Apply the four measured R28 local pyramid repairs from 2026-08-12.

The packet is deliberately coordinate-bounded.  It removes only the natural
terrain intrusion at the north-west pyramid corner, retires the connected
above-floor obsolete service object reported at (-9,-459,312), and restores
the exact corridor voxels removed by the earlier x=72 shaft retirement.
Every touched region is copied before an atomic rewrite and read back.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box
from s21_clean_deep_columns_and_repair_pyramid import pyramid_expected


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S21-PYRAMID-LOCAL-REPAIR-R06"
SOURCE_DIFF = ROOT / "artifacts/s21_office_dogma_access_20260811_225917/block_diff.csv"
AIR = "minecraft:air"
AIR_NAMES = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
NATURAL = {"minecraft:grass_block", "minecraft:dirt", "minecraft:stone"}
OBSOLETE_PALETTE = {
    "minecraft:polished_deepslate", "minecraft:deepslate_tiles",
    "minecraft:polished_basalt", "minecraft:deepslate_bricks",
    "minecraft:gray_stained_glass", "minecraft:orange_concrete",
    "minecraft:reinforced_deepslate", "minecraft:sea_lantern",
    "minecraft:ladder", "minecraft:iron_bars",
    "minecraft:polished_blackstone", "minecraft:light_gray_concrete",
    "minecraft:tinted_glass", "minecraft:cyan_stained_glass",
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def add(desired: dict[tuple[int, int, int], Change], current: dict,
        position: tuple[int, int, int], after: str, reason: str) -> None:
    before = current.get(position, AIR)
    if before == after:
        return
    desired[position] = Change(PACKET, *position, before, after,
                               "bounded_exact_repair", reason)


def obsolete_component(current: dict) -> set[tuple[int, int, int]]:
    seed = (-9, -459, 312)
    if bare(current.get(seed, AIR)) not in OBSOLETE_PALETTE:
        raise RuntimeError(f"obsolete seed changed: {current.get(seed, AIR)}")
    queue = deque([seed])
    seen = {seed}
    while queue:
        x, y, z = queue.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                           (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nxt = (x + dx, y + dy, z + dz)
            if (nxt in seen or not (-48 <= nxt[0] <= -4)
                    or not (-465 <= nxt[1] <= -459)
                    or not (288 <= nxt[2] <= 327)):
                continue
            if bare(current.get(nxt, AIR)) in OBSOLETE_PALETTE:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def plan(world: Path) -> list[Change]:
    lo, hi = (-80, -475, 210), (90, -430, 350)
    current = read_box(world, DIMENSION, lo, hi)
    desired: dict[tuple[int, int, int], Change] = {}

    # Measured intrusion: three natural layers leaked through the north-west
    # stepped shell.  Restore shell witnesses and clear only natural cells on
    # the inside; external terrain north/west of the shell is untouched.
    for x in range(-75, -29):
        for y in range(-446, -443):
            for z in range(222, 236):
                position = (x, y, z)
                if bare(current.get(position, AIR)) not in NATURAL:
                    continue
                expected = pyramid_expected(x, y, z)
                add(desired, current, position, expected or AIR,
                    "clear_northwest_terrain_intrusion"
                    if expected is None else "restore_northwest_pyramid_shell")

    # The reported object is a coherent suspended service installation that
    # sits on the accepted y=-466 pyramid base.  Remove its two above-floor
    # volumes but retain the base slab and buried strata verbatim.
    component = obsolete_component(current)
    # The glass equipment cell is detached above the slab but is visibly part
    # of the same obsolete installation.  Select it by the same measured box
    # and palette instead of relying on the floor to join the two volumes.
    above_floor = {
        (x, y, z)
        for x in range(-48, -3)
        for y in range(-465, -458)
        for z in range(288, 328)
        if bare(current.get((x, y, z), AIR)) in OBSOLETE_PALETTE
    }
    bounds = (
        tuple(min(position[i] for position in above_floor) for i in range(3)),
        tuple(max(position[i] for position in above_floor) for i in range(3)),
    )
    if not (1400 <= len(above_floor) <= 1600
            and bounds == ((-48, -465, 288), (-4, -459, 327))):
        raise RuntimeError(
            f"obsolete service object no longer matches survey: "
            f"count={len(above_floor)} bounds={bounds}")
    for position in above_floor:
        add(desired, current, position, AIR,
            "retire_obsolete_under_pyramid_service_object")

    # Restore the exact authored corridor cross-section from the prior packet's
    # own before-values.  Only air is replaced, so later human edits win.
    with SOURCE_DIFF.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            x, y, z = int(row["x"]), int(row["y"]), int(row["z"])
            if (row["reason"] != "retire_abandoned_x72_z273_shaft"
                    or not (67 <= x <= 77 and -444 <= y <= -438
                            and 270 <= z <= 276)):
                continue
            position = (x, y, z)
            if bare(current.get(position, AIR)) in AIR_NAMES:
                add(desired, current, position, row["before"],
                    "restore_exact_x67_x77_corridor_voxel")

    changes = sorted(desired.values(), key=lambda c: (c.y, c.z, c.x))
    verify(current, changes)
    return changes


def verify(current: dict, changes: list[Change]) -> None:
    proposed = dict(current)
    for change in changes:
        proposed[(change.x, change.y, change.z)] = change.after
    if bare(proposed.get((-54, -444, 232), AIR)) not in AIR_NAMES:
        raise RuntimeError("north-west terrain intrusion seed was not cleared")
    if bare(proposed.get((-9, -459, 312), AIR)) not in AIR_NAMES:
        raise RuntimeError("obsolete service-object seed was not cleared")
    for x in range(67, 78):
        for z in range(271, 276):
            if bare(proposed.get((x, -443, z), AIR)) in AIR_NAMES:
                raise RuntimeError(f"corridor floor gap at {(x, -443, z)}")
            for y in range(-442, -438):
                if bare(proposed.get((x, y, z), AIR)) not in AIR_NAMES:
                    raise RuntimeError(f"corridor headroom blocked at {(x, y, z)}")
            if bare(proposed.get((x, -438, z), AIR)) in AIR_NAMES:
                raise RuntimeError(f"corridor roof gap at {(x, -438, z)}")


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s21_pyramid_local_r06_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True, exist_ok=False)
    region_dir = dimension_dir(world, DIMENSION) / "region"
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    originals: dict[Path, bytes] = {}
    changed: list[Path] = []
    try:
        for (rx, rz), chunk_changes in sorted(by_region.items()):
            path = region_dir / f"r.{rx}.{rz}.mca"
            originals[path] = path.read_bytes()
            shutil.copy2(path, backup / path.name)
            atomic_replace(path, rewrite_region(path, chunk_changes))
            changed.append(path)
        lo = tuple(min(getattr(c, axis) for c in changes)
                   for axis in ("x", "y", "z"))
        hi = tuple(max(getattr(c, axis) for c in changes)
                   for axis in ("x", "y", "z"))
        actual = read_box(world, DIMENSION, lo, hi)
        failed = [c for c in changes
                  if actual.get((c.x, c.y, c.z), AIR) != c.after]
        if failed:
            raise RuntimeError(f"read-back failed for {len(failed)} cells")
    except Exception:
        for path in changed:
            atomic_replace(path, originals[path])
        raise
    reasons = Counter(change.reason for change in changes)
    receipt = {
        "status": "APPLIED_AND_EXACT_READ_BACK_VERIFIED",
        "packet": PACKET,
        "world": str(world),
        "writes": len(changes),
        "reasons": dict(reasons),
        "regionsBeforeSha256": {
            path.name: hashlib.sha256(data).hexdigest()
            for path, data in originals.items()
        },
    }
    (artifact / "block_diff.csv").write_text(
        "x,y,z,before,after,reason\n" + "\n".join(
            f"{c.x},{c.y},{c.z},{c.before},{c.after},{c.reason}"
            for c in changes) + "\n", encoding="utf-8")
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii")
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
        "writes": len(changes),
        "reasons": dict(Counter(c.reason for c in changes)),
    }, indent=2))
    if args.apply:
        print(json.dumps({"artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
