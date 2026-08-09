"""Two horizontal links onto the rear command lift, gated before emission.

Link B joins the command gallery - and through it the commander's dais - to
the lift's new upper level at (13,-409,254).
Link C joins the x27..29 corridor at foot level -418 to the lift head slab.

Both are gated the same way the concourse was: the run is only emitted if the
declared endpoints actually end up in one walkable component afterwards.

    python tools/s21_lift_links.py [--emit DIR]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s21_rear_concourse as base  # noqa: E402
from query_blocks import read_box  # noqa: E402

AIR = base.AIR
FLOOR = base.FLOOR
WALL = base.WALL
CEILING = base.CEILING
TRIM = base.TRIM

"""
Link B - gallery deck to the lift's new level.

The gallery already has a one-wide gap in its west wall at z=254; widening it
to the three-wide section every other mouth uses is the only opening needed.
West of it the volume is empty from y=-418 to -405, so the corridor is free.
"""
B_X0, B_X1 = 13, 19          # 13/14 already carry the human's marker slab
B_Z0, B_Z1 = 253, 255
B_FLOOR = -410
B_CEILING = -406             # interior -409..-407, matching the P8 section
B_DOOR_X = 20                # gallery west wall, opened three wide

"""
Link C - the x27..29 corridor to the lift head.

The corridor stands on an authored slab at y=-419 and is walled at x=26; the
lift head stands on its own slab at x 9..15.  Between them x16..25 has no
floor at all, so the two spaces are a fall apart rather than a wall apart.
"""
C_X0, C_X1 = 16, 25
# z=253 is included so the B-18 landing's route handoff, seven blocks east of
# the shaft at (19,-418,253), lands inside the corridor rather than in its
# south wall.  The ladder well already occupies x22..24 there, so those three
# columns stay as they are and the bay simply narrows past them.
C_Z0, C_Z1 = 250, 253
C_FLOOR = -419
C_CEILING = -415             # interior -418..-416
C_DOOR_X = 26                # authored corridor wall, opened three wide

# What each link has to achieve, checked after the edit.
ENDPOINTS = [
    ("lift-B10-landing", (19, -409, 253)),
    ("commander-dais", (28, -406, 272)),
    ("corridor-x28", (28, -418, 258)),
    ("lift-B18-landing", (19, -418, 253)),
]


def load() -> dict:
    return read_box(base.WORLD, base.DIM, (4, -424, 244), (34, -402, 264))


def design(world: dict):
    plan: dict[tuple[int, int, int], str] = {}
    cut: list[tuple[int, int, int]] = []

    def put(x, y, z, block):
        if world.get((x, y, z), "minecraft:air") not in AIR:
            return
        plan[(x, y, z)] = block

    def open_up(x, y, z):
        if world.get((x, y, z), "minecraft:air") not in AIR:
            cut.append((x, y, z))

    def bay(x0, x1, z0, z1, floor, ceiling, door_x, close_west,
            door_height=3):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                put(x, floor, z, FLOOR)
                put(x, ceiling, z, CEILING)
        for y in range(floor + 1, ceiling):
            for x in range(x0, x1 + 1):
                put(x, y, z0 - 1, WALL)
                put(x, y, z1 + 1, WALL)
            # Link B terminates at the lift landing, so its west end is
            # closed.  Link C runs straight onto the lift head slab, so its
            # west end must stay open - walling it was what kept the first
            # run from connecting anything.
            if close_west:
                for z in range(z0, z1 + 1):
                    put(x0 - 1, y, z, WALL)
        for y in (floor, ceiling):
            for x in range(x0 - 1, x1 + 2):
                put(x, y, z0 - 1, TRIM)
                put(x, y, z1 + 1, TRIM)
        # A two-high doorway is enough to walk through and costs three fewer
        # panes of the authored glazing band than a full-height one.
        for y in range(floor + 1, floor + 1 + door_height):
            for z in range(z0, z1 + 1):
                open_up(door_x, y, z)

    """
    The previous revision walled z=253 as link C's south face.  That course is
    now the corridor's own floor plate, and the B-18 landing hands off through
    it, so the stretch has to come back out - except the three columns the
    ladder well legitimately occupies.
    """
    for x in range(C_X0, C_X1 + 1):
        if 22 <= x <= 24:
            continue
        for y in range(C_FLOOR + 1, C_CEILING):
            if world.get((x, y, 253), "minecraft:air") == WALL:
                cut.append((x, y, 253))

    bay(B_X0, B_X1, B_Z0, B_Z1, B_FLOOR, B_CEILING, B_DOOR_X, True)
    bay(C_X0, C_X1, C_Z0, C_Z1, C_FLOOR, C_CEILING, C_DOOR_X, False,
        door_height=2)
    return plan, cut


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", type=Path)
    args = parser.parse_args()

    world = load()
    plan, cut = design(world)
    print("fill %d cells, cut %d authored cells" % (len(plan), len(cut)))
    from collections import Counter
    print("cut materials:", dict(Counter(
        world[c].split("[")[0].replace("minecraft:", "") for c in cut)))

    wide = read_box(base.WORLD, base.DIM, base.GATE_LO, base.GATE_HI)

    def before(p):
        return wide.get(p, "minecraft:air")

    def after(p):
        if p in cut:
            return "minecraft:air"
        return plan.get(p) or before(p)

    for label, state in (("before", before), ("after", after)):
        cells, comp = base.walk_components(state, base.GATE_LO, base.GATE_HI)
        groups: dict[object, list[str]] = {}
        for name, target in ENDPOINTS:
            foot = base.nearest_foot(cells, target, reach=3)
            groups.setdefault(comp.get(foot), []).append(name)
        print("  %-6s groups=%d  %s"
              % (label, len(groups),
                 " | ".join(",".join(v) for v in groups.values())))

    if args.emit:
        args.emit.mkdir(parents=True, exist_ok=True)
        fwd = ["# S21 lift links B and C"]
        undo = ["# undo S21 lift links B and C"]
        for c in cut:
            fwd.append("execute in %s run setblock %d %d %d minecraft:air "
                       "replace" % (base.DIM, *c))
            undo.append("execute in %s run setblock %d %d %d %s replace"
                        % (base.DIM, *c, world[c]))
        for c, block in sorted(plan.items(),
                               key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            fwd.append("execute in %s run setblock %d %d %d %s replace"
                       % (base.DIM, *c, block))
            undo.append("execute in %s run setblock %d %d %d minecraft:air "
                        "replace" % (base.DIM, *c))
        (args.emit / "s21_lift_links.mcfunction").write_text(
            "\n".join(fwd) + "\n", encoding="utf-8")
        (args.emit / "s21_lift_links_undo.mcfunction").write_text(
            "\n".join(undo) + "\n", encoding="utf-8")
        print("written to %s" % args.emit)


if __name__ == "__main__":
    main()
