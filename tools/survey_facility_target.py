#!/usr/bin/env python3
"""Build a read-only spatial evidence packet around one GeoFront observation.

An F3 coordinate is treated only as an observation anchor.  This tool never
creates an edit mask and never writes the Minecraft world.  It reads Anvil
chunks, renders the same voxel volume from several directions, labels authored
solid and walkable-air components, and records enough hashes to make a later
preview reproducible.

Example:

    python tools/survey_facility_target.py \
        --world SEELE_S20_REBUILD \
        --anchor 52 -394 242 \
        --repair-id S20-R05-GF-OBSERVATION-GALLERY-r01 \
        --screenshot C:/path/to/report.png
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter, deque
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inspect_map_assets import (  # noqa: E402
    decode_modern_section,
    iter_chunks,
    palette_name,
    palette_state,
    state_colour,
)


AIR_NAMES = {
    "minecraft:air", "minecraft:cave_air", "minecraft:void_air",
    "minecraft:light",
}
NATURAL_NAMES = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:tuff",
    "minecraft:dirt", "minecraft:grass_block", "minecraft:coarse_dirt",
    "minecraft:podzol", "minecraft:rooted_dirt", "minecraft:gravel",
    "minecraft:sand", "minecraft:red_sand", "minecraft:sandstone",
    "minecraft:clay", "minecraft:mud", "minecraft:bedrock",
    "minecraft:snow", "minecraft:snow_block", "minecraft:ice",
    "minecraft:packed_ice", "minecraft:blue_ice", "minecraft:andesite",
    "minecraft:diorite", "minecraft:granite", "minecraft:calcite",
}
NATURAL_SUBSTRINGS = (
    "_ore", "_leaves", "_log", "_wood", "mushroom", "azalea",
    "sculk", "dripstone",
)
PASSABLE_SUBSTRINGS = (
    "torch", "button", "lever", "sign", "banner", "rail", "tripwire",
    "flower", "sapling", "short_grass", "fern", "lantern", "carpet",
    "pressure_plate", "candle", "cobweb", "ladder", "scaffolding",
)
FLUID_SUBSTRINGS = ("water", "lava", "lcl")


def base_name(state: str) -> str:
    return state.split("[", 1)[0]


def role_of(state: str) -> str:
    name = base_name(state)
    low = name.lower()
    if name in AIR_NAMES:
        return "air"
    # A sea lantern is a full collision cube.  Matching the generic
    # "lantern" substring made embedded floor/ceiling lights look passable
    # and created phantom walk levels in semantic surveys.
    if name == "minecraft:sea_lantern":
        return "structure"
    if any(text in low for text in FLUID_SUBSTRINGS):
        return "fluid"
    if name in NATURAL_NAMES or any(text in low
                                    for text in NATURAL_SUBSTRINGS):
        return "natural"
    if "glass" in low:
        return "glass"
    if "stairs" in low or "slab" in low:
        return "stair"
    if "door" in low and "trapdoor" not in low:
        return "door"
    if any(text in low for text in PASSABLE_SUBSTRINGS):
        return "fixture"
    return "structure"


def passable(state: str) -> bool:
    role = role_of(state)
    return role in {"air", "fixture", "door"}


def shade(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(value * factor))) for value in rgb)


def component_colour(component_id: int) -> tuple[int, int, int]:
    if component_id < 0:
        return 18, 18, 24
    # A stable, high-contrast colour wheel without external plotting packages.
    angle = (component_id * 0.618033988749895) % 1.0
    segment = int(angle * 6)
    fraction = angle * 6 - segment
    p, q = 48, int(230 - 182 * fraction)
    t = int(48 + 182 * fraction)
    table = ((230, t, p), (q, 230, p), (p, 230, t),
             (p, q, 230), (t, p, 230), (230, p, q))
    return table[segment % 6]


class Volume:
    def __init__(self, world: Path, box: tuple[int, int, int, int, int, int]):
        self.world = world
        self.x0, self.x1, self.y0, self.y1, self.z0, self.z1 = box
        self.sx = self.x1 - self.x0 + 1
        self.sy = self.y1 - self.y0 + 1
        self.sz = self.z1 - self.z0 + 1
        self.states = ["minecraft:air"]
        self.state_ids = {self.states[0]: 0}
        self.code = np.zeros((self.sx, self.sy, self.sz), dtype=np.uint16)
        self.block_entities: dict[tuple[int, int, int], str] = {}
        self.loaded_chunks: set[tuple[int, int]] = set()
        self._load()

    def _state_id(self, state: str) -> int:
        found = self.state_ids.get(state)
        if found is not None:
            return found
        found = len(self.states)
        if found >= np.iinfo(np.uint16).max:
            raise RuntimeError("too many block states in survey volume")
        self.state_ids[state] = found
        self.states.append(state)
        return found

    def _load(self) -> None:
        bounds = (self.x0 // 16, self.x1 // 16,
                  self.z0 // 16, self.z1 // 16)
        linear = np.arange(4096)
        ox, oz, oy = linear & 15, (linear >> 4) & 15, linear >> 8
        for chunk_x, chunk_z, root in iter_chunks(self.world, bounds):
            self.loaded_chunks.add((chunk_x, chunk_z))
            base_x, base_z = chunk_x * 16, chunk_z * 16
            data = root.get("Level", root)
            for section in data.get("Sections", data.get("sections", [])):
                section_y = int(section["Y"]) * 16
                if section_y > self.y1 or section_y + 15 < self.y0:
                    continue
                palette, indices = decode_modern_section(section)
                if not palette:
                    continue
                palette_codes = np.asarray(
                    [self._state_id(palette_state(entry)) for entry in palette],
                    dtype=np.uint16)
                values = palette_codes[np.asarray(indices, dtype=np.int32)]
                xs, ys, zs = base_x + ox, section_y + oy, base_z + oz
                keep = ((xs >= self.x0) & (xs <= self.x1)
                        & (ys >= self.y0) & (ys <= self.y1)
                        & (zs >= self.z0) & (zs <= self.z1))
                if not keep.any():
                    continue
                self.code[xs[keep] - self.x0,
                          ys[keep] - self.y0,
                          zs[keep] - self.z0] = values[keep]
            entities = data.get("block_entities", data.get("TileEntities", []))
            for entry in entities:
                try:
                    x = int(entry.get("x", entry.get("X")))
                    y = int(entry.get("y", entry.get("Y")))
                    z = int(entry.get("z", entry.get("Z")))
                except (TypeError, ValueError):
                    continue
                if (self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1
                        and self.z0 <= z <= self.z1):
                    self.block_entities[(x, y, z)] = str(entry.get("id", "?"))

    def state(self, ix: int, iy: int, iz: int) -> str:
        return self.states[int(self.code[ix, iy, iz])]

    def world_position(self, ix: int, iy: int, iz: int) -> tuple[int, int, int]:
        return (int(self.x0 + ix), int(self.y0 + iy),
                int(self.z0 + iz))

    def masks(self) -> dict[str, np.ndarray]:
        roles = np.asarray([role_of(state) for state in self.states], dtype=object)
        role_grid = roles[self.code]
        is_passable = np.isin(role_grid, ["air", "fixture", "door"])
        is_fluid = role_grid == "fluid"
        is_natural = role_grid == "natural"
        is_solid = ~(is_passable | is_fluid)
        is_authored = is_solid & ~is_natural
        standable = np.zeros_like(is_solid)
        standable[:, 1:-1, :] = (
            is_solid[:, :-2, :]
            & is_passable[:, 1:-1, :]
            & is_passable[:, 2:, :]
        )
        return {
            "passable": is_passable,
            "fluid": is_fluid,
            "natural": is_natural,
            "solid": is_solid,
            "authored": is_authored,
            "standable": standable,
        }

    def region_hashes(self) -> dict[str, str]:
        paths = set()
        for chunk_x, chunk_z in self.loaded_chunks:
            paths.add(self.world / "region"
                      / f"r.{chunk_x // 32}.{chunk_z // 32}.mca")
        out = {}
        for path in sorted(paths):
            if path.is_file():
                out[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return out

    def chunk_hashes(self) -> dict[str, str]:
        out = {}
        for chunk_x, chunk_z in sorted(self.loaded_chunks):
            h = hashlib.sha256()
            xa = max(self.x0, chunk_x * 16)
            xb = min(self.x1, chunk_x * 16 + 15)
            za = max(self.z0, chunk_z * 16)
            zb = min(self.z1, chunk_z * 16 + 15)
            for y in range(self.y0, self.y1 + 1):
                for z in range(za, zb + 1):
                    for x in range(xa, xb + 1):
                        state = self.state(x - self.x0, y - self.y0,
                                           z - self.z0)
                        h.update(state.encode("utf-8"))
                        h.update(b"\0")
            out[f"{chunk_x},{chunk_z}"] = h.hexdigest()
        return out


def label_components(mask: np.ndarray, volume: Volume,
                     walkable: bool = False) -> tuple[np.ndarray, list[dict]]:
    labels = np.full(mask.shape, -1, dtype=np.int32)
    components: list[dict] = []
    sx, sy, sz = mask.shape
    for start in zip(*np.nonzero(mask)):
        if labels[start] >= 0:
            continue
        component_id = len(components)
        labels[start] = component_id
        queue = deque([start])
        count = 0
        mins = [sx, sy, sz]
        maxs = [-1, -1, -1]
        states = Counter()
        touches = False
        while queue:
            x, y, z = queue.popleft()
            count += 1
            mins[0], mins[1], mins[2] = min(mins[0], x), min(mins[1], y), min(mins[2], z)
            maxs[0], maxs[1], maxs[2] = max(maxs[0], x), max(maxs[1], y), max(maxs[2], z)
            touches |= x in (0, sx - 1) or y in (0, sy - 1) or z in (0, sz - 1)
            if not walkable:
                states[volume.state(x, y, z)] += 1
            if walkable:
                neighbours = []
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, nz = x + dx, z + dz
                    if not (0 <= nx < sx and 0 <= nz < sz):
                        continue
                    for dy in (0, 1, -1):
                        ny = y + dy
                        if 0 <= ny < sy and mask[nx, ny, nz]:
                            neighbours.append((nx, ny, nz))
                            break
            else:
                neighbours = ((x + 1, y, z), (x - 1, y, z),
                              (x, y + 1, z), (x, y - 1, z),
                              (x, y, z + 1), (x, y, z - 1))
            for nx, ny, nz in neighbours:
                if not (0 <= nx < sx and 0 <= ny < sy and 0 <= nz < sz):
                    continue
                if mask[nx, ny, nz] and labels[nx, ny, nz] < 0:
                    labels[nx, ny, nz] = component_id
                    queue.append((nx, ny, nz))
        wx0, wy0, wz0 = volume.world_position(*mins)
        wx1, wy1, wz1 = volume.world_position(*maxs)
        entry = {
            "id": component_id,
            "cells": count,
            "bbox": [wx0, wx1, wy0, wy1, wz0, wz1],
            "touches_survey_boundary": bool(touches),
        }
        if states:
            entry["materials"] = dict(states.most_common(12))
        components.append(entry)
    return labels, components


def colour_table(volume: Volume) -> np.ndarray:
    result = np.zeros((len(volume.states), 3), dtype=np.uint8)
    for index, state in enumerate(volume.states):
        if role_of(state) == "air":
            result[index] = (12, 12, 18)
        else:
            result[index] = state_colour(state)
    return result


def add_grid(draw: ImageDraw.ImageDraw, left: int, top: int,
             width: int, depth: int, scale: int,
             x0: int, z0: int, step: int = 8) -> None:
    for x in range(math.ceil(x0 / step) * step, x0 + width, step):
        px = left + (x - x0) * scale
        draw.line((px, top, px, top + depth * scale), fill=(65, 65, 78))
        draw.text((px + 2, top + 2), f"x{x}", fill=(200, 200, 208))
    for z in range(math.ceil(z0 / step) * step, z0 + depth, step):
        pz = top + (z - z0) * scale
        draw.line((left, pz, left + width * scale, pz), fill=(65, 65, 78))
        draw.text((left + 2, pz + 2), f"z{z}", fill=(200, 200, 208))


def plan_image(volume: Volume, y: int, colours: np.ndarray,
               anchor: tuple[int, int, int], scale: int = 4,
               labels: np.ndarray | None = None,
               title: str | None = None) -> Image.Image:
    iy = y - volume.y0
    if not 0 <= iy < volume.sy:
        raise ValueError(f"plan y={y} outside survey")
    if labels is None:
        rgb = colours[volume.code[:, iy, :]].transpose(1, 0, 2)
    else:
        layer = labels[:, iy, :].transpose(1, 0)
        rgb = np.zeros((volume.sz, volume.sx, 3), dtype=np.uint8)
        rgb[:] = (12, 12, 18)
        for component_id in np.unique(layer):
            if component_id >= 0:
                rgb[layer == component_id] = component_colour(int(component_id))
    body = Image.fromarray(rgb, "RGB").resize(
        (volume.sx * scale, volume.sz * scale), Image.Resampling.NEAREST)
    image = Image.new("RGB", (body.width + 100, body.height + 52),
                      (18, 18, 24))
    image.paste(body, (80, 28))
    draw = ImageDraw.Draw(image)
    add_grid(draw, 80, 28, volume.sx, volume.sz, scale,
             volume.x0, volume.z0)
    ax, ay, az = anchor
    px = 80 + (ax - volume.x0) * scale + scale // 2
    pz = 28 + (az - volume.z0) * scale + scale // 2
    draw.ellipse((px - 7, pz - 7, px + 7, pz + 7), outline=(255, 255, 255), width=2)
    draw.line((px - 10, pz, px + 10, pz), fill=(255, 70, 70), width=2)
    draw.line((px, pz - 10, px, pz + 10), fill=(255, 70, 70), width=2)
    draw.text((80, 5), title or f"EXACT BLOCK LAYER y={y}",
              fill=(255, 214, 84))
    draw.text((5, image.height - 18),
              f"OBSERVATION ANCHOR=({ax},{ay},{az}); EDITABLE MASK=EMPTY",
              fill=(235, 235, 240))
    return image


def first_surface_codes(code: np.ndarray, mask: np.ndarray,
                        axis: int, reverse: bool) -> np.ndarray:
    work_mask = np.flip(mask, axis=axis) if reverse else mask
    work_code = np.flip(code, axis=axis) if reverse else code
    present = work_mask.any(axis=axis)
    first = work_mask.argmax(axis=axis)
    picked = np.take_along_axis(work_code, np.expand_dims(first, axis=axis),
                                axis=axis).squeeze(axis=axis)
    picked[~present] = 0
    return picked


def matrix_panel(matrix: np.ndarray, colours: np.ndarray, title: str,
                 horizontal: str, h0: int, v0: int,
                 scale: int = 4) -> Image.Image:
    # matrix is horizontal x vertical; screen y runs opposite world y.
    rgb = colours[matrix].transpose(1, 0, 2)[::-1, :, :]
    body = Image.fromarray(rgb, "RGB").resize(
        (rgb.shape[1] * scale, rgb.shape[0] * scale),
        Image.Resampling.NEAREST)
    image = Image.new("RGB", (body.width + 74, body.height + 38),
                      (18, 18, 24))
    image.paste(body, (60, 22))
    draw = ImageDraw.Draw(image)
    draw.text((60, 3), title, fill=(255, 214, 84))
    draw.text((3, 22), f"y{v0 + matrix.shape[1] - 1}", fill=(205, 205, 215))
    draw.text((3, body.height + 8), f"y{v0}", fill=(205, 205, 215))
    draw.text((60, body.height + 24), f"{horizontal}{h0}", fill=(205, 205, 215))
    draw.text((body.width + 22, body.height + 24),
              f"{horizontal}{h0 + matrix.shape[0] - 1}",
              fill=(205, 205, 215))
    return image


def combine_panels(panels: list[Image.Image], columns: int,
                   output: Path) -> None:
    rows = math.ceil(len(panels) / columns)
    cell_w = max(panel.width for panel in panels)
    cell_h = max(panel.height for panel in panels)
    result = Image.new("RGB", (cell_w * columns, cell_h * rows),
                       (10, 10, 14))
    for index, panel in enumerate(panels):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h
        result.paste(panel, (x, y))
    result.save(output)


def orthographic_packet(volume: Volume, masks: dict[str, np.ndarray],
                        colours: np.ndarray, anchor: tuple[int, int, int],
                        output: Path) -> None:
    render_mask = masks["authored"] | masks["fluid"]
    north = first_surface_codes(volume.code, render_mask, 2, False)
    south = first_surface_codes(volume.code, render_mask, 2, True)
    west = first_surface_codes(volume.code, render_mask, 0, False)
    east = first_surface_codes(volume.code, render_mask, 0, True)
    ax = anchor[0] - volume.x0
    az = anchor[2] - volume.z0
    xlo, xhi = max(0, ax - 2), min(volume.sx, ax + 3)
    zlo, zhi = max(0, az - 2), min(volume.sz, az + 3)
    x_section = first_surface_codes(
        volume.code[xlo:xhi, :, :], render_mask[xlo:xhi, :, :], 0, False)
    z_section = first_surface_codes(
        volume.code[:, :, zlo:zhi], render_mask[:, :, zlo:zhi], 2, False)
    panels = [
        matrix_panel(north, colours, "NORTH ELEVATION (look +Z)", "x",
                     volume.x0, volume.y0, 3),
        matrix_panel(south, colours, "SOUTH ELEVATION (look -Z)", "x",
                     volume.x0, volume.y0, 3),
        matrix_panel(west.transpose(1, 0), colours,
                     "WEST ELEVATION (look +X)", "z", volume.z0,
                     volume.y0, 3),
        matrix_panel(east.transpose(1, 0), colours,
                     "EAST ELEVATION (look -X)", "z", volume.z0,
                     volume.y0, 3),
        matrix_panel(x_section.transpose(1, 0), colours,
                     f"LONGITUDINAL SECTION x={anchor[0]-2}..{anchor[0]+2}",
                     "z", volume.z0, volume.y0, 3),
        matrix_panel(z_section, colours,
                     f"TRANSVERSE SECTION z={anchor[2]-2}..{anchor[2]+2}",
                     "x", volume.x0, volume.y0, 3),
    ]
    combine_panels(panels, 2, output)


def iso_projection(volume: Volume, masks: dict[str, np.ndarray],
                   anchor: tuple[int, int, int], sign_x: int,
                   sign_z: int, title: str) -> Image.Image:
    render_mask = masks["authored"] | masks["fluid"]
    visible = []
    sx, sy, sz = render_mask.shape
    for x, y, z in zip(*np.nonzero(render_mask)):
        exposed = (y + 1 >= sy or not render_mask[x, y + 1, z]
                   or x + sign_x < 0 or x + sign_x >= sx
                   or not render_mask[x + sign_x, y, z]
                   or z + sign_z < 0 or z + sign_z >= sz
                   or not render_mask[x, y, z + sign_z])
        if exposed:
            tx = x if sign_x > 0 else sx - 1 - x
            tz = z if sign_z > 0 else sz - 1 - z
            visible.append((tx + tz, y, x, z))
    visible.sort(key=lambda entry: (entry[0], entry[1]))
    tile_w, tile_h, vertical = 8, 4, 4
    width = (sx + sz + 4) * tile_w // 2 + 80
    height = (sx + sz + 4) * tile_h // 2 + sy * vertical + 80
    image = Image.new("RGB", (width, height), (13, 13, 19))
    draw = ImageDraw.Draw(image)
    origin_x = width // 2
    origin_y = 30 + sy * vertical

    def project(px: float, py: float, pz: float) -> tuple[int, int]:
        tx = px if sign_x > 0 else sx - px
        tz = pz if sign_z > 0 else sz - pz
        return (int(origin_x + (tx - tz) * tile_w / 2),
                int(origin_y + (tx + tz) * tile_h / 2 - py * vertical))

    for _, y, x, z in visible:
        colour = state_colour(volume.state(x, y, z))
        if y + 1 >= sy or not render_mask[x, y + 1, z]:
            top = [project(x, y + 1, z), project(x + 1, y + 1, z),
                   project(x + 1, y + 1, z + 1), project(x, y + 1, z + 1)]
            draw.polygon(top, fill=shade(colour, 1.13))
        nx = x + sign_x
        if nx < 0 or nx >= sx or not render_mask[nx, y, z]:
            face_x = x + (1 if sign_x > 0 else 0)
            poly = [project(face_x, y, z), project(face_x, y + 1, z),
                    project(face_x, y + 1, z + 1), project(face_x, y, z + 1)]
            draw.polygon(poly, fill=shade(colour, 0.76))
        nz = z + sign_z
        if nz < 0 or nz >= sz or not render_mask[x, y, nz]:
            face_z = z + (1 if sign_z > 0 else 0)
            poly = [project(x, y, face_z), project(x, y + 1, face_z),
                    project(x + 1, y + 1, face_z), project(x + 1, y, face_z)]
            draw.polygon(poly, fill=shade(colour, 0.62))
    ax = anchor[0] - volume.x0 + 0.5
    ay = anchor[1] - volume.y0 + 0.5
    az = anchor[2] - volume.z0 + 0.5
    px, py = project(ax, ay, az)
    draw.ellipse((px - 8, py - 8, px + 8, py + 8),
                 outline=(255, 255, 255), width=3)
    draw.line((px - 12, py, px + 12, py), fill=(255, 60, 60), width=2)
    draw.line((px, py - 12, px, py + 12), fill=(255, 60, 60), width=2)
    draw.text((12, 10), title, fill=(255, 214, 84))
    draw.text((12, 28), "authored solids + fluids; natural terrain hidden",
              fill=(210, 210, 220))
    return image


FACE_VERTICES = {
    (1, 0, 0): ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
    (-1, 0, 0): ((0, 0, 1), (0, 1, 1), (0, 1, 0), (0, 0, 0)),
    (0, 1, 0): ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
    (0, -1, 0): ((0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1)),
    (0, 0, 1): ((1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1)),
    (0, 0, -1): ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
}


def write_glb(volume: Volume, masks: dict[str, np.ndarray], output: Path) -> dict:
    render_mask = masks["authored"] | masks["fluid"]
    positions = array("f")
    colours = array("B")
    indices = array("I")
    vertices = 0
    faces = 0
    for x, y, z in zip(*np.nonzero(render_mask)):
        rgb = state_colour(volume.state(x, y, z))
        for (dx, dy, dz), corners in FACE_VERTICES.items():
            nx, ny, nz = x + dx, y + dy, z + dz
            if (0 <= nx < volume.sx and 0 <= ny < volume.sy
                    and 0 <= nz < volume.sz and render_mask[nx, ny, nz]):
                continue
            for cx, cy, cz in corners:
                positions.extend((float(x + cx + volume.x0 - output_anchor[0]),
                                  float(y + cy + volume.y0 - output_anchor[1]),
                                  float(z + cz + volume.z0 - output_anchor[2])))
                colours.extend((*rgb, 255))
            indices.extend((vertices, vertices + 1, vertices + 2,
                            vertices, vertices + 2, vertices + 3))
            vertices += 4
            faces += 1
    position_bytes = positions.tobytes()
    colour_bytes = colours.tobytes()
    index_bytes = indices.tobytes()

    def pad(data: bytes, value: bytes = b"\0") -> bytes:
        return data + value * ((-len(data)) % 4)

    position_offset = 0
    colour_offset = len(pad(position_bytes))
    index_offset = colour_offset + len(pad(colour_bytes))
    binary = pad(position_bytes) + pad(colour_bytes) + pad(index_bytes)
    minimum = [float(volume.x0 - output_anchor[0]),
               float(volume.y0 - output_anchor[1]),
               float(volume.z0 - output_anchor[2])]
    maximum = [float(volume.x1 + 1 - output_anchor[0]),
               float(volume.y1 + 1 - output_anchor[1]),
               float(volume.z1 + 1 - output_anchor[2])]
    document = {
        "asset": {"version": "2.0", "generator": "Project SEELE spatial survey"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "survey_voxels"}],
        "meshes": [{"primitives": [{
            "attributes": {"POSITION": 0, "COLOR_0": 1},
            "indices": 2,
            "mode": 4,
        }]}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": position_offset,
             "byteLength": len(position_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": colour_offset,
             "byteLength": len(colour_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": index_offset,
             "byteLength": len(index_bytes), "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": vertices,
             "type": "VEC3", "min": minimum, "max": maximum},
            {"bufferView": 1, "componentType": 5121, "count": vertices,
             "type": "VEC4", "normalized": True},
            {"bufferView": 2, "componentType": 5125,
             "count": len(indices), "type": "SCALAR"},
        ],
    }
    json_bytes = pad(json.dumps(document, separators=(",", ":")).encode("utf-8"), b" ")
    total_length = 12 + 8 + len(json_bytes) + 8 + len(binary)
    with output.open("wb") as handle:
        handle.write(struct.pack("<4sII", b"glTF", 2, total_length))
        handle.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
        handle.write(json_bytes)
        handle.write(struct.pack("<I4s", len(binary), b"BIN\0"))
        handle.write(binary)
    return {"faces": faces, "vertices": vertices, "bytes": output.stat().st_size}


def component_plan(volume: Volume, labels: np.ndarray,
                   anchor: tuple[int, int, int], output: Path,
                   caption: str) -> None:
    levels = []
    for dy in (-4, -2, 0, 2, 4):
        y = max(volume.y0, min(volume.y1, anchor[1] + dy))
        levels.append(plan_image(volume, y, colour_table(volume), anchor,
                                 scale=3, labels=labels,
                                 title=f"{caption} y={y}"))
    combine_panels(levels, 3, output)


def nearest_walk_component(volume: Volume, walk_labels: np.ndarray,
                           anchor: tuple[int, int, int]) -> int | None:
    ax, ay, az = anchor
    candidates = []
    for dx in range(-3, 4):
        for dy in range(-4, 5):
            for dz in range(-3, 4):
                ix, iy, iz = ax + dx - volume.x0, ay + dy - volume.y0, az + dz - volume.z0
                if (0 <= ix < volume.sx and 0 <= iy < volume.sy
                        and 0 <= iz < volume.sz):
                    component = int(walk_labels[ix, iy, iz])
                    if component >= 0:
                        candidates.append((abs(dx) + abs(dy) + abs(dz), component))
    return min(candidates)[1] if candidates else None


def write_ledger(volume: Volume, solid_labels: np.ndarray,
                 walk_labels: np.ndarray, output: Path) -> int:
    rows = 0
    with gzip.open(output, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("x", "y", "z", "block_state", "role",
                         "solid_component", "adjacent_walk_components",
                         "block_entity", "source"))
        for ix, iy, iz in zip(*np.nonzero(volume.code)):
            x, y, z = volume.world_position(ix, iy, iz)
            state = volume.state(ix, iy, iz)
            adjacent_walk = set()
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                               (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nx, ny, nz = ix + dx, iy + dy, iz + dz
                if (0 <= nx < volume.sx and 0 <= ny < volume.sy
                        and 0 <= nz < volume.sz):
                    found = int(walk_labels[nx, ny, nz])
                    if found >= 0:
                        adjacent_walk.add(found)
            writer.writerow((x, y, z, state, role_of(state),
                             int(solid_labels[ix, iy, iz]),
                             ";".join(map(str, sorted(adjacent_walk))),
                             volume.block_entities.get((x, y, z), ""),
                             "UNKNOWN"))
            rows += 1
    return rows


def legend_image(volume: Volume, output: Path) -> dict:
    state_counts = Counter(volume.states[int(code)]
                           for code in volume.code.ravel() if code)
    role_counts = Counter()
    for state, count in state_counts.items():
        role_counts[role_of(state)] += count
    top = state_counts.most_common(24)
    image = Image.new("RGB", (920, 54 + 25 * (len(top) + 8)), (18, 18, 24))
    draw = ImageDraw.Draw(image)
    draw.text((18, 12), "MATERIAL / OWNERSHIP LEGEND", fill=(255, 214, 84))
    y = 40
    draw.text((18, y), "Ownership: UNKNOWN (no as-built provenance ledger exists)",
              fill=(255, 100, 100))
    y += 28
    for role, count in sorted(role_counts.items()):
        draw.text((18, y), f"role {role:<12} {count:>9}", fill=(220, 220, 228))
        y += 22
    y += 8
    for state, count in top:
        rgb = state_colour(state)
        draw.rectangle((18, y, 38, y + 16), fill=rgb, outline=(230, 230, 230))
        draw.text((48, y + 1), f"{count:>9}  {state}", fill=(220, 220, 228))
        y += 22
    image.crop((0, 0, image.width, y + 14)).save(output)
    return {"roles": dict(role_counts), "top_states": dict(top)}


def write_sha_manifest(directory: Path) -> str:
    rows = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name == "packet.sha256":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(directory).as_posix()}")
    text = "\n".join(rows) + "\n"
    (directory / "packet.sha256").write_text(text, encoding="ascii")
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", default="SEELE_S20_REBUILD")
    parser.add_argument("--dimension", default="dimensions/projectseele/geofront")
    parser.add_argument("--anchor", nargs=3, type=int, required=True,
                        metavar=("X", "Y", "Z"))
    parser.add_argument("--repair-id", required=True)
    parser.add_argument("--horizontal", type=int, default=48)
    parser.add_argument("--vertical", type=int, default=32)
    parser.add_argument("--yaw", type=float)
    parser.add_argument("--pitch", type=float)
    parser.add_argument("--screenshot")
    parser.add_argument("--emit")
    return parser.parse_args()


output_anchor = (0, 0, 0)


def main() -> None:
    global output_anchor
    args = parse_args()
    anchor = tuple(args.anchor)
    output_anchor = anchor
    world_root = ROOT / "run" / "saves" / args.world
    dimension = world_root / args.dimension
    if not dimension.is_dir():
        raise SystemExit(f"dimension not found: {dimension}")
    output = (ROOT / (args.emit or f"artifacts/map_understanding/{args.repair_id}"))
    output.mkdir(parents=True, exist_ok=True)
    plans = output / "02_plan_layers"
    plans.mkdir(exist_ok=True)
    box = (anchor[0] - args.horizontal, anchor[0] + args.horizontal,
           anchor[1] - args.vertical, anchor[1] + args.vertical,
           anchor[2] - args.horizontal, anchor[2] + args.horizontal)
    volume = Volume(dimension, box)
    masks = volume.masks()
    colours = colour_table(volume)
    solid_labels, solid_components = label_components(
        masks["authored"], volume)
    walk_labels, walk_components = label_components(
        masks["standable"], volume, walkable=True)
    selected_walk = nearest_walk_component(volume, walk_labels, anchor)

    levels = sorted(set(
        range(max(volume.y0, anchor[1] - 12),
              min(volume.y1, anchor[1] + 12) + 1)
        ).union(range(volume.y0, volume.y1 + 1, 4)))
    plan_pages = []
    for y in levels:
        image = plan_image(volume, y, colours, anchor)
        image.save(plans / f"y{y}.png")
        plan_pages.append(image)
    if plan_pages:
        plan_pages[0].save(output / "02_plan_layers.pdf", "PDF",
                           save_all=True, append_images=plan_pages[1:],
                           resolution=120.0)

    # Observation registration remains explicit about unknown camera data.
    observation_panels = [
        plan_image(volume, max(volume.y0, min(volume.y1, anchor[1] + dy)),
                   colours, anchor, scale=3,
                   title=f"OBSERVATION PLAN y={anchor[1] + dy}")
        for dy in (-1, 0, 1)
    ]
    combine_panels(observation_panels, 3,
                   output / "01_observation_registered.png")
    orthographic_packet(volume, masks, colours, anchor,
                        output / "03_orthos_sections.png")
    iso_a = iso_projection(volume, masks, anchor, 1, 1,
                           "ISO +X/+Z (BEFORE)")
    iso_b = iso_projection(volume, masks, anchor, -1, -1,
                           "ISO -X/-Z (BEFORE)")
    combine_panels([iso_a, iso_b], 2, output / "04_iso_views.png")
    glb = write_glb(volume, masks, output / "04_iso_before.glb")

    component_plan(volume, solid_labels, anchor,
                   output / "05_components.png", "AUTHORED SOLID COMPONENTS")
    component_plan(volume, walk_labels, anchor,
                   output / "06_walkspace.png", "WALKABLE-AIR COMPONENTS")
    components_payload = {
        "solid_component_count": len(solid_components),
        "walk_component_count": len(walk_components),
        "solid_components": sorted(solid_components,
                                   key=lambda entry: -entry["cells"]),
        "walk_components": sorted(walk_components,
                                  key=lambda entry: -entry["cells"]),
    }
    (output / "05_components.json").write_text(
        json.dumps(components_payload, indent=2), encoding="utf-8")
    selected_entry = (walk_components[selected_walk]
                      if selected_walk is not None else None)
    (output / "06_walkspace.json").write_text(json.dumps({
        "selected_component_near_observation": selected_walk,
        "selected_component": selected_entry,
        "rule": "solid support below + two passable blocks; horizontal or one-block step",
        "components_touching_boundary": [entry["id"] for entry in walk_components
                                          if entry["touches_survey_boundary"]],
    }, indent=2), encoding="utf-8")
    ledger_rows = write_ledger(volume, solid_labels, walk_labels,
                               output / "07_voxel_ledger.csv.gz")
    legend = legend_image(volume, output / "07_legend_ownership.png")

    manifest = {
        "repair_id": args.repair_id,
        "mode": "READ_ONLY_SURVEY",
        "editable_mask": [],
        "world": args.world,
        "world_path": str(world_root.resolve()),
        "dimension": args.dimension,
        "anchor": {"feet_or_reported": list(anchor),
                   "yaw": args.yaw, "pitch": args.pitch,
                   "meaning": "observation anchor only; never an edit target"},
        "source_screenshot": args.screenshot,
        "box": list(box),
        "loaded_chunks": [list(value) for value in sorted(volume.loaded_chunks)],
        "chunk_voxel_hashes": volume.chunk_hashes(),
        "region_file_hashes": volume.region_hashes(),
        "states": len(volume.states),
        "non_air_voxels": int(np.count_nonzero(volume.code)),
        "authored_solid_voxels": int(masks["authored"].sum()),
        "fluid_voxels": int(masks["fluid"].sum()),
        "ledger_rows": ledger_rows,
        "selected_walk_component": selected_walk,
        "survey_boundary_stop": {
            "solid_components_touching": [entry["id"] for entry in solid_components
                                            if entry["touches_survey_boundary"]],
            "walk_components_touching": [entry["id"] for entry in walk_components
                                           if entry["touches_survey_boundary"]],
            "rule": "a touching candidate must be expanded or human-bounded before PREVIEW",
        },
        "ownership": {
            "status": "UNKNOWN",
            "reason": "no exact as-built provenance ledger exists for these saved voxels",
        },
        "legend": legend,
        "glb": glb,
        "automatic_world_writers": "disabled in source; this tool performs no world writes",
    }
    (output / "00_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    digest = write_sha_manifest(output)
    print(f"[survey] {args.repair_id}")
    print(f"[world] {dimension}")
    print(f"[box] {box} chunks={len(volume.loaded_chunks)} states={len(volume.states)}")
    print(f"[components] solid={len(solid_components)} walk={len(walk_components)} selected={selected_walk}")
    print(f"[ledger] rows={ledger_rows} glb={glb}")
    print(f"[output] {output}")
    print(f"[packet-sha] {digest}")


if __name__ == "__main__":
    main()
