#!/usr/bin/env python3
"""Transplant approved underground fabric without copying legacy terrain."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import shutil
import time

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import AIR, dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
TARGET = ROOT / "run/saves/SEELE_S24_COASTAL_REBUILD"
DIMENSION = "projectseele:geofront"
PACKET = "S24-COASTAL-UNDERGROUND-R01"

UPPER = (-64, -512, 96, 159, -273, 399)
DOGMA = (-32, -600, 220, 96, -520, 370)
DOGMA_SEED = (28, -560, 300)
SHAFTS = (
    ("terminal-dogma-lift", (8, -568, 249, 16, -314, 261), False),
    ("public-surface-lift", (126, -443, 269, 134, 96, 277), True),
    ("eva-00", (-29, -443, 203, 5, 96, 237), True),
    ("eva-01", (13, -443, 203, 47, 96, 237), True),
    ("eva-02", (55, -443, 203, 89, 96, 237), True),
)

NATURAL = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:tuff",
    "minecraft:calcite", "minecraft:dripstone_block", "minecraft:bedrock",
    "minecraft:dirt", "minecraft:grass_block", "minecraft:coarse_dirt",
    "minecraft:rooted_dirt", "minecraft:podzol", "minecraft:mud",
    "minecraft:clay", "minecraft:sand", "minecraft:red_sand",
    "minecraft:gravel", "minecraft:water", "minecraft:lava",
    "minecraft:snow", "minecraft:snow_block", "minecraft:ice",
    "minecraft:packed_ice", "minecraft:blue_ice",
    "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern",
    "minecraft:large_fern", "minecraft:dead_bush", "minecraft:vine",
    "minecraft:lily_pad", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp", "minecraft:kelp_plant",
    "minecraft:structure_void", "projectseele:geofront_skyweave",
}


def block_name(state: str) -> str:
    return state.split("[", 1)[0]


def natural(state: str) -> bool:
    value = block_name(state)
    return (value in NATURAL or value.endswith("_leaves")
            or value.endswith("_log") or value.endswith("_wood")
            or value.endswith("_sapling") or value.endswith("_ore"))


def load_transform(target: Path) -> tuple[int, int, int]:
    marker = json.loads((target / ".projectseele_s24_coastal.json")
                        .read_text(encoding="utf-8"))
    transform = tuple(map(int, marker["transform"]))
    if len(transform) != 3 or transform[0] % 16 or transform[2] % 16:
        raise RuntimeError(f"S24 X/Z transform must be chunk-aligned: {transform}")
    return transform


def add(changes: dict[tuple[int, int, int], Change],
        pos: tuple[int, int, int], before: str, after: str,
        reason: str) -> None:
    if before == after:
        return
    changes[pos] = Change(PACKET, *pos, before, after,
                          "human_authorized_coastal_migration", reason)


def plan_upper(source: Path, target: Path,
               changes: dict[tuple[int, int, int], Change],
               transform: tuple[int, int, int]) -> dict:
    dx, dy, dz = transform
    x0, y0, z0, x1, y1, z1 = UPPER
    copied = 0
    scanned_chunks = 0
    for chunk_z in range(z0 >> 4, (z1 >> 4) + 1):
        for chunk_x in range(x0 >> 4, (x1 >> 4) + 1):
            lo_x = max(x0, chunk_x * 16)
            hi_x = min(x1, chunk_x * 16 + 15)
            lo_z = max(z0, chunk_z * 16)
            hi_z = min(z1, chunk_z * 16 + 15)
            source_cells = read_box(source, DIMENSION,
                                    (lo_x, y0, lo_z), (hi_x, y1, hi_z), None)
            target_cells = read_box(target, DIMENSION,
                                    (lo_x + dx, y0 + dy, lo_z + dz),
                                    (hi_x + dx, y1 + dy, hi_z + dz), None)
            if not target_cells:
                raise RuntimeError(f"target upper chunk is not generated: "
                                   f"{(chunk_x, chunk_z)}")
            scanned_chunks += 1
            for pos, state in source_cells.items():
                if state in AIR or natural(state):
                    continue
                target_pos = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
                add(changes, target_pos,
                    target_cells.get(target_pos, "minecraft:air"), state,
                    "approved_upper_facility_solid")
                copied += 1
    return {"chunks": scanned_chunks, "selectedSolids": copied}


def dogma_mask(source: Path) -> tuple[set[tuple[int, int, int]], dict]:
    x0, y0, z0, x1, y1, z1 = DOGMA
    cells = read_box(source, DIMENSION, (x0, y0, z0), (x1, y1, z1), None)
    if cells.get(DOGMA_SEED, "minecraft:air") not in AIR:
        raise RuntimeError(f"Terminal Dogma air seed is blocked: {DOGMA_SEED}")
    interior = {DOGMA_SEED}
    queue = deque([DOGMA_SEED])
    touched_bounds = False
    while queue:
        x, y, z = queue.popleft()
        if x in (x0, x1) or y in (y0, y1) or z in (z0, z1):
            touched_bounds = True
        for neighbour in ((x - 1, y, z), (x + 1, y, z),
                          (x, y - 1, z), (x, y + 1, z),
                          (x, y, z - 1), (x, y, z + 1)):
            nx, ny, nz = neighbour
            if not (x0 <= nx <= x1 and y0 <= ny <= y1
                    and z0 <= nz <= z1) or neighbour in interior:
                continue
            if cells.get(neighbour, "minecraft:air") in AIR:
                interior.add(neighbour)
                queue.append(neighbour)
    selected = set(interior)
    for x, y, z in list(interior):
        for neighbour in ((x - 1, y, z), (x + 1, y, z),
                          (x, y - 1, z), (x, y + 1, z),
                          (x, y, z - 1), (x, y, z + 1)):
            if (x0 <= neighbour[0] <= x1 and y0 <= neighbour[1] <= y1
                    and z0 <= neighbour[2] <= z1):
                selected.add(neighbour)
    for pos, state in cells.items():
        if block_name(state).startswith("projectseele:lcl"):
            selected.add(pos)
    return selected, {
        "interiorAir": len(interior),
        "selectedWithBoundary": len(selected),
        "touchesSurveyBounds": touched_bounds,
    }


def plan_dogma(source: Path, target: Path,
               changes: dict[tuple[int, int, int], Change],
               transform: tuple[int, int, int]) -> dict:
    dx, dy, dz = transform
    selected, report = dogma_mask(source)
    x0, y0, z0, x1, y1, z1 = DOGMA
    source_cells = read_box(source, DIMENSION, (x0, y0, z0), (x1, y1, z1), None)
    target_cells = read_box(target, DIMENSION,
                            (x0 + dx, y0 + dy, z0 + dz),
                            (x1 + dx, y1 + dy, z1 + dz), None)
    if not target_cells:
        raise RuntimeError("target Terminal Dogma chunks are not generated")
    for pos in selected:
        target_pos = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
        add(changes, target_pos,
            target_cells.get(target_pos, "minecraft:air"),
            source_cells.get(pos, "minecraft:air"),
            "terminal_dogma_connected_interior")
    return report


def plan_shafts(source: Path, target: Path,
                changes: dict[tuple[int, int, int], Change],
                transform: tuple[int, int, int]) -> dict:
    dx, dy, dz = transform
    report = {}
    for name, bounds, _reconcile_surface in SHAFTS:
        x0, y0, z0, x1, y1, z1 = bounds
        source_cells = read_box(source, DIMENSION,
                                (x0, y0, z0), (x1, y1, z1), None)
        target_cells = read_box(target, DIMENSION,
                                (x0 + dx, y0 + dy, z0 + dz),
                                (x1 + dx, y1 + dy, z1 + dz), None)
        if not target_cells:
            raise RuntimeError(f"target shaft chunks are not generated: {name}")
        selected = 0
        for source_y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    source_pos = (x, source_y, z)
                    target_pos = (x + dx, source_y + dy, z + dz)
                    add(changes, target_pos,
                        target_cells.get(target_pos, "minecraft:air"),
                        source_cells.get(source_pos, "minecraft:air"),
                        f"exact_{name}_shaft")
                    selected += 1
        report[name] = {"sourceBounds": bounds,
                        "transform": transform,
                        "selectedVoxels": selected}
    return report


def apply_all(target: Path, changes: list[Change], artifact: Path) -> list[dict]:
    root = dimension_dir(target, DIMENSION)
    by_region: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        by_region[(change.x >> 9, change.z >> 9)].append(change)
    backups = artifact / "region_before"
    backups.mkdir(parents=True, exist_ok=False)
    originals: dict[Path, bytes] = {}
    outputs = []
    try:
        for (rx, rz), selected in sorted(by_region.items()):
            path = root / "region" / f"r.{rx}.{rz}.mca"
            if not path.is_file():
                raise FileNotFoundError(f"target region is not generated: {path}")
            before = path.read_bytes()
            originals[path] = before
            shutil.copy2(path, backups / path.name)
            grouped: dict[tuple[int, int], list[Change]] = defaultdict(list)
            for change in selected:
                grouped[(change.x >> 4, change.z >> 4)].append(change)
            atomic_replace(path, rewrite_region(path, grouped))
            outputs.append({
                "region": path.name,
                "changes": len(selected),
                "beforeSha256": hashlib.sha256(before).hexdigest(),
                "afterSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    except Exception:
        for path, content in originals.items():
            atomic_replace(path, content)
        raise
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--phase", choices=("upper", "dogma", "shafts", "all"),
                        default="all")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    target = args.target.resolve()
    if not (target / ".projectseele_s24_coastal.json").is_file():
        raise RuntimeError("target is not an S24 coastal migration save")
    transform = load_transform(target)
    changes: dict[tuple[int, int, int], Change] = {}
    phases = {}
    if args.phase in ("upper", "all"):
        phases["upper"] = plan_upper(source, target, changes, transform)
    if args.phase in ("dogma", "all"):
        phases["dogma"] = plan_dogma(source, target, changes, transform)
    if args.phase in ("shafts", "all"):
        phases["shafts"] = plan_shafts(source, target, changes, transform)
    ordered = sorted(changes.values(), key=lambda item: (item.y, item.z, item.x))
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s24_underground_transplant_{stamp}"
    artifact.mkdir(parents=True, exist_ok=False)
    regions = apply_all(target, ordered, artifact) if args.apply else []
    receipt = {
        "schema": 1,
        "packet": PACKET,
        "applied": args.apply,
        "source": str(source),
        "target": str(target),
        "transform": transform,
        "phase": args.phase,
        "changes": len(ordered),
        "reasons": dict(Counter(change.reason for change in ordered)),
        "phaseReports": phases,
        "regions": regions,
        "rollback": "restore every file under region_before",
    }
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(artifact.resolve()), **receipt}, indent=2))


if __name__ == "__main__":
    main()
