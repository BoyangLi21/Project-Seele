#!/usr/bin/env python3
"""Export a read-only, non-Minecraft spatial twin of a Project SEELE save.

The exporter deliberately does not infer rooms from air.  It streams Anvil
sections into multi-resolution semantic voxels, writes surface-only GLB meshes,
coordinate-labelled evidence images, and an SQLite inventory.  Geometry keeps
Minecraft world coordinates so a point selected in Blender can be copied back
to F3 without a transform.

Typical use::

    python tools/export_spatial_twin.py \
      --world run/saves/SEELE_S20_RECOVERY_R28 \
      --emit artifacts/r28_spatial_twin_20260811
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import struct
import sys
from typing import Iterable

# Prefer the interpreter's own ABI-matched NumPy.  The local helper bundle is
# for pure-Python packages such as trimesh/nbtlib and may contain a NumPy wheel
# built for a different CPython patch line.
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".Codex" / (
        f"pydeps{sys.version_info.major}{sys.version_info.minor}")
# The original local bundle predates the named-version directories and is the
# CPython 3.13 bundle on the current workstation.  Never force a cp312 wheel
# into a newer interpreter merely because that directory happens to exist.
if not LOCAL_DEPS.exists() and sys.version_info[:2] == (3, 13):
    LOCAL_DEPS = ROOT / ".Codex" / "pydeps"
if LOCAL_DEPS.exists():
    if "blender foundation" in sys.executable.lower():
        # Blender ships a matching NumPy build.  Keep it ahead of the local
        # helper packages, while still making nbtlib/Pillow helpers available.
        sys.path.append(str(LOCAL_DEPS))
    else:
        sys.path.insert(0, str(LOCAL_DEPS))
        numpy_dlls = LOCAL_DEPS / "numpy.libs"
        if sys.platform == "win32" and numpy_dlls.exists():
            os.add_dll_directory(str(numpy_dlls))
sys.path.insert(0, str(ROOT / "tools"))

from inspect_map_assets import decode_modern_section, iter_chunks, palette_name


# Category value is also its conflict priority inside a downsampled voxel.
AIR = 0
NATURAL = 1
VEGETATION = 2
WATER = 3
LCL = 4
SKYWEAVE = 5
STRUCTURE = 6
GLASS = 7
TRANSIT = 8
VERTICAL = 9
DOOR = 10
MECHANISM = 11
SCREEN = 12
LIGHT = 13

CATEGORY_NAMES = {
    AIR: "air",
    NATURAL: "natural_terrain",
    VEGETATION: "vegetation",
    WATER: "water",
    LCL: "lcl",
    SKYWEAVE: "geofront_boundary",
    STRUCTURE: "unclassified_hold",
    GLASS: "glass",
    TRANSIT: "transit",
    VERTICAL: "vertical_circulation",
    DOOR: "door_portal",
    MECHANISM: "mechanism",
    SCREEN: "screen_telemetry",
    LIGHT: "lighting",
}

CATEGORY_COLOURS = {
    NATURAL: (93, 111, 73, 255),
    VEGETATION: (52, 135, 67, 255),
    WATER: (48, 120, 205, 170),
    LCL: (240, 112, 25, 180),
    SKYWEAVE: (118, 181, 188, 90),
    STRUCTURE: (103, 108, 120, 255),
    GLASS: (142, 208, 224, 105),
    TRANSIT: (235, 188, 56, 255),
    VERTICAL: (209, 77, 194, 255),
    DOOR: (55, 230, 150, 255),
    MECHANISM: (220, 68, 58, 255),
    SCREEN: (255, 150, 34, 235),
    LIGHT: (255, 244, 174, 255),
}

AIR_NAMES = {"air", "cave_air", "void_air", "light"}
NATURAL_NAMES = {
    "stone", "deepslate", "dirt", "grass_block", "bedrock", "gravel",
    "sand", "red_sand", "clay", "snow", "snow_block", "ice",
    "packed_ice", "blue_ice", "andesite", "diorite", "granite", "tuff",
    "calcite", "dripstone_block", "sandstone", "red_sandstone", "mud",
    "coarse_dirt", "rooted_dirt", "podzol", "moss_block",
}


def classify(name: str) -> int:
    """Coarse semantic family; never interpreted as room/build permission."""
    s = name.split(":", 1)[-1].lower()
    if s in AIR_NAMES:
        return AIR
    if "skyweave" in s or ("sky" in s and "weave" in s):
        return SKYWEAVE
    if "lcl" in s:
        return LCL
    if s == "water" or "water" in s:
        return WATER
    if s in NATURAL_NAMES or any(k in s for k in ("_ore", "sculk")):
        return NATURAL
    if any(k in s for k in ("_leaves", "_log", "_wood", "sapling", "flower",
                             "grass", "fern", "azalea", "mushroom", "vine")):
        return VEGETATION
    if any(k in s for k in ("screen", "monitor", "display", "telemetry")):
        return SCREEN
    if any(k in s for k in ("sea_lantern", "glowstone", "shroomlight",
                             "froglight", "lamp", "light_block")):
        return LIGHT
    if "glass" in s:
        return GLASS
    if "_door" in s and "trapdoor" not in s:
        return DOOR
    if any(k in s for k in ("ladder", "scaffolding", "elevator", "lift",
                             "stairs")):
        return VERTICAL
    if any(k in s for k in ("rail", "track", "road", "asphalt", "platform")):
        return TRANSIT
    if any(k in s for k in ("piston", "observer", "dispenser", "dropper",
                             "lever", "button", "redstone", "command_block",
                             "structure_block", "barrier")):
        return MECHANISM
    return STRUCTURE


@dataclass(frozen=True)
class Bounds:
    x0: int
    x1: int
    y0: int
    y1: int
    z0: int
    z1: int

    def padded(self, n: int) -> "Bounds":
        return Bounds(self.x0 - n, self.x1 + n, self.y0 - n, self.y1 + n,
                      self.z0 - n, self.z1 + n)

    def clamp(self, outer: "Bounds") -> "Bounds":
        return Bounds(max(self.x0, outer.x0), min(self.x1, outer.x1),
                      max(self.y0, outer.y0), min(self.y1, outer.y1),
                      max(self.z0, outer.z0), min(self.z1, outer.z1))

    def as_list(self) -> list[int]:
        return [self.x0, self.x1, self.y0, self.y1, self.z0, self.z1]


@dataclass(frozen=True)
class DimensionSpec:
    key: str
    path: str
    bounds: Bounds


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def grid_shape(bounds: Bounds, lod: int) -> tuple[int, int, int]:
    return (math.ceil((bounds.x1 - bounds.x0 + 1) / lod),
            math.ceil((bounds.y1 - bounds.y0 + 1) / lod),
            math.ceil((bounds.z1 - bounds.z0 + 1) / lod))


def scan_dimension(world: Path, spec: DimensionSpec, lod: int,
                   collect_chunks: bool = True):
    """Stream chunks into a semantic grid and compact per-chunk inventory."""
    b = spec.bounds
    shape = grid_shape(b, lod)
    grid = np.zeros(shape, dtype=np.uint8)
    chunk_rows: list[dict] = []
    authored_min = [10**9, 10**9, 10**9]
    authored_max = [-10**9, -10**9, -10**9]
    block_totals: Counter[str] = Counter()
    category_totals: Counter[int] = Counter()
    lin = np.arange(4096, dtype=np.int32)
    ox = lin & 15
    oz = (lin >> 4) & 15
    oy = lin >> 8
    chunk_bounds = (b.x0 // 16, b.x1 // 16, b.z0 // 16, b.z1 // 16)

    for chunk_x, chunk_z, root in iter_chunks(world / spec.path, chunk_bounds):
        data = root.get("Level", root)
        chunk_counts: Counter[int] = Counter()
        chunk_names: Counter[str] = Counter()
        ymin, ymax = 10**9, -10**9
        for section in data.get("Sections", data.get("sections", [])):
            section_y = int(section["Y"]) * 16
            if section_y > b.y1 or section_y + 15 < b.y0:
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            names = [palette_name(entry) for entry in palette]
            cats = np.fromiter((classify(name) for name in names),
                               dtype=np.uint8, count=len(names))
            arr = np.asarray(indices, dtype=np.int32)
            values = cats[arr]
            hit = values != AIR
            if not hit.any():
                continue
            xs = chunk_x * 16 + ox[hit]
            ys = section_y + oy[hit]
            zs = chunk_z * 16 + oz[hit]
            keep = ((xs >= b.x0) & (xs <= b.x1) & (ys >= b.y0) &
                    (ys <= b.y1) & (zs >= b.z0) & (zs <= b.z1))
            if not keep.any():
                continue
            xs, ys, zs = xs[keep], ys[keep], zs[keep]
            vv = values[hit][keep]
            palette_indices = arr[hit][keep]
            gx = (xs - b.x0) // lod
            gy = (ys - b.y0) // lod
            gz = (zs - b.z0) // lod
            flat = np.ravel_multi_index((gx, gy, gz), shape)
            np.maximum.at(grid.ravel(), flat, vv)
            unique, counts = np.unique(vv, return_counts=True)
            for code, count in zip(unique.tolist(), counts.tolist()):
                chunk_counts[int(code)] += int(count)
                category_totals[int(code)] += int(count)
            name_indices, name_counts = np.unique(palette_indices,
                                                  return_counts=True)
            for index, count in zip(name_indices.tolist(), name_counts.tolist()):
                chunk_names[names[index]] += int(count)
                block_totals[names[index]] += int(count)
            ymin, ymax = min(ymin, int(ys.min())), max(ymax, int(ys.max()))

            authored = np.isin(vv, (STRUCTURE, GLASS, TRANSIT, VERTICAL,
                                     DOOR, MECHANISM, SCREEN, LIGHT))
            if authored.any():
                ax, ay, az = xs[authored], ys[authored], zs[authored]
                authored_min[0] = min(authored_min[0], int(ax.min()))
                authored_min[1] = min(authored_min[1], int(ay.min()))
                authored_min[2] = min(authored_min[2], int(az.min()))
                authored_max[0] = max(authored_max[0], int(ax.max()))
                authored_max[1] = max(authored_max[1], int(ay.max()))
                authored_max[2] = max(authored_max[2], int(az.max()))

        if collect_chunks and chunk_counts:
            chunk_rows.append({
                "dimension": spec.key,
                "chunk_x": chunk_x,
                "chunk_z": chunk_z,
                "min_y": ymin,
                "max_y": ymax,
                "non_air": sum(chunk_counts.values()),
                "categories": {CATEGORY_NAMES[k]: v
                               for k, v in sorted(chunk_counts.items())},
                "top_blocks": chunk_names.most_common(12),
            })

    authored_bounds = None
    if authored_min[0] <= authored_max[0]:
        authored_bounds = Bounds(authored_min[0], authored_max[0],
                                 authored_min[1], authored_max[1],
                                 authored_min[2], authored_max[2])
    return {
        "grid": grid,
        "chunks": chunk_rows,
        "authored_bounds": authored_bounds,
        "block_totals": block_totals,
        "category_totals": category_totals,
    }


def greedy_rectangles(mask: np.ndarray):
    """Yield (code,u0,u1,v0,v1) maximal same-code rectangles."""
    work = mask.copy()
    height, width = work.shape
    while True:
        occupied = np.flatnonzero(work)
        if not len(occupied):
            return
        u0, v0 = divmod(int(occupied[0]), width)
        code = int(work[u0, v0])
        row = work[u0, v0:]
        stop = np.flatnonzero(row != code)
        v1 = v0 + (int(stop[0]) if len(stop) else len(row))
        u1 = u0 + 1
        while u1 < height and np.all(work[u1, v0:v1] == code):
            u1 += 1
        work[u0:u1, v0:v1] = AIR
        yield code, u0, u1, v0, v1


def rectangle_corners(axis: int, sign: int, plane: int,
                      u0: int, u1: int, v0: int, v1: int,
                      bounds: Bounds, lod: int) -> np.ndarray:
    origin = np.asarray((bounds.x0, bounds.y0, bounds.z0), dtype=np.float32)
    if axis == 0:
        raw = ((plane, u0, v0), (plane, u1, v0), (plane, u1, v1),
               (plane, u0, v1)) if sign < 0 else (
               (plane, u0, v0), (plane, u0, v1), (plane, u1, v1),
               (plane, u1, v0))
    elif axis == 1:
        raw = ((u0, plane, v0), (u0, plane, v1), (u1, plane, v1),
               (u1, plane, v0)) if sign < 0 else (
               (u0, plane, v0), (u1, plane, v0), (u1, plane, v1),
               (u0, plane, v1))
    else:
        raw = ((u0, v0, plane), (u1, v0, plane), (u1, v1, plane),
               (u0, v1, plane)) if sign < 0 else (
               (u0, v0, plane), (u0, v1, plane), (u1, v1, plane),
               (u1, v0, plane))
    return origin + np.asarray(raw, dtype=np.float32) * lod


def surface_meshes(grid: np.ndarray, bounds: Bounds, lod: int):
    """Greedy-merge exposed semantic faces; no dense cube export."""
    positions: dict[int, list[np.ndarray]] = defaultdict(list)
    indices: dict[int, list[int]] = defaultdict(list)
    neighbour = np.zeros_like(grid)
    for axis in range(3):
        other = [value for value in range(3) if value != axis]
        for sign in (-1, 1):
            neighbour.fill(AIR)
            if sign < 0:
                dst = [slice(None)] * 3
                src = [slice(None)] * 3
                dst[axis] = slice(1, None)
                src[axis] = slice(None, -1)
            else:
                dst = [slice(None)] * 3
                src = [slice(None)] * 3
                dst[axis] = slice(None, -1)
                src[axis] = slice(1, None)
            neighbour[tuple(dst)] = grid[tuple(src)]
            exposed = np.where((grid != AIR) & (grid != neighbour), grid, AIR)
            for plane_index in range(grid.shape[axis]):
                mask = np.take(exposed, plane_index, axis=axis)
                plane = plane_index + (1 if sign > 0 else 0)
                for code, u0, u1, v0, v1 in greedy_rectangles(mask):
                    # np.take preserves the two remaining axes in ascending
                    # XYZ order, matching rectangle_corners' u/v convention.
                    quad = rectangle_corners(axis, sign, plane, u0, u1, v0, v1,
                                             bounds, lod)
                    offset = len(positions[code]) * 4
                    positions[code].append(quad)
                    indices[code].extend((offset, offset + 1, offset + 2,
                                          offset, offset + 2, offset + 3))
    return {
        code: (np.concatenate(quads).astype("<f4"),
               np.asarray(indices[code], dtype="<u4"))
        for code, quads in positions.items() if quads
    }


def write_glb(path: Path, meshes, metadata: dict) -> dict:
    """Small dependency-free GLB 2.0 writer using unlit vertex positions."""
    binary = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    gltf_meshes = []
    nodes = []
    stats = {}

    def append_blob(raw: bytes, target: int) -> int:
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(raw)
        index = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": offset,
                             "byteLength": len(raw), "target": target})
        return index

    for code in sorted(meshes):
        positions, indices = meshes[code]
        pos_view = append_blob(positions.tobytes(), 34962)
        idx_view = append_blob(indices.tobytes(), 34963)
        pos_accessor = len(accessors)
        accessors.append({
            "bufferView": pos_view, "componentType": 5126,
            "count": int(len(positions)), "type": "VEC3",
            "min": positions.min(axis=0).astype(float).tolist(),
            "max": positions.max(axis=0).astype(float).tolist(),
        })
        idx_accessor = len(accessors)
        accessors.append({"bufferView": idx_view, "componentType": 5125,
                          "count": int(len(indices)), "type": "SCALAR",
                          "min": [int(indices.min())],
                          "max": [int(indices.max())]})
        rgba = [value / 255.0 for value in CATEGORY_COLOURS[code]]
        material = len(materials)
        mat = {
            "name": CATEGORY_NAMES[code],
            "pbrMetallicRoughness": {"baseColorFactor": rgba,
                                     "metallicFactor": 0.0,
                                     "roughnessFactor": 0.92},
            "doubleSided": True,
            "extensions": {"KHR_materials_unlit": {}},
        }
        if rgba[3] < 0.999:
            mat["alphaMode"] = "BLEND"
        materials.append(mat)
        mesh_index = len(gltf_meshes)
        gltf_meshes.append({
            "name": CATEGORY_NAMES[code],
            "primitives": [{"attributes": {"POSITION": pos_accessor},
                            "indices": idx_accessor, "material": material,
                            "mode": 4}],
            "extras": {"semanticCategory": CATEGORY_NAMES[code]},
        })
        nodes.append({"name": CATEGORY_NAMES[code], "mesh": mesh_index,
                      "extras": {"semanticCategory": CATEGORY_NAMES[code]}})
        stats[CATEGORY_NAMES[code]] = {
            "vertices": int(len(positions)),
            "triangles": int(len(indices) // 3),
        }

    doc = {
        "asset": {"version": "2.0", "generator": "Project SEELE spatial twin"},
        "extensionsUsed": ["KHR_materials_unlit"],
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": gltf_meshes,
        "materials": materials,
        "bufferViews": buffer_views,
        "accessors": accessors,
        "buffers": [{"byteLength": len(binary)}],
        "extras": metadata,
    }
    json_bytes = json.dumps(doc, ensure_ascii=False,
                            separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    while len(binary) % 4:
        binary.append(0)
    total = 12 + 8 + len(json_bytes) + 8 + len(binary)
    payload = bytearray(struct.pack("<4sII", b"glTF", 2, total))
    payload.extend(struct.pack("<I4s", len(json_bytes), b"JSON"))
    payload.extend(json_bytes)
    payload.extend(struct.pack("<I4s", len(binary), b"BIN\x00"))
    payload.extend(binary)
    path.write_bytes(payload)
    return stats


def render_top(grid: np.ndarray, bounds: Bounds, lod: int, path: Path,
               title: str) -> None:
    from PIL import Image, ImageDraw

    occupied = grid != AIR
    any_col = occupied.any(axis=1)
    reverse_index = occupied[:, ::-1, :].argmax(axis=1)
    iy = grid.shape[1] - 1 - reverse_index
    codes = np.take_along_axis(grid, iy[:, None, :], axis=1)[:, 0, :]
    codes[~any_col] = AIR
    rgb = np.zeros((grid.shape[2], grid.shape[0], 3), dtype=np.uint8)
    for code, colour in CATEGORY_COLOURS.items():
        rgb[codes.T == code] = colour[:3]
    margin = 72
    image = Image.new("RGB", (rgb.shape[1] + margin, rgb.shape[0] + margin),
                      (17, 19, 24))
    image.paste(Image.fromarray(rgb), (margin, margin))
    draw = ImageDraw.Draw(image)
    draw.text((8, 8), title, fill=(238, 170, 42))
    draw.text((8, 28), f"X {bounds.x0}..{bounds.x1}  Z {bounds.z0}..{bounds.z1}  LOD {lod}",
              fill=(210, 215, 224))
    step = max(64, lod * 16)
    for x in range(math.ceil(bounds.x0 / step) * step, bounds.x1 + 1, step):
        px = margin + (x - bounds.x0) // lod
        draw.line((px, margin, px, margin + rgb.shape[0]), fill=(58, 62, 70))
        draw.text((px + 2, margin - 15), str(x), fill=(175, 180, 190))
    for z in range(math.ceil(bounds.z0 / step) * step, bounds.z1 + 1, step):
        pz = margin + (z - bounds.z0) // lod
        draw.line((margin, pz, margin + rgb.shape[1], pz), fill=(58, 62, 70))
        draw.text((2, pz - 6), str(z), fill=(175, 180, 190))
    draw.text((margin + 4, margin + 4), "N (-Z) ↑", fill=(255, 255, 255))
    image.save(path)


def render_slice(grid: np.ndarray, bounds: Bounds, lod: int, path: Path,
                 axis: str, world_value: int, title: str) -> None:
    from PIL import Image, ImageDraw

    if axis == "x":
        index = max(0, min(grid.shape[0] - 1, (world_value - bounds.x0) // lod))
        layer = grid[index, :, :].T[::-1, :]
        horizontal = f"Z {bounds.z0}..{bounds.z1}"
    else:
        index = max(0, min(grid.shape[2] - 1, (world_value - bounds.z0) // lod))
        layer = grid[:, :, index].T[::-1, :]
        horizontal = f"X {bounds.x0}..{bounds.x1}"
    rgb = np.zeros((*layer.shape, 3), dtype=np.uint8)
    for code, colour in CATEGORY_COLOURS.items():
        rgb[layer == code] = colour[:3]
    margin = 72
    image = Image.new("RGB", (rgb.shape[1] + margin, rgb.shape[0] + margin),
                      (17, 19, 24))
    image.paste(Image.fromarray(rgb), (margin, margin))
    draw = ImageDraw.Draw(image)
    draw.text((8, 8), title, fill=(238, 170, 42))
    draw.text((8, 28), f"{axis.upper()}={world_value}  {horizontal}  Y {bounds.y0}..{bounds.y1}",
              fill=(210, 215, 224))
    for y in range(math.ceil(bounds.y0 / 64) * 64, bounds.y1 + 1, 64):
        py = margin + (bounds.y1 - y) // lod
        draw.line((margin, py, margin + rgb.shape[1], py), fill=(58, 62, 70))
        draw.text((4, py - 6), str(y), fill=(175, 180, 190))
    image.save(path)


def write_database(path: Path, dimension_rows: list[dict], chunks: list[dict],
                   places: list[dict]) -> None:
    if path.exists():
        path.unlink()
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE dimensions (
          id TEXT PRIMARY KEY, path TEXT, bounds_json TEXT, lod INTEGER,
          coordinate_frame TEXT, approval TEXT);
        CREATE TABLE chunks (
          dimension TEXT, chunk_x INTEGER, chunk_z INTEGER, min_y INTEGER,
          max_y INTEGER, non_air INTEGER, categories_json TEXT,
          top_blocks_json TEXT, PRIMARY KEY(dimension,chunk_x,chunk_z));
        CREATE TABLE places (
          id TEXT PRIMARY KEY, dimension TEXT, kind TEXT, purpose TEXT,
          bbox_json TEXT, owner TEXT, protection TEXT, approval TEXT,
          evidence TEXT);
        CREATE TABLE ports (
          id TEXT PRIMARY KEY, place_id TEXT, xyz_json TEXT, normal_json TEXT,
          width INTEGER, height INTEGER, connects TEXT, approval TEXT);
        CREATE TABLE routes (
          id TEXT PRIMARY KEY, from_port TEXT, to_port TEXT, flow TEXT,
          approval TEXT);
        CREATE TABLE patches (
          id TEXT PRIMARY KEY, bbox_json TEXT, status TEXT, forward_ref TEXT,
          inverse_ref TEXT, approved_by TEXT);
    """)
    for row in dimension_rows:
        db.execute("INSERT INTO dimensions VALUES(?,?,?,?,?,?)", (
            row["id"], row["path"], json.dumps(row["bounds"]), row["lod"],
            "+X=east,+Y=up,-Z=north", "MEASURED_READ_ONLY"))
    for row in chunks:
        db.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)", (
            row["dimension"], row["chunk_x"], row["chunk_z"], row["min_y"],
            row["max_y"], row["non_air"], json.dumps(row["categories"]),
            json.dumps(row["top_blocks"])))
    for row in places:
        db.execute("INSERT INTO places VALUES(?,?,?,?,?,?,?,?,?)", (
            row["id"], row["dimension"], row["kind"], row["purpose"],
            json.dumps(row["bbox"]), row["owner"], row["protection"],
            row["approval"], row.get("evidence", "")))
    db.commit()
    db.close()


