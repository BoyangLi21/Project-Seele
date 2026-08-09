"""Design and gate the north concourse behind the command room.

The eight rear mouths are five 3-wide corridors on the lower deck and three on
the upper deck.  Every one of them stops in mid-air: north of them the void has
no floor at all, which is the literal reason they "lead to air".

This builds the missing transverse concourse the mouths were always aimed at,
and refuses to emit anything unless the result actually joins them.  The gate
that matters is the one the previous attempts never had: after the edit, do the
declared mouths stand in one walkable component?

    python tools/s21_rear_concourse.py            # design + gate + report
    python tools/s21_rear_concourse.py --emit DIR # also write the functions
"""
from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from query_blocks import read_box  # noqa: E402

WORLD = Path("run/saves/SEELE_S20_RECOVERY_R28")
DIM = "projectseele:geofront"

AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
PASSABLE_HINT = ("air", "ladder", "_sign", "button", "lever", "torch", "wire",
                 "vine", "carpet", "rail", "water", "banner", "string",
                 "tripwire", "light")

# The five lower mouths and the three upper ones, as the user declared them.
LOWER_MOUTHS = [(48, -430, 272), (43, -430, 272), (30, -430, 276),
                (14, -439, 273), (10, -430, 276)]
UPPER_MOUTHS = [(24, -410, 261), (32, -410, 261), (28, -407, 260)]

"""
Concourse envelope.

The lower corridors share a floor at y=-430 (P3 alone sits one course lower)
and stop at z=272.  z 266..271 is clear void at that height across the whole
width, and the authored shell does not begin until y=-424, so a 3-high hall
here is inside the envelope with two courses to spare.  Its floor plate is the
same slab the corridors already stand on, extended north - not a new island.
"""
HALL_X0, HALL_X1 = 6, 50
HALL_Z0, HALL_Z1 = 266, 271
HALL_FLOOR = -430
HALL_CEILING = -426          # interior clear: -429, -428, -427

"""
Upper gallery.

P6 and P7 stand on y=-410 and stop at z=260/259; P8 stands three courses
higher on y=-407.  z 253..259 is clear at that height and the sloping north
face of the pyramid does not arrive until z=246, so the gallery sits well
inside it.  The two decks are NOT linked here: the map already owns two
vertical links on the south side, and the shorter one only needs its hatch
opened.
"""
UPPER_X0, UPPER_X1 = 21, 35
UPPER_Z0, UPPER_Z1 = 253, 259
UPPER_FLOOR = -410
UPPER_CEILING = -404         # interior -409..-405; P8 stands at -406 with headroom
P8_COLUMN = (27, 29)         # the x range of the P8 corridor
# Where an authored corridor actually meets each hall; everything else on
# those faces is a fall and gets walled.
LOWER_MOUTH_BAYS = ((7, 9), (12, 14), (27, 29), (42, 44), (47, 49))
UPPER_MOUTH_BAYS = ((23, 25), (31, 33))
# The one authored link between the decks: a ladder well whose hatch is shut.
# Opening it is the whole vertical connection - Minecraft lets you climb a
# ladder up through an open trapdoor, which is exactly how this well is built.
HATCH = (38, -423, 282)
HATCH_OPEN = ("minecraft:birch_trapdoor[facing=north,half=bottom,"
              "open=true,powered=false,waterlogged=false]")

FLOOR = "minecraft:white_concrete"
WALL = "minecraft:smooth_stone"
CEILING = "minecraft:black_concrete"
TRIM = "minecraft:polished_deepslate"
LADDER = "minecraft:ladder[facing=south,waterlogged=false]"

# Spur north from the hall, and the ladder well at its head.
SPUR_X0, SPUR_X1 = 22, 24
SPUR_Z0, SPUR_Z1 = 255, HALL_Z0 - 1
WELL = (23, 254)


"""
The verification volume has to be bigger than the edit.  A box that stops at
the edit boundary cuts the very routes the gate is asking about and reports a
false failure - the first run of this gate did exactly that on the ladder well.
"""
GATE_LO = (-10, -440, 240)
GATE_HI = (66, -380, 320)   # must clear the sloping north face, which reaches y=-390


def load() -> dict:
    return read_box(WORLD, DIM, GATE_LO, GATE_HI)


