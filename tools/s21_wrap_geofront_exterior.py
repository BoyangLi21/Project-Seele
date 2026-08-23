#!/usr/bin/env python3
"""Add two natural backfill layers immediately outside R28's GeoFront shell."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import time

import nbtlib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import (
    HEADER_BYTES, SECTOR_BYTES, atomic_replace, chunk_blob,
    decompress_chunk, encode_indices, palette_state, parse_state,
)
from inspect_map_assets import decode_modern_section
from query_blocks import dimension_dir


WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIMENSION = "projectseele:geofront"
PACKET = "S21-GEOFRONT-TWO-LAYER-NATURAL-BACKFILL"
CENTRE = (30, -332, 220)
INNER_RADIUS = 322
OUTER_RADIUS = 324
BACKFILL = "minecraft:dirt"
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
STRAY_SKYWEAVE = (94, -84, 220)


def region_coordinates() -> list[tuple[int, int]]:
    x0 = (CENTRE[0] - OUTER_RADIUS) >> 9
    x1 = (CENTRE[0] + OUTER_RADIUS) >> 9
    z0 = (CENTRE[2] - OUTER_RADIUS) >> 9
    z1 = (CENTRE[2] + OUTER_RADIUS) >> 9
    return [(x, z) for x in range(x0, x1 + 1)
            for z in range(z0, z1 + 1)]


def theoretical_target_count() -> int:
    total = 0
    inner_sq = INNER_RADIUS * INNER_RADIUS
    outer_sq = OUTER_RADIUS * OUTER_RADIUS
    for x in range(CENTRE[0] - OUTER_RADIUS + 1,
                   CENTRE[0] + OUTER_RADIUS):
        dx_sq = (x - CENTRE[0]) ** 2
        for z in range(CENTRE[2] - OUTER_RADIUS + 1,
                       CENTRE[2] + OUTER_RADIUS):
            horizontal = dx_sq + (z - CENTRE[2]) ** 2
            if horizontal >= outer_sq:
                continue
            minimum = (math.ceil(math.sqrt(max(0, inner_sq - horizontal)))
                       if horizontal < inner_sq else 0)
            maximum = math.ceil(math.sqrt(outer_sq - horizontal)) - 1
            total += (1 + 2 * maximum if minimum == 0
                      else 2 * (maximum - minimum + 1))
    return total


def transform_region(path: Path, write: bool) -> tuple[dict[str, int],
                                                        bytes | None]:
    source = path.read_bytes()
    parts = path.stem.split(".")
    region_x, region_z = int(parts[1]), int(parts[2])
    timestamps = source[SECTOR_BYTES:HEADER_BYTES]
    chunks: list[bytes | None] = [None] * 1024
    stats = defaultdict(int)
    inner_sq = INNER_RADIUS * INNER_RADIUS
    outer_sq = OUTER_RADIUS * OUTER_RADIUS

    for slot in range(1024):
        location = source[slot * 4:slot * 4 + 4]
        sector_offset = int.from_bytes(location[:3], "big")
        sector_count = location[3]
        if not sector_offset or not sector_count:
            continue
        byte_offset = sector_offset * SECTOR_BYTES
        length = struct.unpack(">I", source[byte_offset:byte_offset + 4])[0]
        compression = source[byte_offset + 4]
        original_blob = source[byte_offset:byte_offset + 4 + length]
        chunk_x = region_x * 32 + slot % 32
        chunk_z = region_z * 32 + slot // 32
        nearest_x = max(chunk_x * 16,
                        min(CENTRE[0], chunk_x * 16 + 15))
        nearest_z = max(chunk_z * 16,
                        min(CENTRE[2], chunk_z * 16 + 15))
        horizontal_min = ((nearest_x - CENTRE[0]) ** 2
                          + (nearest_z - CENTRE[2]) ** 2)
        if horizontal_min >= outer_sq:
            if write:
                chunks[slot] = original_blob
            continue

        payload = source[byte_offset + 5:byte_offset + 4 + length]
        root = nbtlib.File.parse(io.BytesIO(
            decompress_chunk(compression, payload)))
        chunk_changed = False
        for section in root.get("sections", []):
            section_y = int(section.get("Y", 0))
            base_y = section_y * 16
            nearest_y = max(base_y, min(CENTRE[1], base_y + 15))
            dx = nearest_x - CENTRE[0]
            dy = nearest_y - CENTRE[1]
            dz = nearest_z - CENTRE[2]
            if dx * dx + dy * dy + dz * dz >= outer_sq:
                continue
            palette, decoded = decode_modern_section(section)
            if not palette:
                continue
            indices = np.asarray(decoded, dtype=np.int32).copy()
            offsets = np.arange(4096, dtype=np.int32)
            xs = chunk_x * 16 + (offsets & 15)
            zs = chunk_z * 16 + ((offsets >> 4) & 15)
            ys = base_y + (offsets >> 8)
            radius_sq = ((xs - CENTRE[0]) ** 2
                         + (ys - CENTRE[1]) ** 2
                         + (zs - CENTRE[2]) ** 2)
            target = (radius_sq >= inner_sq) & (radius_sq < outer_sq)
            target_count = int(np.count_nonzero(target))
            states = [palette_state(entry) for entry in palette]
            stray_index = None
            stray_present = False
            if (chunk_x == STRAY_SKYWEAVE[0] >> 4
                    and chunk_z == STRAY_SKYWEAVE[2] >> 4
                    and section_y == STRAY_SKYWEAVE[1] >> 4):
                stray_index = (((STRAY_SKYWEAVE[1] & 15) << 8)
                               | ((STRAY_SKYWEAVE[2] & 15) << 4)
                               | (STRAY_SKYWEAVE[0] & 15))
                stray_present = (states[int(indices[stray_index])]
                                 == "projectseele:geofront_skyweave")
                if stray_present:
                    stats["offShellResidueWrites"] += 1
            if not target_count and not stray_present:
                continue
            stats["presentTargetVoxels"] += target_count
            air_indices = [i for i, state in enumerate(states)
                           if state.split("[", 1)[0] in AIR]
            dirt_indices = [i for i, state in enumerate(states)
                            if state.split("[", 1)[0] == BACKFILL]
            air_target = target & np.isin(indices, air_indices)
            dirt_target = target & np.isin(indices, dirt_indices)
            air_count = int(np.count_nonzero(air_target))
            stats["airWrites"] += air_count
            stats["existingBackfillVoxels"] += int(
                np.count_nonzero(dirt_target))
            stats["preservedAuthoredVoxels"] += (
                target_count - air_count - int(np.count_nonzero(dirt_target)))

            if not write or (not air_count and not stray_present):
                continue
            state_to_index = {state: i for i, state in enumerate(states)}
            if air_count:
                dirt = state_to_index.get(BACKFILL)
                if dirt is None:
                    dirt = len(palette)
                    palette.append(parse_state(BACKFILL))
                    state_to_index[BACKFILL] = dirt
                indices[air_target] = dirt
            if stray_present:
                air = state_to_index.get("minecraft:air")
                if air is None:
                    air = len(palette)
                    palette.append(parse_state("minecraft:air"))
                indices[stray_index] = air
            block_states = section["block_states"]
            block_states["palette"] = nbtlib.List[nbtlib.Compound](palette)
            if len(palette) == 1:
                block_states.pop("data", None)
            else:
                block_states["data"] = encode_indices(indices, len(palette))
            chunk_changed = True
        if write:
            if chunk_changed:
                root["isLightOn"] = nbtlib.Byte(0)
                chunks[slot] = chunk_blob(root)
            else:
                chunks[slot] = original_blob

    if not write:
        return dict(stats), None
    locations = bytearray(SECTOR_BYTES)
    body = bytearray()
    next_sector = 2
    for slot, blob in enumerate(chunks):
        if blob is None:
            continue
        sectors = math.ceil(len(blob) / SECTOR_BYTES)
        locations[slot * 4:slot * 4 + 3] = next_sector.to_bytes(3, "big")
        locations[slot * 4 + 3] = sectors
        body.extend(blob)
        body.extend(b"\x00" * (sectors * SECTOR_BYTES - len(blob)))
        next_sector += sectors
    return dict(stats), bytes(locations) + timestamps + bytes(body)


def survey() -> dict[str, int]:
    root = dimension_dir(WORLD, DIMENSION)
    total = defaultdict(int)
    for region_x, region_z in region_coordinates():
        path = root / "region" / f"r.{region_x}.{region_z}.mca"
        if not path.is_file():
            continue
        stats, _ = transform_region(path, False)
        for key, value in stats.items():
            total[key] += value
    total["theoreticalTargetVoxels"] = theoretical_target_count()
    total["unloadedTargetVoxels"] = (total["theoreticalTargetVoxels"]
                                     - total["presentTargetVoxels"])
    return dict(total)


def apply(preview: dict[str, int]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("artifacts") / f"s21_geofront_backfill_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    replaced: list[Path] = []
    hashes = {}
    try:
        for region_x, region_z in region_coordinates():
            path = root / "region" / f"r.{region_x}.{region_z}.mca"
            if not path.is_file():
                continue
            stats, content = transform_region(path, True)
            if not stats.get("airWrites", 0) \
                    and not stats.get("offShellResidueWrites", 0):
                continue
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            shutil.copy2(path, backup / path.name)
            atomic_replace(path, content)
            replaced.append(path)
        after = survey()
        if after.get("airWrites", 0) or after.get("offShellResidueWrites", 0):
            raise RuntimeError(f"backfill read-back incomplete: {after}")
    except Exception:
        for path in replaced:
            atomic_replace(path, (backup / path.name).read_bytes())
        raise
    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "radialBand": [INNER_RADIUS, OUTER_RADIUS],
        "block": BACKFILL,
        "preview": preview,
        "readBack": after,
        "changedRegions": len(replaced),
        "regionsBeforeSha256": hashes,
        "backup": str(backup.resolve()),
    }
    (backup / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    preview = survey()
    print(json.dumps(preview, indent=2))
    if args.apply:
        print(f"backup={apply(preview)}")


if __name__ == "__main__":
    main()
