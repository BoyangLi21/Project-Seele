#!/usr/bin/env python3
"""Rebuild R28 Terminal Dogma as a sealed, canonical containment chamber.

Scope is limited to the existing Terminal-Dogma ellipsoid, its observation
galleries and the new B-158 handoff.  The x=12 lift, the Central-Dogma shaft,
the accepted B-158 corridor, command room, pyramid, hangars and surface are
outside the write mask.  Every touched region file is copied before writing.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
DIMENSION = "projectseele:geofront"
PACKET = "S21-TERMINAL-DOGMA-R04"
BBOX = ((-12, -620, 246), (72, -528, 344))
AIR = "minecraft:air"
WALL = "minecraft:deepslate_bricks"
RIB = "minecraft:polished_basalt[axis=y]"
TRIM = "minecraft:deepslate_tiles"
FLOOR = "minecraft:polished_blackstone"
STRUCTURE = "minecraft:reinforced_deepslate"
LIGHT = "minecraft:sea_lantern"
INVISIBLE_LIGHT = "minecraft:light[level=15,waterlogged=false]"
RED = "minecraft:redstone_block"
RED_GLASS = "minecraft:red_stained_glass"
LCL = "projectseele:lcl[level=0]"

# Only the original programmatic palette may be retired.  Unknown/player NBT
# remains a collision instead of being silently absorbed by the rebuild.
OLD_OWNED = {
    "minecraft:air", "minecraft:void_air", "minecraft:cave_air",
    "minecraft:deepslate_bricks", "minecraft:polished_basalt",
    "minecraft:deepslate_tiles", "minecraft:redstone_block",
    "minecraft:orange_concrete", "minecraft:polished_blackstone",
    "minecraft:red_stained_glass", "minecraft:reinforced_deepslate",
    "minecraft:light_gray_concrete", "minecraft:sea_lantern",
    "minecraft:iron_block", "minecraft:iron_bars",
    "minecraft:polished_deepslate", "minecraft:light",
    "minecraft:red_concrete", "minecraft:redstone_lamp",
    "minecraft:black_concrete", "minecraft:shroomlight",
    "minecraft:ladder", "minecraft:lodestone", "minecraft:calcite",
    "minecraft:magenta_concrete", "minecraft:netherite_block",
    "minecraft:gray_stained_glass", "projectseele:lcl",
    "minecraft:stone", "minecraft:deepslate", "minecraft:tuff",
}


def bare(state: str) -> str:
    return state.split("[", 1)[0]


def ellipsoid(x: int, y: int, z: int,
              cx: int, cy: int, cz: int,
              rx: float, ry: float, rz: float) -> float:
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2


def protected(x: int, y: int, z: int) -> bool:
    # Accepted lift/corridor packet, including its five-block clear height.
    if -8 <= x <= 17 and -568 <= y <= -561 and 245 <= z <= 266:
        return True
    # Existing x=12 elevator car/shaft below and above the landing.
    if 7 <= x <= 17 and 248 <= z <= 258:
        return True
    # Existing Central-Dogma shaft and controls at x=72,z=273.
    if 67 <= x <= 72 and 267 <= z <= 279:
        return True
    return False


def put(desired: dict, x: int, y: int, z: int,
        state: str, reason: str) -> None:
    if not (BBOX[0][0] <= x <= BBOX[1][0]
            and BBOX[0][1] <= y <= BBOX[1][1]
            and BBOX[0][2] <= z <= BBOX[1][2]):
        raise RuntimeError(f"write escaped Terminal Dogma: {(x, y, z)}")
    if protected(x, y, z):
        return
    desired[(x, y, z)] = (state, reason)


def fill(desired: dict, x0: int, y0: int, z0: int,
         x1: int, y1: int, z1: int, state: str, reason: str) -> None:
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                put(desired, x, y, z, state, reason)


def floor_strip(desired: dict, x0: int, x1: int,
                z0: int, z1: int, y: int, reason: str) -> None:
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            put(desired, x, y, z,
                LIGHT if (x * 7 + z * 11) % 19 == 0 else FLOOR, reason)
            for clear_y in range(y + 1, y + 5):
                put(desired, x, clear_y, z, AIR, reason + " clear")


def rail_x(desired: dict, x0: int, x1: int, y: int, z: int, reason: str) -> None:
    state = "minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]"
    for x in range(x0, x1 + 1):
        put(desired, x, y, z, state, reason)


def rail_z(desired: dict, x: int, y: int, z0: int, z1: int, reason: str) -> None:
    state = "minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]"
    for z in range(z0, z1 + 1):
        put(desired, x, y, z, state, reason)


def design(current: dict[tuple[int, int, int], str]) -> list[Change]:
    desired: dict[tuple[int, int, int], tuple[str, str]] = {}

    # Retire the old low oval and any LCL that escaped inside this one room.
    for (x, y, z), state in current.items():
        old_room = ellipsoid(x, y, z, 30, -566, 296, 39, 31, 47) <= 1.08
        escaped_lcl = bare(state) == "projectseele:lcl"
        if (old_room or escaped_lcl) and bare(state) in OLD_OWNED:
            put(desired, x, y, z, AIR, "retire old Terminal Dogma volume")

    # A tall, sealed pressure cathedral.  Ribs stay sparse so the red cross,
    # white Lilith and orange LCL remain the only dominant silhouettes.
    cx, cy, cz = 30, -574, 296
    rx, ry, rz = 40, 44, 48
    for x in range(cx - rx, cx + rx + 1):
        for y in range(cy - ry, cy + ry + 1):
            for z in range(cz - rz, cz + rz + 1):
                d = ellipsoid(x, y, z, cx, cy, cz, rx, ry, rz)
                if d > 1.0:
                    continue
                if d < 0.88:
                    put(desired, x, y, z, AIR,
                        "Terminal Dogma sealed interior")
                    continue
                angle = math.atan2(z - cz, x - cx)
                vertical_rib = int((angle + math.pi) / (math.pi / 12)) % 3 == 0
                horizontal_rib = (y - (cy - ry)) % 9 <= 1
                material = RIB if horizontal_rib else (TRIM if vertical_rib else WALL)
                put(desired, x, y, z, material,
                    "Terminal Dogma pressure shell")

    # Lilith's blood is a broad bounded lake, not an orange concrete puddle.
    lake_cz = 292
    for x in range(-2, 63):
        for z in range(256, 329):
            d = ((x - 30) / 30.0) ** 2 + ((z - lake_cz) / 34.0) ** 2
            if d <= 1.0:
                put(desired, x, -613, z,
                    LIGHT if (x * 17 + z * 29) % 29 == 0
                    else "minecraft:orange_concrete",
                    "Terminal Dogma LCL lake bed")
                for y in range(-612, -601):
                    put(desired, x, y, z, LCL,
                        "Terminal Dogma bounded LCL lake")
            elif d <= 1.16:
                put(desired, x, -602, z,
                    LIGHT if (x + z) % 11 == 0 else STRUCTURE,
                    "Terminal Dogma LCL containment rim")

    # Preserve the accepted TV-scale red crucifix and Lilith entity anchor.
    fill(desired, 26, -585, 270, 34, -544, 272, RED,
         "Terminal Dogma red crucifix vertical")
    fill(desired, 9, -563, 270, 51, -555, 272, RED,
         "Terminal Dogma red crucifix horizontal")
    fill(desired, 26, -585, 273, 34, -544, 273, RED_GLASS,
         "Terminal Dogma crucifix luminous face")
    fill(desired, 9, -563, 273, 51, -555, 273, RED_GLASS,
         "Terminal Dogma crucifix luminous face")
    for y in range(-584, -543, 4):
        put(desired, 30, y, 271, "minecraft:shroomlight",
            "Terminal Dogma crucifix concealed light")
    for x in range(10, 51, 4):
        put(desired, x, -559, 271, "minecraft:shroomlight",
            "Terminal Dogma crucifix concealed light")

    # Processional observation axis with perimeter access, all at the existing
    # y=-567 datum so no old route is stranded by the rebuild.
    floor_strip(desired, 24, 36, 309, 337, -567,
                "Terminal Dogma axial observation bridge")
    floor_strip(desired, -2, 62, 328, 337, -567,
                "Terminal Dogma south observation gallery")
    floor_strip(desired, -2, 5, 270, 327, -567,
                "Terminal Dogma west observation gallery")
    floor_strip(desired, 54, 62, 278, 327, -567,
                "Terminal Dogma east observation gallery")
    # Keep both side-gallery mouths open into the south gallery; railing only
    # guards the two exposed spans beside the axial bridge.
    rail_x(desired, 7, 23, -566, 327, "Terminal Dogma observation rail")
    rail_x(desired, 37, 53, -566, 327, "Terminal Dogma observation rail")
    rail_z(desired, 6, -566, 278, 308, "Terminal Dogma observation rail")
    rail_z(desired, 53, -566, 278, 308, "Terminal Dogma observation rail")
    rail_x(desired, -2, 62, -566, 338, "Terminal Dogma outer rail")
    rail_z(desired, -3, -566, 278, 337, "Terminal Dogma outer rail")
    rail_z(desired, 63, -566, 278, 337, "Terminal Dogma outer rail")

    # Heaven's Door: a compact two-frame pressure vestibule joining the new
    # B-158 corridor to the west gallery.  Its first five blocks are preserved
    # by the route packet; construction starts at z=267.
    floor_strip(desired, -6, 2, 267, 279, -567,
                "Heaven's Door access floor")
    for x in range(-7, 4):
        for z in range(267, 280):
            boundary = x in (-7, 3)
            if boundary:
                for y in range(-566, -560):
                    put(desired, x, y, z,
                        RED_GLASS if -565 <= y <= -562 else STRUCTURE,
                        "Heaven's Door pressure wall")
            put(desired, x, -560, z,
                LIGHT if (x + z) % 7 == 0 else STRUCTURE,
                "Heaven's Door ceiling")
    for gate_z in (267, 275):
        for x in range(-7, 4):
            for y in range(-566, -560):
                aperture = -5 <= x <= 1 and y <= -561
                put(desired, x, y, gate_z,
                    AIR if aperture else (
                        "minecraft:red_concrete" if y in (-564, -563)
                        else "minecraft:iron_block"),
                    "Heaven's Door security frame")

    # Keep the east Central-Dogma approach as a separate quarantine sequence.
    floor_strip(desired, 51, 66, 299, 315, -567,
                "Terminal Dogma east quarantine floor")
    for x in range(50, 68):
        for z in range(299, 316):
            if x in (50, 67):
                for y in range(-566, -560):
                    put(desired, x, y, z,
                        RED_GLASS if -565 <= y <= -562 else STRUCTURE,
                        "Terminal Dogma east quarantine wall")
            put(desired, x, -560, z, STRUCTURE,
                "Terminal Dogma east quarantine ceiling")
    for gate_z in (299, 307, 315):
        for x in range(50, 68):
            for y in range(-566, -560):
                aperture = 53 <= x <= 65 and y <= -561
                put(desired, x, y, gate_z,
                    AIR if aperture else (
                        "minecraft:red_concrete" if y in (-564, -563)
                        else "minecraft:iron_block"),
                    "Terminal Dogma east quarantine frame")

    # Wall-backed descent to the lake-service rim.
    for y in range(-601, -565):
        put(desired, 66, y, 324, "minecraft:black_concrete",
            "Terminal Dogma service shaft backing")
        put(desired, 65, y, 324,
            "minecraft:ladder[facing=west,waterlogged=false]",
            "Terminal Dogma service ladder")
    floor_strip(desired, 55, 65, 316, 327, -602,
                "Terminal Dogma lower service landing")
    rail_x(desired, 55, 65, -601, 315,
           "Terminal Dogma lower service rail")
    rail_z(desired, 54, -601, 316, 327,
           "Terminal Dogma lower service rail")

    # Sparse, invisible illumination: readable silhouettes without a bright
    # theme-park room or visible lamp lattice.
    for x in range(0, 61, 6):
        for y in (-603, -591, -579, -567, -555, -543):
            for z in (278, 316):
                put(desired, x, y, z, INVISIBLE_LIGHT,
                    "Terminal Dogma controlled scene light")

    # Runtime audit witnesses.  These keep login repair from regenerating the
    # retired low ellipsoid over the authored chamber.
    witnesses = {
        (30, -536, 296): "minecraft:calcite",
        (30, -566, 250): RIB,
        (30, -566, 284): INVISIBLE_LIGHT,
        (30, -583, 296): LCL,
        (30, -558, 271): RED,
        (50, -558, 273): RED_GLASS,
        (30, -567, 330): "minecraft:lodestone",
        (64, -567, 304): "minecraft:netherite_block",
        (63, -567, 304): "minecraft:magenta_concrete",
        (65, -567, 304): "minecraft:lodestone",
        (50, -564, 306): RED_GLASS,
        (54, -567, 286): FLOOR,
    }
    for (x, y, z), state in witnesses.items():
        put(desired, x, y, z, state, "Terminal Dogma runtime witness")

    changes: list[Change] = []
    collisions = []
    for position, (after, reason) in sorted(desired.items(), key=lambda item: item[0][1]):
        before = current.get(position, AIR)
        if before == after:
            continue
        if bare(before) not in OLD_OWNED:
            collisions.append((position, before, after, reason))
            continue
        changes.append(Change(PACKET, *position, before, after,
                              "bounded_authored_edit", reason))
    if collisions:
        sample = ", ".join(f"{p}:{b}" for p, b, _, _ in collisions[:20])
        materials = Counter(bare(before) for _, before, _, _ in collisions)
        raise RuntimeError(
            f"collides with {len(collisions)} protected cells "
            f"{dict(materials.most_common(12))}: {sample}")
    verify(current, changes)
    return changes


def verify(current: dict, changes: list[Change]) -> None:
    proposed = dict(current)
    for change in changes:
        proposed[(change.x, change.y, change.z)] = change.after

    air_blocks = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
    def is_air(pos):
        return bare(proposed.get(pos, AIR)) in air_blocks
    def walkable(pos):
        x, y, z = pos
        return (not is_air((x, y - 1, z)) and is_air((x, y, z))
                and is_air((x, y + 1, z)))

    start = (12, -566, 256)
    goal = (30, -566, 330)
    queue = deque([start])
    seen = {start}
    bounds = (-8, 68, 250, 340)
    while queue:
        x, y, z = queue.popleft()
        if (x, y, z) == goal:
            break
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y, z + dz)
            if (bounds[0] <= nxt[0] <= bounds[1]
                    and bounds[2] <= nxt[2] <= bounds[3]
                    and nxt not in seen and walkable(nxt)):
                seen.add(nxt)
                queue.append(nxt)
    else:
        raise RuntimeError(f"B-158 cannot reach observation axis: {start} -> {goal}")

    required = {
        (30, -536, 296): "minecraft:calcite",
        (30, -566, 250): "minecraft:polished_basalt",
        (30, -583, 296): "projectseele:lcl",
        (30, -558, 271): "minecraft:redstone_block",
        (50, -558, 273): "minecraft:red_stained_glass",
        (30, -567, 330): "minecraft:lodestone",
        (64, -567, 304): "minecraft:netherite_block",
        (65, -576, 324): "minecraft:ladder",
    }
    for pos, expected in required.items():
        if bare(proposed.get(pos, AIR)) != expected:
            raise RuntimeError(f"runtime witness failed at {pos}: {proposed.get(pos)}")
    if not (not is_air((54, -567, 286))
            and is_air((54, -566, 286))
            and is_air((54, -565, 286))):
        raise RuntimeError("runtime deep-access datum is not walkable")


def apply(world: Path, changes: list[Change]) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    artifact = ROOT / "artifacts" / f"s21_terminal_dogma_r04_{stamp}"
    backup = artifact / "region_before"
    backup.mkdir(parents=True)
    region_dir = dimension_dir(world, DIMENSION) / "region"
    by_region: dict[tuple[int, int], dict[tuple[int, int], list[Change]]] = defaultdict(lambda: defaultdict(list))
    for change in changes:
        chunk = (change.x >> 4, change.z >> 4)
        region = (chunk[0] >> 5, chunk[1] >> 5)
        by_region[region][chunk].append(change)

    before_hashes = {}
    for rx, rz in sorted(by_region):
        source = region_dir / f"r.{rx}.{rz}.mca"
        before_hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copy2(source, backup / source.name)
    for (rx, rz), chunk_changes in sorted(by_region.items()):
        source = region_dir / f"r.{rx}.{rz}.mca"
        atomic_replace(source, rewrite_region(source, chunk_changes))

    lo = tuple(min(getattr(c, axis) for c in changes) for axis in ("x", "y", "z"))
    hi = tuple(max(getattr(c, axis) for c in changes) for axis in ("x", "y", "z"))
    actual = read_box(world, DIMENSION, lo, hi)
    failures = [c for c in changes if actual.get((c.x, c.y, c.z), AIR) != c.after]
    if failures:
        for source in backup.glob("r.*.*.mca"):
            shutil.copy2(source, region_dir / source.name)
        raise RuntimeError(f"read-back failed for {len(failures)} cells; restored backup")

    (artifact / "block_diff.json").write_text(json.dumps([
        {"x": c.x, "y": c.y, "z": c.z, "before": c.before,
         "after": c.after, "reason": c.reason}
        for c in changes
    ], separators=(",", ":")), encoding="utf-8")
    (artifact / "receipt.json").write_text(json.dumps({
        "status": "APPLIED_AND_READ_BACK_VERIFIED",
        "packet": PACKET,
        "world": str(world),
        "writes": len(changes),
        "regionsBeforeSha256": before_hashes,
        "route": [[12, -566, 256], [30, -566, 330]],
    }, indent=2) + "\n", encoding="ascii")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, default=WORLD)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    world = args.world.resolve()
    current = read_box(world, DIMENSION, BBOX[0], BBOX[1])
    changes = design(current)
    report = {
        "packet": PACKET,
        "world": str(world),
        "writes": len(changes),
        "bbox": [BBOX[0], BBOX[1]],
        "reasons": dict(Counter(c.reason for c in changes)),
    }
    print(json.dumps(report, indent=2))
    if args.apply:
        print(json.dumps({"artifact": str(apply(world, changes))}, indent=2))


if __name__ == "__main__":
    main()