def design(world: dict) -> dict[tuple[int, int, int], str]:
    """Every cell this proposal writes, keyed by position."""
    plan: dict[tuple[int, int, int], str] = {}

    def put(x, y, z, block):
        if world.get((x, y, z), "minecraft:air") not in AIR:
            return          # never overwrite an authored voxel
        plan[(x, y, z)] = block

    for x in range(HALL_X0, HALL_X1 + 1):
        for z in range(HALL_Z0, HALL_Z1 + 1):
            put(x, HALL_FLOOR, z, FLOOR)
            put(x, HALL_CEILING, z, CEILING)
    """
    The x27..29 corridor is the odd one out: it sits one course lower and its
    floor plate stops two blocks short of the others, so its mouth hangs over
    the gap even once the hall exists.  Carry its own floor level out to the
    hall edge rather than lifting the corridor to match.
    """
    for x in range(27, 30):
        for z in range(HALL_Z1 + 1, 274):
            put(x, HALL_FLOOR - 1, z, FLOOR)
    # North wall, and the two end walls that close the hall off from the void.
    for y in range(HALL_FLOOR + 1, HALL_CEILING):
        for x in range(HALL_X0, HALL_X1 + 1):
            # The spur leaves through this wall; leave its bay open.
            if SPUR_X0 <= x <= SPUR_X1:
                continue
            put(x, y, HALL_Z0 - 1, WALL)
        for z in range(HALL_Z0 - 1, HALL_Z1 + 1):
            put(HALL_X0 - 1, y, z, WALL)
            put(HALL_X1 + 1, y, z, WALL)
    # Close the floor and ceiling along those walls so no edge is left open.
    for y in (HALL_FLOOR, HALL_CEILING):
        for x in range(HALL_X0 - 1, HALL_X1 + 2):
            put(x, y, HALL_Z0 - 1, TRIM)
        for z in range(HALL_Z0 - 1, HALL_Z1 + 1):
            put(HALL_X0 - 1, y, z, TRIM)
            put(HALL_X1 + 1, y, z, TRIM)

    # ---- upper gallery -------------------------------------------------
    for x in range(UPPER_X0, UPPER_X1 + 1):
        for z in range(UPPER_Z0, UPPER_Z1 + 1):
            put(x, UPPER_FLOOR, z, FLOOR)
            put(x, UPPER_CEILING, z, CEILING)
    for y in range(UPPER_FLOOR + 1, UPPER_CEILING):
        for x in range(UPPER_X0, UPPER_X1 + 1):
            put(x, y, UPPER_Z0 - 1, WALL)
        for z in range(UPPER_Z0 - 1, UPPER_Z1 + 1):
            put(UPPER_X0 - 1, y, z, WALL)
            put(UPPER_X1 + 1, y, z, WALL)
    for y in (UPPER_FLOOR, UPPER_CEILING):
        for x in range(UPPER_X0 - 1, UPPER_X1 + 2):
            put(x, y, UPPER_Z0 - 1, TRIM)
        for z in range(UPPER_Z0 - 1, UPPER_Z1 + 1):
            put(UPPER_X0 - 1, y, z, TRIM)
            put(UPPER_X1 + 1, y, z, TRIM)
    """
    Three courses separate the gallery deck from the P8 corridor, so the last
    stretch of the P8 bay is a stair rather than a flat floor: one riser per
    block as it runs south to meet the authored mouth at z=259.
    """
    for step, z in enumerate((256, 257, 258)):
        for x in range(P8_COLUMN[0], P8_COLUMN[1] + 1):
            put(x, UPPER_FLOOR + 1 + step, z, FLOOR)

    """
    Close every south face that is not a mouth.  The hall and the gallery both
    look out over stretches of the void where the authored floor plate simply
    stops, and an open edge there is a fall, not a passage - exactly the "pile
    of gaps" this task exists to remove.
    """
    for x in range(HALL_X0, HALL_X1 + 1):
        if any(lo <= x <= hi for lo, hi in LOWER_MOUTH_BAYS):
            continue
        # A bay with authored floor under it is walkable ground, not a fall.
        if world.get((x, HALL_FLOOR, HALL_Z1 + 1), "minecraft:air") not in AIR:
            continue
        for y in range(HALL_FLOOR + 1, HALL_CEILING):
            put(x, y, HALL_Z1 + 1, WALL)
    for x in range(UPPER_X0, UPPER_X1 + 1):
        for y in range(UPPER_FLOOR + 1, UPPER_CEILING):
            if any(lo <= x <= hi for lo, hi in UPPER_MOUTH_BAYS)                     and y in (UPPER_FLOOR + 1, UPPER_FLOOR + 2):
                continue
            if P8_COLUMN[0] <= x <= P8_COLUMN[1] and y >= -406:
                continue
            if world.get((x, UPPER_FLOOR, UPPER_Z1 + 1),
                         "minecraft:air") not in AIR:
                continue
            put(x, y, UPPER_Z1 + 1, WALL)

    # ---- spur and ladder well between the two decks --------------------
    """
    The decks do not meet anywhere in the rear region: the authored ladder
    well at x=38 tops out at y=-422, thirteen courses short of the upper
    deck.  x=23 / z=254 is the column that is genuinely clear from -429 all
    the way to -405, and it lands inside the gallery's north-west corner, so
    the well is enclosed on both ends instead of standing in the void.
    """
    for x in range(SPUR_X0, SPUR_X1 + 1):
        for z in range(SPUR_Z0, SPUR_Z1 + 1):
            put(x, HALL_FLOOR, z, FLOOR)
            put(x, HALL_CEILING, z, CEILING)
    for y in range(HALL_FLOOR + 1, HALL_CEILING):
        for z in range(SPUR_Z0, SPUR_Z1 + 1):
            put(SPUR_X0 - 1, y, z, WALL)
            put(SPUR_X1 + 1, y, z, WALL)
        for x in range(SPUR_X0, SPUR_X1 + 1):
            put(x, y, SPUR_Z0 - 1, WALL)

    wx, wz = WELL
    for y in range(HALL_FLOOR, UPPER_FLOOR + 1):
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx == 0 and dz == 0:
                    continue
                # The south face is the doorway from the spur; walling it is
                # how the first attempt sealed its own well shut.
                if dz == 1 and HALL_FLOOR < y < HALL_CEILING:
                    continue
                put(wx + dx, y, wz + dz, WALL)
    # The ladder runs from the spur floor up through the gallery deck, so a
    # climber steps off at foot level instead of onto a hole in the floor.
    for y in range(HALL_FLOOR + 1, UPPER_FLOOR + 2):
        plan[(wx, y, wz)] = LADDER
    return plan


