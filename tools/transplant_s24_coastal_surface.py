#!/usr/bin/env python3
"""Fit the approved Tokyo-3 component into fresh coastal terrain."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import shutil
import time

from PIL import Image

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import AIR, dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
TARGET = ROOT / "run/saves/SEELE_S24_COASTAL_REBUILD"
MASK_PATH = ROOT / "artifacts/s24_source_inventory/surface_dominant_mask.png"
DIMENSION = "projectseele:geofront"
PACKET = "S24-COASTAL-TOKYO3-SURFACE-R01"
MASK_X0 = -320
MASK_Z0 = -120
SOURCE_BASE_Y = 80
SOURCE_TOP_Y = 220
BLEND_RADIUS = 128
TARGET_SCAN_MIN_Y = -64
TARGET_SCAN_MAX_Y = 220

FLUIDS = {"minecraft:water", "minecraft:lava"}
NON_GROUND = AIR | FLUIDS | {
    "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern",
    "minecraft:large_fern", "minecraft:dead_bush", "minecraft:vine",
    "minecraft:snow", "minecraft:lily_pad", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp", "minecraft:kelp_plant",
}


def block_name(state: str) -> str:
    return state.split("[", 1)[0]


def ground_candidate(state: str) -> bool:
    value = block_name(state)
    return (value not in NON_GROUND and not value.endswith("_leaves")
            and not value.endswith("_log") and not value.endswith("_wood")
            and not value.endswith("_sapling"))


def load_columns() -> tuple[set[tuple[int, int]], dict[tuple[int, int], int]]:
    image = Image.open(MASK_PATH).convert("1")
    selected = {
        (MASK_X0 + x, MASK_Z0 + z)
        for z in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, z))
    }
    if len(selected) != 207048:
        raise RuntimeError(f"dominant Tokyo-3 mask changed: {len(selected)} columns")
    minimum_x = min(x for x, _ in selected) - BLEND_RADIUS
    maximum_x = max(x for x, _ in selected) + BLEND_RADIUS
    minimum_z = min(z for _, z in selected) - BLEND_RADIUS
    maximum_z = max(z for _, z in selected) + BLEND_RADIUS
    distance: dict[tuple[int, int], int] = {cell: 0 for cell in selected}
    queue = deque(selected)
    while queue:
        x, z = queue.popleft()
        current = distance[(x, z)]
        if current >= BLEND_RADIUS:
            continue
        for neighbour in ((x - 1, z), (x + 1, z),
                          (x, z - 1), (x, z + 1)):
            nx, nz = neighbour
            if not (minimum_x <= nx <= maximum_x
                    and minimum_z <= nz <= maximum_z):
                continue
            if neighbour not in distance:
                distance[neighbour] = current + 1
                queue.append(neighbour)
    return selected, distance


def terrain_top(cells: dict[tuple[int, int, int], str], x: int, z: int) -> int:
    for y in range(128, TARGET_SCAN_MIN_Y - 1, -1):
        if ground_candidate(cells.get((x, y, z), "minecraft:air")):
            return y
    raise RuntimeError(f"fresh terrain has no ground at {(x, z)}")


def ocean_column(cells: dict[tuple[int, int, int], str], x: int, z: int) -> bool:
    return any(block_name(cells.get((x, y, z), "minecraft:air"))
               == "minecraft:water" for y in range(62, 66))


def load_transform(target: Path) -> tuple[int, int, int]:
    marker = json.loads((target / ".projectseele_s24_coastal.json")
                        .read_text(encoding="utf-8"))
    transform = tuple(map(int, marker["transform"]))
    if len(transform) != 3 or transform[0] % 16 or transform[2] % 16:
        raise RuntimeError(f"S24 X/Z transform must be chunk-aligned: {transform}")
    return transform


def audit_target(target: Path, selected: set[tuple[int, int]],
                 dx: int, dz: int, target_base_y: int) -> dict:
    heights = []
    ocean = 0
    by_chunk: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for source_x, source_z in selected:
        cell = (source_x + dx, source_z + dz)
        by_chunk[(cell[0] >> 4, cell[1] >> 4)].append(cell)
    for (chunk_x, chunk_z), columns in sorted(by_chunk.items()):
        cells = read_box(target, DIMENSION,
                         (chunk_x * 16, TARGET_SCAN_MIN_Y, chunk_z * 16),
                         (chunk_x * 16 + 15, 128, chunk_z * 16 + 15), None)
        if not cells:
            raise RuntimeError(f"target chunk is not generated: {(chunk_x, chunk_z)}")
        for x, z in columns:
            heights.append(terrain_top(cells, x, z))
            ocean += int(ocean_column(cells, x, z))
    heights.sort()
    p10 = heights[round((len(heights) - 1) * 0.10)]
    median = heights[len(heights) // 2]
    p90 = heights[round((len(heights) - 1) * 0.90)]
    land_fraction = 1.0 - ocean / len(heights)
    result = {
        "columns": len(heights),
        "landFraction": land_fraction,
        "median": median,
        "p10": p10,
        "p90": p90,
        "spread": p90 - p10,
    }
    if land_fraction < 0.80:
        raise RuntimeError(f"coastal hard gate failed: {result}")
    if p90 - p10 > 15:
        raise RuntimeError(f"flatness hard gate failed: {result}")
    if abs(median - target_base_y) > 8:
        raise RuntimeError(f"datum hard gate failed: {result}")
    return result


def fit_material(y: int, target_top: int, target_base_y: int) -> str:
    if y >= target_base_y - 3:
        return "minecraft:dirt"
    return "minecraft:stone" if target_top >= 0 else "minecraft:deepslate"


def plan_region(source: Path, target: Path, region: tuple[int, int],
                selected: set[tuple[int, int]],
                distance: dict[tuple[int, int], int],
                transform: tuple[int, int, int]) -> list[Change]:
    dx, dy, dz = transform
    target_base_y = SOURCE_BASE_Y + dy
    region_x, region_z = region
    region_columns = [cell for cell in distance
                      if (cell[0] + dx) >> 9 == region_x
                      and (cell[1] + dz) >> 9 == region_z]
    by_chunk: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for cell in region_columns:
        by_chunk[(cell[0] >> 4, cell[1] >> 4)].append(cell)
    result: list[Change] = []

    def add(pos: tuple[int, int, int], before: str, after: str,
            reason: str) -> None:
        if before == after:
            return
        result.append(Change(PACKET, *pos, before, after,
                             "human_authorized_coastal_migration", reason))

    for (source_chunk_x, source_chunk_z), columns in sorted(by_chunk.items()):
        source_lo_x, source_lo_z = source_chunk_x * 16, source_chunk_z * 16
        target_chunk_x = source_chunk_x + dx // 16
        target_chunk_z = source_chunk_z + dz // 16
        target_lo_x, target_lo_z = target_chunk_x * 16, target_chunk_z * 16
        target_cells = read_box(target, DIMENSION,
                                (target_lo_x, TARGET_SCAN_MIN_Y, target_lo_z),
                                (target_lo_x + 15, TARGET_SCAN_MAX_Y,
                                 target_lo_z + 15), None)
        source_cells = read_box(source, DIMENSION,
                                (source_lo_x, SOURCE_BASE_Y, source_lo_z),
                                (source_lo_x + 15, SOURCE_TOP_Y,
                                 source_lo_z + 15), None)
        if not target_cells:
            raise RuntimeError(f"target chunk is not generated: "
                               f"{(target_chunk_x, target_chunk_z)}")
        for source_x, source_z in columns:
            target_x, target_z = source_x + dx, source_z + dz
            native_top = terrain_top(target_cells, target_x, target_z)
            distance_value = distance[(source_x, source_z)]
            if (source_x, source_z) not in selected:
                if ocean_column(target_cells, target_x, target_z):
                    continue
                desired = round(target_base_y - 1
                                + (native_top - (target_base_y - 1))
                                * distance_value / BLEND_RADIUS)
                if desired < native_top:
                    for y in range(desired + 1, native_top + 1):
                        add((target_x, y, target_z),
                            target_cells.get((target_x, y, target_z), "minecraft:air"),
                            "minecraft:air", "native_land_blend_cut")
                elif desired > native_top:
                    for y in range(native_top + 1, desired + 1):
                        add((target_x, y, target_z),
                            target_cells.get((target_x, y, target_z), "minecraft:air"),
                            fit_material(y, native_top, target_base_y),
                            "native_land_blend_fill")
                continue

            if native_top < target_base_y - 1:
                for y in range(native_top + 1, target_base_y):
                    add((target_x, y, target_z),
                        target_cells.get((target_x, y, target_z), "minecraft:air"),
                        fit_material(y, native_top, target_base_y),
                        "city_load_bearing_fill")
            for source_y in range(SOURCE_BASE_Y, SOURCE_TOP_Y + 1):
                target_y = source_y + dy
                add((target_x, target_y, target_z),
                    target_cells.get((target_x, target_y, target_z),
                                     "minecraft:air"),
                    source_cells.get((source_x, source_y, source_z),
                                     "minecraft:air"),
                    "approved_tokyo3_column")
    return result


def apply_region(target: Path, region: tuple[int, int], changes: list[Change],
                 backup_root: Path) -> dict:
    region_x, region_z = region
    path = dimension_dir(target, DIMENSION) / "region" / (
        f"r.{region_x}.{region_z}.mca")
    if not path.is_file():
        raise FileNotFoundError(f"target region is not generated: {path}")
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / path.name
    shutil.copy2(path, backup)
    before = path.read_bytes()
    grouped: dict[tuple[int, int], list[Change]] = defaultdict(list)
    for change in changes:
        grouped[(change.x >> 4, change.z >> 4)].append(change)
    try:
        content = rewrite_region(path, grouped)
        atomic_replace(path, content)
    except Exception:
        atomic_replace(path, before)
        raise
    return {
        "region": path.name,
        "changes": len(changes),
        "beforeSha256": hashlib.sha256(before).hexdigest(),
        "afterSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "backup": str(backup.resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    target = args.target.resolve()
    if source == target:
        raise RuntimeError("source and target must differ")
    if not (target / ".projectseele_s24_coastal.json").is_file():
        raise RuntimeError("target is not an S24 coastal migration save")
    if not (target / ".projectseele_s22_migration_frozen.json").is_file():
        raise RuntimeError("target migration freeze marker is missing")
    transform = load_transform(target)
    target_base_y = SOURCE_BASE_Y + transform[1]
    selected, distance = load_columns()
    target_audit = audit_target(target, selected, transform[0], transform[2],
                                target_base_y)
    if args.audit_only:
        print(json.dumps({"target": str(target),
                          "selectedColumns": len(selected),
                          "targetAudit": target_audit}, indent=2))
        return
    regions = sorted({((x + transform[0]) >> 9,
                       (z + transform[2]) >> 9)
                      for x, z in distance})
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s24_surface_transplant_{stamp}"
    reports = []
    totals = Counter()
    for region in regions:
        changes = plan_region(source, target, region, selected, distance,
                              transform)
        totals["changes"] += len(changes)
        totals["regions"] += 1
        totals.update(change.reason for change in changes)
        if args.apply and changes:
            reports.append(apply_region(target, region, changes,
                                        artifact / "region_before"))
        else:
            reports.append({"region": f"r.{region[0]}.{region[1]}.mca",
                            "changes": len(changes), "applied": False})
    artifact.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": 1,
        "packet": PACKET,
        "applied": args.apply,
        "source": str(source),
        "target": str(target),
        "targetAudit": target_audit,
        "transform": transform,
        "selectedColumns": len(selected),
        "blendColumns": len(distance) - len(selected),
        "totals": dict(totals),
        "regions": reports,
        "rollback": "restore every file under region_before",
    }
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(artifact.resolve()), **receipt}, indent=2))


if __name__ == "__main__":
    main()
