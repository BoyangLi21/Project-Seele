#!/usr/bin/env python3
"""Render the S22 GeoFront production-reference spatial contract.

This is a design artifact, not a world writer.  It keeps every measured and
already-applied exterior packet visible against the TV setting drawing's
6 km shallow dome / 2 km flat ceiling proportions so later construction does
not invent rooms in unmeasured air or overlap approved authored geometry.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CENTRE_X = 30
CENTRE_Z = 296
DOME_RADIUS = 1800
FLAT_CEILING_RADIUS = 600
CITY_RADIUS = 450
SURFACE_DATUM = 68
DOME_BASE_Y = -512
ROOF_COVER = 16
FLOOR_Y = -466


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def roof_height(distance: float) -> int:
    flat_top = SURFACE_DATUM - ROOF_COVER
    if distance <= FLAT_CEILING_RADIUS:
        return flat_top
    transition = min(1.0, (distance - FLAT_CEILING_RADIUS)
                     / (DOME_RADIUS - FLAT_CEILING_RADIUS))
    dome = math.sqrt(max(0.0, 1.0 - transition * transition))
    return DOME_BASE_Y + math.floor((flat_top - DOME_BASE_Y) * dome)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/s22_coastal_rebuild/"
                                     "canonical_masterplan.png"))
    args = parser.parse_args()

    width, height = 1800, 1050
    image = Image.new("RGB", (width, height), "#0b1118")
    draw = ImageDraw.Draw(image, "RGBA")
    title = font(28)
    body = font(17)
    small = font(14)
    draw.text((36, 20), "S22 GEOFRONT / TV PRODUCTION GEOMETRY CONTRACT",
              font=title, fill="#f0b323")
    draw.text((36, 57),
              "3,600-block shallow dome | 1,200-block flat roof | command interior frozen",
              font=body, fill="#c8d3df")

    plan_box = (40, 95, 1020, 1015)
    px0, py0, px1, py1 = plan_box
    plan_cx = (px0 + px1) / 2
    plan_cy = (py0 + py1) / 2
    scale = min((px1 - px0) / (DOME_RADIUS * 2.12),
                (py1 - py0) / (DOME_RADIUS * 2.12))

    def point(x: float, z: float) -> tuple[float, float]:
        return (plan_cx + (x - CENTRE_X) * scale,
                plan_cy + (z - CENTRE_Z) * scale)

    def circle(radius: int, fill, outline, width_px=2) -> None:
        cx, cy = point(CENTRE_X, CENTRE_Z)
        r = radius * scale
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=fill,
                     outline=outline, width=width_px)

    circle(DOME_RADIUS, "#17252e", "#7da3ac", 3)
    circle(FLAT_CEILING_RADIUS, "#24313c88", "#63c7e6", 3)
    circle(CITY_RADIUS, "#463c5555", "#b790d4", 2)

    # Lake uses the same canonical equation as the chunk generator.
    lake = []
    for angle in range(361):
        a = math.radians(angle)
        # Setting-derived asymmetric ellipse; small harmonics keep the shore
        # from reading as a mathematically perfect oval.
        radius = 1.0 - 0.08 * math.sin(angle * 3 * math.pi / 180)
        x = CENTRE_X - 310 + math.cos(a) * 320 * radius
        z = CENTRE_Z - 200 + math.sin(a) * 210 * radius
        lake.append(point(x, z))
    draw.polygon(lake, fill="#226ba4d8", outline="#62b7e9")

    # Forest and hill masses are deliberately asymmetric like the production
    # plan.  Ellipses show influence zones, not permission to overwrite.
    zones = [
        (-620, 626, 430, 310, "FOREST NW", "#2c7b4f88"),
        (-130, 1056, 390, 290, "FOREST / SOUTH HILLS", "#39794d88"),
        (750, 476, 380, 280, "FOREST EAST", "#2f6f4788"),
        (450, 976, 360, 210, "HILLS", "#80674688"),
    ]
    for x, z, rx, rz, label, colour in zones:
        cx, cy = point(x, z)
        draw.ellipse((cx-rx*scale, cy-rz*scale,
                      cx+rx*scale, cy+rz*scale), fill=colour,
                     outline="#8db081")
        draw.text((cx-rx*scale+5, cy-8), label, font=small,
                  fill="#d3e9ce")

    def rect(bounds, fill, outline, label, offset=(3, 3)) -> None:
        x0, z0, x1, z1 = bounds
        a, b = point(x0, z0), point(x1, z1)
        box = (min(a[0], b[0]), min(a[1], b[1]),
               max(a[0], b[0]), max(a[1], b[1]))
        draw.rectangle(box, fill=fill, outline=outline, width=2)
        draw.text((box[0]+offset[0], box[1]+offset[1]), label,
                  font=small, fill="#ffffff")

    rect((-104, 193, 159, 400), "#6d737ccc", "#e6e8ea",
         "MEASURED HQ CAMPUS")
    rect((-106, 190, -65, 232), "#c87b2acc", "#ffc36b",
         "MAIN ENTRANCE")
    rect((-184, 122, -96, 180), "#7f335fcc", "#ed8cc0",
         "EVA DOCK / 3 BERTHS")
    rect((160, 244, 364, 402), "#4f5666bb", "#99a9bf",
         "ARTIFICIAL SECTOR")

    route = [(-220, 120), (-100, 120), (-100, 210), (-65, 210)]
    draw.line([point(x, z) for x, z in route], fill="#f0a33c",
              width=5, joint="curve")
    draw.text(point(-218, 104), "LAKE TERMINAL", font=small,
              fill="#ffd394")

    cx, cy = point(CENTRE_X, CENTRE_Z)
    draw.line((cx-10, cy, cx+10, cy), fill="#ffffff", width=2)
    draw.line((cx, cy-10, cx, cy+10), fill="#ffffff", width=2)
    draw.text((cx+10, cy+8), "GeoFront datum (30,296)", font=small,
              fill="#ffffff")

    # Cross-section uses the exact r6 equation.
    sx0, sy0, sx1, sy1 = 1080, 130, 1760, 700
    draw.rounded_rectangle((1050, 92, 1780, 735), radius=18,
                           fill="#111923", outline="#354a59", width=2)
    draw.text((1080, 112), "CANONICAL CROSS-SECTION", font=body,
              fill="#f0b323")

    min_y, max_y = -540, 80
    def sec(distance: float, y: float) -> tuple[float, float]:
        x = sx0 + (distance + DOME_RADIUS) / (2*DOME_RADIUS) * (sx1-sx0)
        py = sy1 - (y-min_y)/(max_y-min_y)*(sy1-sy0)
        return x, py

    roof_points = [sec(d, roof_height(abs(d)))
                   for d in range(-DOME_RADIUS, DOME_RADIUS+1, 12)]
    floor_points = [sec(d, FLOOR_Y) for d in (-DOME_RADIUS, DOME_RADIUS)]
    draw.line(roof_points, fill="#70d4ed", width=4)
    draw.line(floor_points, fill="#75a26a", width=4)
    draw.line((sec(-FLAT_CEILING_RADIUS, 52),
               sec(FLAT_CEILING_RADIUS, 52)), fill="#d6eff5", width=2)
    draw.text((1090, sec(0, 52)[1]-26), "flat ceiling y=52",
              font=small, fill="#d6eff5")
    draw.text((1090, sec(0, FLOOR_Y)[1]+8), "park floor y≈-466",
              font=small, fill="#b9d9ad")

    heights = [(0, roof_height(0)), (600, roof_height(600)),
               (900, roof_height(900)), (1200, roof_height(1200)),
               (1500, roof_height(1500)), (1800, roof_height(1800))]
    draw.text((1080, 765), "ROOF PROFILE (radius -> y)", font=body,
              fill="#f0b323")
    for row, (radius, y) in enumerate(heights):
        draw.text((1090, 804+row*29), f"{radius:4d} -> {y:4d}",
                  font=body, fill="#d4dde6")

    draw.text((1330, 765), "FROZEN / IMPLEMENTED CONTRACT", font=body,
              fill="#f0b323")
    notes = [
        "- command-room interior: FROZEN",
        "- main entrance: compact, lake-facing",
        "- underground lake: irregular west/northwest mass",
        "- EVA dock: separate vertical mechanical landmark",
        "- outer chunks: generated lazily; no 50k-chunk pregen",
        "- no generic rooms in empty volume",
    ]
    for row, note in enumerate(notes):
        draw.text((1340, 804+row*29), note, font=small,
                  fill="#c8d3df")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