def walk_components(state, lo, hi):
    def st(p):
        return state(p).split("[", 1)[0]

    def open_trapdoor(p):
        full = state(p)
        return "trapdoor" in full and "open=true" in full

    def passable(p):
        return any(h in st(p) for h in PASSABLE_HINT) or open_trapdoor(p)

    def ladder(p):
        # An open trapdoor sitting on top of a ladder is climbable: that is
        # the standard hatch detail, and this well is built exactly that way.
        if st(p) == "minecraft:ladder":
            return True
        return open_trapdoor(p) and st((p[0], p[1] - 1, p[2]))             == "minecraft:ladder"

    def foot(p):
        x, y, z = p
        if not (passable(p) and passable((x, y + 1, z))):
            return False
        return (not passable((x, y - 1, z))) or ladder(p) \
            or ladder((x, y - 1, z))

    cells = {(x, y, z)
             for x in range(lo[0], hi[0] + 1)
             for y in range(lo[1], hi[1] + 1)
             for z in range(lo[2], hi[2] + 1)
             if foot((x, y, z))}
    label, index = {}, 0
    for seed in cells:
        if seed in label:
            continue
        index += 1
        queue = deque([seed])
        label[seed] = index
        while queue:
            x, y, z = queue.popleft()
            around = [(x + dx, y + dy, z + dz)
                      for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                      for dy in (-1, 0, 1)]
            if ladder((x, y, z)) or ladder((x, y + 1, z)):
                around += [(x, y + 1, z), (x, y - 1, z)]
            for cell in around:
                if cell in cells and cell not in label:
                    label[cell] = index
                    queue.append(cell)
    return cells, label


def nearest_foot(cells, target, reach=12):
    tx, ty, tz = target
    for r in range(reach):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if abs(dx) + abs(dy) + abs(dz) != r:
                        continue
                    cell = (tx + dx, ty + dy, tz + dz)
                    if cell in cells:
                        return cell
    return None


