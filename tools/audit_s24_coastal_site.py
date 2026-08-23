#!/usr/bin/env python3
"""Exact one-block coastal-site audit after real chunk generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from query_blocks import AIR, iter_box_cells


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S24_COASTAL_REBUILD"
OUTPUT = ROOT / "artifacts/s24_coastal_site_exact"
DIMENSION = "projectseele:geofront"
Y0, Y1 = -64, 128

FLUIDS = {"minecraft:water", "minecraft:lava"}
PLANTS = {
    "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern",
    "minecraft:large_fern", "minecraft:dead_bush", "minecraft:vine",
    "minecraft:snow", "minecraft:lily_pad", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp", "minecraft:kelp_plant",
}


def name(state: str) -> str:
    return state.split("[", 1)[0]


def ground(state: str) -> bool:
    value = name(state)
    return (value not in AIR and value not in FLUIDS and value not in PLANTS
            and not value.endswith("_leaves") and not value.endswith("_log")
            and not value.endswith("_wood") and not value.endswith("_sapling"))


def color(height: int, water: bool) -> tuple[int, int, int]:
    if water:
        return 24, 111, 184
    if height <= 72:
        return 72, min(200, 150 + max(0, height - 64) * 5), 82
    if height <= 88:
        return 142 + (height - 73) * 4, 140, 76
    value = min(235, 170 + (height - 89) * 3)
    return value, value, value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--anchor-x", type=int)
    parser.add_argument("--anchor-z", type=int)
    args = parser.parse_args()
    marker = json.loads((args.world / ".projectseele_s24_coastal.json")
                        .read_text(encoding="utf-8"))
    marker_x, deck_y, marker_z = map(int, marker["target_anchor"])
    anchor_x = args.anchor_x if args.anchor_x is not None else marker_x
    anchor_z = args.anchor_z if args.anchor_z is not None else marker_z
    x0, x1 = anchor_x - 224, anchor_x + 224
    z0, z1 = anchor_z - 300, anchor_z + 148
    tops: dict[tuple[int, int], int] = {}
    water_columns: set[tuple[int, int]] = set()
    seen_columns: set[tuple[int, int]] = set()
    for (x, y, z), state in iter_box_cells(
            args.world, DIMENSION, (x0, Y0, z0), (x1, Y1, z1)):
        seen_columns.add((x, z))
        if 62 <= y <= 65 and name(state) == "minecraft:water":
            water_columns.add((x, z))
        if ground(state):
            tops[(x, z)] = max(tops.get((x, z), Y0), y)
    expected = (x1 - x0 + 1) * (z1 - z0 + 1)
    if len(seen_columns) != expected:
        raise RuntimeError(f"site chunks incomplete: loaded columns "
                           f"{len(seen_columns)}/{expected}")
    for cell in seen_columns:
        tops.setdefault(cell, Y0 - 1)
    land_heights = sorted(height for cell, height in tops.items()
                          if cell not in water_columns)
    p10 = land_heights[round((len(land_heights) - 1) * 0.10)]
    median = land_heights[len(land_heights) // 2]
    p90 = land_heights[round((len(land_heights) - 1) * 0.90)]
    land_fraction = 1.0 - len(water_columns) / expected
    image = Image.new("RGB", (x1 - x0 + 1, z1 - z0 + 1))
    pixels = image.load()
    for (x, z), height in tops.items():
        pixels[x - x0, z - z0] = color(height, (x, z) in water_columns)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width - 1, image.height - 1),
                   outline=(255, 64, 48), width=2)
    args.output.mkdir(parents=True, exist_ok=True)
    image.save(args.output / "tokyo3_core_heightmap.png")
    report = {
        "schema": 1,
        "world": str(args.world.resolve()),
        "dimension": DIMENSION,
        "targetAnchor": [anchor_x, deck_y, anchor_z],
        "bounds": [x0, z0, x1, z1],
        "columns": expected,
        "landColumns": expected - len(water_columns),
        "waterColumns": len(water_columns),
        "landFraction": land_fraction,
        "median": median,
        "p10": p10,
        "p90": p90,
        "spread": p90 - p10,
        "passes": land_fraction >= 0.80 and p90 - p10 <= 15
                  and abs(median - deck_y) <= 8,
    }
    (args.output / "site_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
