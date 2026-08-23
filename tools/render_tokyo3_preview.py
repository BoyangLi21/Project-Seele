#!/usr/bin/env python3
"""Render the deterministic original Tokyo-3 sortie district without Minecraft."""

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
JAVA_BUILDER = ROOT / (
    "src/main/java/com/projectseele/world/ThirdTokyoSurfaceBuilder.java")
DEFAULT_OUTPUT = ROOT / "external-assets/work/tokyo3-preview/tokyo3_preview.png"

DISTRICT_HALF = 208
ROAD_AXES = (-180, -140, -100, -60, -20, 20, 60, 100, 140, 180)
LOT_CENTRES = (-160, -120, -80, -40, 0, 40, 80, 120, 160)
OUTER_LOT_CENTRES = (-200, -160, -120, -80, -40, 0,
                     40, 80, 120, 160, 200)
LOT_HALF = 12
OUTER_LOT_HALF = 9
PYLONS = ((-180, -160), (-180, 0), (-180, 160),
          (180, -160), (180, 0), (180, 160))
UNIT_BAYS = ((-42, "UNIT-00", "#d78620"),
             (0, "UNIT-01", "#783cad"),
             (42, "UNIT-02", "#b92f35"))


def tower_height(x, z):
    grid_x, grid_z = x // 40, z // 40
    return 22 + ((grid_x * 31 + grid_z * 17) % 6) * 4


def lot_kind(x, z):
    if abs(x) <= 40 and abs(z) <= 40:
        return "reserved"
    if (x, z) in ((-120, -80), (120, -80), (120, 80),
                  (80, 80), (80, 40)):
        return "private"
    if (x, z) in ((0, -80), (80, 0)):
        return "substation"
    if (x, z) == (0, 80):
        return "weapon"
    return "tower"


def outer_tower_height(x, z):
    return 18 + ((x * 13 + z * 29) % 5) * 5


def outer_lots():
    for x in OUTER_LOT_CENTRES:
        for z in OUTER_LOT_CENTRES:
            if max(abs(x), abs(z)) == 200 and x != 200:
                yield x, z


