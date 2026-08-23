#!/usr/bin/env python3
"""Inventory the full R28 GeoFront targets that need semantic repair.

This intentionally scans the complete spherical cavity instead of the former
cropped core model.  It reports three independent targets: natural stone
needles intruding into the exposed upper cavity, water components, and LCL
components / blocks below their lowest surface.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import json
import math
from pathlib import Path

import numpy as np

from inspect_map_assets import (
    decode_modern_section,
    iter_chunks,
    palette_name,
    palette_state,
)
from query_blocks import dimension_dir


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
CENTRE = (30, -332, 220)
RADIUS = 320


def components(cells: set[tuple[int, int, int]]):
    remaining = set(cells)
    while remaining:
        seed = remaining.pop()
        found = {seed}
        queue = deque([seed])
        while queue:
            x, y, z = queue.popleft()
            for neighbour in ((x + 1, y, z), (x - 1, y, z),
                              (x, y + 1, z), (x, y - 1, z),
                              (x, y, z + 1), (x, y, z - 1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    found.add(neighbour)
                    queue.append(neighbour)
        yield found


def summary(component):
    xs = [p[0] for p in component]
    ys = [p[1] for p in component]
    zs = [p[2] for p in component]
    return {
        "blocks": len(component),
        "bbox": [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
        "sample": list(next(iter(component))),
    }


def contiguous_runs(values: list[int]) -> list[tuple[int, int, int]]:
    ordered = sorted(set(values))
    if not ordered:
        return []
    found = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value != previous + 1:
            found.append((previous - start + 1, start, previous))
            start = value
        previous = value
    found.append((previous - start + 1, start, previous))
    return found


def scan(world: Path):
    root = dimension_dir(world, DIMENSION)
    cx, cy, cz = CENTRE
    bounds = ((cx - RADIUS) >> 4, (cx + RADIUS) >> 4,
              (cz - RADIUS) >> 4, (cz + RADIUS) >> 4)
    stone_columns: dict[tuple[int, int], list[int]] = defaultdict(list)
    water: set[tuple[int, int, int]] = set()
    lcl: set[tuple[int, int, int]] = set()
    below_lcl_non_natural: set[tuple[int, int, int]] = set()
    non_natural_names = {
        "minecraft:orange_concrete", "minecraft:orange_stained_glass",
        "minecraft:reinforced_deepslate", "minecraft:iron_block",
        "minecraft:smooth_stone", "minecraft:gray_concrete",
        "minecraft:white_concrete", "minecraft:black_concrete",
        "minecraft:deepslate_bricks", "minecraft:deepslate_tiles",
    }
    radius_sq = RADIUS * RADIUS

    for chunk_x, chunk_z, chunk in iter_chunks(root, bounds):
        bx, bz = chunk_x * 16, chunk_z * 16
        for section in chunk.get("sections", []):
            by = int(section["Y"]) * 16
            if by > cy + RADIUS or by + 15 < cy - RADIUS:
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            array = np.asarray(indices, dtype=np.int32)
            for index, entry in enumerate(palette):
                name = palette_name(entry)
                if (name != "minecraft:stone" and
                        name != "minecraft:water" and
                        name != "projectseele:lcl" and
                        name not in non_natural_names):
                    continue
                offsets = np.flatnonzero(array == index)
                if not offsets.size:
                    continue
                xs = bx + (offsets & 15)
                zs = bz + ((offsets >> 4) & 15)
                ys = by + (offsets >> 8)
                sphere = ((xs - cx) ** 2 + (ys - cy) ** 2 +
                          (zs - cz) ** 2 <= radius_sq)
                for x, y, z in zip(xs[sphere], ys[sphere], zs[sphere]):
                    cell = int(x), int(y), int(z)
                    if name == "minecraft:stone":
                        horizontal = math.hypot(cell[0] - cx, cell[2] - cz)
                        # The user-confirmed defect is a boundary needle in
                        # exposed air, not the landscaped floor or deep fill.
                        if horizontal >= 285 and cell[1] >= -430:
                            stone_columns[(cell[0], cell[2])].append(cell[1])
                    elif name == "minecraft:water":
                        water.add(cell)
                    elif name == "projectseele:lcl":
                        lcl.add(cell)
                    elif cell[1] <= -613:
                        below_lcl_non_natural.add(cell)

    needles = []
    needle_cells = set()
    for (x, z), values in stone_columns.items():
        for length, y0, y1 in contiguous_runs(values):
            if length < 8:
                continue
            cells = {(x, y, z) for y in range(y0, y1 + 1)}
            needle_cells.update(cells)
            needles.append({"x": x, "z": z, "y0": y0, "y1": y1,
                            "blocks": length})
    needles.sort(key=lambda item: (-item["blocks"], item["x"], item["z"]))

    water_components = sorted(components(water), key=len, reverse=True)
    lcl_components = sorted(components(lcl), key=len, reverse=True)
    lcl_by_y = defaultdict(int)
    for _, y, _ in lcl:
        lcl_by_y[y] += 1
    return {
        "world": str(world.resolve()),
        "fullSphere": [cx - RADIUS, cy - RADIUS, cz - RADIUS,
                       cx + RADIUS, cy + RADIUS, cz + RADIUS],
        "stoneNeedleColumns": len(needles),
        "stoneNeedleBlocks": len(needle_cells),
        "stoneNeedles": needles,
        "waterBlocks": len(water),
        "waterComponents": [summary(c) for c in water_components[:30]],
        "lclBlocks": len(lcl),
        "lclComponents": [summary(c) for c in lcl_components[:30]],
        "lclBlocksByY": {str(y): lcl_by_y[y] for y in sorted(lcl_by_y)},
        "nonNaturalAtOrBelowY613": len(below_lcl_non_natural),
        "nonNaturalAtOrBelowY613Components": [
            summary(c) for c in sorted(components(below_lcl_non_natural),
                                       key=len, reverse=True)[:30]
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = scan(args.world.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "output": str(args.output.resolve()),
        "stoneNeedleColumns": report["stoneNeedleColumns"],
        "stoneNeedleBlocks": report["stoneNeedleBlocks"],
        "waterComponents": report["waterComponents"][:5],
        "lclComponents": report["lclComponents"][:5],
        "nonNaturalAtOrBelowY613": report["nonNaturalAtOrBelowY613"],
    }, indent=2))


if __name__ == "__main__":
    main()
