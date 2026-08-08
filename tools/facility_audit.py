"""Element-level facility audit for a Project SEELE world.

Block-level scans drown in noise: a plain walkability flood fill of the S20
plant produced 3,463 components and no usable statement. This tool works one
level up, on architectural elements — ramps, ladders, doors and floor plates —
and checks the invariants that actually fail in review:

  * a ramp must land on a floor plate at both ends;
  * a ladder run must land on a floor plate at both ends;
  * a real door must have somewhere to stand on both sides.

It deliberately emits *candidates*, never verdicts. Every candidate carries the
real block names at its key coordinates and a rendered section/plan pair, so
the reviewer looks at the geometry before calling anything a defect. That order
matters: earlier passes reported decorative trapdoors as broken doors and
natural cavern grass as dead-end corridors purely because nothing was rendered
or reverse-looked-up first.

Read-only. Writes only into the directory given by --emit.

    python tools/facility_audit.py --world SEELE_S20_REBUILD \
        --emit artifacts/audit_s20
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
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

AIR = {"air", "cave_air", "void_air", "light"}
NATURAL = {"grass_block", "dirt", "stone", "coarse_dirt", "podzol", "gravel",
           "sand", "sandstone", "deepslate", "tuff", "andesite", "diorite",
           "granite", "clay", "mud", "moss_block", "rooted_dirt", "bedrock",
           "snow_block", "packed_ice"}
NATURAL_SUB = ("_log", "_leaves", "_wood", "mushroom", "_ore", "azalea",
               "sculk")
# Trapdoors are used here as lamp housings under froglights, so they are decor,
# not portals. Reporting them as doors was a false positive in an earlier pass.
DECOR_SUB = ("torch", "button", "lever", "sign", "banner", "rail", "tripwire",
             "flower", "sapling", "short_grass", "fern", "lantern", "carpet",
             "pressure_plate", "candle", "cobweb", "trapdoor")
FLUID_SUB = ("water", "lava", "lcl")
CLIMB_SUB = ("ladder", "scaffolding")

STEP_UP = 1          # blocks a player can walk up without jumping
SEARCH_R = 3         # horizontal radius when looking for a landing


def classify(name: str) -> str:
    s = name.split(":", 1)[-1]
    if s in AIR:
        return "air"
    if s in NATURAL or any(k in s for k in NATURAL_SUB):
        return "natural"
    if any(k in s for k in FLUID_SUB):
        return "fluid"
    if any(k in s for k in CLIMB_SUB):
        return "climb"
    if "_door" in s and "trapdoor" not in s:
        return "door"
    if any(k in s for k in DECOR_SUB):
        return "decor"
    if "stairs" in s:
        return "stair"
    return "solid"


class World:
    """Sparse block store with names kept for reverse lookup."""

    def __init__(self, world: Path, box) -> None:
        self.box = box
        (self.x0, self.x1, self.y0, self.y1, self.z0, self.z1) = box
        self.name: dict[tuple[int, int, int], str] = {}
        self._load(world)

    def _load(self, world: Path) -> None:
        bounds = (self.x0 // 16, self.x1 // 16, self.z0 // 16, self.z1 // 16)
        lin = np.arange(4096)
        ox, oz, oy = lin & 15, (lin >> 4) & 15, lin >> 8
        chunks = 0
        for chunk_x, chunk_z, root in iter_chunks(world, bounds):
            chunks += 1
            bx, bz = chunk_x * 16, chunk_z * 16
            data = root.get("Level", root)
            for section in data.get("Sections", data.get("sections", [])):
                sy = int(section["Y"]) * 16
                if sy > self.y1 or sy + 15 < self.y0:
                    continue
                palette, indices = decode_modern_section(section)
                if not palette:
                    continue
                names = [palette_name(e).split(":")[-1] for e in palette]
                arr = np.asarray(indices, dtype=np.int32)
                xs, ys, zs = bx + ox, sy + oy, bz + oz
                keep = ((xs >= self.x0) & (xs <= self.x1) & (ys >= self.y0)
                        & (ys <= self.y1) & (zs >= self.z0) & (zs <= self.z1))
                for i in np.nonzero(keep)[0]:
                    nm = names[arr[i]]
                    if nm in AIR:
                        continue
                    self.name[(int(xs[i]), int(ys[i]), int(zs[i]))] = nm
        print(f"[load] chunks={chunks} non-air cells={len(self.name)}")

    def at(self, x: int, y: int, z: int) -> str:
        return self.name.get((x, y, z), "air")

    def kind(self, x: int, y: int, z: int) -> str:
        return classify(self.at(x, y, z))

    def standable(self, x: int, y: int, z: int) -> bool:
        """Feet cell: solid-ish floor below, body and head clear."""
        below = self.kind(x, y - 1, z)
        if below not in ("solid", "stair", "natural"):
            return False
        return (self.kind(x, y, z) in ("air", "decor", "door", "climb")
                and self.kind(x, y + 1, z) in ("air", "decor", "door", "climb"))

    def drop_below(self, x: int, y: int, z: int, limit: int = 64) -> int | None:
        """Blocks of empty space under a cell before the first floor."""
        for d in range(1, limit + 1):
            if self.kind(x, y - d, z) in ("solid", "stair", "natural"):
                return d - 1
        return None


def cluster(points, reach: int = 2):
    """Group cells that are within `reach` on every axis (bridges the flat
    landings that alternate with stair treads on a 1:2 ramp)."""
    remaining = set(points)
    groups = []
    while remaining:
        seed = remaining.pop()
        group = [seed]
        queue = deque([seed])
        while queue:
            cx, cy, cz = queue.popleft()
            near = [p for p in remaining
                    if abs(p[0] - cx) <= reach and abs(p[1] - cy) <= reach
                    and abs(p[2] - cz) <= reach]
            for p in near:
                remaining.discard(p)
                group.append(p)
                queue.append(p)
        groups.append(group)
    return groups


def ramp_elements(world: World, min_blocks: int = 8):
    stairs = [p for p, n in world.name.items() if classify(n) == "stair"]
    out = []
    for group in cluster(stairs, reach=2):
        if len(group) < min_blocks:
            continue
        arr = np.array(group)
        span_x = arr[:, 0].max() - arr[:, 0].min()
        span_z = arr[:, 2].max() - arr[:, 2].min()
        span_y = arr[:, 1].max() - arr[:, 1].min()
        if span_y < 3:
            continue                     # flat decorative stair trim
        axis = 0 if span_x >= span_z else 2
        lo_i = int(np.argmin(arr[:, 1]))
        hi_i = int(np.argmax(arr[:, 1]))
        out.append({
            "cells": group,
            "axis": "x" if axis == 0 else "z",
            "low": tuple(int(v) for v in arr[lo_i]),
            "high": tuple(int(v) for v in arr[hi_i]),
            "material": world.at(*group[0]),
            "count": len(group),
            "bbox": [int(arr[:, 0].min()), int(arr[:, 0].max()),
                     int(arr[:, 1].min()), int(arr[:, 1].max()),
                     int(arr[:, 2].min()), int(arr[:, 2].max())],
        })
    return out


def ladder_elements(world: World, min_len: int = 4):
    ladders = [p for p, n in world.name.items() if "ladder" in n]
    columns = defaultdict(list)
    for x, y, z in ladders:
        columns[(x, z)].append(y)
    out = []
    for (x, z), ys in columns.items():
        ys.sort()
        run = [ys[0]]
        for y in ys[1:]:
            if y == run[-1] + 1:
                run.append(y)
            else:
                if len(run) >= min_len:
                    out.append({"x": x, "z": z, "y0": run[0], "y1": run[-1]})
                run = [y]
        if len(run) >= min_len:
            out.append({"x": x, "z": z, "y0": run[0], "y1": run[-1]})
    return out


def door_elements(world: World):
    doors = [p for p, n in world.name.items() if classify(n) == "door"]
    seen, out = set(), []
    for x, y, z in doors:
        if (x, y - 1, z) in seen or world.kind(x, y - 1, z) == "door":
            continue
        seen.add((x, y, z))
        out.append({"pos": (x, y, z), "material": world.at(x, y, z)})
    return out


def is_floor_plate(world: World, x: int, y: int, z: int,
                   need: int = 6) -> bool:
    """True when a cell belongs to a flat standable area, not a single tread.

    A ramp's own steps are standable, and so are the flat blocks that alternate
    with them on a 1:2 run, so proximity alone let every staircase 'land on
    itself'. Requiring a flat neighbourhood at one height distinguishes a real
    landing from another rung of the same slope.
    """
    hits = 0
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            if world.standable(x + dx, y, z + dz):
                hits += 1
    return hits >= need


def landing_near(world: World, x: int, y: int, z: int, exclude=frozenset()):
    """Nearest standable cell within a step of `y` and SEARCH_R horizontally.

    `exclude` holds the element's own blocks. Without it a ramp always passes:
    its own treads are standable, so every staircase would look like it landed
    on itself. The supporting block under a genuine landing must belong to
    something other than the element being checked.
    """
    best = None
    for dx in range(-SEARCH_R, SEARCH_R + 1):
        for dz in range(-SEARCH_R, SEARCH_R + 1):
            for dy in range(-STEP_UP, STEP_UP + 1):
                cx, cy, cz = x + dx, y + dy, z + dz
                if (cx, cy, cz) in exclude or (cx, cy - 1, cz) in exclude:
                    continue
                if world.standable(cx, cy, cz) and is_floor_plate(
                        world, cx, cy, cz):
                    d = abs(dx) + abs(dz) + abs(dy)
                    if best is None or d < best[0]:
                        best = (d, (cx, cy, cz))
    return None if best is None else best[1]


# --------------------------------------------------------------------------
# rendering: every candidate gets a section along its own axis plus two plans

PALETTE = [
    ("stairs", (255, 80, 80)), ("ladder", (255, 0, 255)),
    ("door", (0, 255, 120)), ("lcl", (255, 150, 40)),
    ("orange", (255, 150, 40)), ("glass", (140, 220, 255)),
    ("lantern", (255, 255, 150)), ("froglight", (255, 255, 150)),
    ("iron", (210, 210, 225)), ("purple", (170, 90, 220)),
    ("grass", (90, 150, 70)), ("dirt", (105, 80, 60)),
    ("concrete", (185, 185, 195)), ("deepslate", (110, 110, 120)),
    ("stone", (120, 120, 128)), ("basalt", (95, 95, 105)),
]


def colour(name: str):
    for key, rgb in PALETTE:
        if key in name:
            return rgb
    return (85, 85, 95)


def render(world: World, path: Path, mode: str, fixed_lo: int, fixed_hi: int,
           h_range, v_range, title: str, scale: int = 8) -> None:
    """mode 'section': horizontal axis z, vertical axis y (x collapsed).
       mode 'plan':    horizontal axis x, vertical axis z (y collapsed)."""
    h0, h1 = h_range
    v0, v1 = v_range
    w = (h1 - h0 + 1) * scale
    h = (v1 - v0 + 1) * scale
    img = Image.new("RGB", (w + 62, h + 34), (18, 18, 24))
    draw = ImageDraw.Draw(img)
    for (x, y, z), nm in world.name.items():
        if mode == "section":
            if not (fixed_lo <= x <= fixed_hi):
                continue
            hv, vv = z, y
            px = (hv - h0) * scale + 52
            py = (v1 - vv) * scale + 12
        else:
            if not (fixed_lo <= y <= fixed_hi):
                continue
            hv, vv = x, z
            px = (hv - h0) * scale + 52
            py = (vv - v0) * scale + 12
        if not (h0 <= hv <= h1 and v0 <= vv <= v1):
            continue
        draw.rectangle([px, py, px + scale - 1, py + scale - 1],
                       fill=colour(nm))
    for hv in range(h0, h1 + 1, 10):
        px = (hv - h0) * scale + 52
        draw.line([px, 12, px, h + 12], fill=(58, 58, 72))
        draw.text((px + 2, h + 16), f"{'z' if mode=='section' else 'x'}{hv}",
                  fill=(205, 205, 205))
    for vv in range(v0, v1 + 1, 5 if mode == "section" else 10):
        py = ((v1 - vv) if mode == "section" else (vv - v0)) * scale + 12
        draw.line([52, py, w + 52, py], fill=(58, 58, 72))
        draw.text((3, py - 4), f"{vv}", fill=(205, 205, 205))
    draw.text((52, 1), title, fill=(255, 255, 255))
    draw.text((52, h + 24),
              "red=stairs  magenta=ladder  green=door  orange=LCL  "
              "yellow=light  cyan=glass  greenish=natural",
              fill=(160, 160, 170))
    img.save(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="SEELE_S20_REBUILD")
    ap.add_argument("--dimension", default="dimensions/projectseele/geofront")
    ap.add_argument("--emit", default="artifacts/facility_audit")
    ap.add_argument("--box", nargs=6, type=int,
                    default=[-200, 320, -480, -330, 110, 540],
                    metavar=("X0", "X1", "Y0", "Y1", "Z0", "Z1"))
    ap.add_argument("--max-candidates", type=int, default=40)
    args = ap.parse_args()

    world_dir = ROOT / "run/saves" / args.world / args.dimension
    if not world_dir.is_dir():
        raise SystemExit(f"world not found: {world_dir}")
    out_dir = ROOT / args.emit
    (out_dir / "images").mkdir(parents=True, exist_ok=True)

    world = World(world_dir, tuple(args.box))
    ramps = ramp_elements(world)
    ladders = ladder_elements(world)
    doors = door_elements(world)
    print(f"[elements] ramps={len(ramps)} ladder_runs={len(ladders)} "
          f"doors={len(doors)}")

    candidates = []

    for i, ramp in enumerate(ramps):
        own = frozenset(ramp["cells"])
        for end_name, cell in (("low", ramp["low"]), ("high", ramp["high"])):
            x, y, z = cell
            landing = landing_near(world, x, y, z, exclude=own)
            if landing is not None:
                continue
            gap = world.drop_below(x, y, z)
            candidates.append({
                "id": f"ramp{i:02d}_{end_name}",
                "type": "ramp_end_without_landing",
                "severity": 100 if (gap is None or gap >= 3) else 40,
                "element": {"kind": "ramp", "material": ramp["material"],
                            "blocks": ramp["count"], "axis": ramp["axis"],
                            "bbox": ramp["bbox"]},
                "at": [x, y, z],
                "drop_to_floor": gap,
                "blocks_here": {
                    "at": world.at(x, y, z),
                    "below": world.at(x, y - 1, z),
                    "+x": world.at(x + 1, y, z), "-x": world.at(x - 1, y, z),
                    "+z": world.at(x, y, z + 1), "-z": world.at(x, y, z - 1),
                },
            })

    for i, lad in enumerate(ladders):
        for end_name, y in (("bottom", lad["y0"] - 1), ("top", lad["y1"] + 1)):
            if landing_near(world, lad["x"], y, lad["z"]) is not None:
                continue
            candidates.append({
                "id": f"ladder{i:02d}_{end_name}",
                "type": "ladder_end_without_landing",
                "severity": 70,
                "element": {"kind": "ladder", "x": lad["x"], "z": lad["z"],
                            "y0": lad["y0"], "y1": lad["y1"]},
                "at": [lad["x"], y, lad["z"]],
                "drop_to_floor": world.drop_below(lad["x"], y, lad["z"]),
                "blocks_here": {"at": world.at(lad["x"], y, lad["z"])},
            })

    for i, door in enumerate(doors):
        x, y, z = door["pos"]
        sides = {t: world.standable(x + dx, y, z + dz)
                 for t, (dx, dz) in (("+x", (1, 0)), ("-x", (-1, 0)),
                                     ("+z", (0, 1)), ("-z", (0, -1)))}
        if sum(sides.values()) >= 2:
            continue
        candidates.append({
            "id": f"door{i:02d}",
            "type": "door_without_footing",
            "severity": 60,
            "element": {"kind": "door", "material": door["material"]},
            "at": [x, y, z],
            "standable_sides": sides,
            "blocks_here": {
                "below": world.at(x, y - 1, z),
                "+x": world.at(x + 1, y, z), "-x": world.at(x - 1, y, z),
                "+z": world.at(x, y, z + 1), "-z": world.at(x, y, z - 1),
            },
        })

    candidates.sort(key=lambda c: -c["severity"])
    candidates = candidates[:args.max_candidates]

    for cand in candidates:
        x, y, z = cand["at"]
        stem = cand["id"]
        sec = out_dir / "images" / f"{stem}_section.png"
        plan = out_dir / "images" / f"{stem}_plan.png"
        render(world, sec, "section", x - 6, x + 6,
               (z - 45, z + 45), (y - 22, y + 22),
               f"{stem} SECTION  x={x-6}..{x+6}  centre=({x},{y},{z})")
        render(world, plan, "plan", y - 3, y + 3,
               (x - 35, x + 35), (z - 35, z + 35),
               f"{stem} PLAN  y={y-3}..{y+3}  centre=({x},{y},{z})")
        cand["images"] = [str(sec.relative_to(ROOT)),
                          str(plan.relative_to(ROOT))]
        cand["teleport"] = (f"/execute in projectseele:geofront run tp @s "
                            f"{x} {y} {z}")

    report = {
        "world": args.world,
        "box": args.box,
        "counts": {"ramps": len(ramps), "ladder_runs": len(ladders),
                   "doors": len(doors), "candidates": len(candidates)},
        "note": ("Candidates are geometry observations, not verdicts. Look at "
                 "the rendered section and plan before judging, and check "
                 "blocks_here: decorative trapdoors and natural terrain have "
                 "produced false positives before."),
        "candidates": candidates,
    }
    (out_dir / "candidates.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8")
    print(f"[emit] {out_dir/'candidates.json'}  candidates={len(candidates)}")
    for cand in candidates[:15]:
        print(f"   {cand['severity']:>3} {cand['id']:<18} {cand['type']:<28} "
              f"at={cand['at']} drop={cand.get('drop_to_floor')}")


if __name__ == "__main__":
    main()
