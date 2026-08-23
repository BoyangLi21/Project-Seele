#!/usr/bin/env python3
"""Transplant approved authored geometry from R28 into the clean S22 world.

The tool is deliberately phase-based.  The first phase copies only the exact
underground core (command, hangars, launch plant, Dogma-facing infrastructure)
and leaves the new world's surface and the retired spherical shell untouched.
It preserves target biomes and copies block states plus block entities only.

Preview is the default.  ``--apply`` takes a localized backup of every target
region before replacing it atomically.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import os
import shutil
import struct
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import nbtlib
import numpy as np

from apply_s20_approved_semantic_repairs import (
    HEADER_BYTES,
    SECTOR_BYTES,
    atomic_replace,
    chunk_blob,
    decompress_chunk,
    encode_indices,
)
from inspect_map_assets import decode_modern_section, palette_state


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "run/saves/SEELE_S20_RECOVERY_R28"
TARGET = REPO / "run/saves/SEELE_S22_COASTAL"
DIMENSION = Path("dimensions/projectseele/geofront")

# Exact section-aligned central facility envelope.  It contains the approved
# R28 command complex, hangars, launch bays and deep plant, but deliberately
# excludes the old surface, old outer shell and remote visual-lab chunks.
CORE_CHUNK_X = range(-4, 10)       # block x -64..159
CORE_CHUNK_Z = range(6, 25)        # block z  96..399
CORE_SECTION_Y = range(-42, -17)   # block y -672..-273

SURFACE_SOURCE_MIN_Y = 80
SURFACE_SOURCE_MAX_Y = 239
SURFACE_DY = -12
SURFACE_DATUM_Y = 68

# These are world-generation materials, not authored Tokyo-3 fabric.  The
# footprint detector ignores them; once a column is selected by an authored
# block, the source air/building column is copied exactly from its first
# authored voxel upward.
NATURAL_NAMES = {
    "minecraft:air", "minecraft:cave_air", "minecraft:void_air",
    "minecraft:stone", "minecraft:deepslate", "minecraft:dirt",
    "minecraft:grass_block", "minecraft:coarse_dirt", "minecraft:podzol",
    "minecraft:rooted_dirt", "minecraft:mud", "minecraft:clay",
    "minecraft:sand", "minecraft:red_sand", "minecraft:gravel",
    "minecraft:water", "minecraft:lava", "minecraft:bedrock",
    "minecraft:snow", "minecraft:snow_block", "minecraft:ice",
    "minecraft:packed_ice", "minecraft:blue_ice",
    "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern",
    "minecraft:large_fern", "minecraft:dead_bush", "minecraft:vine",
    "minecraft:lily_pad", "minecraft:seagrass", "minecraft:tall_seagrass",
    "minecraft:kelp", "minecraft:kelp_plant",
}


@dataclass(frozen=True)
class ChunkAddress:
    x: int
    z: int

    @property
    def region(self) -> tuple[int, int]:
        return self.x // 32, self.z // 32

    @property
    def index(self) -> int:
        return (self.x & 31) + (self.z & 31) * 32


@dataclass(frozen=True)
class ShaftBox:
    name: str
    x0: int
    x1: int
    z0: int
    z1: int
    cutoff_y: int


SHAFT_BOXES = (
    ShaftBox("eva-00", -29, 5, 203, 237, 67),
    ShaftBox("eva-01", 13, 47, 203, 237, 67),
    ShaftBox("eva-02", 55, 89, 203, 237, 67),
    ShaftBox("public-lift", 126, 134, 269, 277, 69),
)
SHAFT_SOURCE_MIN_Y = -443
SHAFT_SOURCE_MAX_Y = 239
RUNTIME_ENTITY_IDS = {
    "projectseele:eva_unit00",
    "projectseele:eva_unit01",
    "projectseele:eva_unit02",
    "minecraft:text_display",
    "minecraft:armor_stand",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def region_path(save: Path, kind: str, rx: int, rz: int) -> Path:
    return save / DIMENSION / kind / f"r.{rx}.{rz}.mca"


def read_region(path: Path) -> tuple[bytes, list[bytes | None]]:
    raw = path.read_bytes()
    if len(raw) < HEADER_BYTES:
        raise RuntimeError(f"truncated region: {path}")
    chunks: list[bytes | None] = [None] * 1024
    for index in range(1024):
        location = raw[index * 4:index * 4 + 4]
        sector_offset = int.from_bytes(location[:3], "big")
        sector_count = location[3]
        if not sector_offset or not sector_count:
            continue
        byte_offset = sector_offset * SECTOR_BYTES
        if byte_offset + 5 > len(raw):
            raise RuntimeError(f"chunk {index} points beyond {path.name}")
        length = struct.unpack(">I", raw[byte_offset:byte_offset + 4])[0]
        if length <= 1 or length + 4 > sector_count * SECTOR_BYTES:
            raise RuntimeError(f"invalid chunk length at {path.name}:{index}")
        chunks[index] = raw[byte_offset:byte_offset + 4 + length]
    return raw[SECTOR_BYTES:HEADER_BYTES], chunks


def parse_chunk(blob: bytes) -> nbtlib.File:
    length = struct.unpack(">I", blob[:4])[0]
    compression = blob[4]
    if compression & 0x80:
        raise RuntimeError("external chunk streams are not supported")
    payload = blob[5:4 + length]
    return nbtlib.File.parse(io.BytesIO(decompress_chunk(compression, payload)))


def build_region(timestamps: bytes, chunks: list[bytes | None]) -> bytes:
    locations = bytearray(SECTOR_BYTES)
    body = bytearray()
    next_sector = 2
    for index, blob in enumerate(chunks):
        if blob is None:
            continue
        sectors = math.ceil(len(blob) / SECTOR_BYTES)
        if sectors > 255 or next_sector >= 1 << 24:
            raise RuntimeError("region allocation overflow")
        locations[index * 4:index * 4 + 3] = next_sector.to_bytes(3, "big")
        locations[index * 4 + 3] = sectors
        body.extend(blob)
        body.extend(b"\x00" * (sectors * SECTOR_BYTES - len(blob)))
        next_sector += sectors
    return bytes(locations) + timestamps + bytes(body)


def section_map(root: nbtlib.File) -> dict[int, nbtlib.Compound]:
    return {int(section["Y"]): section for section in root.get("sections", [])}


def entry_y(entry: nbtlib.Compound) -> int | None:
    value = entry.get("y")
    return int(value) if value is not None else None


def merge_entries(target: nbtlib.File, source: nbtlib.File, key: str,
                  min_y: int, max_y: int) -> int:
    source_entries = [copy.deepcopy(entry) for entry in source.get(key, [])
                      if entry_y(entry) is not None
                      and min_y <= int(entry_y(entry)) <= max_y]
    kept = [copy.deepcopy(entry) for entry in target.get(key, [])
            if entry_y(entry) is None
            or not (min_y <= int(entry_y(entry)) <= max_y)]
    if source_entries or key in target:
        target[key] = nbtlib.List[nbtlib.Compound](kept + source_entries)
    return len(source_entries)


def copy_core_chunk(target: nbtlib.File, source: nbtlib.File) -> dict[str, int]:
    source_sections = section_map(source)
    target_sections = section_map(target)
    missing = [sy for sy in CORE_SECTION_Y if sy not in source_sections]
    if missing:
        raise RuntimeError(f"source misses sections {missing}")

    copied = 0
    for sy in CORE_SECTION_Y:
        source_section = source_sections[sy]
        target_section = target_sections.get(sy)
        if target_section is None:
            target.get("sections").append(copy.deepcopy(source_section))
            target_sections[sy] = target.get("sections")[-1]
        else:
            states = source_section.get("block_states")
            if states is None:
                target_section.pop("block_states", None)
            else:
                target_section["block_states"] = copy.deepcopy(states)
        copied += 4096

    min_y = min(CORE_SECTION_Y) * 16
    max_y = (max(CORE_SECTION_Y) + 1) * 16 - 1
    block_entities = merge_entries(target, source, "block_entities", min_y, max_y)
    block_ticks = merge_entries(target, source, "block_ticks", min_y, max_y)
    fluid_ticks = merge_entries(target, source, "fluid_ticks", min_y, max_y)
    target["isLightOn"] = nbtlib.Byte(0)
    return {
        "voxels": copied,
        "block_entities": block_entities,
        "block_ticks": block_ticks,
        "fluid_ticks": fluid_ticks,
    }


def state_name(state: str) -> str:
    return state.split("[", 1)[0]


def is_natural(state: str) -> bool:
    name = state_name(state)
    return (name in NATURAL_NAMES or name.endswith("_leaves")
            or name.endswith("_log") or name.endswith("_wood")
            or name.endswith("_sapling") or name.endswith("_ore"))


def decoded_sections(root: nbtlib.File) -> dict[int, tuple[list, np.ndarray, dict[str, int]]]:
    result: dict[int, tuple[list, np.ndarray, dict[str, int]]] = {}
    for section in root.get("sections", []):
        sy = int(section["Y"])
        palette, indices = decode_modern_section(section)
        if palette:
            result[sy] = (
                palette,
                np.asarray(indices, dtype=np.int32).copy(),
                {palette_state(entry): index for index, entry in enumerate(palette)},
            )
    return result


def get_state(decoded: dict[int, tuple[list, np.ndarray, dict[str, int]]], x: int, y: int,
              z: int) -> str:
    item = decoded.get(y // 16)
    if item is None:
        return "minecraft:air"
    palette, indices, _ = item
    index = (y & 15) * 256 + (z & 15) * 16 + (x & 15)
    return palette_state(palette[int(indices[index])])


def set_state(root: nbtlib.File,
              decoded: dict[int, tuple[list, np.ndarray, dict[str, int]]],
              x: int, y: int, z: int, state: str) -> bool:
    sy = y // 16
    item = decoded.get(sy)
    if item is None:
        raise RuntimeError(f"target misses section y={sy}")
    palette, indices, state_to_index = item
    index = (y & 15) * 256 + (z & 15) * 16 + (x & 15)
    current = palette_state(palette[int(indices[index])])
    if current == state:
        return False
    target_index = state_to_index.get(state)
    if target_index is None:
        from apply_s20_approved_semantic_repairs import parse_state
        target_index = len(palette)
        palette.append(parse_state(state))
        state_to_index[state] = target_index
    indices[index] = target_index
    return True


def flush_decoded(root: nbtlib.File,
                  decoded: dict[int, tuple[list, np.ndarray, dict[str, int]]]) -> None:
    sections = section_map(root)
    for sy, (palette, indices, _) in decoded.items():
        section = sections.get(sy)
        if section is None:
            raise RuntimeError(f"target section disappeared y={sy}")
        states = section.get("block_states")
        if states is None:
            states = nbtlib.Compound()
            section["block_states"] = states
        states["palette"] = nbtlib.List[nbtlib.Compound](palette)
        if len(palette) == 1:
            states.pop("data", None)
        else:
            states["data"] = encode_indices(indices, len(palette))


def ensure_decoded_section(root: nbtlib.File,
                           decoded: dict[int, tuple[list, np.ndarray, dict[str, int]]],
                           source_root: nbtlib.File, sy: int):
    item = decoded.get(sy)
    if item is not None:
        return item
    source_section = section_map(source_root).get(sy)
    if source_section is None:
        raise RuntimeError(f"source misses shaft section y={sy}")
    section = copy.deepcopy(source_section)
    section.pop("BlockLight", None)
    section.pop("SkyLight", None)
    air = nbtlib.Compound({"Name": nbtlib.String("minecraft:air")})
    section["block_states"] = nbtlib.Compound({
        "palette": nbtlib.List[nbtlib.Compound]([air]),
    })
    root.get("sections").append(section)
    item = ([air], np.zeros(4096, dtype=np.int32), {"minecraft:air": 0})
    decoded[sy] = item
    return item


def shift_entry(entry: nbtlib.Compound, dy: int) -> nbtlib.Compound:
    result = copy.deepcopy(entry)
    if result.get("y") is not None:
        result["y"] = nbtlib.Int(int(result["y"]) + dy)
    return result


def merge_shifted_entries(target: nbtlib.File, source: nbtlib.File, key: str,
                          columns: set[tuple[int, int]], min_y: int,
                          max_y: int, dy: int) -> int:
    selected = []
    for entry in source.get(key, []):
        x = entry.get("x")
        y = entry.get("y")
        z = entry.get("z")
        if x is None or y is None or z is None:
            continue
        if (int(x), int(z)) in columns and min_y <= int(y) <= max_y:
            selected.append(shift_entry(entry, dy))
    destination_min = min_y + dy
    destination_max = max_y + dy
    kept = []
    for entry in target.get(key, []):
        x = entry.get("x")
        y = entry.get("y")
        z = entry.get("z")
        if x is None or y is None or z is None:
            kept.append(copy.deepcopy(entry))
            continue
        inside = ((int(x), int(z)) in columns
                  and destination_min <= int(y) <= destination_max)
        if not inside:
            kept.append(copy.deepcopy(entry))
    if selected or key in target:
        target[key] = nbtlib.List[nbtlib.Compound](kept + selected)
    return len(selected)


def copy_surface_chunk(target: nbtlib.File, source: nbtlib.File,
                       chunk_x: int, chunk_z: int) -> dict[str, int]:
    source_decoded = decoded_sections(source)
    target_decoded = decoded_sections(target)
    first_authored = np.full(256, -1, dtype=np.int16)
    for source_y in range(SURFACE_SOURCE_MIN_Y, SURFACE_SOURCE_MAX_Y + 1):
        item = source_decoded.get(source_y // 16)
        if item is None:
            continue
        palette, indices, _ = item
        authored_palette = np.asarray(
            [not is_natural(palette_state(entry)) for entry in palette],
            dtype=np.bool_,
        )
        start = (source_y & 15) * 256
        layer = indices[start:start + 256]
        new = (first_authored < 0) & authored_palette[layer]
        first_authored[new] = source_y

    footprint = first_authored >= 0
    if not np.any(footprint):
        return {"columns": 0, "changed_voxels": 0, "block_entities": 0,
                "block_ticks": 0, "fluid_ticks": 0}

    columns = {
        (chunk_x * 16 + (index & 15), chunk_z * 16 + (index >> 4))
        for index in np.flatnonzero(footprint).tolist()
    }
    changed = 0

    def ensure_target_state(item, state: str) -> int:
        palette, _, state_to_index = item
        value = state_to_index.get(state)
        if value is None:
            from apply_s20_approved_semantic_repairs import parse_state
            value = len(palette)
            palette.append(parse_state(state))
            state_to_index[state] = value
        return value

    # Determine the original natural surface for all 256 columns at once.
    target_surface = np.full(256, -65, dtype=np.int16)
    unresolved = np.ones(256, dtype=np.bool_)
    empty_names = {"minecraft:air", "minecraft:cave_air",
                   "minecraft:void_air", "minecraft:water"}
    for y in range(SURFACE_DATUM_Y + 12, -65, -1):
        item = target_decoded.get(y // 16)
        if item is None:
            continue
        palette, indices, _ = item
        solid_palette = np.asarray(
            [state_name(palette_state(entry)) not in empty_names
             for entry in palette], dtype=np.bool_)
        start = (y & 15) * 256
        solid = solid_palette[indices[start:start + 256]]
        found = unresolved & solid
        target_surface[found] = y
        unresolved[found] = False
        if not np.any(unresolved & footprint):
            break

    # Grade only the actual authored footprint up to one block below datum.
    for y in range(-64, SURFACE_DATUM_Y):
        fill = footprint & (target_surface < y)
        if not np.any(fill):
            continue
        item = target_decoded.get(y // 16)
        if item is None:
            raise RuntimeError(f"target misses foundation section y={y // 16}")
        _, indices, _ = item
        start = (y & 15) * 256
        layer = indices[start:start + 256]
        dirt_index = ensure_target_state(item, "minecraft:dirt")
        changed += int(np.count_nonzero(fill & (layer != dirt_index)))
        layer[fill] = dirt_index

    # Copy each source horizontal layer in vector form.  Air is intentional:
    # above the first authored voxel it clears trees/terrain from interiors,
    # while columns outside the footprint are never touched.
    for source_y in range(SURFACE_SOURCE_MIN_Y, SURFACE_SOURCE_MAX_Y + 1):
        active = footprint & (first_authored <= source_y)
        if not np.any(active):
            continue
        source_item = source_decoded.get(source_y // 16)
        destination_y = source_y + SURFACE_DY
        target_item = target_decoded.get(destination_y // 16)
        if source_item is None or target_item is None:
            raise RuntimeError(
                f"missing section for surface layer {source_y}->{destination_y}")
        source_palette, source_indices, _ = source_item
        _, target_indices, _ = target_item
        source_start = (source_y & 15) * 256
        target_start = (destination_y & 15) * 256
        source_layer = source_indices[source_start:source_start + 256]
        target_layer = target_indices[target_start:target_start + 256]
        for source_index in np.unique(source_layer[active]).tolist():
            state = palette_state(source_palette[int(source_index)])
            target_index = ensure_target_state(target_item, state)
            mask = active & (source_layer == source_index)
            changed += int(np.count_nonzero(mask & (target_layer != target_index)))
            target_layer[mask] = target_index

    flush_decoded(target, target_decoded)
    column_set = columns
    block_entities = merge_shifted_entries(
        target, source, "block_entities", column_set,
        SURFACE_SOURCE_MIN_Y, SURFACE_SOURCE_MAX_Y, SURFACE_DY)
    block_ticks = merge_shifted_entries(
        target, source, "block_ticks", column_set,
        SURFACE_SOURCE_MIN_Y, SURFACE_SOURCE_MAX_Y, SURFACE_DY)
    fluid_ticks = merge_shifted_entries(
        target, source, "fluid_ticks", column_set,
        SURFACE_SOURCE_MIN_Y, SURFACE_SOURCE_MAX_Y, SURFACE_DY)
    target.pop("Heightmaps", None)
    target["isLightOn"] = nbtlib.Byte(0)
    return {
        "columns": len(columns),
        "changed_voxels": changed,
        "block_entities": block_entities,
        "block_ticks": block_ticks,
        "fluid_ticks": fluid_ticks,
    }


def shaft_for(x: int, z: int) -> ShaftBox | None:
    for box in SHAFT_BOXES:
        if box.x0 <= x <= box.x1 and box.z0 <= z <= box.z1:
            return box
    return None


def shaft_destination_y(box: ShaftBox, source_y: int) -> int:
    return source_y if source_y <= box.cutoff_y else source_y + SURFACE_DY


def copy_shaft_chunk(target: nbtlib.File, source: nbtlib.File,
                     chunk_x: int, chunk_z: int) -> dict[str, int]:
    source_decoded = decoded_sections(source)
    target_decoded = decoded_sections(target)
    masks: list[tuple[ShaftBox, np.ndarray]] = []
    for box in SHAFT_BOXES:
        mask = np.zeros(256, dtype=np.bool_)
        for local_z in range(16):
            z = chunk_z * 16 + local_z
            if not box.z0 <= z <= box.z1:
                continue
            for local_x in range(16):
                x = chunk_x * 16 + local_x
                if box.x0 <= x <= box.x1:
                    mask[local_z * 16 + local_x] = True
        if np.any(mask):
            masks.append((box, mask))
    if not masks:
        return {"columns": 0, "changed_voxels": 0, "block_entities": 0,
                "block_ticks": 0, "fluid_ticks": 0}

    def ensure_target_state(item, state: str) -> int:
        palette, _, state_to_index = item
        value = state_to_index.get(state)
        if value is None:
            from apply_s20_approved_semantic_repairs import parse_state
            value = len(palette)
            palette.append(parse_state(state))
            state_to_index[state] = value
        return value

    changed = 0
    for source_y in range(SHAFT_SOURCE_MIN_Y, SHAFT_SOURCE_MAX_Y + 1):
        source_item = source_decoded.get(source_y // 16)
        if source_item is None:
            # A missing source section is semantically all air.
            source_palette = [nbtlib.Compound({
                "Name": nbtlib.String("minecraft:air")})]
            source_indices = np.zeros(4096, dtype=np.int32)
        else:
            source_palette, source_indices, _ = source_item
        source_start = (source_y & 15) * 256
        source_layer = source_indices[source_start:source_start + 256]
        for box, mask in masks:
            destination_y = shaft_destination_y(box, source_y)
            target_item = ensure_decoded_section(
                target, target_decoded, source, destination_y // 16)
            _, target_indices, _ = target_item
            target_start = (destination_y & 15) * 256
            target_layer = target_indices[target_start:target_start + 256]
            for source_index in np.unique(source_layer[mask]).tolist():
                state = palette_state(source_palette[int(source_index)])
                target_index = ensure_target_state(target_item, state)
                selected = mask & (source_layer == source_index)
                changed += int(np.count_nonzero(
                    selected & (target_layer != target_index)))
                target_layer[selected] = target_index

    flush_decoded(target, target_decoded)
    source_columns = {
        (chunk_x * 16 + (index & 15), chunk_z * 16 + (index >> 4))
        for _, mask in masks for index in np.flatnonzero(mask).tolist()
    }

    def merge_shaft_entries(key: str) -> int:
        selected = []
        for entry in source.get(key, []):
            x, y, z = entry.get("x"), entry.get("y"), entry.get("z")
            if x is None or y is None or z is None:
                continue
            box = shaft_for(int(x), int(z))
            if box is None or not SHAFT_SOURCE_MIN_Y <= int(y) <= SHAFT_SOURCE_MAX_Y:
                continue
            result = copy.deepcopy(entry)
            result["y"] = nbtlib.Int(shaft_destination_y(box, int(y)))
            selected.append(result)
        kept = []
        for entry in target.get(key, []):
            x, y, z = entry.get("x"), entry.get("y"), entry.get("z")
            if x is None or y is None or z is None:
                kept.append(copy.deepcopy(entry))
                continue
            box = shaft_for(int(x), int(z))
            inside = (box is not None and SHAFT_SOURCE_MIN_Y <= int(y)
                      <= SHAFT_SOURCE_MAX_Y + SURFACE_DY)
            if not inside:
                kept.append(copy.deepcopy(entry))
        if selected or key in target:
            target[key] = nbtlib.List[nbtlib.Compound](kept + selected)
        return len(selected)

    block_entities = merge_shaft_entries("block_entities")
    block_ticks = merge_shaft_entries("block_ticks")
    fluid_ticks = merge_shaft_entries("fluid_ticks")
    target.pop("Heightmaps", None)
    target["isLightOn"] = nbtlib.Byte(0)
    return {
        "columns": len(source_columns),
        "changed_voxels": changed,
        "block_entities": block_entities,
        "block_ticks": block_ticks,
        "fluid_ticks": fluid_ticks,
    }


def backup_files(paths: list[Path], phase: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = phase.upper().replace("-", "_")
    backup = REPO / "backups" / f"SEELE_S22_PRE_{label}_{stamp}"
    rows: list[dict[str, str | int]] = []
    for path in paths:
        relative = path.relative_to(TARGET)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        rows.append({
            "path": relative.as_posix(),
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        })
    backup.mkdir(parents=True, exist_ok=True)
    with (backup / "SHA256_MANIFEST.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)
    return backup


def ensure_safe_worlds() -> None:
    if not (SOURCE / ".projectseele_s20_rebuild.json").exists():
        raise RuntimeError("source is not R28/S20 authority")
    if not (TARGET / ".projectseele_s22_coastal.json").exists():
        raise RuntimeError("target is not the S22 coastal world")
    if not (TARGET / ".projectseele_s22_migration_frozen.json").exists():
        raise RuntimeError("S22 migration freeze marker is missing")
    for save in (SOURCE, TARGET):
        lock = save / "session.lock"
        if lock.exists():
            try:
                with lock.open("r+b"):
                    pass
            except OSError as exc:
                raise RuntimeError(f"world appears open: {save.name}") from exc


def transplant_core(apply: bool) -> dict:
    ensure_safe_worlds()
    wanted = [ChunkAddress(cx, cz) for cx in CORE_CHUNK_X for cz in CORE_CHUNK_Z]
    grouped: dict[tuple[int, int], list[ChunkAddress]] = {}
    for address in wanted:
        grouped.setdefault(address.region, []).append(address)

    outputs: dict[Path, bytes] = {}
    totals = {"chunks": 0, "voxels": 0, "block_entities": 0,
              "block_ticks": 0, "fluid_ticks": 0}
    region_reports = []
    for (rx, rz), addresses in sorted(grouped.items()):
        source_path = region_path(SOURCE, "region", rx, rz)
        target_path = region_path(TARGET, "region", rx, rz)
        if not source_path.exists() or not target_path.exists():
            raise RuntimeError(f"missing region pair r.{rx}.{rz}.mca")
        source_timestamps, source_chunks = read_region(source_path)
        target_timestamps, target_chunks = read_region(target_path)
        del source_timestamps
        for address in addresses:
            source_blob = source_chunks[address.index]
            target_blob = target_chunks[address.index]
            if source_blob is None or target_blob is None:
                raise RuntimeError(f"missing chunk {address.x},{address.z}")
            source_root = parse_chunk(source_blob)
            target_root = parse_chunk(target_blob)
            if int(source_root.get("xPos", address.x)) != address.x \
                    or int(source_root.get("zPos", address.z)) != address.z:
                raise RuntimeError(f"source coordinate mismatch {address}")
            if int(target_root.get("xPos", address.x)) != address.x \
                    or int(target_root.get("zPos", address.z)) != address.z:
                raise RuntimeError(f"target coordinate mismatch {address}")
            counts = copy_core_chunk(target_root, source_root)
            target_chunks[address.index] = chunk_blob(target_root)
            totals["chunks"] += 1
            for key, value in counts.items():
                totals[key] += value
        content = build_region(target_timestamps, target_chunks)
        outputs[target_path] = content
        region_reports.append({
            "region": f"r.{rx}.{rz}.mca",
            "chunks": len(addresses),
            "before_sha256": sha256(target_path),
            "after_sha256": hashlib.sha256(content).hexdigest(),
        })

    backup = None
    if apply:
        backup = backup_files(list(outputs), "underground-transplant")
        for path, content in outputs.items():
            atomic_replace(path, content)
        for item in region_reports:
            path = TARGET / DIMENSION / "region" / item["region"]
            if sha256(path) != item["after_sha256"]:
                raise RuntimeError(f"post-write hash mismatch: {path.name}")

    report = {
        "phase": "underground-core",
        "applied": apply,
        "source": str(SOURCE),
        "target": str(TARGET),
        "block_box": [-64, -672, 96, 159, -273, 399],
        "totals": totals,
        "regions": region_reports,
        "backup": str(backup) if backup else None,
    }
    return report


def transplant_surface(apply: bool) -> dict:
    ensure_safe_worlds()
    target_region_dir = TARGET / DIMENSION / "region"
    outputs: dict[Path, bytes] = {}
    totals = {"chunks_scanned": 0, "chunks_changed": 0, "columns": 0,
              "changed_voxels": 0, "block_entities": 0,
              "block_ticks": 0, "fluid_ticks": 0}
    region_reports = []

    for target_path in sorted(target_region_dir.glob("r.*.*.mca")):
        if target_path.stat().st_size < HEADER_BYTES:
            continue
        _, raw_rx, raw_rz = target_path.stem.split(".")
        rx, rz = int(raw_rx), int(raw_rz)
        # The clean coastal seed was generated only around the selected site.
        # Remote regions are never inferred or created by this migrator.
        source_path = region_path(SOURCE, "region", rx, rz)
        if not source_path.exists():
            continue
        _, source_chunks = read_region(source_path)
        target_timestamps, target_chunks = read_region(target_path)
        changed_chunks = 0
        for index, target_blob in enumerate(target_chunks):
            if target_blob is None:
                continue
            source_blob = source_chunks[index]
            if source_blob is None:
                continue
            chunk_x = rx * 32 + index % 32
            chunk_z = rz * 32 + index // 32
            # Exclude any accidentally generated remote/test chunk.
            if not (-12 <= chunk_x <= 11 and 2 <= chunk_z <= 28):
                continue
            totals["chunks_scanned"] += 1
            source_root = parse_chunk(source_blob)
            target_root = parse_chunk(target_blob)
            counts = copy_surface_chunk(target_root, source_root, chunk_x, chunk_z)
            if not counts["columns"]:
                continue
            target_chunks[index] = chunk_blob(target_root)
            changed_chunks += 1
            totals["chunks_changed"] += 1
            for key, value in counts.items():
                totals[key] += value
        if changed_chunks:
            content = build_region(target_timestamps, target_chunks)
            outputs[target_path] = content
            region_reports.append({
                "region": target_path.name,
                "chunks": changed_chunks,
                "before_sha256": sha256(target_path),
                "after_sha256": hashlib.sha256(content).hexdigest(),
            })

    if not outputs:
        raise RuntimeError("no Tokyo-3 authored footprint found in generated target chunks")

    backup = None
    if apply:
        backup = backup_files(list(outputs), "surface-transplant")
        for path, content in outputs.items():
            atomic_replace(path, content)
        for item in region_reports:
            path = TARGET / DIMENSION / "region" / item["region"]
            if sha256(path) != item["after_sha256"]:
                raise RuntimeError(f"post-write hash mismatch: {path.name}")

    return {
        "phase": "surface-tokyo3",
        "applied": apply,
        "source_y": [SURFACE_SOURCE_MIN_Y, SURFACE_SOURCE_MAX_Y],
        "destination_y": [SURFACE_SOURCE_MIN_Y + SURFACE_DY,
                          SURFACE_SOURCE_MAX_Y + SURFACE_DY],
        "dy": SURFACE_DY,
        "totals": totals,
        "regions": region_reports,
        "backup": str(backup) if backup else None,
    }


def transplant_shafts(apply: bool) -> dict:
    ensure_safe_worlds()
    target_region_dir = TARGET / DIMENSION / "region"
    outputs: dict[Path, bytes] = {}
    totals = {"chunks_scanned": 0, "chunks_changed": 0, "columns": 0,
              "changed_voxels": 0, "block_entities": 0,
              "block_ticks": 0, "fluid_ticks": 0}
    region_reports = []
    for target_path in sorted(target_region_dir.glob("r.*.*.mca")):
        if target_path.stat().st_size < HEADER_BYTES:
            continue
        _, raw_rx, raw_rz = target_path.stem.split(".")
        rx, rz = int(raw_rx), int(raw_rz)
        source_path = region_path(SOURCE, "region", rx, rz)
        if not source_path.exists():
            continue
        _, source_chunks = read_region(source_path)
        target_timestamps, target_chunks = read_region(target_path)
        changed_chunks = 0
        for index, target_blob in enumerate(target_chunks):
            if target_blob is None or source_chunks[index] is None:
                continue
            chunk_x = rx * 32 + index % 32
            chunk_z = rz * 32 + index // 32
            if not any(box.x0 // 16 <= chunk_x <= box.x1 // 16
                       and box.z0 // 16 <= chunk_z <= box.z1 // 16
                       for box in SHAFT_BOXES):
                continue
            totals["chunks_scanned"] += 1
            source_root = parse_chunk(source_chunks[index])
            target_root = parse_chunk(target_blob)
            counts = copy_shaft_chunk(target_root, source_root, chunk_x, chunk_z)
            if not counts["columns"]:
                continue
            target_chunks[index] = chunk_blob(target_root)
            changed_chunks += 1
            totals["chunks_changed"] += 1
            for key, value in counts.items():
                totals[key] += value
        if changed_chunks:
            content = build_region(target_timestamps, target_chunks)
            outputs[target_path] = content
            region_reports.append({
                "region": target_path.name,
                "chunks": changed_chunks,
                "before_sha256": sha256(target_path),
                "after_sha256": hashlib.sha256(content).hexdigest(),
            })
    if not outputs:
        raise RuntimeError("no generated chunks intersect the four shaft boxes")
    backup = None
    if apply:
        backup = backup_files(list(outputs), "shaft-transplant")
        for path, content in outputs.items():
            atomic_replace(path, content)
        for item in region_reports:
            path = TARGET / DIMENSION / "region" / item["region"]
            if sha256(path) != item["after_sha256"]:
                raise RuntimeError(f"post-write hash mismatch: {path.name}")
    return {
        "phase": "physical-shafts",
        "applied": apply,
        "shafts": [box.__dict__ for box in SHAFT_BOXES],
        "vertical_rule": "source y<=cutoff unchanged; upper source shifted -12",
        "totals": totals,
        "regions": region_reports,
        "backup": str(backup) if backup else None,
    }


def shifted_entity(entity: nbtlib.Compound) -> nbtlib.Compound:
    result = copy.deepcopy(entity)
    position = result.get("Pos")
    if position is not None and len(position) >= 3 and float(position[1]) >= 80.0:
        position[1] = nbtlib.Double(float(position[1]) + SURFACE_DY)
    return result


def transplant_runtime(apply: bool) -> dict:
    ensure_safe_worlds()
    outputs: dict[Path, bytes] = {}
    entity_counts: dict[str, int] = {}
    entity_region_reports = []
    for rx, rz in ((-1, 0), (0, 0)):
        source_path = region_path(SOURCE, "entities", rx, rz)
        target_path = region_path(TARGET, "entities", rx, rz)
        if not source_path.exists() or source_path.stat().st_size < HEADER_BYTES:
            continue
        source_timestamps, source_chunks = read_region(source_path)
        target_chunks: list[bytes | None] = [None] * 1024
        selected_chunks = 0
        for index, blob in enumerate(source_chunks):
            if blob is None:
                continue
            root = parse_chunk(blob)
            selected = []
            for entity in root.get("Entities", []):
                entity_id = str(entity.get("id", ""))
                if entity_id not in RUNTIME_ENTITY_IDS:
                    continue
                position = entity.get("Pos", [])
                if len(position) < 3:
                    continue
                x, y, z = map(float, position[:3])
                if not (-64 <= x <= 159 and 96 <= z <= 399
                        and -672 <= y <= 239):
                    continue
                selected.append(shifted_entity(entity))
                entity_counts[entity_id] = entity_counts.get(entity_id, 0) + 1
            if not selected:
                continue
            root["Entities"] = nbtlib.List[nbtlib.Compound](selected)
            target_chunks[index] = chunk_blob(root)
            selected_chunks += 1
        if not selected_chunks:
            continue
        content = build_region(source_timestamps, target_chunks)
        outputs[target_path] = content
        entity_region_reports.append({
            "region": target_path.name,
            "chunks": selected_chunks,
            "after_sha256": hashlib.sha256(content).hexdigest(),
        })

    data_sources = [
        SOURCE / "data/projectseele_eva_fleet.dat",
        SOURCE / "data/projectseele_nerv_command_displays.dat",
    ]
    receipt_sources = sorted(SOURCE.glob(
        ".projectseele_approved_semantic_repairs*.json"))
    backup = None
    if apply:
        existing = [path for path in outputs if path.exists()]
        existing.extend(TARGET / "data" / path.name for path in data_sources
                        if (TARGET / "data" / path.name).exists())
        existing.extend(TARGET / path.name for path in receipt_sources
                        if (TARGET / path.name).exists())
        backup = backup_files(existing, "runtime-transplant") if existing else None
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_replace(path, content)
        (TARGET / "data").mkdir(parents=True, exist_ok=True)
        for source in data_sources:
            shutil.copy2(source, TARGET / "data" / source.name)
        for source in receipt_sources:
            shutil.copy2(source, TARGET / source.name)

    return {
        "phase": "runtime-authority",
        "applied": apply,
        "entity_counts": entity_counts,
        "entity_regions": entity_region_reports,
        "saved_data": [path.name for path in data_sources],
        "approval_receipts": [path.name for path in receipt_sources],
        "backup": str(backup) if backup else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase",
                        choices=("underground", "surface", "shafts", "runtime"),
                        default="underground")
    parser.add_argument("--apply", action="store_true",
                        help="write target regions after a localized backup")
    parser.add_argument("--report", type=Path,
                        default=REPO / "artifacts/s22_coastal_rebuild/underground_transplant.json")
    args = parser.parse_args()
    if args.phase == "underground":
        report = transplant_core(args.apply)
    elif args.phase == "surface":
        report = transplant_surface(args.apply)
    elif args.phase == "shafts":
        report = transplant_shafts(args.apply)
    else:
        report = transplant_runtime(args.apply)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
