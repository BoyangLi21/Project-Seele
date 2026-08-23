"""Replace the retired Create-only facility palette in one saved world.

The command is deliberately namespace-bounded: it never touches a block that
is not currently stored as ``create:*``.  Run without ``--apply`` for a census;
``--apply`` rewrites only the region files that contain matched cells.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import (  # noqa: E402
    Change,
    atomic_replace,
    rewrite_region,
)
from query_blocks import dimension_dir, read_box  # noqa: E402


REPLACEMENTS = {
    "create:metal_girder": "minecraft:polished_deepslate",
    "create:railway_casing": "minecraft:iron_block",
    "create:andesite_casing": "minecraft:copper_block",
    "create:brass_casing": "minecraft:cut_copper",
    "create:gantry_carriage": "minecraft:polished_blackstone",
    "create:rope_pulley": "minecraft:piston[facing=down,extended=false]",
    "create:pulley_magnet": "minecraft:exposed_copper",
    "create:piston_extension_pole": "minecraft:chain[axis=y,waterlogged=false]",
}


def base_name(state: str) -> str:
    return state.split("[", 1)[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--dim", default="projectseele:geofront")
    parser.add_argument("--box", type=int, nargs=6, required=True,
                        metavar=("X0", "Y0", "Z0", "X1", "Y1", "Z1"))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    x0, y0, z0, x1, y1, z1 = args.box
    lo = (min(x0, x1), min(y0, y1), min(z0, z1))
    hi = (max(x0, x1), max(y0, y1), max(z0, z1))
    cells = read_box(args.world, args.dim, lo, hi, "create")

    unknown = Counter(base_name(state) for state in cells.values()
                      if base_name(state) not in REPLACEMENTS)
    if unknown:
        raise RuntimeError("unmapped Create blocks: " + ", ".join(
            f"{name}={count}" for name, count in sorted(unknown.items())))

    changes = [
        Change(
            packet="retire-create",
            x=x, y=y, z=z,
            before=state,
            after=REPLACEMENTS[base_name(state)],
            kind="replace",
            reason="Create runtime retired; preserve the authored machine footprint",
        )
        for (x, y, z), state in sorted(cells.items())
    ]
    summary = Counter(base_name(change.before) for change in changes)
    report = {
        "schema": 1,
        "world": str(args.world.resolve()),
        "dimension": args.dim,
        "box": [*lo, *hi],
        "changes": len(changes),
        "by_block": dict(sorted(summary.items())),
        "applied": bool(args.apply),
    }
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n",
                               encoding="utf-8")
    if not args.apply or not changes:
        return

    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = \
        defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk].append(change)

    root = dimension_dir(args.world, args.dim) / "region"
    for (region_x, region_z), chunk_changes in sorted(by_region.items()):
        path = root / f"r.{region_x}.{region_z}.mca"
        removable = {
            (change.x, change.y, change.z)
            for changes_in_chunk in chunk_changes.values()
            for change in changes_in_chunk
        }
        atomic_replace(path, rewrite_region(
            path, chunk_changes, removable_block_entities=removable))

    remaining = read_box(args.world, args.dim, lo, hi, "create")
    if remaining:
        raise RuntimeError(f"verification failed: {len(remaining)} create blocks remain")


if __name__ == "__main__":
    main()
