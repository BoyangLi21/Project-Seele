#!/usr/bin/env python3
"""Render two compact, read-only S20 semantic selection boards.

This script deliberately has no APPLY mode.  It reads the disaster-free
Anvil archive and produces human-readable selection sheets for the two places
where a coordinate-driven repair failed:

* the unknown-version descending personnel route near (97,-425,201);
* the launch-control observation gallery near (52,-394,242).

An observation coordinate is never converted into an edit AABB.  Red/orange
cells on the route board are standable-air candidates only, not a block mask.
The observation board shows complete cross-section concepts; it does not
write any of them back to the save.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import corridor_semantic_packet as corridor  # noqa: E402
import survey_facility_target as survey  # noqa: E402


BG = (13, 15, 22)
GRID = (53, 58, 72)
TEXT = (232, 235, 242)
MUTED = (158, 164, 178)
CYAN = (38, 220, 226)
BLUE = (65, 132, 255)
GREEN = (68, 194, 118)
RED = (239, 77, 74)
ORANGE = (245, 156, 54)
MAGENTA = (220, 78, 188)
WHITE = (255, 255, 255)

BLOCK_COLOURS = {
    "air": BG,
    "structure": (102, 108, 122),
    "glass": (94, 190, 218),
    "stair": (126, 179, 126),
    "fixture": (235, 215, 105),
    "door": (208, 116, 191),
    "fluid": (220, 105, 30),
    "natural": (94, 75, 55),
}


def font(size: int = 18):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/consola.ttf", size)
    except OSError:
        return ImageFont.load_default()


def grid(draw: ImageDraw.ImageDraw, left: int, top: int, width: int,
         height: int, x0: int, z0: int, scale: int, step: int = 8):
    for x in range(((x0 + step - 1) // step) * step, x0 + width, step):
        px = left + (x - x0) * scale
        draw.line((px, top, px, top + height * scale), fill=GRID)
        draw.text((px + 2, top + 2), f"x{x}", fill=MUTED, font=font(13))
    for z in range(((z0 + step - 1) // step) * step, z0 + height, step):
        pz = top + (z - z0) * scale
        draw.line((left, pz, left + width * scale, pz), fill=GRID)
        draw.text((left + 2, pz + 2), f"z{z}", fill=MUTED, font=font(13))


def mark_anchor(draw: ImageDraw.ImageDraw, left: int, top: int,
                x0: int, z0: int, scale: int, x: int, z: int):
    px = left + (x - x0) * scale + scale // 2
    pz = top + (z - z0) * scale + scale // 2
    draw.ellipse((px - 8, pz - 8, px + 8, pz + 8),
                 outline=WHITE, width=2)
    draw.line((px - 12, pz, px + 12, pz), fill=WHITE, width=2)
    draw.line((px, pz - 12, px, pz + 12), fill=WHITE, width=2)


def selected_route(volume: survey.Volume, anchor: tuple[int, int, int]):
    masks = volume.masks()
    _labels, _components, _cid, route = corridor.selected_component(
        volume, masks["standable"], anchor)
    return corridor.anchor_level_sheet(route, volume, anchor)[0]


def route_candidate(point: tuple[int, int, int], volume: survey.Volume):
    ix, iy, iz = point
    x, y, z = volume.world_position(ix, iy, iz)
    if not (140 <= z <= 205 and 88 <= x <= 104):
        return None
    expected_y = -395 - ((z - 140) // 2)
    if y != expected_y:
        return None
    if z <= 186:
        return "A"
    if z <= 195:
        return "B"
    return "C"


def route_plan(volume: survey.Volume, route: np.ndarray):
    scale = 8
    left, top = 86, 68
    body_w, body_h = volume.sx * scale, volume.sz * scale
    image = Image.new("RGB", (body_w + 580, body_h + 150), BG)
    draw = ImageDraw.Draw(image)
    grid(draw, left, top, volume.sx, volume.sz,
         volume.x0, volume.z0, scale)

    # Green is the surrounding walkable network.  Candidate colours replace
    # only the descending height field; they are not a shell or deletion mask.
    for raw in np.argwhere(route):
        point = tuple(int(value) for value in raw)
        x, _y, z = volume.world_position(*point)
        tag = route_candidate(point, volume)
        colour = {"A": RED, "B": ORANGE, "C": MAGENTA}.get(tag, GREEN)
        px = left + (x - volume.x0) * scale
        pz = top + (z - volume.z0) * scale
        draw.rectangle((px, pz, px + scale - 1, pz + scale - 1),
                       fill=colour)

    # Source geometry is a protection/provenance overlay only.
    def rect(x0, z0, x1, z1, colour, label):
        box = (left + (x0 - volume.x0) * scale,
               top + (z0 - volume.z0) * scale,
               left + (x1 - volume.x0 + 1) * scale - 1,
               top + (z1 - volume.z0 + 1) * scale - 1)
        draw.rectangle(box, outline=colour, width=3)
        draw.text((box[0] + 4, box[1] + 4), label,
                  fill=colour, font=font(14))

    rect(55, 203, 89, 237, BLUE, "PROTECT: UNIT-02 WELL SHELL")
    rect(-36, 238, 96, 244, CYAN, "SOURCE OVERLAY: LAUNCH CONTROL SPINE")

    for z, label in ((139, "CUT? upper interface"),
                     (186, "A/B boundary"),
                     (195, "B/C boundary"),
                     (206, "CUT? lower interface")):
        if volume.z0 <= z <= volume.z1:
            py = top + (z - volume.z0) * scale
            draw.line((left, py, left + body_w, py), fill=WHITE, width=2)
            draw.text((left + body_w + 12, py - 9), f"z={z} {label}",
                      fill=WHITE, font=font(14))

    mark_anchor(draw, left, top, volume.x0, volume.z0, scale, 97, 201)
    draw.text((left, 18),
              "S20-R02  UNKNOWN-VERSION DESCENDING ROUTE / SELECTION BOARD",
              fill=(255, 214, 84), font=font(22))
    lx = left + body_w + 26
    legend = [
        (RED, "A  stable 7-wide descending ramp  z140..186"),
        (ORANGE, "B  broken dogleg / shared junction  z187..195"),
        (MAGENTA, "C  lower tail fragments  z196..205"),
        (GREEN, "surrounding walkable network: RETAIN / UNKNOWN"),
        (BLUE, "Unit-02 launch-well protection outline"),
        (CYAN, "current builder geometry: source overlay only"),
        (WHITE, "human cut-plane candidate / observation anchor"),
    ]
    draw.text((lx, 82), "LEGEND", fill=TEXT, font=font(18))
    for index, (colour, label) in enumerate(legend):
        y = 118 + index * 38
        draw.rectangle((lx, y, lx + 22, y + 22), fill=colour)
        draw.text((lx + 34, y + 1), label, fill=TEXT, font=font(15))
    notes = [
        "Observation coordinate is not an edit target.",
        "Red/orange/magenta show WALKABLE AIR only.",
        "No floor/wall/window/ceiling block is selected yet.",
        "B and C intersect shared topology: automatic deletion forbidden.",
        "Human must approve route segments + two cut planes + shared walls.",
    ]
    for index, line in enumerate(notes):
        draw.text((lx, 410 + index * 31), line,
                  fill=MUTED if index else TEXT, font=font(14))
    draw.text((left, image.height - 40),
              "READ-ONLY / EDITABLE MASK EMPTY / BASE = 2026-08-01 15:07",
              fill=(255, 120, 120), font=font(17))
    return image


def route_profile(volume: survey.Volume, route: np.ndarray):
    scale_z, scale_y = 8, 10
    z0, z1 = 132, 210
    y0, y1 = -432, -388
    left, top = 88, 58
    image = Image.new("RGB",
                      ((z1 - z0 + 1) * scale_z + 500,
                       (y1 - y0 + 1) * scale_y + 130), BG)
    draw = ImageDraw.Draw(image)
    for z in range(136, z1 + 1, 8):
        px = left + (z - z0) * scale_z
        draw.line((px, top, px, top + (y1 - y0 + 1) * scale_y), fill=GRID)
        draw.text((px + 2, top + 2), f"z{z}", fill=MUTED, font=font(13))
    for y in range(-432, -387, 4):
        py = top + (y1 - y) * scale_y
        draw.line((left, py, left + (z1 - z0 + 1) * scale_z, py), fill=GRID)
        draw.text((6, py - 7), f"y{y}", fill=MUTED, font=font(13))

    seen = set()
    for raw in np.argwhere(route):
        point = tuple(int(value) for value in raw)
        x, y, z = volume.world_position(*point)
        if not (z0 <= z <= z1 and y0 <= y <= y1):
            continue
        tag = route_candidate(point, volume)
        key = (z, y, tag)
        if key in seen:
            continue
        seen.add(key)
        colour = {"A": RED, "B": ORANGE, "C": MAGENTA}.get(tag, GREEN)
        px = left + (z - z0) * scale_z
        py = top + (y1 - y) * scale_y
        radius = 4 if tag else 2
        draw.ellipse((px - radius, py - radius, px + radius, py + radius),
                     fill=colour)
    draw.text((left, 14),
              "LONGITUDINAL ELEVATION: the red path descends 1 block / 2 Z",
              fill=(255, 214, 84), font=font(20))
    tx = left + (z1 - z0 + 1) * scale_z + 24
    draw.text((tx, 80), "WHY THE OLD AABB FAILED", fill=TEXT, font=font(18))
    explanation = [
        "The unwanted ramp shares one walkable component",
        "with green upper routes and junctions.",
        "A solid flood-fill reaches legal walls.",
        "A rectangular clear leaves the bent tail behind.",
        "Only a human-approved path + cut planes can",
        "define the future shell extraction.",
    ]
    for index, line in enumerate(explanation):
        draw.text((tx, 122 + index * 30), line, fill=MUTED, font=font(14))
    draw.text((left, image.height - 38),
              "PROFILE IS EVIDENCE, NOT AN APPLY PATCH", fill=(255, 120, 120),
              font=font(17))
    return image


def route_cross_section_panel(volume: survey.Volume, route: np.ndarray,
                              z: int, tag: str, scale: int = 10):
    """Render an actual X/Y block cut with standable-air overlays."""
    x0, x1 = 80, 116
    y0, y1 = -434, -388
    left, top = 64, 48
    width = (x1 - x0 + 1) * scale
    height = (y1 - y0 + 1) * scale
    image = Image.new("RGB", (width + 90, height + 92), BG)
    draw = ImageDraw.Draw(image)
    iz = z - volume.z0
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            state = volume.state(x - volume.x0, y - volume.y0, iz)
            role = survey.role_of(state)
            colour = BLOCK_COLOURS.get(role, BLOCK_COLOURS["structure"])
            px = left + (x - x0) * scale
            py = top + (y1 - y) * scale
            draw.rectangle((px, py, px + scale - 1, py + scale - 1),
                           fill=colour)
            if route[x - volume.x0, y - volume.y0, iz]:
                candidate = route_candidate(
                    (x - volume.x0, y - volume.y0, iz), volume)
                outline = {"A": RED, "B": ORANGE, "C": MAGENTA}.get(
                    candidate, GREEN)
                draw.rectangle((px + 1, py + 1,
                                px + scale - 2, py + scale - 2),
                               outline=outline, width=2)
    for x in range(80, 117, 8):
        px = left + (x - x0) * scale
        draw.line((px, top, px, top + height), fill=GRID)
        draw.text((px + 2, top + 2), f"x{x}", fill=MUTED, font=font(11))
    for y in range(-432, -387, 8):
        py = top + (y1 - y) * scale
        draw.line((left, py, left + width, py), fill=GRID)
        draw.text((4, py - 6), f"y{y}", fill=MUTED, font=font(11))
    draw.text((left, 10), f"{tag} / REAL BLOCK CUT z={z}",
              fill=(255, 214, 84), font=font(16))
    draw.text((left, image.height - 29),
              "outline = standable air; filled cells = real saved blocks",
              fill=TEXT, font=font(12))
    return image


def route_section_sheet(volume: survey.Volume, route: np.ndarray):
    sections = [
        ("A START", 140), ("A MID", 163), ("A END", 186),
        ("B START", 187), ("B MID", 191), ("B END", 195),
        ("C START", 196), ("C MID", 201), ("C END", 205),
    ]
    panels = [route_cross_section_panel(volume, route, z, label)
              for label, z in sections]
    cell_w = max(panel.width for panel in panels)
    cell_h = max(panel.height for panel in panels)
    image = Image.new("RGB", (cell_w * 3, cell_h * 3 + 94), BG)
    for index, panel in enumerate(panels):
        image.paste(panel, ((index % 3) * cell_w,
                            78 + (index // 3) * cell_h))
    draw = ImageDraw.Draw(image)
    draw.text((28, 18),
              "S20-R02  START / MID / END CROSS-SECTIONS FOR EACH SEMANTIC SEGMENT",
              fill=(255, 214, 84), font=font(22))
    draw.text((28, 50),
              "A is stable; B/C visibly mix with neighbouring structures. No shell extraction yet.",
              fill=TEXT, font=font(15))
    return image


def route_iso_xray(volume: survey.Volume, route: np.ndarray):
    """Put the selected walkable-air candidates over the real saved shell.

    The overlay is intentionally x-ray: it is drawn after the saved blocks so
    that a route hidden by a wall remains visible.  It is evidence about the
    air path only and must never be interpreted as an editable solid mask.
    """
    masks = volume.masks()
    panels = []
    for sign_x, sign_z, title in (
            (1, 1, "SAVED VOXELS +X/+Z / WALK-AIR X-RAY"),
            (-1, -1, "SAVED VOXELS -X/-Z / WALK-AIR X-RAY")):
        panel = survey.iso_projection(
            volume, masks, (97, -425, 201), sign_x, sign_z, title)
        draw = ImageDraw.Draw(panel)
        sx, sy, sz = volume.sx, volume.sy, volume.sz
        tile_w, tile_h, vertical = 8, 4, 4
        origin_x = panel.width // 2
        origin_y = 30 + sy * vertical

        def project(px: float, py: float, pz: float):
            tx = px if sign_x > 0 else sx - px
            tz = pz if sign_z > 0 else sz - pz
            return (int(origin_x + (tx - tz) * tile_w / 2),
                    int(origin_y + (tx + tz) * tile_h / 2 - py * vertical))

        for raw in np.argwhere(route):
            point = tuple(int(value) for value in raw)
            tag = route_candidate(point, volume)
            if tag is None:
                continue
            x, y, z = point
            px, py = project(x + 0.5, y + 0.15, z + 0.5)
            colour = {"A": RED, "B": ORANGE, "C": MAGENTA}[tag]
            draw.ellipse((px - 3, py - 3, px + 3, py + 3),
                         fill=colour, outline=WHITE)
        draw.text((12, 48),
                  "X-RAY DOTS = WALKABLE AIR; NOT FLOOR/WALL DELETE MASK",
                  fill=(255, 120, 120), font=font(13))
        panels.append(panel)
    result = Image.new("RGB", (sum(p.width for p in panels),
                               max(p.height for p in panels)), BG)
    x = 0
    for panel in panels:
        result.paste(panel, (x, 0))
        x += panel.width
    return result


def state_role_name(state: str):
    return survey.role_of(state)


def cross_section(volume: survey.Volume, x: int):
    ix = x - volume.x0
    result = {}
    for y in range(volume.y0, volume.y1 + 1):
        for z in range(volume.z0, volume.z1 + 1):
            state = volume.state(ix, y - volume.y0, z - volume.z0)
            if state_role_name(state) != "air":
                result[(y, z)] = state
    return result


def variant_sections(base: dict[tuple[int, int], str]):
    variants = {"BASE": dict(base)}

    # A: increase clear height upward by two blocks.  Floor/support stay put;
    # the complete ceiling and both side boundaries move/extend together.
    a = dict(base)
    for z in range(238, 245):
        a.pop((-390, z), None)
        a[(-388, z)] = "minecraft:deepslate_tiles"
    for y in (-390, -389):
        a[(y, 238)] = "minecraft:polished_blackstone_bricks"
        a[(y, 244)] = "minecraft:polished_blackstone_bricks"
    variants["A  RAISE CEILING +2"] = a

    # B1: increase clear height downward by one block.  Ceiling and the top of
    # the existing window band stay; floor/support descend together and both
    # boundaries extend down.  This is the complete-section counterpart to
    # the rejected floor-only edit seen in the human screenshot.
    b = dict(base)
    for z in range(239, 244):
        b.pop((-395, z), None)
    for z in range(238, 245):
        b[(-396, z)] = "minecraft:polished_deepslate"
        b[(-397, z)] = "minecraft:reinforced_deepslate"
    b[(-395, 238)] = "minecraft:light_gray_stained_glass"
    b[(-395, 244)] = "minecraft:polished_blackstone_bricks"
    variants["B1 LOWER FLOOR -1 + EXTEND WALL/WINDOW"] = b

    # C: translate the complete authored cross-section down two blocks.  This
    # preserves its proportions but does not create more internal headroom.
    c = dict(base)
    moving = {(y, z): state for (y, z), state in base.items()
              if 238 <= z <= 244 and -396 <= y <= -390}
    for key in moving:
        c.pop(key, None)
    for (y, z), state in moving.items():
        c[(y - 2, z)] = state
    variants["C  MOVE WHOLE SECTION -2"] = c
    return variants


def section_panel(name: str, states: dict[tuple[int, int], str],
                  base: dict[tuple[int, int], str]):
    z0, z1, y0, y1 = 234, 248, -401, -384
    scale = 28
    left, top = 66, 58
    image = Image.new("RGB", ((z1 - z0 + 1) * scale + 74,
                              (y1 - y0 + 1) * scale + 120), BG)
    draw = ImageDraw.Draw(image)
    for z in range(z0, z1 + 1):
        for y in range(y0, y1 + 1):
            state = states.get((y, z), "minecraft:air")
            role = state_role_name(state)
            colour = BLOCK_COLOURS.get(role, BLOCK_COLOURS["structure"])
            x0 = left + (z - z0) * scale
            yy = top + (y1 - y) * scale
            draw.rectangle((x0, yy, x0 + scale - 1, yy + scale - 1),
                           fill=colour, outline=(28, 31, 40))
            before = base.get((y, z), "minecraft:air")
            if before != state:
                if state_role_name(state) == "air":
                    draw.line((x0 + 3, yy + 3,
                               x0 + scale - 4, yy + scale - 4),
                              fill=RED, width=3)
                    draw.line((x0 + scale - 4, yy + 3,
                               x0 + 3, yy + scale - 4),
                              fill=RED, width=3)
                else:
                    draw.rectangle((x0 + 2, yy + 2,
                                    x0 + scale - 3, yy + scale - 3),
                                   outline=GREEN, width=3)
    for z in range(z0, z1 + 1, 2):
        px = left + (z - z0) * scale
        draw.text((px, top - 22), str(z), fill=MUTED, font=font(12))
    for y in range(y0, y1 + 1, 2):
        py = top + (y1 - y) * scale
        draw.text((5, py + 4), str(y), fill=MUTED, font=font(12))
    draw.text((left, 12), name, fill=(255, 214, 84), font=font(18))
    draw.text((left, image.height - 45),
              "GREEN BORDER=ADD/MOVE  RED X=REMOVE  (concept only)",
              fill=TEXT, font=font(13))
    return image


def observation_board(volume: survey.Volume):
    # x=72 crosses a real Unit-02 light-gray observation window instead of a
    # solid mullion, so all floor/window/wall/ceiling roles are visible.
    base = cross_section(volume, 72)
    variants = variant_sections(base)
    panels = [section_panel(name, states, base)
              for name, states in variants.items()]
    cell_w = max(panel.width for panel in panels)
    cell_h = max(panel.height for panel in panels)
    image = Image.new("RGB", (cell_w * 2, cell_h * 2 + 130), BG)
    for index, panel in enumerate(panels):
        image.paste(panel, ((index % 2) * cell_w,
                            100 + (index // 2) * cell_h))
    draw = ImageDraw.Draw(image)
    draw.text((30, 18),
              "S20-R05  OBSERVATION GALLERY / THREE COMPLETE SECTION OPTIONS",
              fill=(255, 214, 84), font=font(23))
    draw.text((30, 55),
              "Representative X=72 (real window bay). Nothing is selected or written.",
              fill=TEXT, font=font(16))
    draw.text((30, image.height - 28),
              "A adds height upward; B1 adds 1 downward with full sides/support; C translates. Human choice required.",
              fill=(255, 120, 120), font=font(16))
    return image, variants


def sha_packet(directory: Path):
    rows = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name != "packet.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    payload = "\n".join(rows) + "\n"
    (directory / "packet.sha256").write_text(payload, encoding="ascii")
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def write_readme(output: Path):
    text = """# S20 地图语义选择板（只读）

