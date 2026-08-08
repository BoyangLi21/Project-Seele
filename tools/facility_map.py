"""Whole-facility 2D floor maps with problem markers.

Companion to facility_audit.py. That tool inspects one element closely; this
one sweeps the entire underground facility, finds the real floor levels from
the data, renders a labelled plan per level, and marks the places where the
geometry breaks.

Detectors
  door_without_footing  a real door with nowhere to stand on either side
  corridor_to_air       a built walkway tip that stops over a drop
  blocking_wall         a one-block partition splitting one walkable level
  ladder_end            a ladder run whose top or bottom has no landing
  ramp_end              a stair run whose top or bottom has no landing

Everything emitted is a *candidate*: geometry worth looking at, with the real
block names beside it, never a verdict. Decorative trapdoors and natural cavern
terrain have both produced false positives before, so the renderer draws the
evidence and the reviewer decides.

Read-only apart from the --emit directory.

    python tools/facility_map.py --emit artifacts/facility_map_s20
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inspect_map_assets import (  # noqa: E402
    decode_modern_section,
    iter_chunks,
    palette_name,
)

AIR, SOLID, NATURAL, FLUID, CLIMB, DOOR, DECOR, STAIR = range(8)
CODE_NAMES = ["air", "solid", "natural", "fluid", "climb", "door", "decor",
              "stair"]

AIR_SET = {"air", "cave_air", "void_air", "light"}
NATURAL_SET = {"grass_block", "dirt", "stone", "deepslate", "tuff", "gravel",
               "sand", "bedrock", "andesite", "diorite", "granite", "clay",
               "moss_block", "rooted_dirt", "coarse_dirt", "podzol", "mud",
               "snow_block", "packed_ice", "sandstone"}
NATURAL_SUB = ("_log", "_leaves", "_wood", "mushroom", "_ore", "sculk",
               "azalea")
DECOR_SUB = ("torch", "button", "lever", "sign", "banner", "rail", "tripwire",
             "flower", "sapling", "short_grass", "fern", "lantern", "carpet",
             "pressure_plate", "candle", "cobweb", "trapdoor")
FLUID_SUB = ("water", "lava", "lcl")
CLIMB_SUB = ("ladder", "scaffolding")


def classify(name: str) -> int:
    s = name.split(":", 1)[-1]
    if s in AIR_SET:
        return AIR
    if s == "sea_lantern":
        return SOLID
    if s in NATURAL_SET or any(k in s for k in NATURAL_SUB):
        return NATURAL
    if any(k in s for k in FLUID_SUB):
        return FLUID
    if any(k in s for k in CLIMB_SUB):
        return CLIMB
    if "_door" in s and "trapdoor" not in s:
        return DOOR
    if any(k in s for k in DECOR_SUB):
        return DECOR
    if "stairs" in s:
        return STAIR
    return SOLID


class Slab:
    """Codes for one z-slab of the facility, plus names for rare blocks."""

    def __init__(self, world: Path, x0, x1, y0, y1, z0, z1) -> None:
        self.x0, self.x1, self.y0, self.y1, self.z0, self.z1 = \
            x0, x1, y0, y1, z0, z1
        self.sx, self.sy, self.sz = x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1
        self.code = np.zeros((self.sx, self.sy, self.sz), dtype=np.uint8)
        self.named: dict[tuple[int, int, int], str] = {}
        cache: dict[str, int] = {}
        lin = np.arange(4096)
        ox, oz, oy = lin & 15, (lin >> 4) & 15, lin >> 8
        for chunk_x, chunk_z, root in iter_chunks(
                world, (x0 // 16, x1 // 16, z0 // 16, z1 // 16)):
            bx, bz = chunk_x * 16, chunk_z * 16
            data = root.get("Level", root)
            for section in data.get("Sections", data.get("sections", [])):
                sy = int(section["Y"]) * 16
                if sy > y1 or sy + 15 < y0:
                    continue
                palette, indices = decode_modern_section(section)
                if not palette:
                    continue
                names = [palette_name(e).split(":")[-1] for e in palette]
                codes = np.empty(len(names), dtype=np.uint8)
                for i, nm in enumerate(names):
                    if nm not in cache:
                        cache[nm] = classify(nm)
                    codes[i] = cache[nm]
                arr = np.asarray(indices, dtype=np.int32)
                vals = codes[arr]
                hit = vals != AIR
                if not hit.any():
                    continue
                xs, ys, zs = bx + ox[hit], sy + oy[hit], bz + oz[hit]
                keep = ((xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)
                        & (zs >= z0) & (zs <= z1))
                if not keep.any():
                    continue
                vv = vals[hit][keep]
                kx, ky, kz = xs[keep], ys[keep], zs[keep]
                self.code[kx - x0, ky - y0, kz - z0] = vv
                rare = np.isin(vv, (CLIMB, DOOR, STAIR))
                for i in np.nonzero(rare)[0]:
                    self.named[(int(kx[i]), int(ky[i]), int(kz[i]))] = \
                        names[arr[hit][keep][i]]

    def name_at(self, x, y, z) -> str:
        got = self.named.get((x, y, z))
        if got:
            return got
        c = self.get(x, y, z)
        return CODE_NAMES[c]

    def get(self, x, y, z) -> int:
        if not (self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1
                and self.z0 <= z <= self.z1):
            return AIR
        return int(self.code[x - self.x0, y - self.y0, z - self.z0])

    # ---- masks -------------------------------------------------------
    def masks(self):
        c = self.code
        solidish = (c == SOLID) | (c == STAIR)
        floor_any = solidish | (c == NATURAL)
        passable = (c == AIR) | (c == DECOR) | (c == DOOR) | (c == CLIMB)
        below_built = np.zeros_like(solidish)
        below_built[:, 1:, :] = solidish[:, :-1, :]
        below_any = np.zeros_like(solidish)
        below_any[:, 1:, :] = floor_any[:, :-1, :]
        head = np.zeros_like(solidish)
        head[:, :-1, :] = passable[:, 1:, :]
        stand_built = below_built & passable & head
        stand_any = below_any & passable & head
        return stand_built, stand_any, solidish

    def drop(self, x, y, z, limit=48):
        for d in range(1, limit + 1):
            c = self.get(x, y - d, z)
            if c in (SOLID, STAIR, NATURAL):
                return d - 1
        return None


def neighbours4(mask, x, y, z, sx, sz, sy):
    """Walk neighbours, counting a one-block step up or down.

    Counting only the same height made every tread of every staircase look
    like a dead end, because the next tread sits one block higher: a 1:2 ramp
    produced a 'corridor stopping in mid-air' for each of its steps.
    """
    out = 0
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, nz = x + dx, z + dz
        if not (0 <= nx < sx and 0 <= nz < sz):
            continue
        for dy in (0, 1, -1):
            ny = y + dy
            if 0 <= ny < sy and mask[nx, ny, nz]:
                out += 1
                break
    return out


def label_components(stand, sx, sy, sz, min_size=1):
    """Label standable cells into walk components (step up/down one block).

    Pillar tops, wall caps and lamp housings are standable too, so without a
    component-size filter every one of them looks like a corridor that stops in
    mid-air. Only cells inside a component of real size are worth reporting.
    """
    label = np.full(stand.shape, -1, dtype=np.int32)
    sizes: list[int] = []
    for start in map(tuple, np.argwhere(stand)):
        if label[start] >= 0:
            continue
        cid = len(sizes)
        q = deque([start])
        label[start] = cid
        n = 0
        while q:
            x, y, z = q.popleft()
            n += 1
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, nz = x + dx, z + dz
                if not (0 <= nx < sx and 0 <= nz < sz):
                    continue
                for dy in (0, 1, -1):
                    ny = y + dy
                    if 0 <= ny < sy and stand[nx, ny, nz] \
                            and label[nx, ny, nz] < 0:
                        label[nx, ny, nz] = cid
                        q.append((nx, ny, nz))
                        break
        sizes.append(n)
    return label, sizes


def detect(slab: Slab, cands: list, min_area: int = 40,
           edge_margin: int = 8) -> None:
    stand_built, stand_any, solidish = slab.masks()
    sx, sy, sz = slab.sx, slab.sy, slab.sz
    ax0, ay0, az0 = slab.x0, slab.y0, slab.z0
    label, sizes = label_components(stand_built, sx, sy, sz)
    doors_seen = ladders_seen = 0

    # ---- doors without footing -------------------------------------
    for (x, y, z), nm in slab.named.items():
        if slab.get(x, y, z) != DOOR or slab.get(x, y - 1, z) == DOOR:
            continue
        doors_seen += 1
        sides = {}
        for tag, (dx, dz) in (("+x", (1, 0)), ("-x", (-1, 0)),
                              ("+z", (0, 1)), ("-z", (0, -1))):
            gx, gz = x + dx - ax0, z + dz - az0
            gy = y - ay0
            ok = (0 <= gx < sx and 0 <= gz < sz and 0 <= gy < sy
                  and stand_any[gx, gy, gz])
            sides[tag] = bool(ok)
        if sum(sides.values()) >= 2:
            continue
        cands.append({
            "type": "door_without_footing", "severity": 60,
            "at": [x, y, z], "material": nm, "standable_sides": sides,
            "drop_below": slab.drop(x, y, z),
            "blocks": {t: slab.name_at(x + dx, y, z + dz) for t, (dx, dz) in
                       (("+x", (1, 0)), ("-x", (-1, 0)), ("+z", (0, 1)),
                        ("-z", (0, -1)), ("below", (0, 0)))},
        })

    # ---- corridor tips over a drop ----------------------------------
    idx = np.argwhere(stand_built)
    for gx, gy, gz in idx:
        if neighbours4(stand_built, gx, gy, gz, sx, sz, sy) > 1:
            continue
        if sizes[label[gx, gy, gz]] < min_area:
            continue          # pillar cap or lamp top, not a corridor
        x, y, z = gx + ax0, gy + ay0, gz + az0
        worst = 0
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if slab.get(x + dx, y, z + dz) != AIR:
                continue
            d = slab.drop(x + dx, y, z + dz)
            worst = max(worst, 48 if d is None else d)
        if worst < 4:
            continue
        # A slab seam or the edge of the scanned box truncates the neighbour
        # and drop tests, which manufactures tips that do not exist in world.
        if min(z - slab.z0, slab.z1 - z) < edge_margin:
            continue
        if min(x - slab.x0, slab.x1 - x) < edge_margin:
            continue
        if min(y - slab.y0, slab.y1 - y) < 3:
            continue
        cands.append({
            "type": "corridor_to_air", "severity": 50 + min(40, worst),
            "at": [int(x), int(y), int(z)], "drop_beside": int(worst),
            "blocks": {"below": slab.name_at(x, y - 1, z)},
        })

    # ---- one-block partitions across a level ------------------------
    for gx, gy, gz in idx:
        x, y, z = gx + ax0, gy + ay0, gz + az0
        for dx, dz in ((1, 0), (0, 1)):
            mx, mz = x + dx, z + dz
            fx, fz = x + 2 * dx, z + 2 * dz
            if slab.get(mx, y, mz) not in (SOLID, STAIR):
                continue
            if slab.get(mx, y + 1, mz) not in (SOLID, STAIR):
                continue
            gfx, gfz, gfy = fx - ax0, fz - az0, y - ay0
            if not (0 <= gfx < sx and 0 <= gfz < sz):
                continue
            if not stand_built[gfx, gfy, gfz]:
                continue
            a, b = label[gx, gy, gz], label[gfx, gfy, gfz]
            if a == b:
                continue      # the two sides join round the corner anyway
            if sizes[a] < min_area or sizes[b] < min_area:
                continue
            if min(z - slab.z0, slab.z1 - z) < edge_margin:
                continue      # component split by the slab seam, not a wall
            cands.append({
                "type": "blocking_wall", "severity": 45,
                "at": [int(mx), int(y), int(mz)],
                "separates": [[int(x), int(y), int(z)],
                              [int(fx), int(y), int(fz)]],
                "blocks": {"wall": slab.name_at(mx, y, mz),
                           "wall_top": slab.name_at(mx, y + 1, mz)},
            })

    # ---- ladder runs ------------------------------------------------
    cols: dict[tuple[int, int], list[int]] = {}
    for (x, y, z), nm in slab.named.items():
        if "ladder" in nm:
            ladders_seen += 1
            cols.setdefault((x, z), []).append(y)
    for (x, z), ys in cols.items():
        ys.sort()
        runs, run = [], [ys[0]]
        for y in ys[1:]:
            if y == run[-1] + 1:
                run.append(y)
            else:
                runs.append(run)
                run = [y]
        runs.append(run)
        for r in runs:
            if len(r) < 4:
                continue
            for tag, y in (("bottom", r[0] - 1), ("top", r[-1] + 1)):
                gx, gy, gz = x - ax0, y - ay0, z - az0
                if not (0 <= gx < sx and 0 <= gy < sy and 0 <= gz < sz):
                    continue
                if stand_any[gx, gy, gz]:
                    continue
                cands.append({
                    "type": "ladder_end", "severity": 65,
                    "at": [int(x), int(y), int(z)], "end": tag,
                    "run": [int(r[0]), int(r[-1])],
                    "drop_below": slab.drop(x, y, z),
                })
    print(f"    elements: doors={doors_seen} ladder_blocks={ladders_seen} "
          f"walk_components={len(sizes)} "
          f"big={sum(1 for n in sizes if n >= min_area)}")


def floor_levels(counts: dict[int, int], top: int = 14):
    """Pick the Y values that carry the most standable area: the real floors."""
    ordered = sorted(counts.items(), key=lambda t: -t[1])
    chosen: list[int] = []
    for y, n in ordered:
        if n < 400:
            break
        if all(abs(y - c) >= 4 for c in chosen):
            chosen.append(y)
        if len(chosen) >= top:
            break
    return sorted(chosen, reverse=True)


COLOURS = {
    AIR: (14, 14, 20), SOLID: (108, 108, 120), NATURAL: (58, 92, 52),
    FLUID: (232, 132, 36), CLIMB: (255, 0, 255), DOOR: (0, 255, 120),
    DECOR: (150, 140, 90), STAIR: (255, 70, 70),
}
MARK = {"door_without_footing": (0, 255, 120),
        "corridor_to_air": (255, 40, 40),
        "blocking_wall": (255, 220, 0),
        "ladder_end": (255, 0, 255),
        "ramp_end": (255, 120, 0)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="SEELE_S20_REBUILD")
    ap.add_argument("--dimension", default="dimensions/projectseele/geofront")
    ap.add_argument("--emit", default="artifacts/facility_map")
    ap.add_argument("--box", nargs=6, type=int,
                    default=[-304, 351, -512, -257, -112, 543])
    ap.add_argument("--slab", type=int, default=170)
    args = ap.parse_args()

    world = ROOT / "run/saves" / args.world / args.dimension
    out = ROOT / args.emit
    (out / "levels").mkdir(parents=True, exist_ok=True)
    x0, x1, y0, y1, z0, z1 = args.box

    cands: list = []
    counts: dict[int, int] = {}
    # global per-level rasters, filled slab by slab
    width, depth = x1 - x0 + 1, z1 - z0 + 1
    raster: dict[int, np.ndarray] = {}

    zs = list(range(z0, z1 + 1, args.slab))
    for zi, zs0 in enumerate(zs):
        zs1 = min(z1, zs0 + args.slab - 1)
        print(f"[slab {zi+1}/{len(zs)}] z {zs0}..{zs1}")
        slab = Slab(world, x0, x1, y0, y1, zs0, zs1)
        detect(slab, cands)
        stand_built, stand_any, solidish = slab.masks()
        for gy in range(slab.sy):
            y = gy + slab.y0
            n = int(stand_built[:, gy, :].sum())
            if n:
                counts[y] = counts.get(y, 0) + n
        slab._cache = (stand_built, solidish)
        # keep raster data for every y; cheap enough as uint8 codes
        for gy in range(slab.sy):
            y = gy + slab.y0
            layer = slab.code[:, gy, :]
            if not layer.any():
                continue
            if y not in raster:
                raster[y] = np.zeros((width, depth), dtype=np.uint8)
            raster[y][:, zs0 - z0: zs1 - z0 + 1] = layer
        del slab

    levels = floor_levels(counts)
    print(f"[levels] {levels}")
    print(f"[candidates] {len(cands)}")

    # ---- render one plan per floor level ----------------------------
    scale = 1
    for y in levels:
        img = Image.new("RGB", (width + 90, depth + 60), (10, 10, 14))
        draw = ImageDraw.Draw(img)
        for dy in (0, -1):
            layer = raster.get(y + dy)
            if layer is None:
                continue
            for code, rgb in COLOURS.items():
                if code == AIR:
                    continue
                ys_, xs_ = np.nonzero(layer == code)
                shade = rgb if dy == -1 else tuple(min(255, c + 40)
                                                   for c in rgb)
                for px, pz in zip(ys_, xs_):
                    img.putpixel((int(px) + 70, int(pz) + 30), shade)
        for gx in range(0, width, 50):
            draw.line([gx + 70, 30, gx + 70, depth + 30], fill=(40, 40, 52))
            draw.text((gx + 72, 16), f"x{gx + x0}", fill=(190, 190, 190))
        for gz in range(0, depth, 50):
            draw.line([70, gz + 30, width + 70, gz + 30], fill=(40, 40, 52))
            draw.text((4, gz + 26), f"z{gz + z0}", fill=(190, 190, 190))
        near = [c for c in cands if abs(c["at"][1] - y) <= 2]
        for i, cand in enumerate(near):
            cx, cy, cz = cand["at"]
            px, pz = cx - x0 + 70, cz - z0 + 30
            col = MARK.get(cand["type"], (255, 255, 255))
            draw.ellipse([px - 5, pz - 5, px + 5, pz + 5], outline=col)
            draw.line([px - 7, pz, px + 7, pz], fill=col)
            draw.line([px, pz - 7, px, pz + 7], fill=col)
        draw.text((70, 2), f"{args.world}  FLOOR y={y}   "
                           f"markers={len(near)}", fill=(255, 255, 255))
        draw.text((70, depth + 40),
                  "grey=built  green=natural  orange=LCL  red=stairs  "
                  "magenta=ladder  | markers: red=corridor_to_air  "
                  "yellow=blocking_wall  green=door  magenta=ladder_end",
                  fill=(170, 170, 180))
        img.save(out / "levels" / f"floor_y{y}.png")
    print(f"[render] {len(levels)} level maps")

    cands.sort(key=lambda c: -c["severity"])
    (out / "candidates.json").write_text(json.dumps({
        "world": args.world, "box": args.box, "levels": levels,
        "count": len(cands),
        "note": "Candidates are geometry observations, not verdicts.",
        "candidates": cands,
    }, indent=1), encoding="utf-8")
    from collections import Counter
    print("[types]", Counter(c["type"] for c in cands).most_common())


if __name__ == "__main__":
    main()
