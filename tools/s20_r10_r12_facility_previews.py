#!/usr/bin/env python3
"""Read-only previews for the next human-directed S20 facility repairs.

The live human-edited save is never written.  Each proposal is compiled into
an in-memory voxel volume and emitted through the established exact-diff,
fixed-camera approval packet pipeline.

R10 relocates the command personnel lift to the explicitly selected x/z axis,
turns its upper landing toward the measured command passage, and builds only
the short lower T-join that the new landing requires.

R11 adds a compact west-side lift between the launch observation gallery and
the retained hangar circulation.  Its two short orthogonal approaches remain
outside every 31x31 EVA carrier aperture.

R12 is additive-only launch-well recovery.  It restores missing canonical
foundation/shell cells while retaining every existing authored block, all
three north carrier apertures, and the human-cleared route area.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_semantic_repair_previews as repair  # noqa: E402
import s20_r06_r07_topology_previews as topology  # noqa: E402
import survey_facility_target as survey  # noqa: E402


AIR = "minecraft:air"
POLISHED = "minecraft:polished_deepslate"
REINFORCED = "minecraft:reinforced_deepslate"
TILES = "minecraft:deepslate_tiles"
BLACKSTONE = "minecraft:polished_blackstone_bricks"
IRON = "minecraft:iron_block"
QUARTZ = "minecraft:smooth_quartz"
BLACK = "minecraft:black_concrete"
ORANGE = "minecraft:orange_concrete"
PURPLE = "minecraft:purple_concrete"
RED = "minecraft:red_concrete"
GRAY_GLASS = "minecraft:gray_stained_glass"
LIGHT_GRAY_GLASS = "minecraft:light_gray_stained_glass"
SEA_LANTERN = "minecraft:sea_lantern"
POLISHED_BASALT = "minecraft:polished_basalt[axis=y]"
LADDER_NORTH = "minecraft:ladder[facing=north,waterlogged=false]"

# The human explicitly cleared the obsolete east-side stair/bridge by hand.
# This is a protected observation envelope, not a repair mask.  New packets
# must prove that none of their changed coordinates enter it.
HUMAN_CLEARED_EAST_ROUTE = (90, 105, -430, -390, 135, 205)


def state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


def base(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return survey.base_name(state(volume, x, y, z))


def put(volume: survey.Volume,
        reasons: dict[tuple[int, int, int], str],
        x: int, y: int, z: int, value: str, reason: str) -> None:
    repair.set_proposed(volume, reasons, x, y, z, value, reason)


def put_if_missing(volume: survey.Volume,
                   reasons: dict[tuple[int, int, int], str],
                   x: int, y: int, z: int, value: str,
                   reason: str) -> None:
    role = survey.role_of(state(volume, x, y, z))
    if role in {"air", "fluid", "natural"}:
        put(volume, reasons, x, y, z, value, reason)


def button(facing: str) -> str:
    return ("minecraft:polished_blackstone_button[face=wall,facing="
            + facing + ",powered=false]")


def protected_overlap(reasons: dict[tuple[int, int, int], str],
                      box: tuple[int, int, int, int, int, int]) -> int:
    x0, x1, y0, y1, z0, z1 = box
    return sum(1 for x, y, z in reasons
               if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1)


def build_enclosed_hall(volume: survey.Volume,
                        reasons: dict[tuple[int, int, int], str],
                        start: int, end: int, fixed: int, floor_y: int,
                        along_x: bool, reason: str) -> None:
    """Build a five-wide, four-high personnel pressure section."""
    lo, hi = sorted((start, end))
    for axis in range(lo, hi + 1):
        for lateral in range(-3, 4):
            x, z = ((axis, fixed + lateral) if along_x
                    else (fixed + lateral, axis))
            if abs(lateral) <= 2:
                put(volume, reasons, x, floor_y - 1, z,
                    REINFORCED, reason + ":support")
                put(volume, reasons, x, floor_y, z,
                    SEA_LANTERN if (axis + lateral) % 11 == 0
                    else POLISHED, reason + ":floor")
                for y in range(floor_y + 1, floor_y + 5):
                    put(volume, reasons, x, y, z, AIR,
                        reason + ":headroom")
                put(volume, reasons, x, floor_y + 5, z,
                    SEA_LANTERN if (axis - lateral) % 13 == 0
                    else TILES, reason + ":ceiling")
            else:
                put(volume, reasons, x, floor_y - 1, z,
                    REINFORCED, reason + ":wall-support")
                for y in range(floor_y, floor_y + 6):
                    material = (GRAY_GLASS if y in (floor_y + 2,
                                                    floor_y + 3)
                                else (ORANGE if y == floor_y + 1
                                      else TILES))
                    put(volume, reasons, x, y, z, material,
                        reason + ":side-shell")


def open_hall_junction(volume: survey.Volume,
                       reasons: dict[tuple[int, int, int], str],
                       centre_x: int, centre_z: int, floor_y: int,
                       reason: str) -> None:
    for x in range(centre_x - 2, centre_x + 3):
        for z in range(centre_z - 2, centre_z + 3):
            put(volume, reasons, x, floor_y - 1, z, REINFORCED,
                reason + ":support")
            put(volume, reasons, x, floor_y, z,
                SEA_LANTERN if (x + z) % 9 == 0 else POLISHED,
                reason + ":floor")
            for y in range(floor_y + 1, floor_y + 5):
                put(volume, reasons, x, y, z, AIR,
                    reason + ":headroom")
            put(volume, reasons, x, floor_y + 5, z, TILES,
                reason + ":ceiling")


def build_landing(volume: survey.Volume,
                  reasons: dict[tuple[int, int, int], str],
                  cx: int, walk_y: int, cz: int, direction: str,
                  door_open: bool, reason: str) -> None:
    steps = {"north": (0, -1), "south": (0, 1),
             "east": (1, 0), "west": (-1, 0)}
    dx, dz = steps[direction]
    # Minecraft clockwise horizontal direction.
    lateral = {"north": (1, 0), "east": (0, 1),
               "south": (-1, 0), "west": (0, -1)}[direction]
    lx, lz = lateral
    for depth in (5, 6):
        for side in range(-2, 3):
            x = cx + dx * depth + lx * side
            z = cz + dz * depth + lz * side
            put(volume, reasons, x, walk_y - 1, z,
                SEA_LANTERN if (side + depth) % 7 == 0 else POLISHED,
                reason + ":threshold")
            for y in range(walk_y, walk_y + 3):
                put(volume, reasons, x, y, z, AIR,
                    reason + ":threshold-headroom")
    for side in (-3, 3):
        for dy in range(-1, 5):
            x = cx + dx * 4 + lx * side
            z = cz + dz * 4 + lz * side
            put(volume, reasons, x, walk_y + dy, z,
                ORANGE if dy == 2 else REINFORCED,
                reason + ":frame")
    for side in range(-2, 3):
        x = cx + dx * 4 + lx * side
        z = cz + dz * 4 + lz * side
        put(volume, reasons, x, walk_y + 3, z,
            SEA_LANTERN if side == 0 else REINFORCED,
            reason + ":header")
        for dy in range(3):
            put(volume, reasons, x, walk_y + dy, z,
                AIR if door_open else GRAY_GLASS,
                reason + ":landing-door")
    panel_x = cx + dx * 4 + lx * 3
    panel_z = cz + dz * 4 + lz * 3
    put(volume, reasons, panel_x, walk_y + 1, panel_z,
        ORANGE, reason + ":call-panel")
    put(volume, reasons, panel_x + dx, walk_y + 1, panel_z + dz,
        button(direction), reason + ":call-button")


def build_physical_lift(volume: survey.Volume,
                        reasons: dict[tuple[int, int, int], str],
                        cx: int, cz: int, lower_y: int, upper_y: int,
                        lower_direction: str, upper_direction: str,
                        reason: str) -> None:
    directions = {"north": (0, -1), "south": (0, 1),
                  "east": (1, 0), "west": (-1, 0)}
    # Complete fixed pressure shaft around the moving 5x5 cabin.
    for y in range(lower_y - 1, upper_y + 5):
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                if max(abs(dx), abs(dz)) != 3:
                    continue
                aperture = False
                for walk_y, direction in ((lower_y, lower_direction),
                                          (upper_y, upper_direction)):
                    sx, sz = directions[direction]
                    forward = dx * sx + dz * sz
                    lateral = dx * (-sz) + dz * sx
                    if (y in range(walk_y, walk_y + 3)
                            and forward == 3 and abs(lateral) <= 2):
                        aperture = True
                value = AIR if aperture else (
                    SEA_LANTERN if (y - lower_y) % 12 == 0
                    and (dx == 0 or dz == 0) else REINFORCED)
                put(volume, reasons, cx + dx, y, cz + dz, value,
                    reason + ":shaft-shell")
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            put(volume, reasons, cx + dx, lower_y - 2, cz + dz,
                REINFORCED, reason + ":shaft-foundation")

    build_landing(volume, reasons, cx, lower_y, cz, lower_direction,
                  True, reason + ":lower")
    build_landing(volume, reasons, cx, upper_y, cz, upper_direction,
                  False, reason + ":upper")

    # One real cabin parked at the lower stop.
    exit_x, exit_z = directions[lower_direction]
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            put(volume, reasons, cx + dx, lower_y - 1, cz + dz,
                POLISHED, reason + ":cabin-floor")
            put(volume, reasons, cx + dx, lower_y + 4, cz + dz,
                QUARTZ, reason + ":cabin-roof")
            if abs(dx) != 2 and abs(dz) != 2:
                continue
            forward = dx * exit_x + dz * exit_z
            lateral = dx * (-exit_z) + dz * exit_x
            for dy in range(4):
                is_door = forward == 2 and abs(lateral) <= 1 and dy < 3
                put(volume, reasons, cx + dx, lower_y + dy, cz + dz,
                    AIR if is_door else IRON,
                    reason + ":cabin-wall")
    # In-cabin two-button panel, matching the runtime contract.
    side_x, side_z = -exit_z, exit_x
    panel_x = cx + side_x * 2
    panel_z = cz + side_z * 2
    put(volume, reasons, panel_x, lower_y + 1, panel_z,
        BLACK, reason + ":cabin-panel")
    put(volume, reasons, panel_x, lower_y + 2, panel_z,
        BLACK, reason + ":cabin-panel")
    facing = {"north": "west", "south": "east",
              "east": "north", "west": "south"}[lower_direction]
    put(volume, reasons, panel_x - side_x, lower_y + 1,
        panel_z - side_z, button(facing), reason + ":cabin-button")
    put(volume, reasons, panel_x - side_x, lower_y + 2,
        panel_z - side_z, button(facing), reason + ":cabin-button")


def remove_old_command_lift(volume: survey.Volume,
                            reasons: dict[tuple[int, int, int], str]) -> None:
    reason = "retire-old-command-lift"
    lift_palette = {POLISHED, IRON, QUARTZ, BLACK,
                    LIGHT_GRAY_GLASS, GRAY_GLASS,
                    REINFORCED, ORANGE, SEA_LANTERN,
                    "minecraft:polished_blackstone_button"}
    # The saved cabin is parked at the lower stop.  This exact bounded cabin
    # does not include the R06 observation connector crossing the old axis.
    for x in range(26, 31):
        for y in range(-449, -443):
            for z in range(250, 255):
                if base(volume, x, y, z) in lift_palette:
                    put(volume, reasons, x, y, z, AIR, reason + ":cabin")
    # Two known landing assemblies.  The door plane is closed with a compact
    # NERV wall instead of leaving either abandoned opening exposed.
    for walk_y in (-448, -406):
        for x in range(25, 32):
            for y in range(walk_y - 1, walk_y + 5):
                for z in range(256, 259):
                    if base(volume, x, y, z) in lift_palette:
                        put(volume, reasons, x, y, z, AIR,
                            reason + ":landing-hardware")
        for x in range(25, 32):
            for y in range(walk_y - 1, walk_y + 5):
                put(volume, reasons, x, y, 256,
                    ORANGE if y == walk_y + 2 else TILES,
                    reason + ":sealed-former-door")


def build_r10(world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R10-COMMAND-LIFT-RELOCATION-PREVIEW-r01"
    box = (6, 34, -452, -400, 244, 286)
    anchor = (12, -446, 253)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}
    remove_old_command_lift(after, reasons)
    build_physical_lift(after, reasons, 12, 253, -448, -406,
                        "south", "north", "relocated-command-lift")
    # Lower stop turns east into the retained B-40 north/south route.
    build_enclosed_hall(after, reasons, 12, 28, 260, -449, True,
                        "relocated-lift-lower-link")
    open_hall_junction(after, reasons, 28, 260, -449,
                       "relocated-lift-b40-junction")
    overlap = protected_overlap(reasons, HUMAN_CLEARED_EAST_ROUTE)
    if overlap:
        raise RuntimeError(f"R10 enters human-cleared east route: {overlap}")
    output = output_root / repair_id
    digest = repair.emit_preview(
        world_root, output, repair_id, box, anchor, before, after, reasons,
        ["retire the exact old lower cabin and two old landing assemblies",
         "move the physical command lift to axis x=12,z=253",
         "lower stop opens south and turns east into retained B-40",
         "upper stop opens north directly onto the measured z=248 passage"],
        {"new_axis": [12, 253], "walk_y": [-448, -406],
         "lower_exit": "south", "upper_exit": "north",
         "human_cleared_wrong_stair_touched": False,
         "human_cleared_protected_box": list(HUMAN_CLEARED_EAST_ROUTE),
         "human_cleared_overlap_count": overlap})
    topology.render_feet_layers(
        before, after, [-448, -406], anchor,
        output / "08_endpoint_walkspace.png")
    return repair_id, digest


def build_r11(world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R11-OBSERVATION-HANGAR-LIFT-PREVIEW-r01"
    box = (-48, -26, -423, -388, 176, 246)
    anchor = (-40, -406, 200)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}
    build_physical_lift(after, reasons, -40, 200, -418, -394,
                        "south", "north", "observation-hangar-lift")
    build_enclosed_hall(after, reasons, 207, 241, -40, -419, False,
                        "lower-gallery-approach")
    build_enclosed_hall(after, reasons, -40, -35, 241, -419, True,
                        "lower-gallery-final-link")
    open_hall_junction(after, reasons, -40, 241, -419,
                       "lower-gallery-corner")
    build_enclosed_hall(after, reasons, 183, 193, -40, -395, False,
                        "upper-hangar-approach")
    build_enclosed_hall(after, reasons, -40, -31, 183, -395, True,
                        "upper-hangar-final-link")
    open_hall_junction(after, reasons, -40, 183, -395,
                       "upper-hangar-corner")
    overlap = protected_overlap(reasons, HUMAN_CLEARED_EAST_ROUTE)
    if overlap:
        raise RuntimeError(f"R11 enters human-cleared east route: {overlap}")
    output = output_root / repair_id
    digest = repair.emit_preview(
        world_root, output, repair_id, box, anchor, before, after, reasons,
        ["new west-side physical lift from observation feet y=-418 to hangar feet y=-394",
         "two orthogonal sealed approaches outside all EVA carrier apertures",
         "open only the measured west gallery and hangar-circulation interfaces"],
        {"axis": [-40, 200], "walk_y": [-418, -394],
         "eva_well_centres": [[-12, 220], [30, 220], [72, 220]],
         "minimum_x_clearance_from_west_well_shell": 7,
         "human_cleared_east_stair_touched": False,
         "human_cleared_protected_box": list(HUMAN_CLEARED_EAST_ROUTE),
         "human_cleared_overlap_count": overlap})
    topology.render_feet_layers(
        before, after, [-418, -394], anchor,
        output / "08_endpoint_walkspace.png")
    return repair_id, digest


def shaft_wall(relative_y: int, dx: int, dz: int,
               accent: str) -> str:
    if relative_y % 32 == 0:
        return accent
    if relative_y % 8 == 0 and (dx == 0 or dz == 0):
        return SEA_LANTERN
    if abs(dx) == 17 and abs(dz) == 17:
        return IRON
    return REINFORCED


def build_r12(world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R12-THREE-LAUNCH-WELL-ADDITIVE-RESTORE-PREVIEW-r01"
    box = (-31, 89, -447, -368, 201, 239)
    anchor = (30, -408, 220)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}
    centres = (-12, 30, 72)
    accents = (ORANGE, PURPLE, RED)
    for cx, accent in zip(centres, accents):
        # Two-layer raft: additive only, so manual or authored non-air blocks
        # can never be replaced by this recovery packet.
        for y in (-445, -444):
            for dx in range(-17, 18):
                for dz in range(-17, 18):
                    beam = (y == -445 or dx % 8 == 0 or dz % 8 == 0)
                    put_if_missing(after, reasons, cx + dx, y, 220 + dz,
                                   REINFORCED if beam else POLISHED,
                                   "launch-well-foundation-missing-only")
        for y in range(-443, -369):
            relative_y = y - (-442)
            for dx in range(-17, 18):
                for dz in range(-17, 18):
                    if max(abs(dx), abs(dz)) != 17:
                        continue
                    carrier_aperture = dz == -17 and abs(dx) <= 15
                    if carrier_aperture:
                        continue
                    if (y >= -442 and y <= -382
                            and dz == 17 and abs(dx) <= 15):
                        expected = GRAY_GLASS
                    else:
                        expected = shaft_wall(relative_y, dx, dz, accent)
                    put_if_missing(after, reasons, cx + dx, y, 220 + dz,
                                   expected,
                                   "launch-well-shell-missing-only")
            if y >= -442:
                for dx in (-16, 16):
                    for dz in (-16, 16):
                        put_if_missing(after, reasons, cx + dx, y,
                                       220 + dz, POLISHED_BASALT,
                                       "launch-well-guide-missing-only")
                put_if_missing(after, reasons, cx, y, 236,
                               LADDER_NORTH,
                               "launch-well-ladder-missing-only")
    overlap = protected_overlap(reasons, HUMAN_CLEARED_EAST_ROUTE)
    if overlap:
        raise RuntimeError(f"R12 enters human-cleared east route: {overlap}")
    output = output_root / repair_id
    digest = repair.emit_preview(
        world_root, output, repair_id, box, anchor, before, after, reasons,
        ["restore only absent/natural/fluid cells in the three canonical foundation rafts",
         "restore only absent/natural/fluid cells in the three canonical pressure shells",
         "retain all existing authored blocks and all north EVA carrier apertures",
         "never clear any interior volume or replay an old broad builder"],
        {"well_centres": [[x, -443, 220] for x in centres],
         "outer_radius": 17, "clear_radius": 15,
         "additive_only": True,
         "north_carrier_apertures_preserved": True,
         "human_manual_route_edits_touched": False,
         "human_cleared_protected_box": list(HUMAN_CLEARED_EAST_ROUTE),
         "human_cleared_overlap_count": overlap})
    return repair_id, digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True,
                        help="Path to dimensions/projectseele/geofront")
    parser.add_argument("--emit-root", default="artifacts/map_previews")
    parser.add_argument("--repair", choices=("r10", "r11", "r12", "all"),
                        default="all")
    args = parser.parse_args()
    world = Path(args.world).resolve()
    output = Path(args.emit_root).resolve()
    builders = {"r10": build_r10, "r11": build_r11, "r12": build_r12}
    selected = builders.items() if args.repair == "all" else [
        (args.repair, builders[args.repair])]
    for _name, builder in selected:
        repair_id, digest = builder(world, output)
        print(f"{repair_id} {digest}")


if __name__ == "__main__":
    main()
