"""Measure and join the two structural gaps between the three launch bays.

This tool never infers permission from air.  A candidate row exists only when
the measured outer wall of both neighbouring bays is solid at the same y/z.
Observation-gallery and wet-hangar coordinates are outside the read/write box.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from query_blocks import read_box  # noqa: E402
from apply_s20_approved_semantic_repairs import (  # noqa: E402
    Change,
    atomic_replace,
    rewrite_region,
)


WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIM = "projectseele:geofront"
LO = (5, -460, 180)
HI = (55, 100, 260)
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
GAPS = ((5, 13), (47, 55))

NON_STRUCTURAL_HINTS = (
    "air", "lcl", "water", "lava", "light", "button", "lever", "door",
    "ladder", "rail", "torch", "sign", "banner", "carpet", "wire",
    "rack",
)


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def structural(state: str) -> bool:
    name = bare(state)
    return not any(hint in name for hint in NON_STRUCTURAL_HINTS)


def design(world: dict[tuple[int, int, int], str]) \
        -> dict[tuple[int, int, int], str]:
    """Fill only measured structural spans between matching bay walls."""
    plan: dict[tuple[int, int, int], str] = {}
    for left, right in GAPS:
        for y in range(LO[1], HI[1] + 1):
            for z in range(LO[2], HI[2] + 1):
                left_state = world.get((left, y, z), "minecraft:air")
                right_state = world.get((right, y, z), "minecraft:air")
                if not (structural(left_state) and structural(right_state)):
                    continue
                for x in range(left + 1, right):
                    current = world.get((x, y, z), "minecraft:air")
                    if bare(current) not in AIR:
                        continue
                    # Identical layers remain identical.  Unit-colour layers
                    # meet at the seam by inheriting the nearest bay state;
                    # no invented palette or decorative pattern is introduced.
                    target = (left_state if x - left <= right - x
                              else right_state)
                    plan[(x, y, z)] = target
    return plan


def gate(world: dict[tuple[int, int, int], str],
         plan: dict[tuple[int, int, int], str]) -> None:
    escaped = [p for p in plan
               if not ((6 <= p[0] <= 12) or (48 <= p[0] <= 54))]
    overwritten = [p for p in plan
                   if bare(world.get(p, "minecraft:air")) not in AIR]
    unresolved = []
    for left, right in GAPS:
        for y in range(LO[1], HI[1] + 1):
            for z in range(LO[2], HI[2] + 1):
                ls = world.get((left, y, z), "minecraft:air")
                rs = world.get((right, y, z), "minecraft:air")
                if not (structural(ls) and structural(rs)):
                    continue
                for x in range(left + 1, right):
                    after = plan.get((x, y, z),
                                     world.get((x, y, z), "minecraft:air"))
                    if bare(after) in AIR:
                        unresolved.append((x, y, z))
    if escaped or overwritten or unresolved:
        raise RuntimeError(
            f"gate failed escaped={len(escaped)} overwritten={len(overwritten)} "
            f"unresolved={len(unresolved)}")

    ys = [p[1] for p in plan]
    zs = [p[2] for p in plan]
    print(f"proposal writes={len(plan)} y={min(ys)}..{max(ys)} "
          f"z={min(zs)}..{max(zs)}")
    print("structural seams unresolved after proposal: 0")
    print("existing non-air voxels overwritten: 0")
    print("observation gallery/hangars: 0 writes (their z is outside 180..260)")


def apply_to_world(world, plan) -> None:
    region = (WORLD / "dimensions" / "projectseele" / "geofront" /
              "region" / "r.0.0.mca")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("artifacts") / f"s21_launch_bay_shell_join_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(region, backup / region.name)
    before_sha = hashlib.sha256(region.read_bytes()).hexdigest()

    by_chunk: dict[tuple[int, int], list[Change]] = {}
    for (x, y, z), target in plan.items():
        change = Change(
            "S21-LAUNCH-BAY-SHELL-JOIN", x, y, z,
            world.get((x, y, z), "minecraft:air"), target,
            "add", "join measured launch-bay wall layers",
        )
        by_chunk.setdefault((x // 16, z // 16), []).append(change)

    rewritten = rewrite_region(region, by_chunk)
    atomic_replace(region, rewritten)
    actual = read_box(WORLD, DIM, LO, HI)
    failures = [(p, target, actual.get(p, "minecraft:air"))
                for p, target in plan.items()
                if actual.get(p, "minecraft:air") != target]
    if failures:
        shutil.copy2(backup / region.name, region)
        raise RuntimeError(f"read-back failed: {failures[:3]}")

    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "world": WORLD.name,
        "dimension": DIM,
        "writes": len(plan),
        "scope": "two launch-bay structural seams only",
        "regionBeforeSha256": before_sha,
        "regionAfterSha256": hashlib.sha256(region.read_bytes()).hexdigest(),
        "backup": str((backup / region.name).resolve()),
    }
    (backup / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii")
    print(f"applied and read-back verified; backup={backup}")


def survey(world: dict[tuple[int, int, int], str]) -> None:
    def block(pos: tuple[int, int, int]) -> str:
        return bare(world.get(pos, "minecraft:air"))

    for left, right in GAPS:
        rows: list[tuple[int, tuple[tuple[int, int], ...]]] = []
        for y in range(LO[1], HI[1] + 1):
            zs = [
                z for z in range(LO[2], HI[2] + 1)
                if block((left, y, z)) not in AIR
                and block((right, y, z)) not in AIR
                and any(block((x, y, z)) in AIR
                        for x in range(left + 1, right))
            ]
            if zs:
                spans: list[list[int]] = []
                for z in zs:
                    if not spans or z != spans[-1][1] + 1:
                        spans.append([z, z])
                    else:
                        spans[-1][1] = z
                rows.append((y, tuple((a, b) for a, b in spans)))
        print(f"gap x={left + 1}..{right - 1}: {len(rows)} y rows")
        runs: list[list[tuple[int, tuple[tuple[int, int], ...]]]] = []
        for row in rows:
            if (not runs or row[0] != runs[-1][-1][0] + 1
                    or row[1] != runs[-1][-1][1]):
                runs.append([row])
            else:
                runs[-1].append(row)
        for run in runs:
            first, last = run[0], run[-1]
            spans = ", ".join(
                str(a) if a == b else f"{a}..{b}" for a, b in first[1])
            print(f"  y={first[0]}..{last[0]} z={spans}")
        pairs = Counter()
        for y, spans in rows:
            for start, end in spans:
                for z in range(start, end + 1):
                    pairs[(block((left, y, z)), block((right, y, z)))] += 1
        print("  endpoint pairs:")
        for (a, b), count in pairs.most_common():
            print(f"    {count:4d}  {a}  |  {b}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--survey", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = read_box(WORLD, DIM, LO, HI)
    if args.survey:
        survey(world)
    plan = design(world)
    gate(world, plan)
    if args.apply:
        apply_to_world(world, plan)


if __name__ == "__main__":
    main()
