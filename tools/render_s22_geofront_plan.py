#!/usr/bin/env python3
"""Render compact material plans of the authored S22 GeoFront.

This is a reusable map-reading tool, not a generator.  It renders selected
horizontal slices directly from the saved Anvil chunks so exterior packets can
be placed around, rather than through, accepted facilities.
"""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from query_blocks import read_box


AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = AIR | {
    "minecraft:water", "minecraft:grass_block", "minecraft:dirt",
    "minecraft:stone", "minecraft:deepslate", "minecraft:sand",
    "minecraft:clay", "minecraft:gravel", "minecraft:oak_log",
    "minecraft:oak_leaves", "minecraft:spruce_log",
    "minecraft:spruce_leaves", "minecraft:bedrock",
}


def bare(state: str | None) -> str:
    if state is None:
        return "missing"
    return state.split("[", 1)[0]


def colour(state: str | None) -> tuple[int, int, int]:
    name = bare(state)
    if name == "missing":
        return 10, 10, 14
    if name in AIR:
        return 20, 22, 28
    if name == "minecraft:water":
        return 39, 107, 170
    if name in {"minecraft:grass_block", "minecraft:dirt",
                "minecraft:oak_log", "minecraft:oak_leaves",
                "minecraft:spruce_log", "minecraft:spruce_leaves"}:
        return 53, 116, 65
    if name in {"minecraft:sand", "minecraft:clay", "minecraft:gravel"}:
        return 162, 140, 91
    if name in {"minecraft:stone", "minecraft:deepslate"}:
        return 74, 76, 82
    if name == "minecraft:orange_concrete":
        return 226, 106, 18
    if name == "minecraft:yellow_concrete":
        return 225, 188, 30
    if name == "minecraft:purple_concrete":
        return 111, 42, 146
    if name == "minecraft:red_concrete":
        return 174, 43, 48
    if name in {"projectseele:clear_glass", "minecraft:glass",
                "ars_nouveau:sky_block",
                "projectseele:geofront_skyweave"}:
        return 89, 190, 205
    if name in {"minecraft:sea_lantern", "minecraft:light"}:
        return 220, 242, 225
    if "black" in name:
        return 35, 35, 40
    if "polished" in name or "concrete" in name or "iron" in name:
        return 154, 158, 165
    return 118, 98, 121


def engineered_components(cells, y: int) -> list[dict[str, object]]:
    remaining = {(x, z) for (x, cell_y, z), state in cells.items()
                 if cell_y == y and bare(state) not in NATURAL}
    result = []
    while remaining:
        seed = remaining.pop()
        queue = deque([seed])
        component = [seed]
        while queue:
            x, z = queue.popleft()
            for neighbour in ((x - 1, z), (x + 1, z),
                              (x, z - 1), (x, z + 1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)
                    component.append(neighbour)
        xs = [position[0] for position in component]
        zs = [position[1] for position in component]
        result.append({"cells": len(component),
                       "bbox": [min(xs), y, min(zs), max(xs), y, max(zs)]})
    result.sort(key=lambda item: -int(item["cells"]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--dim", default="projectseele:geofront")
    parser.add_argument("--box", nargs=4, type=int, required=True,
                        metavar=("X0", "Z0", "X1", "Z1"))
    parser.add_argument("--levels", nargs="+", type=int, required=True)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--components-json", type=Path)
    args = parser.parse_args()

    x0, z0, x1, z1 = args.box
    lo_x, hi_x = sorted((x0, x1))
    lo_z, hi_z = sorted((z0, z1))
    scale = max(1, args.scale)
    panel_w = (hi_x - lo_x + 1) * scale
    panel_h = (hi_z - lo_z + 1) * scale
    margin = 34
    image = Image.new("RGB", (panel_w * len(args.levels), panel_h + margin),
                      (17, 19, 24))
    draw = ImageDraw.Draw(image)

    summaries = {}
    for panel, y in enumerate(args.levels):
        cells = read_box(args.world, args.dim,
                         (lo_x, y, lo_z), (hi_x, y, hi_z))
        summaries[str(y)] = engineered_components(cells, y)[:40]
        origin_x = panel * panel_w
        for z in range(lo_z, hi_z + 1):
            py = margin + (z - lo_z) * scale
            for x in range(lo_x, hi_x + 1):
                px = origin_x + (x - lo_x) * scale
                image.paste(colour(cells.get((x, y, z))),
                            (px, py, px + scale, py + scale))
        draw.text((origin_x + 6, 7),
                  f"S22 GeoFront y={y}  x={lo_x}..{hi_x} z={lo_z}..{hi_z}",
                  fill=(245, 177, 26))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    if args.components_json:
        args.components_json.parent.mkdir(parents=True, exist_ok=True)
        args.components_json.write_text(
            json.dumps(summaries, indent=2) + "\n", encoding="ascii")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
