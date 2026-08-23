#!/usr/bin/env python3
"""Backfill the buried lower GeoFront hemisphere without touching facilities.

The visible parkland and NERV plant end above ``FILL_TOP_Y``.  Evangelion's
GeoFront is a buried cavity rather than a second empty world, so air below
that datum is replaced with natural strata.  Terminal Dogma, both known
Dogma routes, Lilith's chamber and their lift shafts are explicit keep-air
volumes and are never inspected as candidates.

This script edits loaded chunk sections directly.  It backs up every changed
region, writes atomically, and performs a complete read-back survey before it
reports success.
"""

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


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S21-GEOFRONT-BURIED-LOWER-EARTH-R01"

CENTRE = (30, -332, 220)
FILL_RADIUS = 318
FILL_TOP_Y = -467
MIN_Y = -672
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}

# Inclusive XYZ boxes.  These are deliberately larger than the measured
# constructed components: keeping surrounding air is part of preserving a
# room, a lift and its approach.  The v2 boxes are included even when their
# chunks have not yet been commissioned in this rescue save.
PROTECTED_BOXES = (
    # Measured legacy Terminal Dogma, its chamber and vertical access.
    (-14, -624, 244, 92, -453, 348, "legacy_terminal_dogma"),
    # FacilitySchemaV2 DOGMA_LIFT_SHAFT plus a four-block service margin.
    (50, -640, 452, 74, -380, 484, "dogma_lift_shaft_v2"),
    # FacilitySchemaV2 DOGMA_SPINE and the complete processional route.
    (-16, -664, 474, 116, -512, 622, "dogma_spine_v2"),
    # FacilitySchemaV2 LILITH_CHAMBER, including its LCL containment shell.
    (-88, -672, 610, 148, -568, 846, "lilith_chamber_v2"),
    # The third exact deep-authored component beneath the west plant.
    (-40, -474, 298, -20, -454, 318, "west_deep_authored_component"),
)


def region_coordinates() -> list[tuple[int, int]]:
    x0 = (CENTRE[0] - FILL_RADIUS) >> 9
    x1 = (CENTRE[0] + FILL_RADIUS) >> 9
    z0 = (CENTRE[2] - FILL_RADIUS) >> 9
    z1 = (CENTRE[2] + FILL_RADIUS) >> 9
    return [(rx, rz) for rx in range(x0, x1 + 1)
            for rz in range(z0, z1 + 1)]


def protected_mask(xs: np.ndarray, ys: np.ndarray,
                   zs: np.ndarray) -> tuple[np.ndarray, dict[str, int]]:
    mask = np.zeros(xs.shape, dtype=bool)
    counts: dict[str, int] = {}
    for x0, y0, z0, x1, y1, z1, name in PROTECTED_BOXES:
        current = ((xs >= x0) & (xs <= x1)
                   & (ys >= y0) & (ys <= y1)
                   & (zs >= z0) & (zs <= z1))
        counts[name] = int(np.count_nonzero(current))
        mask |= current
    return mask, counts


def material_for_y(y: int) -> str:
    # Natural, quiet strata: no block entities, ticks or lighting work.
    if y <= -576:
        return "minecraft:deepslate"
    if y <= -512:
        return "minecraft:tuff"
    return "minecraft:stone"


