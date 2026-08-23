#!/usr/bin/env python3
"""Backfill genuinely empty loaded S22 GeoFront parkland columns.

The coastal save contains transplanted legacy chunks whose GeoFront floor was
carved to air before the canonical shallow-dome generator existed.  Future
chunks already use the canonical terrain equations; this packet applies those
same equations only to loaded columns which are entirely empty in the floor
band and contain no authored block anywhere in the playable/deep-facility
height range.  Existing terrain, water, buildings, shafts and human edits are
therefore frozen column-by-column.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from inspect_map_assets import decode_modern_section, iter_chunks, palette_state
from query_blocks import dimension_dir, read_box


WORLD = Path("run/saves/SEELE_S22_COASTAL")
DIMENSION = "projectseele:geofront"
PACKET = "S22-CANONICAL-LOADED-PARKLAND-BACKFILL-R01"
CENTRE_X = 30
CENTRE_Z = 296
FLOOR_Y = -466
BASE_Y = -512
LAKE_Y = -462
BBOX = ((-520, -640, -96), (520, 60, 800))
PLAN = Path("artifacts/s22_coastal_rebuild/parkland_backfill_r01.png")

AIR = {"minecraft:air", "minecraft:void_air", "minecraft:cave_air"}
NATURAL = {
    "minecraft:stone", "minecraft:deepslate", "minecraft:tuff",
    "minecraft:dirt", "minecraft:grass_block", "minecraft:water",
    "minecraft:sand", "minecraft:gravel", "minecraft:clay",
    "minecraft:snow", "minecraft:snow_block", "minecraft:short_grass",
    "minecraft:tall_grass", "minecraft:oak_log", "minecraft:oak_leaves",
    "minecraft:spruce_log", "minecraft:spruce_leaves",
    "minecraft:seagrass", "minecraft:tall_seagrass", "minecraft:kelp",
    "minecraft:kelp_plant", "minecraft:sculk", "minecraft:sculk_vein",
    "minecraft:sculk_sensor", "minecraft:sculk_catalyst",
    "minecraft:bedrock", "minecraft:coal_ore", "minecraft:iron_ore",
    "minecraft:copper_ore", "minecraft:gold_ore", "minecraft:redstone_ore",
    "minecraft:diamond_ore", "minecraft:lapis_ore",
    "minecraft:deepslate_coal_ore", "minecraft:deepslate_iron_ore",
    "minecraft:deepslate_copper_ore", "minecraft:deepslate_gold_ore",
    "minecraft:deepslate_redstone_ore", "minecraft:deepslate_diamond_ore",
    "minecraft:deepslate_lapis_ore",
}
ROOF_ONLY = {
    "projectseele:geofront_skyweave", "ars_nouveau:sky_block",
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def gaussian(x: int, z: int, cx: float, cz: float, radius: float) -> float:
    dx = x - cx
    dz = z - cz
    return math.exp(-(dx * dx + dz * dz) / (radius * radius))


def terrain_height(x: int, z: int) -> int:
    rx = x - CENTRE_X
    rz = z - CENTRE_Z
    rolling = (5.0 * math.sin(rx / 173.0)
               + 4.0 * math.cos(rz / 211.0)
               + 3.0 * math.sin((rx + rz) / 97.0))
    south = 22.0 * gaussian(rx, rz, 420.0, 680.0, 430.0)
    east = 14.0 * gaussian(rx, rz, 780.0, -260.0, 360.0)
    shelf = 9.0 * gaussian(rx, rz, -520.0, -320.0, 330.0)
    return FLOOR_Y + round(rolling + south + east - shelf)


def lake_value(x: int, z: int) -> float:
    rx = x - CENTRE_X
    rz = z - CENTRE_Z
    dx = (rx + 310.0) / 320.0
    dz = (rz + 200.0) / 210.0
    return (dx * dx + dz * dz
            + 0.10 * math.sin((rx + rz) / 41.0)
            + 0.07 * math.cos((rx - rz) / 53.0))


def scan_columns():
    root = dimension_dir(WORLD, DIMENSION)
    chunk_bounds = (BBOX[0][0] >> 4, BBOX[1][0] >> 4,
                    BBOX[0][2] >> 4, BBOX[1][2] >> 4)
    loaded_chunks: set[tuple[int, int]] = set()
    authored: set[tuple[int, int]] = set()
    occupied_floor: set[tuple[int, int]] = set()

    for chunk_x, chunk_z, chunk in iter_chunks(root, chunk_bounds):
        loaded_chunks.add((chunk_x, chunk_z))
        base_x, base_z = chunk_x * 16, chunk_z * 16
        for section in chunk.get("sections", []):
            section_y = int(section.get("Y", 0))
            base_y = section_y * 16
            if base_y > BBOX[1][1] or base_y + 15 < BBOX[0][1]:
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            states = [palette_state(entry) for entry in palette]
            for offset in range(4096):
                y = base_y + (offset >> 8)
                if not BBOX[0][1] <= y <= BBOX[1][1]:
                    continue
                z = base_z + ((offset >> 4) & 15)
                x = base_x + (offset & 15)
                if not (BBOX[0][0] <= x <= BBOX[1][0]
                        and BBOX[0][2] <= z <= BBOX[1][2]):
                    continue
                name = bare(states[indices[offset]])
                if name in AIR:
                    continue
                key = (x, z)
                if BASE_Y <= y <= -420:
                    occupied_floor.add(key)
                if name not in NATURAL and name not in ROOF_ONLY:
                    authored.add(key)
    return loaded_chunks, authored, occupied_floor


def design():
    loaded, authored, occupied = scan_columns()
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}
    counters = Counter()
    filled_columns: set[tuple[int, int]] = set()

    for chunk_x, chunk_z in sorted(loaded):
        for local_z in range(16):
            z = chunk_z * 16 + local_z
            if not BBOX[0][2] <= z <= BBOX[1][2]:
                continue
            for local_x in range(16):
                x = chunk_x * 16 + local_x
                if not BBOX[0][0] <= x <= BBOX[1][0]:
                    continue
                key = (x, z)
                if key in authored:
                    counters["frozen_authored_columns"] += 1
                    continue
                if key in occupied:
                    counters["frozen_existing_floor_columns"] += 1
                    continue
                if (x - CENTRE_X) ** 2 + (z - CENTRE_Z) ** 2 > 1800 ** 2:
                    counters["outside_canonical_dome"] += 1
                    continue

                target = terrain_height(x, z)
                shore = lake_value(x, z)
                if shore < 1.0:
                    depth = 3 + round(max(0.0, 1.0 - shore) * 7.0)
                    bed = LAKE_Y - depth
                    for y in range(BASE_Y, bed - 2):
                        desired[(x, y, z)] = (
                            "minecraft:deepslate", "canonical lake support")
                    for y in range(bed - 2, bed + 1):
                        state = ("minecraft:clay" if (x * 7 + z * 11) % 17 == 0
                                 else "minecraft:sand")
                        desired[(x, y, z)] = (state, "canonical lake bed")
                    for y in range(bed + 1, LAKE_Y + 1):
                        desired[(x, y, z)] = (
                            "minecraft:water", "canonical underground lake")
                    counters["lake_columns"] += 1
                else:
                    for y in range(BASE_Y, target - 3):
                        desired[(x, y, z)] = (
                            "minecraft:deepslate", "canonical parkland support")
                    for y in range(target - 3, target):
                        desired[(x, y, z)] = (
                            "minecraft:dirt", "canonical parkland soil")
                    desired[(x, target, z)] = (
                        "minecraft:grass_block[snowy=false]",
                        "canonical parkland surface")
                    counters["parkland_columns"] += 1
                filled_columns.add(key)

    changes = [
        Change(PACKET, x, y, z, "minecraft:air", state, "replace", reason)
        for (x, y, z), (state, reason) in sorted(
            desired.items(), key=lambda item: (item[0][1], item[0][2], item[0][0]))
    ]
    counters["loaded_chunks"] = len(loaded)
    counters["authored_columns"] = len(authored)
    counters["occupied_floor_columns"] = len(occupied)
    counters["filled_columns"] = len(filled_columns)
    counters["writes"] = len(changes)
    return changes, counters, loaded, authored, occupied, filled_columns


def render_plan(loaded, authored, occupied, filled):
    x0, z0, x1, z1 = BBOX[0][0], BBOX[0][2], BBOX[1][0], BBOX[1][2]
    image = Image.new("RGB", (x1 - x0 + 1, z1 - z0 + 1), (8, 9, 13))
    pixels = image.load()
    for z in range(z0, z1 + 1):
        for x in range(x0, x1 + 1):
            key = (x, z)
            chunk = (x >> 4, z >> 4)
            if chunk not in loaded:
                colour = (8, 9, 13)
            elif key in authored:
                colour = (228, 139, 31)
            elif key in occupied:
                colour = (56, 126, 68)
            elif key in filled:
                colour = ((49, 103, 153) if lake_value(x, z) < 1.0
                          else (95, 178, 103))
            else:
                colour = (45, 47, 53)
            pixels[x - x0, z - z0] = colour
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    image.save(PLAN)


def apply(changes: list[Change], counters: Counter) -> Path:
    root = dimension_dir(WORLD, DIMENSION)
    by_region = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        by_region[(chunk[0] >> 5, chunk[1] >> 5)][chunk].append(change)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = Path("backups") / f"SEELE_S22_PRE_PARKLAND_BACKFILL_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for rx_rz in sorted(by_region):
        rx, rz = rx_rz
        path = root / "region" / f"r.{rx}.{rz}.mca"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, backup / path.name)
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        path = root / "region" / f"r.{rx}.{rz}.mca"
        atomic_replace(path, rewrite_region(path, chunk_changes))

    # Exact readback is intentionally chunked by touched region so the audit
    # never allocates the entire million-column plan as one Python dictionary.
    failures = []
    grouped = defaultdict(list)
    for change in changes:
        grouped[(change.x >> 9, change.z >> 9)].append(change)
    for (_rx, _rz), group in grouped.items():
        lo = (min(c.x for c in group), min(c.y for c in group),
              min(c.z for c in group))
        hi = (max(c.x for c in group), max(c.y for c in group),
              max(c.z for c in group))
        actual = read_box(WORLD, DIMENSION, lo, hi)
        failures.extend(c for c in group
                        if actual.get((c.x, c.y, c.z), "minecraft:air")
                        != c.after)
    if failures:
        for copied in backup.glob("r.*.*.mca"):
            shutil.copy2(copied, root / "region" / copied.name)
        raise RuntimeError(f"readback failed for {len(failures)} cells")
    (backup / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "counts": dict(counters),
        "regionsBeforeSha256": hashes,
    }, indent=2) + "\n", encoding="ascii")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes, counters, loaded, authored, occupied, filled = design()
    render_plan(loaded, authored, occupied, filled)
    print(json.dumps({"packet": PACKET, **dict(counters),
                      "plan": str(PLAN)}, indent=2))
    if args.apply:
        print(f"backup={apply(changes, counters)}")


if __name__ == "__main__":
    main()
