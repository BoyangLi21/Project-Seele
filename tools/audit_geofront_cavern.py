#!/usr/bin/env python3
"""Audit the GeoFront sphere shell and raw-stone vertical remnants.

This is a read-only whole-cavern audit. It decodes only relevant palette
indices from loaded Anvil sections, so it does not materialize the complete
641-cubed sphere in memory.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import csv
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from inspect_map_assets import decode_modern_section, iter_chunks, palette_name
from query_blocks import dimension_dir


CENTRE = (30, -332, 220)
RADIUS = 320
FLOOR_Y = -444
STONE = "minecraft:stone"
SHELL_NAMES = {
    "minecraft:cyan_terracotta",
    "ars_nouveau:sky_block",
    "projectseele:geofront_skyweave",
}


def contiguous_runs(values: list[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    runs: list[list[int]] = [[values[0], values[0]]]
    for value in values[1:]:
        if value == runs[-1][1] + 1:
            runs[-1][1] = value
        else:
            runs.append([value, value])
    return [(start, end) for start, end in runs]


def scan(world: Path, dimension: str) -> tuple[
        dict[str, object], list[tuple[int, int, int]],
        list[tuple[int, int, int]]]:
    root = dimension_dir(world, dimension)
    min_x = (CENTRE[0] - RADIUS) >> 4
    max_x = (CENTRE[0] + RADIUS) >> 4
    min_z = (CENTRE[2] - RADIUS) >> 4
    max_z = (CENTRE[2] + RADIUS) >> 4
    bounds = (min_x, max_x, min_z, max_z)

    shell_counts: dict[str, int] = defaultdict(int)
    shell_radial_counts: dict[str, int] = defaultdict(int)
    shell_off_band_samples: dict[str, list[list[int]]] = defaultdict(list)
    stone_by_column: dict[tuple[int, int], list[int]] = defaultdict(list)
    parsed_chunks = 0
    relevant_sections = 0

    centre_x, centre_y, centre_z = CENTRE
    # The visible cavity ends at the inner face of the three-block shell.
    # Using R-6 hid most of the edge needles: the reported column at
    # (-194, *, 0) intersected only nine cells of that smaller audit sphere
    # even though roughly 80 stone cells protruded into the visible cavern.
    inner_radius_sq = (RADIUS - 3) ** 2
    shell_inner_sq = (RADIUS - 4) ** 2
    shell_outer_sq = (RADIUS + 4) ** 2

    for chunk_x, chunk_z, chunk in iter_chunks(root, bounds):
        parsed_chunks += 1
        base_x, base_z = chunk_x * 16, chunk_z * 16
        for section in chunk.get("sections", []):
            section_y = int(section.get("Y", 0))
            base_y = section_y * 16
            if base_y > centre_y + RADIUS + 4 \
                    or base_y + 15 < centre_y - RADIUS - 4:
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            names = [palette_name(entry) for entry in palette]
            wanted = [index for index, name in enumerate(names)
                      if name == STONE or name in SHELL_NAMES]
            if not wanted:
                continue
            relevant_sections += 1
            for palette_index in wanted:
                offsets = np.flatnonzero(indices == palette_index)
                if not offsets.size:
                    continue
                name = names[palette_index]
                xs = base_x + (offsets & 15)
                zs = base_z + ((offsets >> 4) & 15)
                ys = base_y + (offsets >> 8)
                dx = xs - centre_x
                dy = ys - centre_y
                dz = zs - centre_z
                radius_sq = dx * dx + dy * dy + dz * dz

                if name in SHELL_NAMES:
                    shell_counts[name] += int(offsets.size)
                    radial_mask = ((radius_sq >= shell_inner_sq)
                                   & (radius_sq <= shell_outer_sq))
                    shell_radial_counts[name] += int(np.count_nonzero(
                        radial_mask))
                    if len(shell_off_band_samples[name]) < 20:
                        for x, y, z in zip(xs[~radial_mask], ys[~radial_mask],
                                           zs[~radial_mask]):
                            shell_off_band_samples[name].append(
                                [int(x), int(y), int(z)])
                            if len(shell_off_band_samples[name]) >= 20:
                                break
                    continue

                # Keep all interior raw stone by column.  The upper residue
                # audit below still uses FLOOR_Y + 8, while the legacy-floor
                # audit detects continuous stone extending below the four-
                # layer authored terrain slab.  The old upper-only filter
                # missed the chunk-grid needles reported at (176, *, 432).
                mask = radius_sq <= inner_radius_sq
                for x, y, z in zip(xs[mask], ys[mask], zs[mask]):
                    stone_by_column[(int(x), int(z))].append(int(y))

    vertical_voxels: set[tuple[int, int, int]] = set()
    legacy_floor_voxels: set[tuple[int, int, int]] = set()
    column_runs: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for column, values in stone_by_column.items():
        unique = sorted(set(values))
        upper = [value for value in unique if value >= FLOOR_Y + 8]
        runs = contiguous_runs(upper)
        tall = [(start, end) for start, end in runs
                if end - start + 1 >= 4]
        if not tall:
            tall = []
        else:
            column_runs[column] = tall
            for start, end in tall:
                vertical_voxels.update(
                    (column[0], y, column[1])
                    for y in range(start, end + 1))

        # The accepted fabric terrain is exactly four layers deep.  A raw-
        # stone run that reaches y <= -450 and continues for at least eight
        # blocks is therefore a legacy support/needle, not terrain.  Include
        # the complete connected run so the portion piercing buildings is not
        # left hanging above the repaired floor.
        for start, end in contiguous_runs(unique):
            if start <= FLOOR_Y - 6 and end - start + 1 >= 8:
                legacy_floor_voxels.update(
                    (column[0], y, column[1])
                    for y in range(start, end + 1))

    components: list[dict[str, object]] = []
    suspicious_cells: list[tuple[int, int, int]] = []
    remaining = set(vertical_voxels)
    while remaining:
        seed = remaining.pop()
        queue = deque([seed])
        cells = [seed]
        while queue:
            x, y, z = queue.popleft()
            for neighbour in ((x + 1, y, z), (x - 1, y, z),
                              (x, y + 1, z), (x, y - 1, z),
                              (x, y, z + 1), (x, y, z - 1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)
                    cells.append(neighbour)
        xs = [cell[0] for cell in cells]
        ys = [cell[1] for cell in cells]
        zs = [cell[2] for cell in cells]
        footprint = len({(cell[0], cell[2]) for cell in cells})
        width = max(xs) - min(xs) + 1
        height = max(ys) - min(ys) + 1
        depth = max(zs) - min(zs) + 1
        suspicious = height >= 12 and width <= 8 and depth <= 8
        if suspicious:
            suspicious_cells.extend(cells)
        components.append({
            "voxels": len(cells),
            "footprintColumns": footprint,
            "bbox": [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
            "width": width,
            "height": height,
            "depth": depth,
            "suspicious": suspicious,
        })
    components.sort(key=lambda item: (-int(item["height"]),
                                      -int(item["voxels"])))

    report = {
        "world": str(world.resolve()),
        "dimension": dimension,
        "sphere": {"centre": list(CENTRE), "radius": RADIUS},
        "parsedChunks": parsed_chunks,
        "relevantSections": relevant_sections,
        "shellBlocks": dict(sorted(shell_counts.items())),
        "shellBlocksWithinRadiusBand": dict(sorted(
            shell_radial_counts.items())),
        "shellBlocksOutsideRadiusBandSamples": dict(sorted(
            shell_off_band_samples.items())),
        "stoneColumnsWithRunsAtLeast4": len(column_runs),
        "verticalStoneVoxels": len(vertical_voxels),
        "suspiciousStoneComponents": sum(
            1 for item in components if item["suspicious"]),
        "suspiciousStoneVoxels": len(suspicious_cells),
        "legacyFloorColumnCount": len({
            (x, z) for x, _, z in legacy_floor_voxels
        }),
        "legacyFloorColumnVoxels": len(legacy_floor_voxels),
        "verticalStoneComponents": components,
    }
    return report, sorted(suspicious_cells), sorted(legacy_floor_voxels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--dim", default="projectseele:geofront")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--candidate-csv", type=Path)
    parser.add_argument("--legacy-floor-csv", type=Path)
    args = parser.parse_args()
    report, suspicious, legacy_floor = scan(args.world.resolve(), args.dim)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    if args.candidate_csv:
        args.candidate_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.candidate_csv.open("w", newline="", encoding="ascii") as stream:
            writer = csv.writer(stream)
            writer.writerow(("x", "y", "z", "before", "after"))
            writer.writerows((x, y, z, STONE, "minecraft:air")
                             for x, y, z in suspicious)
    if args.legacy_floor_csv:
        args.legacy_floor_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.legacy_floor_csv.open(
                "w", newline="", encoding="ascii") as stream:
            writer = csv.writer(stream)
            writer.writerow(("x", "y", "z", "before", "after"))
            writer.writerows((x, y, z, STONE, "minecraft:air")
                             for x, y, z in legacy_floor)
    print(json.dumps({
        "world": report["world"],
        "parsedChunks": report["parsedChunks"],
        "shellBlocks": report["shellBlocks"],
        "shellBlocksWithinRadiusBand":
            report["shellBlocksWithinRadiusBand"],
        "suspiciousStoneComponents":
            report["suspiciousStoneComponents"],
        "suspiciousStoneVoxels": report["suspiciousStoneVoxels"],
        "legacyFloorColumnCount": report["legacyFloorColumnCount"],
        "legacyFloorColumnVoxels": report["legacyFloorColumnVoxels"],
    }, indent=2))


if __name__ == "__main__":
    main()
