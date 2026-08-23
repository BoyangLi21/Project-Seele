#!/usr/bin/env python3
"""Render the read-only coastal seed shortlist emitted by the dev command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "run/SEELE_S22_COASTAL/coastal_seed_scout.json"
DEFAULT_OUTPUT = ROOT / "artifacts/s24_coastal_seed_scout/candidates.png"


def color(height: int) -> tuple[int, int, int]:
    if height <= 63:
        depth = min(34, 63 - height)
        return 26, 104 + depth, 174 + min(54, depth * 2)
    if height <= 72:
        return 72, 153 + (height - 64) * 3, 86
    if height <= 88:
        value = 118 + (height - 73) * 4
        return value, 142, 82
    value = min(232, 150 + (height - 89) * 3)
    return value, value, value


def render_candidate(candidate: dict, bounds: list[int], step: int,
                     scale: int = 10) -> Image.Image:
    grid = candidate["grid"]
    if not grid:
        raise RuntimeError("Candidate report does not contain a height grid")
    height = len(grid)
    width = len(grid[0])
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for z, row in enumerate(grid):
        for x, value in enumerate(row):
            pixels[x, z] = color(int(value))
    image = image.resize((width * scale, height * scale),
                         Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    x0, x1, z0, z1 = bounds
    grid_x0 = x0 - 256
    grid_z0 = z0 - 256
    left = round((x0 - grid_x0) / step * scale)
    right = round((x1 - grid_x0) / step * scale)
    top = round((z0 - grid_z0) / step * scale)
    bottom = round((z1 - grid_z0) / step * scale)
    draw.rectangle((left, top, right, bottom), outline=(255, 62, 50), width=3)
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    candidates = [item for item in report["candidates"] if item.get("grid")]
    if not candidates:
        raise RuntimeError("No rendered finalists in survey report")
    panels = []
    font = ImageFont.load_default()
    for index, candidate in enumerate(candidates):
        body = render_candidate(candidate, report["cityRelativeBounds"],
                                report["sampleStep"])
        panel = Image.new("RGB", (body.width, body.height + 48), (20, 23, 28))
        panel.paste(body, (0, 48))
        draw = ImageDraw.Draw(panel)
        draw.text((8, 5), f"#{index + 1} seed {candidate['seed']}",
                  fill=(255, 186, 0), font=font)
        draw.text((8, 21),
                  f"land {candidate['landFraction'] * 100:.1f}%  "
                  f"p90-p10 {candidate['p90Spread']}  "
                  f"median {candidate['medianHeight']}  "
                  f"coast {candidate['coastSide']} "
                  f"{candidate['coastFraction'] * 100:.1f}%",
                  fill=(230, 232, 236), font=font)
        panels.append(panel)
    sheet = Image.new("RGB", (max(p.width for p in panels),
                              sum(p.height for p in panels) + 12 * (len(panels) - 1)),
                      (10, 12, 16))
    y = 0
    for panel in panels:
        sheet.paste(panel, (0, y))
        y += panel.height + 12
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(json.dumps({"report": str(args.report.resolve()),
                      "output": str(args.output.resolve()),
                      "candidates": len(panels)}, indent=2))


if __name__ == "__main__":
    main()
