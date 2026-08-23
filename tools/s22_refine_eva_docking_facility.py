#!/usr/bin/env python3
"""Replace S22's exposed EVA rack with a three-cell mechanical dock.

The accepted sortie deck and transfer rails remain authoritative.  This
packet only owns the west docking superstructure: a grounded pressure wall,
three recessed arresting cells, shoulder service bridges and overhead crane
rails.  C-22, the lake, the hangars, launch silos and command interior are
outside the edit mask.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-CANONICAL-EVA-DOCKING-FACILITY-R02"
BBOX = ((-186, -452, 122), (-150, -386, 180))

AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
OWNED = {
    "minecraft:polished_deepslate", "minecraft:polished_blackstone",
    "minecraft:polished_basalt", "minecraft:smooth_stone",
    "minecraft:light_gray_concrete", "minecraft:gray_concrete",
    "minecraft:black_concrete", "minecraft:orange_concrete",
    "minecraft:yellow_concrete", "minecraft:purple_concrete",
    "minecraft:red_concrete", "minecraft:deepslate",
    "minecraft:sea_lantern", "projectseele:clear_glass",
}

EDGE = "minecraft:polished_blackstone"
STEEL = "minecraft:polished_deepslate"
CORE = "minecraft:deepslate"
PANEL = "minecraft:gray_concrete"
VOID_PANEL = "minecraft:black_concrete"
WHITE = "minecraft:light_gray_concrete"
ORANGE = "minecraft:orange_concrete"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"
DECK_Y = -451
BAYS = (135, 151, 167)
COLOURS = (
    "minecraft:yellow_concrete",
    "minecraft:purple_concrete",
    "minecraft:red_concrete",
)


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def put(desired, x: int, y: int, z: int, state: str, reason: str) -> None:
    if x > -150:
        raise RuntimeError(f"crossed dock edit mask at {x},{y},{z}")
    desired[(x, y, z)] = (state, reason)


def design(world: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Retire only the previous R01 superstructure.  The accepted deck at
    # y=-451 and every cell east of x=-166 remain untouched.
    for x in range(-184, -166):
        for y in range(DECK_Y + 1, -383):
            for z in range(126, 177):
                before = bare(world.get((x, y, z), "minecraft:air"))
                if before in OWNED:
                    put(desired, x, y, z, "minecraft:air",
                        "retire exposed prototype docking rack")

    # Four-block pressure/back wall.  Its east face is the visible dock face;
    # the body is genuinely load-bearing rather than a one-block billboard.
    for x in range(-184, -180):
        for y in range(DECK_Y, -391):
            for z in range(126, 177):
                boundary = z in (126, 127, 142, 143, 158, 159, 175, 176)
                top_or_base = y <= -447 or y >= -395
                state = CORE if x <= -183 else (EDGE if boundary or top_or_base else PANEL)
                put(desired, x, y, z, state, "EVA dock pressure wall")

    for unit, centre in enumerate(BAYS):
        colour = COLOURS[unit]

        # Recessed dark service bay on the pressure-wall face.  Narrow colour
        # and white bands identify the unit without turning the structure into
        # a test chart.
        for z in range(centre - 5, centre + 6):
            for y in range(-444, -398):
                frame = z in (centre - 5, centre + 5) or y in (-444, -443, -399, -398)
                state = EDGE if frame else VOID_PANEL
                put(desired, -180, y, z, state,
                    f"EVA-{unit:02d} recessed arresting cell")
        for z in range(centre - 4, centre + 5):
            put(desired, -179, -423, z, colour,
                f"EVA-{unit:02d} identity band")
            put(desired, -179, -422, z, WHITE,
                f"EVA-{unit:02d} datum stripe")

        # Foot cradle and rail stop remain fully behind the EVA standing pad.
        for x in range(-179, -170):
            for z in range(centre - 5, centre + 6):
                for y in range(DECK_Y + 1, DECK_Y + 7):
                    side = z in (centre - 5, centre + 5)
                    upper = y in (DECK_Y + 5, DECK_Y + 6)
                    state = colour if upper and not side else (EDGE if side else STEEL)
                    put(desired, x, y, z, state,
                        f"EVA-{unit:02d} heel lock")

        # Two shoulder-height service bridges: a solid service deck, glazed
        # guard on the bay side and compact end clamp.  The central 9-wide EVA
        # silhouette remains open.
        for z in (centre - 6, centre + 6):
            for x in range(-179, -157):
                for dy in (0, 1):
                    put(desired, x, -421 + dy, z, STEEL,
                        f"EVA-{unit:02d} shoulder service bridge")
                put(desired, x, -419, z,
                    LIGHT if x in (-174, -165, -158) else GLASS,
                    f"EVA-{unit:02d} shoulder guard")
            for y in range(-423, -414):
                put(desired, -157, y, z, EDGE,
                    f"EVA-{unit:02d} shoulder lock actuator")

        # Overhead crane rail and two hangers.  This reads as machinery above
        # each berth without recreating the former giant flat black roof.
        for x in range(-180, -153):
            for y in range(-397, -394):
                for z in range(centre - 6, centre + 7):
                    edge = z in (centre - 6, centre + 6) or y in (-397, -395)
                    state = EDGE if edge else (ORANGE if x % 7 == 0 else STEEL)
                    put(desired, x, y, z, state,
                        f"EVA-{unit:02d} overhead crane rail")
        for x in (-164, -157):
            for y in range(-417, -394):
                for z in (centre - 6, centre + 6):
                    put(desired, x, y, z, STEEL,
                        f"EVA-{unit:02d} crane hanger")

    # One continuous rear inspection gallery.  It connects all three cells
    # but stays behind the EVA line and does not bridge into C-22.
    for z in range(127, 176):
        for x in range(-179, -172):
            put(desired, x, -410, z,
                LIGHT if x == -175 and z % 8 == 0 else STEEL,
                "shared EVA dock inspection gallery")
        put(desired, -172, -409, z,
            EDGE if z % 4 == 0 else GLASS,
            "shared EVA dock gallery guard")

    changes: list[Change] = []
    collisions: list[tuple[tuple[int, int, int], str]] = []
    allowed = AIR | OWNED
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = world.get(position, "minecraft:air")
        if before == after:
            continue
        if bare(before) not in allowed:
            collisions.append((position, before))
            continue
        changes.append(Change(PACKET, *position, before, after, "replace", reason))
    if collisions:
        sample = ", ".join(f"{p}:{s}" for p, s in collisions[:12])
        raise RuntimeError(f"collides with {len(collisions)} protected cells: {sample}")
    return changes


def apply(changes: list[Change]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_EVA_DOCK_R02_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
        atomic_replace(path, rewrite_region(path, chunk_changes))

    lo = tuple(min(getattr(c, axis) for c in changes) for axis in ("x", "y", "z"))
    hi = tuple(max(getattr(c, axis) for c in changes) for axis in ("x", "y", "z"))
    actual = read_box(WORLD, DIMENSION, lo, hi)
    failures = [c for c in changes
                if actual.get((c.x, c.y, c.z), "minecraft:air") != c.after]
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "writes": len(changes),
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIMENSION, BBOX[0], BBOX[1])
    changes = design(world)
    reasons = defaultdict(int)
    for change in changes:
        reasons[change.reason] += 1
    report = {
        "packet": PACKET,
        "writes": len(changes),
        "bounds": [
            min(c.x for c in changes), min(c.y for c in changes), min(c.z for c in changes),
            max(c.x for c in changes), max(c.y for c in changes), max(c.z for c in changes),
        ],
        "parts": dict(sorted(reasons.items())),
    }
    print(json.dumps(report, indent=2))
    if args.apply:
        print(f"backup={apply(changes)}")


if __name__ == "__main__":
    main()