def auto_detail_bounds(authored: Bounds | None, outer: Bounds,
                       max_cells: int = 14_000_000) -> tuple[Bounds | None, int]:
    if authored is None:
        return None, 2
    detail = authored.padded(12).clamp(outer)
    lod = 2
    while math.prod(grid_shape(detail, lod)) > max_cells:
        lod *= 2
    return detail, lod


def region_inventory(region_dir: Path, primary: Bounds) -> list[dict]:
    """Read only Anvil headers; record disconnected files without meshing them."""
    rows = []
    for path in sorted(region_dir.glob("r.*.*.mca")):
        parts = path.stem.split(".")
        rx, rz = int(parts[1]), int(parts[2])
        header = path.read_bytes()[:4096]
        chunks = sum(1 for offset in range(0, len(header), 4)
                     if struct.unpack_from(">I", header, offset)[0] >> 8)
        bbox = [rx * 512, rx * 512 + 511, rz * 512, rz * 512 + 511]
        intersects = not (bbox[1] < primary.x0 or bbox[0] > primary.x1 or
                          bbox[3] < primary.z0 or bbox[2] > primary.z1)
        rows.append({"file": path.name, "region": [rx, rz], "xzBounds": bbox,
                     "presentChunks": chunks, "bytes": path.stat().st_size,
                     "includedInPrimaryModel": intersects})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path,
                        default=ROOT / "run/saves/SEELE_S20_RECOVERY_R28")
    parser.add_argument("--emit", type=Path,
                        default=ROOT / "artifacts/r28_spatial_twin_20260811")
    parser.add_argument("--overview-lod", type=int, default=4)
    parser.add_argument("--skip-detail", action="store_true")
    args = parser.parse_args()

    world = args.world if args.world.is_absolute() else ROOT / args.world
    out = args.emit if args.emit.is_absolute() else ROOT / args.emit
    out.mkdir(parents=True, exist_ok=True)
    (out / "models").mkdir(exist_ok=True)
    (out / "evidence").mkdir(exist_ok=True)

    specs = [
        DimensionSpec("tokyo3_overworld", "",
                      Bounds(-512, 511, -64, 319, -512, 511)),
        DimensionSpec("geofront", "dimensions/projectseele/geofront",
                      Bounds(-320, 380, -672, 319, -120, 560)),
    ]
    manifest = {
        "format": "project-seele-spatial-twin-v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "authoritySave": str(world.resolve()),
        "coordinateFrame": {"east": "+X", "up": "+Y", "north": "-Z",
                            "units": "Minecraft blocks = GLB metres"},
        "dimensions": [],
        "artifacts": [],
        "policy": {"airGrantsBuildPermission": False,
                   "unknownSemantics": "HOLD",
                   "humanEdits": "HARD_PRESERVE"},
    }
    all_chunks: list[dict] = []
    db_dimensions: list[dict] = []
    places: list[dict] = []

    for spec in specs:
        print(f"[{spec.key}] overview LOD {args.overview_lod}", flush=True)
        result = scan_dimension(world, spec, args.overview_lod)
        grid = result["grid"]
        meshes = surface_meshes(grid, spec.bounds, args.overview_lod)
        glb = out / "models" / f"{spec.key}_overview_lod{args.overview_lod}.glb"
        mesh_stats = write_glb(glb, meshes, {
            "dimension": spec.key, "bounds": spec.bounds.as_list(),
            "lod": args.overview_lod, "worldCoordinates": True,
        })
        top = out / "evidence" / f"{spec.key}_top.png"
        xs = out / "evidence" / f"{spec.key}_slice_x.png"
        zs = out / "evidence" / f"{spec.key}_slice_z.png"
        render_top(grid, spec.bounds, args.overview_lod, top,
                   f"{spec.key} / semantic top view")
        center_x = (spec.bounds.x0 + spec.bounds.x1) // 2
        center_z = (spec.bounds.z0 + spec.bounds.z1) // 2
        render_slice(grid, spec.bounds, args.overview_lod, xs, "x", center_x,
                     f"{spec.key} / east-west coordinate section")
        render_slice(grid, spec.bounds, args.overview_lod, zs, "z", center_z,
                     f"{spec.key} / north-south coordinate section")
        all_chunks.extend(result["chunks"])
        detail_bounds, detail_lod = auto_detail_bounds(result["authored_bounds"],
                                                       spec.bounds)
        dim_entry = {
            "id": spec.key, "path": spec.path,
            "bounds": spec.bounds.as_list(), "lod": args.overview_lod,
            "overviewModel": str(glb.relative_to(out)).replace("\\", "/"),
            "topView": str(top.relative_to(out)).replace("\\", "/"),
            "authoredBounds": (result["authored_bounds"].as_list()
                               if result["authored_bounds"] else None),
            "categories": {CATEGORY_NAMES[k]: int(v) for k, v in
                           sorted(result["category_totals"].items())},
            "meshStats": mesh_stats,
        }
        manifest["dimensions"].append(dim_entry)
        db_dimensions.append(dim_entry)
        manifest["artifacts"].extend([str(glb.relative_to(out)),
                                      str(top.relative_to(out)),
                                      str(xs.relative_to(out)),
                                      str(zs.relative_to(out))])
        places.append({
            "id": f"{spec.key.upper()}_MEASURED_EXTENT",
            "dimension": spec.key, "kind": "exterior",
            "purpose": "Measured read-only scan extent",
            "bbox": spec.bounds.as_list(), "owner": "world",
            "protection": "HARD", "approval": "MEASURED",
            "evidence": str(top.relative_to(out)).replace("\\", "/"),
        })

        detail_regions = []
        if spec.key == "tokyo3_overworld" and detail_bounds is not None:
            detail_regions.append(("authored", detail_bounds, detail_lod))
        elif spec.key == "geofront":
            # R28 contains its connected Tokyo-3 surface and underground NERV
            # in this dimension.  Keep three independently hideable/detail
            # models instead of one enormous authored bounding box.
            detail_regions.extend((
                ("tokyo3_surface", Bounds(-320, 380, 64, 200, -120, 560), 2),
                ("nerv_facilities", Bounds(-304, 351, -512, -257, -112, 543), 2),
                ("terminal_dogma", Bounds(-160, 220, -672, -480, 40, 400), 2),
            ))
        if not args.skip_detail:
            dim_entry["detailModels"] = []
            for label, region_bounds, region_lod in detail_regions:
                print(f"[{spec.key}] {label} LOD {region_lod} "
                      f"{region_bounds.as_list()}", flush=True)
                detail_spec = DimensionSpec(spec.key, spec.path, region_bounds)
                detail = scan_dimension(world, detail_spec, region_lod,
                                        collect_chunks=False)
                detail_glb = (out / "models" /
                              f"{spec.key}_{label}_lod{region_lod}.glb")
                detail_stats = write_glb(
                    detail_glb,
                    surface_meshes(detail["grid"], region_bounds, region_lod),
                    {"dimension": spec.key, "bounds": region_bounds.as_list(),
                     "lod": region_lod, "worldCoordinates": True,
                     "selection": label})
                detail_entry = {
                    "label": label,
                    "model": str(detail_glb.relative_to(out)).replace("\\", "/"),
                    "bounds": region_bounds.as_list(), "lod": region_lod,
                    "meshStats": detail_stats,
                }
                dim_entry["detailModels"].append(detail_entry)
                manifest["artifacts"].append(str(detail_glb.relative_to(out)))
        del grid

    # The cavern extent is a measured geometric anchor, not a room inference.
    places.append({
        "id": "GEOFRONT_PRIMARY_CAVERN",
        "dimension": "geofront", "kind": "exterior",
        "purpose": "Primary GeoFront cavern/shell reference",
        "bbox": [-292, 352, -656, -8, -102, 542],
        "owner": "projectseele", "protection": "HARD",
        "approval": "MEASURED_APPROX_CENTER_R322",
        "evidence": "evidence/geofront_top.png",
    })

    database = out / "spatial_twin.sqlite"
    write_database(database, db_dimensions, all_chunks, places)
    manifest["artifacts"].append(database.name)
    manifest["places"] = places
    manifest["inventory"] = {
        "chunks": len(all_chunks),
        "sqlite": database.name,
        "regions": {
            spec.key: region_inventory(world / spec.path / "region", spec.bounds)
            for spec in specs
        },
        "note": "Disconnected far-region islands are listed but are not treated as NERV facilities.",
    }
    manifest_path = out / "spatial_twin.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Project SEELE spatial twin place card",
        "type": "object",
        "required": ["id", "dimension", "kind", "bbox", "owner",
                     "protection", "approval"],
        "properties": {
            "id": {"type": "string"},
            "dimension": {"enum": ["tokyo3_overworld", "geofront"]},
            "kind": {"enum": ["room", "corridor", "door", "elevator",
                               "stair", "platform", "exterior"]},
            "bbox": {"type": "array", "items": {"type": "integer"},
                     "minItems": 6, "maxItems": 6},
            "owner": {"type": "string"},
            "protection": {"enum": ["HARD", "HOLD", "PATCH_OWNED"]},
            "approval": {"enum": ["MEASURED", "HUMAN_APPROVED", "HOLD"]},
            "ports": {"type": "array", "items": {"type": "object",
                "required": ["id", "pos", "normal", "width", "height",
                             "approval"]}},
        },
    }
    (out / "place_card.schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = (
        "# R28 spatial twin\n\n"
        "Read-only scan; no Minecraft blocks were changed. Native GLB vertex "
        "positions equal F3 `(X,Y,Z)`. Blender imports glTF Y-up as Z-up, so "
        "its displayed `(Xb,Yb,Zb)` converts back to F3 as "
        "`(Xb,Zb,-Yb)`.\n\n"
        "- Open `models/*overview*.glb` in Blender for the whole scene.\n"
        "- Use the semantic material/object list to hide terrain, shell, water, "
        "glass, or mechanisms.\n"
        "- `spatial_twin.sqlite` stores measured chunks and is the future single "
        "source for confirmed places/ports/routes.\n"
        "- Air is never treated as permission to build; inferred rooms and "
        "routes remain HOLD until human approval.\n"
    )
    (out / "README.md").write_text(readme, encoding="utf-8")

    for relative in list(manifest["artifacts"]):
        target = out / relative
        if target.exists():
            pass
    receipt = {
        "status": "READ_ONLY_TWIN_EXPORTED",
        "manifest": str(manifest_path),
        "manifestSha256": sha256(manifest_path),
        "databaseSha256": sha256(database),
        "chunks": len(all_chunks),
        "models": [entry["overviewModel"] for entry in manifest["dimensions"]],
    }
    (out / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