本目录只读取 2026-08-01 15:07 的灾难前归档并生成图片；世界零写入，editable mask 为空。

## 01_wrong_route_selection.png

- 红 A：规则七格宽下降坡，z=140..186。
- 橙 B：折向并与邻近结构共用拓扑的汇合区，z=187..195。
- 紫 C：断续尾段，z=196..205，靠近二号机发射井保护轮廓。
- 绿色：同一可行走网络中的其他区域，默认保留。
- 白线只是候选切面；未获人工选择时不构成批准边界。

## 02_wrong_route_profile.png

纵剖面显示 A 每前进两格 Z 下降一格。它证明旧矩形清除为何既破坏合法结构又留下尾段。

## 03_wrong_route_cross_sections.png

逐一显示 A/B/C 起点、中点、终点的真实 X/Y 方块截面。A 截面稳定；B/C 已混入竖井、平台或共享墙，不能自动抽取壳体。

## 04_wrong_route_iso_xray.png

两个相反方向的真实存档等距视图。彩色点是可行走空气的 X-ray 标记，不是待删方块。

## 05_observation_section_options.png

代表截面取自 x=72 的真实窗格：A 抬高完整顶棚；B 降低地板/承重层并向下延伸窗墙；C 将完整截面整体下移。三者都只是语义概念，尚未生成逐块补丁。
"""
    (output / "README_CN.md").write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", default=(
        "_archive/SEELE_S20_REBUILD-post-handoff-reconcile-20260801-150700"))
    parser.add_argument("--emit", default=(
        "artifacts/map_semantics/S20-R02-R05-SELECTION-BOARDS-r02"))
    args = parser.parse_args()

    dimension = "dimensions/projectseele/geofront"
    world = ROOT / "run" / "saves" / args.world / dimension
    output = ROOT / args.emit
    output.mkdir(parents=True, exist_ok=True)

    route_volume = survey.Volume(world, (48, 124, -435, -388, 125, 246))
    route = selected_route(route_volume, (97, -425, 201))
    route_plan(route_volume, route).save(output / "01_wrong_route_selection.png")
    route_profile(route_volume, route).save(output / "02_wrong_route_profile.png")
    route_section_sheet(route_volume, route).save(
        output / "03_wrong_route_cross_sections.png")
    route_iso_xray(route_volume, route).save(
        output / "04_wrong_route_iso_xray.png")

    observation_volume = survey.Volume(
        world, (70, 74, -401, -384, 234, 248))
    obs_image, variants = observation_board(observation_volume)
    obs_image.save(output / "05_observation_section_options.png")

    manifest = {
        "mode": "READ_ONLY_HUMAN_SEMANTIC_SELECTION",
        "world_files_written": False,
        "editable_mask": [],
        "source_save": args.world,
        "source_dimension": dimension,
        "route_observation_anchor": [97, -425, 201],
        "route_candidates": {
            "A": {"z": [140, 186], "meaning": "stable descending ramp"},
            "B": {"z": [187, 195], "meaning": "broken dogleg/shared junction"},
            "C": {"z": [196, 205], "meaning": "lower tail fragments"},
        },
        "route_candidate_is_block_mask": False,
        "route_saved_geometry_provenance": "ORPHAN_GEOMETRY",
        "route_source_overlays_are_edit_authority": False,
        "observation_anchor": [52, -394, 242],
        "observation_representative_window_section_x": 72,
        "observation_options": list(variants),
        "automatic_decision": "STOP",
        "fail_closed_conditions": [
            "selected route remains connected to the survey boundary",
            "a cut plane enters a branch, shared wall or protected structure",
            "either interface lacks three stable complete cross-sections",
            "a future shell voxel cannot be proven exclusive to the selected path",
            "builder overlays conflict with each other or with saved voxels",
        ],
        "approval_needed": [
            "route segment IDs A/B/C",
            "upper and lower cut planes",
            "shared-wall protection at both interfaces",
            "observation option A/B/C or a corrected fourth semantic",
        ],
        "region_file_hashes": route_volume.region_hashes(),
    }
    (output / "00_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    write_readme(output)
    digest = sha_packet(output)
    print(f"[selection] read-only packet={output} sha256={digest}")


if __name__ == "__main__":
    main()