def transform_region(path: Path, write: bool) -> tuple[dict[str, object],
                                                        bytes | None]:
    source = path.read_bytes()
    parts = path.stem.split(".")
    region_x, region_z = int(parts[1]), int(parts[2])
    timestamps = source[SECTOR_BYTES:HEADER_BYTES]
    chunks: list[bytes | None] = [None] * 1024
    stats: defaultdict[str, int] = defaultdict(int)
    per_material: defaultdict[str, int] = defaultdict(int)
    radius_sq = FILL_RADIUS * FILL_RADIUS

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
        if ((nearest_x - CENTRE[0]) ** 2
                + (nearest_z - CENTRE[2]) ** 2 >= radius_sq):
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
            if base_y > FILL_TOP_Y or base_y + 15 < MIN_Y:
                continue
            palette, decoded = decode_modern_section(section)
            if not palette:
                continue
            indices = np.asarray(decoded, dtype=np.int32).copy()
            offsets = np.arange(4096, dtype=np.int32)
            xs = chunk_x * 16 + (offsets & 15)
            zs = chunk_z * 16 + ((offsets >> 4) & 15)
            ys = base_y + (offsets >> 8)
            geometric = (((xs - CENTRE[0]) ** 2
                          + (ys - CENTRE[1]) ** 2
                          + (zs - CENTRE[2]) ** 2 <= radius_sq)
                         & (ys <= FILL_TOP_Y) & (ys >= MIN_Y))
            if not np.any(geometric):
                continue

            protected, _ = protected_mask(xs, ys, zs)
            states = [palette_state(entry) for entry in palette]
            air_indices = [index for index, state in enumerate(states)
                           if state.split("[", 1)[0] in AIR]
            air = np.isin(indices, air_indices)
            target = geometric & air & ~protected
            target_count = int(np.count_nonzero(target))
            stats["geometricVoxels"] += int(np.count_nonzero(geometric))
            stats["airCandidates"] += int(
                np.count_nonzero(geometric & air))
            stats["protectedAirVoxels"] += int(
                np.count_nonzero(geometric & air & protected))
            if not target_count:
                continue

            stats["airWrites"] += target_count
            if not write:
                # Count strata without materialising three full masks when
                # this is only a proposal survey.
                for y in np.unique(ys[target]):
                    count = int(np.count_nonzero(target & (ys == y)))
                    per_material[material_for_y(int(y))] += count
                continue

            state_to_index = {state: i for i, state in enumerate(states)}
            for y in np.unique(ys[target]):
                state = material_for_y(int(y))
                palette_index = state_to_index.get(state)
                if palette_index is None:
                    palette_index = len(palette)
                    palette.append(parse_state(state))
                    state_to_index[state] = palette_index
                layer_mask = target & (ys == y)
                indices[layer_mask] = palette_index
                per_material[state] += int(np.count_nonzero(layer_mask))

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

    result: dict[str, object] = dict(stats)
    result["byMaterial"] = dict(sorted(per_material.items()))
    if not write:
        return result, None

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
    return result, bytes(locations) + timestamps + bytes(body)


def survey() -> dict[str, object]:
    root = dimension_dir(WORLD, DIMENSION)
    totals: defaultdict[str, int] = defaultdict(int)
    materials: defaultdict[str, int] = defaultdict(int)
    for region_x, region_z in region_coordinates():
        path = root / "region" / f"r.{region_x}.{region_z}.mca"
        if not path.is_file():
            continue
        stats, _ = transform_region(path, False)
        for key, value in stats.items():
            if key == "byMaterial":
                for material, count in value.items():
                    materials[material] += int(count)
            else:
                totals[key] += int(value)
    result: dict[str, object] = dict(totals)
    result["byMaterial"] = dict(sorted(materials.items()))
    result["protectedBoxes"] = [list(box) for box in PROTECTED_BOXES]
    return result


def apply(preview: dict[str, object]) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = ROOT / "artifacts" / f"s21_lower_earth_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    replaced: list[Path] = []
    hashes: dict[str, str] = {}
    try:
        for region_x, region_z in region_coordinates():
            path = root / "region" / f"r.{region_x}.{region_z}.mca"
            if not path.is_file():
                continue
            stats, content = transform_region(path, True)
            if not int(stats.get("airWrites", 0)):
                continue
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            shutil.copy2(path, backup / path.name)
            atomic_replace(path, content)
            replaced.append(path)
        after = survey()
        if int(after.get("airWrites", 0)) != 0:
            raise RuntimeError(f"lower-earth read-back incomplete: {after}")
    except Exception:
        for path in replaced:
            atomic_replace(path, (backup / path.name).read_bytes())
        raise

    receipt = {
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "sphere": {"centre": list(CENTRE), "radius": FILL_RADIUS,
                   "topY": FILL_TOP_Y, "minY": MIN_Y},
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
