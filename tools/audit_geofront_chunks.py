#!/usr/bin/env python3
"""Audit generated block states at the GeoFront cavern sample points.

This is an offline counterpart to ``GeoFrontBuilder.countVanillaLavaSamples``.
It reads the custom dimension's Anvil chunks after a client run so generator
mistakes can be diagnosed without visually entering a dangerous world.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from inspect_map_assets import decode_modern_section, palette_name, region_chunks


HORIZONTAL = (-192, -128, -64, 0, 64, 128, 192)
VERTICAL = (-224, -160, -104, -64, 0, 64, 128, 192)
CAVERN_RADIUS = 256
CAVERN_CENTRE_OFFSET = (0, 112, -76)


def chunk_sections(chunk) -> list:
    root = chunk.get("Level", chunk)
    return list(root.get("sections", root.get("Sections", [])))


def load_chunks(region_dir: Path, coordinates: set[tuple[int, int]]) -> dict:
    chunks = {}
    by_region: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
    for chunk_x, chunk_z in coordinates:
        by_region[(chunk_x // 32, chunk_z // 32)].add((chunk_x, chunk_z))

    for (region_x, region_z), wanted in sorted(by_region.items()):
        region_path = region_dir / f"r.{region_x}.{region_z}.mca"
        if not region_path.is_file():
            continue
        min_x = min(point[0] for point in wanted)
        max_x = max(point[0] for point in wanted)
        min_z = min(point[1] for point in wanted)
        max_z = max(point[1] for point in wanted)
        for chunk_x, chunk_z, chunk in region_chunks(
                region_path, (min_x, max_x, min_z, max_z)):
            if (chunk_x, chunk_z) in wanted:
                chunks[(chunk_x, chunk_z)] = chunk
    return chunks


def state_at(chunks: dict, x: int, y: int, z: int) -> str:
    chunk = chunks.get((x // 16, z // 16))
    if chunk is None:
        return "<missing-chunk>"
    section_y = y // 16
    section = next((entry for entry in chunk_sections(chunk)
                    if int(entry.get("Y", 0)) == section_y), None)
    if section is None:
        return "minecraft:air"
    palette, indices = decode_modern_section(section)
    if not palette:
        return "minecraft:air"
    index = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
    palette_index = int(indices[index])
    if palette_index < 0 or palette_index >= len(palette):
        return "<invalid-palette-index>"
    return palette_name(palette[palette_index])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--origin", nargs=3, type=int,
                        default=(30, -380, 296), metavar=("X", "Y", "Z"))
    args = parser.parse_args()

    region_dir = (args.world / "dimensions" / "projectseele" / "geofront"
                  / "region")
    centre = tuple(args.origin[index] + CAVERN_CENTRE_OFFSET[index]
                   for index in range(3))
    safe_radius_squared = (CAVERN_RADIUS - 20) ** 2
    points = []
    for dx in HORIZONTAL:
        for dy in VERTICAL:
            for dz in HORIZONTAL:
                if dx * dx + dy * dy + dz * dz <= safe_radius_squared:
                    points.append((centre[0] + dx, centre[1] + dy,
                                   centre[2] + dz))

    chunk_coordinates = {(x // 16, z // 16) for x, _, z in points}
    chunks = load_chunks(region_dir, chunk_coordinates)
    states = Counter()
    states_by_y: dict[int, Counter] = defaultdict(Counter)
    for x, y, z in points:
        state = state_at(chunks, x, y, z)
        states[state] += 1
        states_by_y[y][state] += 1

    print(f"region={region_dir}")
    print(f"centre={centre} points={len(points)} chunks={len(chunks)}/"
          f"{len(chunk_coordinates)}")
    print("states=" + ", ".join(
        f"{name}:{count}" for name, count in states.most_common()))
    for y in sorted(states_by_y):
        summary = ", ".join(
            f"{name}:{count}" for name, count in states_by_y[y].most_common())
        print(f"y={y}: {summary}")


if __name__ == "__main__":
    main()