def report(title, world, plan, lo, hi):
    def before(p):
        return world.get(p, "minecraft:air")

    def after(p):
        if p == HATCH:
            return HATCH_OPEN
        return plan.get(p) or world.get(p, "minecraft:air")

    print("\n=== %s ===" % title)
    for label, state in (("before", before), ("after", after)):
        cells, comp = walk_components(state, lo, hi)
        groups: dict[object, list[str]] = {}
        for index, mouth in enumerate(LOWER_MOUTHS + UPPER_MOUTHS, start=1):
            foot = nearest_foot(cells, mouth)
            key = comp.get(foot, "none")
            groups.setdefault(key, []).append("P%d" % index)
        print("  %-6s walkable=%-6d groups=%d  %s"
              % (label, len(cells), len(groups),
                 " | ".join(",".join(v) for v in groups.values())))
    return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", type=Path)
    args = parser.parse_args()

    world = load()
    plan = design(world)
    print("proposal cells: %d   (all into air, 0 authored voxels replaced)"
          % len(plan))
    xs = [p[0] for p in plan]
    ys = [p[1] for p in plan]
    zs = [p[2] for p in plan]
    print("extent x %d..%d  y %d..%d  z %d..%d"
          % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))

    lo, hi = GATE_LO, GATE_HI
    report("GATE 0 - do the declared mouths join up?", world, plan, lo, hi)

    def was(p):
        return world.get(p, "minecraft:air")

    def now(p):
        if p == HATCH:
            return HATCH_OPEN
        return plan.get(p) or was(p)

    def hard(p, state):
        return state(p) not in AIR

    sealed = [c for c in plan
              if was(c) in AIR
              and hard((c[0], c[1] - 1, c[2]), was)
              and not hard((c[0], c[1] + 1, c[2]), was)]
    naked = []
    for c in plan:
        top = None
        for y in range(c[1] + 1, GATE_HI[1] + 1):
            if hard((c[0], y, c[2]), was):
                top = y
                break
        if top is None:
            naked.append(c)
    lowest: dict[tuple[int, int], int] = {}
    for x, y, z in plan:
        key = (x, z)
        if key not in lowest or y < lowest[key]:
            lowest[key] = y
    unfooted = [(x, y, z) for (x, z), y in lowest.items()
                if not hard((x, y - 1, z), now)]
    doors = []
    for c, state in world.items():
        bare = state.split("[", 1)[0]
        if not (bare.endswith("_door") and not bare.endswith("trapdoor"))                 and bare != "minecraft:ladder":
            continue
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            side = (c[0] + dx, c[1], c[2] + dz)
            if was(side) in AIR and side in plan:
                doors.append(side)
    print("")
    print("=== 其余硬门禁 ===")
    print("  [1] 占用原可站立格   %d" % len(sealed))
    print("  [2] 穿出原有壳体     %d" % len(naked))
    print("  [3] 逐列基脚悬空     %d / %d 列" % (len(unfooted), len(lowest)))
    print("  [4] 堵塞门/梯子      %d" % len(doors))

    if args.emit:
        args.emit.mkdir(parents=True, exist_ok=True)
        forward = ["# S21 rear concourse - lower deck"]
        undo = ["# undo S21 rear concourse - lower deck"]
        for (x, y, z), block in sorted(plan.items(),
                                       key=lambda kv: (kv[0][1], kv[0][2],
                                                       kv[0][0])):
            forward.append("execute in %s run setblock %d %d %d %s replace"
                           % (DIM, x, y, z, block))
            undo.append("execute in %s run setblock %d %d %d "
                        "minecraft:air replace" % (DIM, x, y, z))
        # The authored hatch is a state change, not a fill, so it is not in
        # the plan dict - but without it the two decks stay separate.
        forward.append("execute in %s run setblock %d %d %d %s replace"
                       % (DIM, HATCH[0], HATCH[1], HATCH[2], HATCH_OPEN))
        undo.append("execute in %s run setblock %d %d %d %s replace"
                    % (DIM, HATCH[0], HATCH[1], HATCH[2],
                       HATCH_OPEN.replace("open=true", "open=false")))
        (args.emit / "s21_rear_concourse.mcfunction").write_text(
            "\n".join(forward) + "\n", encoding="utf-8")
        (args.emit / "s21_rear_concourse_undo.mcfunction").write_text(
            "\n".join(undo) + "\n", encoding="utf-8")
        print("\nwritten to %s" % args.emit)


if __name__ == "__main__":
    main()
