#!/usr/bin/env python3
"""Inventory authored Tokyo-3 surface columns using the shared map reader."""

from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path

from PIL import Image, ImageDraw

from query_blocks import AIR, iter_box_cells


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
OUTPUT = ROOT / "artifacts/s24_source_inventory"
DIMENSION = "projectseele:geofront"
BOUNDS = (-320, 64, -120, 380, 220, 560)

NATURAL = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:tuff",
    "minecraft:calcite", "minecraft:dripstone_block", "minecraft:bedrock",
    "minecraft:dirt", "minecraft:grass_block", "minecraft:coarse_dirt",
    "minecraft:rooted_dirt", "minecraft:podzol", "minecraft:mud",
    "minecraft:clay", "minecraft:sand", "minecraft:red_sand",
    "minecraft:gravel", "minecraft:water", "minecraft:lava",
    "minecraft:snow", "minecraft:snow_block", "minecraft:ice",
    "minecraft:packed_ice", "minecraft:blue_ice",
    "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern",
    "minecraft:large_fern", "minecraft:dead_bush", "minecraft:vine",
    "minecraft:lily_pad", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp",
    "minecraft:kelp_plant", "minecraft:structure_void",
    "projectseele:geofront_skyweave",
}


def name(state: str) -> str:
    return state.split("[", 1)[0]


def natural(state: str) -> bool:
    value = name(state)
    return (value in NATURAL or value.endswith("_leaves")
            or value.endswith("_log") or value.endswith("_wood")
            or value.endswith("_sapling") or value.endswith("_ore"))


def components(columns: dict[tuple[int, int], list[int]]) -> list[dict]:
    remaining = set(columns)
    result = []
    while remaining:
        seed = remaining.pop()
        queue = deque([seed])
        cells = [seed]
        while queue:
            x, z = queue.popleft()
            for neighbour in ((x - 1, z), (x + 1, z),
                              (x, z - 1), (x, z + 1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)
                    cells.append(neighbour)
        xs = [cell[0] for cell in cells]
        zs = [cell[1] for cell in cells]
        bases = sorted(columns[cell][0] for cell in cells)
        tops = sorted(columns[cell][1] for cell in cells)
        result.append({
            "size": len(cells),
            "bbox": [min(xs), min(zs), max(xs), max(zs)],
            "baseMin": min(bases),
            "baseMedian": bases[len(bases) // 2],
            "topMax": max(tops),
            "cells": cells,
        })
    result.sort(key=lambda item: item["size"], reverse=True)
    return result


def render(parts: list[dict], output: Path) -> None:
    x0, _, z0, x1, _, z1 = BOUNDS
    image = Image.new("RGB", (x1 - x0 + 1, z1 - z0 + 1), (16, 20, 24))
    pixels = image.load()
    palette = [
        (255, 169, 0), (54, 195, 235), (220, 72, 72),
        (115, 214, 115), (181, 122, 255), (255, 225, 93),
    ]
    for index, part in enumerate(parts):
        color = palette[index % len(palette)] if index < 24 else (92, 98, 106)
        for x, z in part["cells"]:
            pixels[x - x0, z - z0] = color
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width - 1, image.height - 1),
                   outline=(230, 230, 230))
    image.save(output)
    dominant = Image.new("1", image.size, 0)
    dominant_pixels = dominant.load()
    for x, z in parts[0]["cells"]:
        dominant_pixels[x - x0, z - z0] = 1
    dominant.save(output.with_name("surface_dominant_mask.png"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    columns: dict[tuple[int, int], list[int]] = {}
    states = Counter()
    base_histogram = Counter()
    for (x, y, z), state in iter_box_cells(
            args.world, DIMENSION,
            (BOUNDS[0], BOUNDS[1], BOUNDS[2]),
            (BOUNDS[3], BOUNDS[4], BOUNDS[5])):
        if state in AIR or natural(state):
            continue
        states[name(state)] += 1
        column = columns.get((x, z))
        if column is None:
            columns[(x, z)] = [y, y]
        else:
            column[0] = min(column[0], y)
            column[1] = max(column[1], y)
    for low, _high in columns.values():
        base_histogram[low] += 1
    parts = components(columns)
    args.output.mkdir(parents=True, exist_ok=True)
    render(parts, args.output / "surface_authored_components.png")
    report = {
        "schema": 1,
        "world": str(args.world.resolve()),
        "dimension": DIMENSION,
        "bounds": BOUNDS,
        "authoredColumns": len(columns),
        "componentCount": len(parts),
        "components": [{key: value for key, value in part.items()
                        if key != "cells"} for part in parts[:200]],
        "baseHistogram": base_histogram.most_common(),
        "blockCounts": states.most_common(),
        "selectionAdvice": {
            "retain": "large human-authored components after visual review",
            "reject": "small isolated residual components and all natural terrain",
        },
    }
    path = args.output / "surface_authored_components.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(path.resolve()),
        "image": str((args.output / 'surface_authored_components.png').resolve()),
        "mask": str((args.output / 'surface_dominant_mask.png').resolve()),
        "authoredColumns": len(columns),
        "components": len(parts),
        "largest": [part["size"] for part in parts[:10]],
    }, indent=2))


if __name__ == "__main__":
    main()