def load_font(size):
    candidates = (
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def world_to_plan(x, z, centre=(350, 480), scale=1.35):
    return centre[0] + x * scale, centre[1] + z * scale


def iso(x, z, y=0.0, centre=(1135, 670)):
    return centre[0] + (x - z) * 0.78, centre[1] + (x + z) * 0.33 - y * 1.4


def rectangle_world(draw, bounds, fill, outline=None, width=1):
    x0, z0, x1, z1 = bounds
    p0 = world_to_plan(x0, z0)
    p1 = world_to_plan(x1, z1)
    draw.rectangle((*p0, *p1), fill=fill, outline=outline, width=width)


def draw_plan(draw, fonts):
    panel = (24, 86, 684, 824)
    draw.rounded_rectangle(panel, radius=16, fill="#151c25", outline="#3b4857", width=2)
    draw.text((44, 103), "TOKYO-3 / SURFACE SORTIE PLAN", font=fonts["sub"], fill="#f0a000")

    rectangle_world(draw, (-208, -208, 208, 208), "#202a34", "#627181", 2)
    for axis in ROAD_AXES:
        rectangle_world(draw, (axis - 7, -208, axis + 7, 208), "#58616a")
        rectangle_world(draw, (axis - 4, -208, axis + 4, 208), "#171a1d")
        rectangle_world(draw, (-208, axis - 7, 208, axis + 7), "#58616a")
        rectangle_world(draw, (-208, axis - 4, 208, axis + 4), "#171a1d")

    for axis in ROAD_AXES:
        p0 = world_to_plan(axis, -208)
        p1 = world_to_plan(axis, 208)
        draw.line((p0, p1), fill="#c99916", width=1)
        p0 = world_to_plan(-208, axis)
        p1 = world_to_plan(208, axis)
        draw.line((p0, p1), fill="#c99916", width=1)

    tower_count = 0
    for x in LOT_CENTRES:
        for z in LOT_CENTRES:
            kind = lot_kind(x, z)
            if kind == "reserved":
                continue
            if kind == "tower":
                height = tower_height(x, z)
                colour = "#526d80" if height < 34 else "#668aa3"
                rectangle_world(draw, (x - LOT_HALF, z - LOT_HALF,
                                       x + LOT_HALF, z + LOT_HALF),
                                colour, "#a8d8ed", 2)
                px, py = world_to_plan(x, z)
                draw.text((px - 12, py - 7), str(height), font=fonts["tiny"],
                          fill="#e6f5ff")
                tower_count += 1
            elif kind == "private":
                rectangle_world(draw, (x - LOT_HALF, z - LOT_HALF,
                                       x + LOT_HALF, z + LOT_HALF),
                                "#684b78", "#f29cff", 2)
                px, py = world_to_plan(x, z)
                draw.text((px - 16, py - 7), "NBT",
                          font=fonts["tiny"], fill="#ffe7ff")
            elif kind == "substation":
                rectangle_world(draw, (x - LOT_HALF, z - LOT_HALF,
                                       x + LOT_HALF, z + LOT_HALF),
                                "#9e6233", "#f0a000", 2)
                px, py = world_to_plan(x, z)
                draw.text((px - 17, py - 7), "SUB", font=fonts["tiny"], fill="#fff0bd")
            elif kind == "weapon":
                rectangle_world(draw, (x - LOT_HALF, z - 8,
                                       x + LOT_HALF, z + 8),
                                "#29313b", "#f0a000", 3)
                px, py = world_to_plan(x, z)
                draw.text((px - 28, py - 7), "WPN LIFT",
                          font=fonts["micro"], fill="#f0a000")
            else:
                rectangle_world(draw, (x - LOT_HALF, z - LOT_HALF,
                                       x + LOT_HALF, z + LOT_HALF),
                                "#652129", "#ff4b55", 2)
                px, py = world_to_plan(x, z)
                draw.ellipse((px - 8, py - 8, px + 8, py + 8),
                             fill="#ff172d", outline="#ffd6d9", width=2)

    outer_count = 0
    for x, z in outer_lots():
        rectangle_world(draw, (x - OUTER_LOT_HALF, z - OUTER_LOT_HALF,
                               x + OUTER_LOT_HALF, z + OUTER_LOT_HALF),
                        "#405768", "#8ebbd1", 1)
        outer_count += 1

    rectangle_world(draw, (-48, -36, 48, 44), "#3b4149", "#f0a000", 3)
    px, py = world_to_plan(0, 28)
    draw.text((px - 39, py - 8), "NERV SORTIE", font=fonts["tiny"], fill="#f0a000")
    for x, label, colour in UNIT_BAYS:
        cx, cy = world_to_plan(x, 0)
        draw.rectangle((cx - 15, cy - 15, cx + 15, cy + 15),
                       fill="#090b0e", outline=colour, width=3)
        draw.text((cx - 22, cy + 18), label, font=fonts["micro"], fill=colour)

    for side_x in (-180, 180):
        points = [world_to_plan(side_x, z) for z in (-160, 0, 160)]
        draw.line(points, fill="#b7c6cc", width=2)
    for x, z in PYLONS:
        cx, cy = world_to_plan(x, z)
        draw.polygon(((cx, cy - 7), (cx - 6, cy + 6), (cx + 6, cy + 6)),
                     fill="#c6d0d5", outline="#ffffff")

    ox, oy = world_to_plan(0, 216)
    draw.rectangle((ox - 13, oy - 7, ox + 13, oy + 7),
                   fill="#d9e1e5", outline="#f0a000", width=2)
    draw.text((ox - 28, oy + 10), "OBS DECK", font=fonts["micro"], fill="#f0a000")
    draw.text((44, 785),
               f"416 x 416 | {tower_count} inner + {outer_count} outer + 3 local towers",
              font=fonts["tiny"], fill="#aebcc8")


def iso_box(draw, x, z, half, height, top, left, right):
    base = [iso(x - half, z - half), iso(x + half, z - half),
            iso(x + half, z + half), iso(x - half, z + half)]
    roof = [iso(x - half, z - half, height), iso(x + half, z - half, height),
            iso(x + half, z + half, height), iso(x - half, z + half, height)]
    draw.polygon((base[1], base[2], roof[2], roof[1]), fill=right)
    draw.polygon((base[2], base[3], roof[3], roof[2]), fill=left)
    draw.polygon(roof, fill=top, outline="#b8d6e4")


def draw_isometric(draw, fonts):
    panel = (704, 86, 1576, 824)
    draw.rounded_rectangle(panel, radius=16, fill="#111820", outline="#3b4857", width=2)
    draw.text((724, 103), "EVA-SCALE SKYLINE / NERV SORTIE AXIS",
              font=fonts["sub"], fill="#f0a000")

    ground = [iso(-208, -208), iso(208, -208),
              iso(208, 208), iso(-208, 208)]
    draw.polygon(ground, fill="#26323d", outline="#7b8a96")
    for axis in ROAD_AXES:
        draw.line((iso(axis, -208), iso(axis, 208)), fill="#101316", width=7)
        draw.line((iso(-208, axis), iso(208, axis)), fill="#101316", width=7)
        draw.line((iso(axis, -208), iso(axis, 208)), fill="#a57b13", width=1)
        draw.line((iso(-208, axis), iso(208, axis)), fill="#a57b13", width=1)

    lots = []
    for x in LOT_CENTRES:
        for z in LOT_CENTRES:
            kind = lot_kind(x, z)
            if kind != "reserved":
                lots.append((x + z, x, z, kind))
    for x, z in outer_lots():
        lots.append((x + z, x, z, "outer"))
    for _, x, z, kind in sorted(lots):
        if kind == "tower":
            iso_box(draw, x, z, LOT_HALF, tower_height(x, z),
                    "#7597aa", "#354a59", "#486575")
        elif kind == "outer":
            iso_box(draw, x, z, OUTER_LOT_HALF, outer_tower_height(x, z),
                    "#58768a", "#283b48", "#374f60")
        elif kind == "private":
            iso_box(draw, x, z, LOT_HALF, 46,
                    "#9067a0", "#423049", "#5d4268")
        elif kind == "substation":
            iso_box(draw, x, z, LOT_HALF, 6,
                    "#b9773e", "#684228", "#875430")
        elif kind == "weapon":
            iso_box(draw, x, z, LOT_HALF, 21,
                    "#4e5863", "#151b21", "#272f38")
            door_left = iso(x - 9, z + 8, 3)
            door_right = iso(x + 9, z + 8, 17)
            draw.line((door_left, door_right), fill="#f0a000", width=4)
        else:
            iso_box(draw, x, z, LOT_HALF, 1,
                    "#802b35", "#46171c", "#5d1f27")

    iso_box(draw, 0, 4, 48, 1, "#555d66", "#292e34", "#353b42")
    for x, label, colour in UNIT_BAYS:
        iso_box(draw, x, 0, 5, 30, colour, "#281d30", "#362441")
        tx, ty = iso(x, 0, 34)
        draw.text((tx - 23, ty - 8), label, font=fonts["micro"], fill=colour)

    for x, z in PYLONS:
        bottom = iso(x, z)
        top = iso(x, z, 28)
        draw.line((bottom, top), fill="#d3dde2", width=3)
        draw.line((iso(x - 5, z, 27), iso(x + 5, z, 27)),
                  fill="#d3dde2", width=2)
    for side_x in (-180, 180):
        for wire_x in (-4, 0, 4):
            draw.line([iso(side_x + wire_x, z, 27)
                       for z in (-160, 0, 160)],
                      fill="#71838c", width=1)

    deck_base = iso(0, 216)
    deck_top = iso(0, 216, 38)
    draw.line((deck_base, deck_top), fill="#bdc9ce", width=5)
    draw.line((iso(-6, 216, 38), iso(6, 216, 38)),
              fill="#f0a000", width=4)

    draw.text((742, 774),
              "Central cages -> vertical catapults -> 20-block EVA streets -> Angel plaza",
              font=fonts["tiny"], fill="#aebcc8")


def validate_source():
    source = JAVA_BUILDER.read_text(encoding="utf-8")
    required = {
        "district_size": "DISTRICT_HALF_SIZE = 208",
        "outer_wards": "buildOuterWardTower",
        "tower_catalog": "ARMOURED_TOWERS = createArmouredTowers()",
        "tower_count": "EXPECTED_TOWERS = ARMOURED_TOWERS.size()",
        "retraction": "applyRetractionDepth",
        "road_grid": "buildRoadGrid(level, origin)",
        "foundation": "buildFoundation(level, origin)",
        "substations": "buildSubstation(level, centre)",
        "battle_plaza": "buildBattlePlaza(level, centre)",
        "power_grid": "connectPowerGrid(level, origin",
        "observation": "buildObservationDeck(level",
        "runtime_audit": "DistrictAudit inspect",
    }
    missing = [name for name, token in required.items() if token not in source]
    command_source = (ROOT / "src/main/java/com/projectseele/visual/"
                      "ThirdTokyoCommands.java").read_text(encoding="utf-8")
    for token in ('Commands.literal("tokyo3")', 'Commands.literal("setup")',
                  'Commands.literal("audit")', 'Commands.literal("overview")'):
        if token not in command_source:
            missing.append(token)
    return missing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_path = args.report or args.output.with_suffix(".json")

    image = Image.new("RGB", (1600, 860), "#0b1016")
    draw = ImageDraw.Draw(image)
    fonts = {
        "title": load_font(28), "sub": load_font(18),
        "tiny": load_font(13), "micro": load_font(10),
    }
    draw.text((26, 24), "PROJECT SEELE / THIRD NEW TOKYO CITY VISUAL CONTRACT",
              font=fonts["title"], fill="#f0a000")
    draw.text((27, 57), "Original block-built development layout - no official assets",
              font=fonts["tiny"], fill="#8998a5")
    draw_plan(draw, fonts)
    draw_isometric(draw, fonts)
    image.save(args.output)

    towers = sum(lot_kind(x, z) == "tower"
                  for x in LOT_CENTRES for z in LOT_CENTRES)
    outer_wards = sum(1 for _ in outer_lots())
    private_towers = sum(lot_kind(x, z) == "private"
                         for x in LOT_CENTRES for z in LOT_CENTRES)
    missing = validate_source()
    report = {
        "status": "PASS" if (
            not missing and towers == 64
            and outer_wards == 29 and private_towers == 5
        ) else "FAIL",
        "district_blocks": 416,
        "tower_count": towers,
        "outer_ward_count": outer_wards,
        "local_skyscraper_count": private_towers,
        "substations": 2,
        "battle_plazas": 1,
        "pylons": len(PYLONS),
        "launch_bays": 3,
        "source_contract_missing": missing,
        "image": str(args.output),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Tokyo-3 preview: {report['status']} -> {args.output}")
    if args.strict and report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
