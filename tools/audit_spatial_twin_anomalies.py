#!/usr/bin/env python3
"""Exact, read-only anomaly inventory for the connected R28 GeoFront.

The report complements the GLB spatial twin.  It never infers a room from
air and never edits the save.  All coordinates are native Minecraft XYZ.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from export_spatial_twin import (  # noqa: E402
    AIR,
    CATEGORY_NAMES,
    LCL,
    NATURAL,
    SKYWEAVE,
    VEGETATION,
    WATER,
    classify,
)
from inspect_map_assets import (  # noqa: E402
    decode_modern_section,
    iter_chunks,
    palette_name,
    palette_state,
)
from query_blocks import dimension_dir  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CENTRE = (30, -332, 220)
RADIUS = 320
SURFACE = (-320, 380, 60, 200, -120, 560)
LCL_NEIGHBOUR_BOX = (-32, 96, -672, -392, 112, 352)
FLOOR_Y = -444


def neighbours(cell: tuple[int, int, int]):
    x, y, z = cell
    yield x + 1, y, z
    yield x - 1, y, z
    yield x, y + 1, z
    yield x, y - 1, z
    yield x, y, z + 1
    yield x, y, z - 1


def components(cells: set[tuple[int, int, int]], limit: int | None = None):
    remaining = set(cells)
    rows = []
    while remaining:
        seed = remaining.pop()
        queue = deque([seed])
        part = [seed]
        while queue:
            current = queue.popleft()
            for neighbour in neighbours(current):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)
                    part.append(neighbour)
        xs = [p[0] for p in part]
        ys = [p[1] for p in part]
        zs = [p[2] for p in part]
        rows.append({
            "blocks": len(part),
            "bbox": [min(xs), min(ys), min(zs),
                     max(xs), max(ys), max(zs)],
            "sample": list(min(part)),
        })
    rows.sort(key=lambda row: -row["blocks"])
    return rows if limit is None else rows[:limit]


def exact_sphere_layer_sizes() -> dict[int, int]:
    result = {}
    for y in range(CENTRE[1] - RADIUS, CENTRE[1] + RADIUS + 1):
        dy = y - CENTRE[1]
        planar_sq = RADIUS * RADIUS - dy * dy
        count = 0
        max_dx = math.isqrt(max(0, planar_sq))
        for dx in range(-max_dx, max_dx + 1):
            max_dz = math.isqrt(planar_sq - dx * dx)
            count += max_dz * 2 + 1
        result[y] = count
    return result


def inside_box(xs, ys, zs, box):
    x0, x1, y0, y1, z0, z1 = box
    return ((xs >= x0) & (xs <= x1) &
            (ys >= y0) & (ys <= y1) &
            (zs >= z0) & (zs <= z1))


def scan(world: Path, dimension: str) -> dict[str, object]:
    root = dimension_dir(world, dimension)
    chunk_bounds = ((SURFACE[0] >> 4), (SURFACE[1] >> 4),
                    (SURFACE[4] >> 4), (SURFACE[5] >> 4))
    layer_sizes = exact_sphere_layer_sizes()
    layer_counts: dict[int, Counter[str]] = defaultdict(Counter)
    surface_constructed: set[tuple[int, int, int]] = set()
    surface_states: dict[tuple[int, int, int], str] = {}
    perimeter_states: Counter[str] = Counter()
    perimeter_cells: set[tuple[int, int, int]] = set()
    lcl_cells: set[tuple[int, int, int]] = set()
    lcl_states: dict[tuple[int, int, int], str] = {}
    lcl_nearby_non_air: set[tuple[int, int, int]] = set()
    deep_constructed: set[tuple[int, int, int]] = set()
    parsed_chunks = 0

    cx, cy, cz = CENTRE
    radius_sq = RADIUS * RADIUS
    for chunk_x, chunk_z, chunk in iter_chunks(root, chunk_bounds):
        parsed_chunks += 1
        base_x, base_z = chunk_x * 16, chunk_z * 16
        for section in chunk.get("sections", []):
            base_y = int(section.get("Y", 0)) * 16
            if base_y > SURFACE[3] or base_y + 15 < cy - RADIUS:
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            names = [palette_name(entry) for entry in palette]
            states = [palette_state(entry) for entry in palette]
            for palette_index, name in enumerate(names):
                state = states[palette_index]
                code = classify(name)
                if code == AIR:
                    continue
                offsets = np.flatnonzero(indices == palette_index)
                if not offsets.size:
                    continue
                xs = base_x + (offsets & 15)
                zs = base_z + ((offsets >> 4) & 15)
                ys = base_y + (offsets >> 8)

                sphere_mask = ((xs - cx) ** 2 + (ys - cy) ** 2 +
                               (zs - cz) ** 2 <= radius_sq)
                if np.any(sphere_mask):
                    sphere_ys = ys[sphere_mask]
                    unique_y, counts = np.unique(sphere_ys,
                                                 return_counts=True)
                    label = CATEGORY_NAMES[code]
                    for y, count in zip(unique_y, counts):
                        layer_counts[int(y)][label] += int(count)

                surface_mask = inside_box(xs, ys, zs, SURFACE)
                if np.any(surface_mask) and code not in {
                        NATURAL, VEGETATION, WATER, LCL, SKYWEAVE}:
                    for x, y, z in zip(xs[surface_mask], ys[surface_mask],
                                       zs[surface_mask]):
                        cell = (int(x), int(y), int(z))
                        surface_constructed.add(cell)
                        surface_states[cell] = state
                        radial = math.hypot(cell[0] - cx, cell[2] - cz)
                        if 328.0 <= radial <= 350.0:
                            perimeter_cells.add(cell)
                            perimeter_states[name] += 1

                if code == LCL:
                    for x, y, z in zip(xs, ys, zs):
                        cell = (int(x), int(y), int(z))
                        lcl_cells.add(cell)
                        lcl_states[cell] = state

                lcl_box_mask = inside_box(xs, ys, zs, LCL_NEIGHBOUR_BOX)
                if np.any(lcl_box_mask):
                    for x, y, z in zip(xs[lcl_box_mask], ys[lcl_box_mask],
                                       zs[lcl_box_mask]):
                        lcl_nearby_non_air.add((int(x), int(y), int(z)))

                deep_mask = (sphere_mask & (ys < FLOOR_Y) &
                             (code not in {NATURAL, VEGETATION, WATER,
                                           LCL, SKYWEAVE}))
                if np.any(deep_mask):
                    for x, y, z in zip(xs[deep_mask], ys[deep_mask],
                                       zs[deep_mask]):
                        deep_constructed.add((int(x), int(y), int(z)))

    profile = []
    below_totals = Counter()
    for y, total in layer_sizes.items():
        counts = layer_counts.get(y, Counter())
        non_air = sum(counts.values())
        row = {"y": y, "insideSphere": total,
               "air": max(0, total - non_air)}
        row.update(dict(sorted(counts.items())))
        row["airFraction"] = round(row["air"] / total, 6) if total else 0.0
        profile.append(row)
        if y < FLOOR_Y:
            below_totals["insideSphere"] += total
            below_totals["air"] += row["air"]
            for name, count in counts.items():
                below_totals[name] += count

    surface_components = components(surface_constructed)
    small_surface = [row for row in surface_components if row["blocks"] <= 16]
    small_distribution = Counter(row["blocks"] for row in small_surface)
    singleton_surface = [row for row in small_surface if row["blocks"] == 1]
    perimeter_components = components(perimeter_cells)
    lcl_components = components(lcl_cells)
    lcl_horizontal_exposed = 0
    lcl_downward_exposed = 0
    for x, y, z in lcl_cells:
        if (x, y - 1, z) not in lcl_nearby_non_air:
            lcl_downward_exposed += 1
        if any(neighbour not in lcl_nearby_non_air for neighbour in (
                (x + 1, y, z), (x - 1, y, z),
                (x, y, z + 1), (x, y, z - 1))):
            lcl_horizontal_exposed += 1

    return {
        "status": "READ_ONLY_EXACT_AUDIT",
        "world": str(world.resolve()),
        "dimension": dimension,
        "coordinateFrame": "Minecraft XYZ",
        "parsedChunks": parsed_chunks,
        "sphere": {"centre": list(CENTRE), "radius": RADIUS,
                   "profile": profile,
                   "belowVisibleFloorY": FLOOR_Y,
                   "belowVisibleFloorTotals": dict(below_totals)},
        "tokyo3Surface": {
            "bounds": list(SURFACE),
            "constructedBlocks": len(surface_constructed),
            "connectedComponents": len(surface_components),
            "largestComponents": surface_components[:20],
            "smallComponentsAtMost16Blocks": len(small_surface),
            "smallComponentSizeDistribution": {
                str(size): count for size, count in sorted(
                    small_distribution.items())
            },
            "singleBlockComponents": len(singleton_surface),
            "singleBlockSamples": singleton_surface[:100],
            "smallComponentSamples": small_surface[:100],
            "perimeterBand": {
                "radialRange": [328, 350],
                "blocks": len(perimeter_cells),
                "components": perimeter_components[:30],
                "topStates": perimeter_states.most_common(30),
            },
        },
        "lcl": {
            "blocks": len(lcl_cells),
            "components": lcl_components,
            "fallingLevel8Blocks": sum(
                1 for state in lcl_states.values() if "level=8" in state),
            "downwardFacesOpenToAir": lcl_downward_exposed,
            "blocksWithHorizontalAirExposure": lcl_horizontal_exposed,
        },
        "deepConstructedBelowFloor": {
            "blocks": len(deep_constructed),
            "components": components(deep_constructed, 50),
            "note": "Inventory only; Terminal Dogma/core approval is human-owned.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path,
                        default=ROOT / "run/saves/SEELE_S20_RECOVERY_R28")
    parser.add_argument("--dim", default="projectseele:geofront")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    world = args.world if args.world.is_absolute() else ROOT / args.world
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report = scan(world, args.dim)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {
        "output": str(output.resolve()),
        "surfacePerimeterBlocks":
            report["tokyo3Surface"]["perimeterBand"]["blocks"],
        "surfaceSmallComponents":
            report["tokyo3Surface"]["smallComponentsAtMost16Blocks"],
        "lclBlocks": report["lcl"]["blocks"],
        "lclComponents": len(report["lcl"]["components"]),
        "lclFalling": report["lcl"]["fallingLevel8Blocks"],
        "deepConstructedBlocks": report["deepConstructedBelowFloor"]["blocks"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
