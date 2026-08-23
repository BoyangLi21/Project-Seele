#!/usr/bin/env python3
"""Copy approved block entities after S24 block-state migration."""

from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import time

import nbtlib

from apply_s20_approved_semantic_repairs import atomic_replace
from query_blocks import iter_block_entities
from transplant_s22_authority import (
    ChunkAddress,
    build_region,
    chunk_blob,
    parse_chunk,
    read_region,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
TARGET = ROOT / "run/saves/SEELE_S24_COASTAL_REBUILD"
DIMENSION = "projectseele:geofront"
DIMENSION_PATH = Path("dimensions/projectseele/geofront")
MASK_PATH = ROOT / "artifacts/s24_source_inventory/surface_dominant_mask.png"
SURFACE_BOUNDS = (-320, 80, -120, 380, 220, 560)
UPPER_BOUNDS = (-64, -512, 96, 159, -273, 399)
DOGMA_BOUNDS = (-32, -600, 220, 96, -520, 370)
SHAFT_BOUNDS = (
    (8, -568, 249, 16, -314, 261),
    (126, -443, 269, 134, 96, 277),
    (-29, -443, 203, 5, 96, 237),
    (13, -443, 203, 47, 96, 237),
    (55, -443, 203, 89, 96, 237),
)


def inside(pos: tuple[int, int, int], bounds: tuple[int, ...]) -> bool:
    x, y, z = pos
    x0, y0, z0, x1, y1, z1 = bounds
    return x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1


def load_surface_mask() -> set[tuple[int, int]]:
    from PIL import Image
    image = Image.open(MASK_PATH).convert("1")
    return {(-320 + x, -120 + z)
            for z in range(image.height) for x in range(image.width)
            if image.getpixel((x, z))}


def shifted(entry: nbtlib.Compound,
            transform: tuple[int, int, int]) -> nbtlib.Compound:
    dx, dy, dz = transform
    result = copy.deepcopy(entry)
    result["x"] = nbtlib.Int(int(result["x"]) + dx)
    result["y"] = nbtlib.Int(int(result["y"]) + dy)
    result["z"] = nbtlib.Int(int(result["z"]) + dz)
    data = result.get("data")
    if data is not None:
        for key, delta in (("controllerX", dx), ("controllerY", dy),
                           ("controllerZ", dz)):
            if data.get(key) is not None:
                data[key] = nbtlib.Int(int(data[key]) + delta)
    return result


def collect(source: Path, transform: tuple[int, int, int]
            ) -> dict[tuple[int, int, int], nbtlib.Compound]:
    dx, dy, dz = transform
    surface_mask = load_surface_mask()
    selected: dict[tuple[int, int, int], nbtlib.Compound] = {}
    bounds = (-320, -600, -120, 380, 220, 560)
    for pos, entry in iter_block_entities(
            source, DIMENSION,
            (bounds[0], bounds[1], bounds[2]),
            (bounds[3], bounds[4], bounds[5])):
        destination = None
        value = None
        if (inside(pos, SURFACE_BOUNDS)
                and (pos[0], pos[2]) in surface_mask):
            destination = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
            value = shifted(entry, transform)
        elif (inside(pos, UPPER_BOUNDS) or inside(pos, DOGMA_BOUNDS)
              or any(inside(pos, box) for box in SHAFT_BOUNDS)):
            destination = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
            value = shifted(entry, transform)
        if destination is not None and value is not None:
            value["x"] = nbtlib.Int(destination[0])
            value["y"] = nbtlib.Int(destination[1])
            value["z"] = nbtlib.Int(destination[2])
            selected[destination] = value
    return selected


def entry_pos(entry: nbtlib.Compound) -> tuple[int, int, int] | None:
    if not all(key in entry for key in ("x", "y", "z")):
        return None
    return int(entry["x"]), int(entry["y"]), int(entry["z"])


def apply(target: Path,
          selected: dict[tuple[int, int, int], nbtlib.Compound],
          artifact: Path) -> list[dict]:
    by_region: dict[tuple[int, int], dict[tuple[int, int], dict]] = defaultdict(
        lambda: defaultdict(dict))
    for pos, entry in selected.items():
        chunk = (pos[0] >> 4, pos[2] >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk][pos] = entry
    backup_root = artifact / "region_before"
    backup_root.mkdir(parents=True, exist_ok=False)
    reports = []
    originals: dict[Path, bytes] = {}
    try:
        for (rx, rz), chunks_to_write in sorted(by_region.items()):
            path = target / DIMENSION_PATH / "region" / f"r.{rx}.{rz}.mca"
            if not path.is_file():
                raise FileNotFoundError(f"target region is not generated: {path}")
            before = path.read_bytes()
            originals[path] = before
            shutil.copy2(path, backup_root / path.name)
            timestamps, chunks = read_region(path)
            changed_chunks = 0
            for (chunk_x, chunk_z), entries in chunks_to_write.items():
                address = ChunkAddress(chunk_x, chunk_z)
                blob = chunks[address.index]
                if blob is None:
                    raise RuntimeError(f"target chunk is not generated: "
                                       f"{(chunk_x, chunk_z)}")
                root = parse_chunk(blob)
                kept = [copy.deepcopy(entry)
                        for entry in root.get("block_entities", [])
                        if entry_pos(entry) not in entries]
                root["block_entities"] = nbtlib.List[nbtlib.Compound](
                    kept + [copy.deepcopy(entry) for entry in entries.values()])
                chunks[address.index] = chunk_blob(root)
                changed_chunks += 1
            atomic_replace(path, build_region(timestamps, chunks))
            reports.append({
                "region": path.name,
                "chunks": changed_chunks,
                "entries": sum(len(value) for value in chunks_to_write.values()),
                "beforeSha256": hashlib.sha256(before).hexdigest(),
                "afterSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    except Exception:
        for path, content in originals.items():
            atomic_replace(path, content)
        raise
    return reports


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    target = args.target.resolve()
    marker = json.loads((target / ".projectseele_s24_coastal.json")
                        .read_text(encoding="utf-8"))
    transform = tuple(map(int, marker["transform"]))
    selected = collect(source, transform)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s24_block_entities_{stamp}"
    artifact.mkdir(parents=True, exist_ok=False)
    regions = apply(target, selected, artifact) if args.apply else []
    receipt = {
        "schema": 1,
        "applied": args.apply,
        "source": str(source),
        "target": str(target),
        "transform": transform,
        "entries": len(selected),
        "ids": dict(Counter(str(entry.get("id", "?"))
                            for entry in selected.values())),
        "regions": regions,
        "rollback": "restore every file under region_before",
    }
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(artifact.resolve()), **receipt}, indent=2))


if __name__ == "__main__":
    main()
