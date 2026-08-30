#!/usr/bin/env python3
"""Build a chronological contact sheet with red review-frame numbers."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--cell-width", type=int, default=640)
    parser.add_argument("--font", type=Path,
                        default=Path(r"C:\Windows\Fonts\arialbd.ttf"))
    args = parser.parse_args()
    paths = sorted(args.input_dir.glob("*.png"))
    if not paths:
        raise SystemExit(f"no PNG frames in {args.input_dir}")
    if args.columns < 1 or args.cell_width < 64:
        raise SystemExit("columns and cell width must be positive")

    first = Image.open(paths[0]).convert("RGB")
    cell_height = round(first.height * args.cell_width / first.width)
    rows = math.ceil(len(paths) / args.columns)
    sheet = Image.new(
        "RGB", (args.columns * args.cell_width, rows * cell_height),
        (6, 8, 12),
    )
    font = ImageFont.truetype(
        str(args.font), max(28, round(cell_height * 0.105)))
    mapping = []
    for number, path in enumerate(paths, 1):
        image = Image.open(path).convert("RGB").resize(
            (args.cell_width, cell_height), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(image)
        label = f"{number:02d}"
        draw.text(
            (args.cell_width - 12, cell_height - 10), label,
            font=font, fill=(255, 24, 24), anchor="rb",
            stroke_width=3, stroke_fill=(255, 255, 255),
        )
        column = (number - 1) % args.columns
        row = (number - 1) // args.columns
        sheet.paste(image, (column * args.cell_width, row * cell_height))
        mapping.append({"review_number": number, "source_frame": path.name})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    report = {
        "schema": 1,
        "instruction": (
            "red number is chronological review order; smaller is earlier; "
            "it is not model geometry, texture, UI, or a joint marker"
        ),
        "input_dir": str(args.input_dir.resolve()),
        "output": str(args.output.resolve()),
        "frames": mapping,
    }
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
