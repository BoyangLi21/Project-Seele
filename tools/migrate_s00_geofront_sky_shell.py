#!/usr/bin/env python3
"""Replace the legacy Ars GeoFront sky shell with a non-ticking rescue shell."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import time
import zlib

import nbtlib


SOURCE_BLOCK = "ars_nouveau:sky_block"
REPLACEMENT_BLOCK = "minecraft:cyan_terracotta"
MIGRATION_VERSION = 1
SECTOR_BYTES = 4096
HEADER_BYTES = SECTOR_BYTES * 2


def decompress_chunk(compression: int, payload: bytes) -> bytes:
    if compression == 1:
        return gzip.decompress(payload)
    if compression == 2:
        return zlib.decompress(payload)
    if compression == 3:
        return payload
    raise ValueError(f"unsupported region compression {compression}")


def chunk_blob(root: nbtlib.File) -> bytes:
    output = io.BytesIO()
    root.write(output)
    payload = zlib.compress(output.getvalue(), level=6)
    length = len(payload) + 1
    return struct.pack(">I", length) + b"\x02" + payload


def migrate_chunk(root: nbtlib.File) -> tuple[int, int]:
    replaced_sections = 0
    for section in root.get("sections", []):
        block_states = section.get("block_states")
        if block_states is None:
            continue
        palette = block_states.get("palette", [])
        names = [str(entry.get("Name", "")) for entry in palette]
        if SOURCE_BLOCK not in names:
            continue
        if REPLACEMENT_BLOCK in names:
            raise ValueError(
                "source and replacement share one palette; refusing an "
                "ambiguous palette-index rewrite"
            )
        for entry in palette:
            if str(entry.get("Name", "")) == SOURCE_BLOCK:
                entry["Name"] = nbtlib.String(REPLACEMENT_BLOCK)
                replaced_sections += 1

    block_entities = root.get("block_entities")
    removed_entities = 0
    if block_entities is not None:
        retained = [
            block_entity for block_entity in block_entities
            if str(block_entity.get("id", "")) != SOURCE_BLOCK
        ]
        removed_entities = len(block_entities) - len(retained)
        if removed_entities:
            block_entities[:] = retained
    return replaced_sections, removed_entities


def rewrite_region(path: Path) -> tuple[bytes | None, int, int, int]:
    source = path.read_bytes()
    if len(source) < HEADER_BYTES:
        raise ValueError(f"truncated region header: {path}")

    timestamps = source[SECTOR_BYTES:HEADER_BYTES]
    chunks: list[bytes | None] = [None] * 1024
    changed_chunks = 0
    replaced_sections = 0
    removed_entities = 0

    for index in range(1024):
        location = source[index * 4:index * 4 + 4]
        sector_offset = int.from_bytes(location[:3], "big")
        sector_count = location[3]
        if sector_offset == 0 or sector_count == 0:
            continue
        byte_offset = sector_offset * SECTOR_BYTES
        if byte_offset + 5 > len(source):
            raise ValueError(f"chunk {index} points beyond {path.name}")
        length = struct.unpack(
            ">I", source[byte_offset:byte_offset + 4]
        )[0]
        if length <= 1 or length + 4 > sector_count * SECTOR_BYTES:
            raise ValueError(f"invalid chunk length at {path.name}:{index}")
        compression = source[byte_offset + 4]
        if compression & 0x80:
            raise ValueError(
                f"external chunk streams are unsupported at {path.name}:{index}"
            )
        original_blob = source[byte_offset:byte_offset + 4 + length]
        payload = source[byte_offset + 5:byte_offset + 4 + length]
        root = nbtlib.File.parse(io.BytesIO(
            decompress_chunk(compression, payload)
        ))
        section_delta, entity_delta = migrate_chunk(root)
        if section_delta or entity_delta:
            chunks[index] = chunk_blob(root)
            changed_chunks += 1
            replaced_sections += section_delta
            removed_entities += entity_delta
        else:
            chunks[index] = original_blob

    if changed_chunks == 0:
        return None, 0, 0, 0

    locations = bytearray(SECTOR_BYTES)
    body = bytearray()
    next_sector = 2
    for index, blob in enumerate(chunks):
        if blob is None:
            continue
        sectors = math.ceil(len(blob) / SECTOR_BYTES)
        if sectors > 255 or next_sector >= 1 << 24:
            raise ValueError(f"region allocation overflow in {path.name}")
        locations[index * 4:index * 4 + 3] = next_sector.to_bytes(3, "big")
        locations[index * 4 + 3] = sectors
        body.extend(blob)
        body.extend(b"\x00" * (sectors * SECTOR_BYTES - len(blob)))
        next_sector += sectors
    return bytes(locations) + timestamps + bytes(body), changed_chunks, \
        replaced_sections, removed_entities


def atomic_replace(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".s00.tmp")
    with temporary.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def migrate(save: Path, backup_root: Path) -> dict[str, object]:
    region_dir = save / "dimensions" / "projectseele" / "geofront" / "region"
    if not region_dir.is_dir():
        return {
            "version": MIGRATION_VERSION,
            "status": "dimension-not-generated",
            "regions": 0,
            "chunks": 0,
            "paletteSections": 0,
            "removedBlockEntities": 0,
        }

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = backup_root / (
        f"{save.name}-s00-sky-shell-{timestamp}"
    )
    changed_regions = 0
    changed_chunks = 0
    replaced_sections = 0
    removed_entities = 0

    for region_path in sorted(region_dir.glob("r.*.*.mca")):
        rewritten, chunk_delta, section_delta, entity_delta = \
            rewrite_region(region_path)
        if rewritten is None:
            continue
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(region_path, backup_dir / region_path.name)
        atomic_replace(region_path, rewritten)
        changed_regions += 1
        changed_chunks += chunk_delta
        replaced_sections += section_delta
        removed_entities += entity_delta
        print(
            f"migrated {region_path.name}: chunks={chunk_delta} "
            f"paletteSections={section_delta} "
            f"removedBlockEntities={entity_delta}"
        )

    return {
        "version": MIGRATION_VERSION,
        "status": "complete",
        "sourceBlock": SOURCE_BLOCK,
        "replacementBlock": REPLACEMENT_BLOCK,
        "regions": changed_regions,
        "chunks": changed_chunks,
        "paletteSections": replaced_sections,
        "removedBlockEntities": removed_entities,
        "backup": str(backup_dir) if changed_regions else None,
        "completedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--if-needed", action="store_true")
    args = parser.parse_args()

    save = args.save.resolve()
    marker = save / "projectseele-s00-sky-shell-v1.json"
    if args.if_needed and marker.is_file():
        previous = json.loads(marker.read_text(encoding="utf-8"))
        if previous.get("version") == MIGRATION_VERSION:
            print(
                "Legacy GeoFront shell migration already complete: "
                f"removedBlockEntities="
                f"{previous.get('removedBlockEntities', 0)}"
            )
            return

    result = migrate(save, args.backup_root.resolve())
    marker.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(
        "Legacy GeoFront shell migration complete: "
        f"regions={result['regions']} chunks={result['chunks']} "
        f"paletteSections={result['paletteSections']} "
        f"removedBlockEntities={result['removedBlockEntities']} "
        f"replacement={REPLACEMENT_BLOCK}"
    )


if __name__ == "__main__":
    main()
