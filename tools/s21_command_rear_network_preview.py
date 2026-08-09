#!/usr/bin/env python3
"""Compile the compact S21 command-room rear circulation preview in memory.

The eight user-declared rear outlets terminate at three authored elevations.
This revision joins them with a shallow transverse service corridor and one
narrow central stair core; it deliberately avoids the rejected full-width
atrium/annex mass.  It emits a reversible packet and never writes the save.
"""
from __future__ import annotations

import argparse
import heapq
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np  # noqa: E402

import s20_r06_r07_topology_previews as topology  # noqa: E402
import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


REPAIR_ID = "S21-COMMAND-REAR-NETWORK-PREVIEW-r02"
BOX = (4, 52, -441, -403, 242, 304)
ANCHOR = (28, -418, 260)
DEBUG_COMPONENT_BOX = (4, 52, -441, -403, 242, 304)
REAR_REPRESENTATIVES = {
    "lower_east_outer": (48, -429, 272),
    "lower_east_inner": (43, -429, 272),
    "lower_centre": (28, -430, 277),
    "lower_west_inner": (13, -429, 272),
    "lower_west_outer": (8, -429, 276),
    "upper_west": (24, -409, 265),
    "upper_east": (32, -409, 265),
    "upper_centre": (28, -406, 265),
    "existing_centre_bridge": (28, -412, 250),
}

CONNECTION_SPECS = {
    "lower-side-to-centre": (
        "lower_west_inner", "lower_centre",
        (4, 52, -431, -420, 270, 304)),
    "lower-centre-to-upper-side": (
        "lower_centre", "upper_west",
        (18, 38, -431, -404, 270, 304)),
    "upper-side-to-bridge": (
        "upper_west", "existing_centre_bridge",
        (20, 36, -414, -406, 255, 280)),
    "upper-side-to-centre": (
        "upper_west", "upper_centre",
        (20, 36, -412, -404, 255, 280)),
}

BREAKPOINT_IDS = {
    "upper-side-to-bridge": "S21-COMMAND-REAR-B1-N2-N5-PREVIEW-r02",
    "upper-side-to-centre": "S21-COMMAND-REAR-B2-N2-N4-PREVIEW-r02",
    "lower-centre-to-upper-side": "S21-COMMAND-REAR-B3-N3-N2-PREVIEW-r02",
    "lower-side-to-centre": "S21-COMMAND-REAR-B4-N1-N3-PREVIEW-r02",
}

PATH_PROTECTED_TOKENS = (
    "seat", "button", "lever", "sign", "banner", "glass", "door",
    "ladder", "trapdoor", "stool", "sofa", "chair", "screen", "magi",
)

AIR = {
    "minecraft:air", "minecraft:cave_air", "minecraft:void_air",
    # Invisible light blocks are passable runtime illumination, not authored
    # geometry. Replacing them where a structural cell is required is safe.
    "minecraft:light",
}
WHITE = "minecraft:white_concrete"
POLISHED = "minecraft:polished_deepslate"
TILES = "minecraft:deepslate_tiles"
SMOOTH = "minecraft:smooth_stone"
BLACK = "minecraft:black_concrete"
RED = "minecraft:red_concrete"
LIGHT = "minecraft:sea_lantern"
GLASS = "projectseele:clear_glass"
STAIR_NORTH = (
    "minecraft:polished_deepslate_stairs"
    "[facing=north,half=bottom,shape=straight,waterlogged=false]"
)
STAIR_SOUTH = (
    "minecraft:polished_deepslate_stairs"
    "[facing=south,half=bottom,shape=straight,waterlogged=false]"
)


def state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


def path_cell_cost(volume: survey.Volume,
                   point: tuple[int, int, int]) -> tuple[int, tuple] | None:
    """Cost a feet cell that can be opened without inventing a floor.

    This planner is deliberately conservative: the floor must already be
    solid, and protected fixtures/art assets are never candidates for removal.
    It is a topology probe, not a builder.
    """
    x, y, z = point
    if not (volume.x0 <= x <= volume.x1
            and volume.y0 + 1 <= y < volume.y1
            and volume.z0 <= z <= volume.z1):
        return None
    floor = state(volume, x, y - 1, z)
    if survey.role_of(floor) in {"air", "fixture", "door", "fluid"}:
        return None
    removals = []
    cost = 0
    for body_y in (y, y + 1):
        current = state(volume, x, body_y, z)
        role = survey.role_of(current)
        if role in {"air", "fixture", "door"}:
            continue
        low = survey.base_name(current).lower()
        if any(token in low for token in PATH_PROTECTED_TOKENS):
            return None
        removals.append((x, body_y, z, current))
        cost += 80 if role == "natural" else 24
    return cost, tuple(removals)


def supported_path(volume: survey.Volume,
                   labels: np.ndarray,
                   source_id: int,
                   target_id: int,
                   bounds: tuple[int, int, int, int, int, int],
                   forbidden: set[tuple[int, int, int]] | None = None) -> dict:
    """Find the least-destructive stepped path over existing solid floors."""
    x0, x1, y0, y1, z0, z1 = bounds
    forbidden = forbidden or set()
    starts = []
    targets = set()
    for ix, iy, iz in zip(*np.nonzero(labels >= 0)):
        x, y, z = volume.world_position(ix, iy, iz)
        if not (x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1):
            continue
        cid = int(labels[ix, iy, iz])
        if cid == source_id:
            starts.append((x, y, z))
        elif cid == target_id:
            targets.add((x, y, z))
    if not starts or not targets:
        raise RuntimeError(
            f"path endpoints missing in {bounds}: starts={len(starts)} "
            f"targets={len(targets)}")

    best = {}
    previous = {}
    queue = []
    serial = 0
    for start in starts:
        best[start] = 0
        heapq.heappush(queue, (0, serial, start))
        serial += 1
    reached = None
    while queue:
        score, _, current = heapq.heappop(queue)
        if score != best.get(current):
            continue
        if current in targets:
            reached = current
            break
        x, y, z = current
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                nxt = (x + dx, y + dy, z + dz)
                if nxt in forbidden:
                    continue
                if not (x0 <= nxt[0] <= x1 and y0 <= nxt[1] <= y1
                        and z0 <= nxt[2] <= z1):
                    continue
                candidate = path_cell_cost(volume, nxt)
                if candidate is None:
                    continue
                cell_cost, _ = candidate
                next_score = score + 1 + cell_cost
                if next_score >= best.get(nxt, 1 << 60):
                    continue
                best[nxt] = next_score
                previous[nxt] = current
                heapq.heappush(queue, (next_score, serial, nxt))
                serial += 1
    if reached is None:
        return {"found": False, "bounds": list(bounds)}

    path = [reached]
    while path[-1] not in starts:
        path.append(previous[path[-1]])
    path.reverse()
    removals = {}
    for point in path:
        candidate = path_cell_cost(volume, point)
        if candidate is None:
            continue
        for x, y, z, current in candidate[1]:
            removals[(x, y, z)] = current
    return {
        "found": True,
        "bounds": list(bounds),
        "score": best[reached],
        "path": [list(point) for point in path],
        "removals": [list(point) + [current]
                     for point, current in sorted(removals.items())],
    }


def supported_nonconflicting_path(
        volume: survey.Volume,
        labels: np.ndarray,
        source_id: int,
        target_id: int,
        bounds: tuple[int, int, int, int, int, int]) -> dict:
    """Reject paths whose own clearance removal destroys a later floor."""
    forbidden = set()
    for _ in range(128):
        plan = supported_path(
            volume, labels, source_id, target_id, bounds, forbidden)
        if not plan["found"]:
            return plan
        floors = {(x, y - 1, z) for x, y, z in plan["path"]}
        conflict_node = None
        for point in plan["path"]:
            candidate = path_cell_cost(volume, tuple(point))
            if candidate is None:
                continue
            if any((x, y, z) in floors
                   for x, y, z, _ in candidate[1]):
                conflict_node = tuple(point)
                break
        if conflict_node is None:
            plan["forbidden_conflict_nodes"] = len(forbidden)
            return plan
        forbidden.add(conflict_node)
    raise RuntimeError("supported path conflict resolution exceeded 128 nodes")


def run_debug_path_plan(world_root: Path) -> None:
    """Emit one JSON report for the three measured component gaps."""
    volume = survey.Volume(world_root, DEBUG_COMPONENT_BOX)
    labels, _ = survey.label_components(
        volume.masks()["standable"], volume, walkable=True)

    def component(label: str) -> int:
        x, y, z = REAR_REPRESENTATIVES[label]
        return int(labels[x - volume.x0, y - volume.y0, z - volume.z0])

    report = {
        "lower_side_to_centre": supported_path(
            volume, labels, component("lower_west_inner"),
            component("lower_centre"),
            (4, 52, -431, -420, 270, 304)),
        "upper_side_to_bridge": supported_path(
            volume, labels, component("upper_west"),
            component("existing_centre_bridge"),
            (20, 36, -414, -406, 255, 280)),
        "upper_side_to_centre": supported_path(
            volume, labels, component("upper_west"),
            component("upper_centre"),
            (20, 36, -412, -404, 255, 280)),
        "lower_centre_to_upper_side": supported_path(
            volume, labels, component("lower_centre"),
            component("upper_west"),
            (18, 38, -431, -404, 270, 304)),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


def add_surgical_connections(
        volume: survey.Volume,
        reasons: dict[tuple[int, int, int], str],
        selected: tuple[str, ...] | None = None) -> dict:
    """Open the least-destructive routes already supported by the asset."""
    names = tuple(CONNECTION_SPECS) if selected is None else selected
    plans = {}
    removals: dict[tuple[int, int, int], tuple[str, set[str]]] = {}
    additions: dict[tuple[int, int, int], tuple[str, str]] = {}
    replacements: dict[tuple[int, int, int], tuple[str, str]] = {}
    for name in names:
        source, target, bounds = CONNECTION_SPECS[name]
        labels, _ = survey.label_components(
            volume.masks()["standable"], volume, walkable=True)

        def component(label: str) -> int:
            x, y, z = REAR_REPRESENTATIVES[label]
            return int(labels[
                x - volume.x0, y - volume.y0, z - volume.z0])

        source_id = component(source)
        target_id = component(target)
        if source_id == target_id:
            plans[name] = {
                "found": True, "already_connected": True,
                "bounds": list(bounds), "path": [], "removals": [],
            }
            continue
        if name == "upper-side-to-bridge":
            # r01 opened x=29..30 but left x=30 above a literal-air floor.
            # Preserve that proven topology while completing its footing from
            # the existing smooth-stone support one block below.  This yields
            # a contiguous two-wide, two-high aperture with no fall edge.
            exact = ((29, -410, 279), (30, -410, 279))
            floor = (30, -411, 279)
            if state(volume, *floor) not in AIR:
                raise RuntimeError(
                    f"B1 footing source changed at {floor}: "
                    f"{state(volume, *floor)}")
            if state(volume, 30, -412, 279) != "minecraft:smooth_stone":
                raise RuntimeError("B1 footing no longer has authored support")
            for x, y, z in exact:
                if state(volume, x, y + 1, z) not in AIR:
                    raise RuntimeError(
                        f"B1 head clearance changed at {(x, y + 1, z)}")
            replace_exact(
                volume, reasons, *floor, state(volume, *floor),
                "minecraft:iron_block", "surgical-footing:" + name)
            additions[floor] = ("minecraft:air", "minecraft:iron_block")
            plan = {
                "found": True,
                "bounds": list(bounds),
                "score": None,
                "path": [[x, -410, z] for x, _, z in exact],
                "removals": [
                    [x, y, z, state(volume, x, y, z)]
                    for x, y, z in exact
                ],
                "additions": [[*floor, "minecraft:air",
                               "minecraft:iron_block"]],
                "aperture": "measured-supported-2-wide/x29..30",
            }
            for x, y, z, expected in plan["removals"]:
                if expected != "minecraft:white_concrete":
                    raise RuntimeError(
                        f"B1 aperture source changed at {(x, y, z)}: {expected}")
        elif name == "upper-side-to-centre":
            # r01's one-cell dogleg was topologically valid but visually read
            # as a hole in the pier.  Replace it with two parallel, guarded
            # stair lanes ascending east from the lower authored gallery.
            stair = (
                "minecraft:smooth_quartz_stairs"
                "[facing=east,half=bottom,shape=straight,waterlogged=false]"
            )
            added_steps = ((25, -409, 260), (25, -409, 261))
            replaced_steps = ((26, -408, 260), (26, -408, 261))
            clear = (
                (26, -407, 260), (26, -407, 261),
                (26, -406, 260), (26, -406, 261),
            )
            for point in added_steps:
                expected = state(volume, *point)
                if expected not in AIR:
                    raise RuntimeError(
                        f"B2 lower stair source changed at {point}: {expected}")
                replace_exact(volume, reasons, *point, expected, stair,
                              "surgical-stair:" + name)
                additions[point] = (expected, stair)
            for point in replaced_steps:
                expected = state(volume, *point)
                if expected != "minecraft:black_concrete":
                    raise RuntimeError(
                        f"B2 rise source changed at {point}: {expected}")
                replace_exact(volume, reasons, *point, expected, stair,
                              "surgical-stair:" + name)
                replacements[point] = (expected, stair)
            plan = {
                "found": True,
                "bounds": list(bounds),
                "score": None,
                "path": [
                    [x, y, z]
                    for z in (260, 261)
                    for x, y in ((24, -409), (25, -408),
                                 (26, -407), (27, -406))
                ],
                "removals": [
                    [x, y, z, state(volume, x, y, z)]
                    for x, y, z in clear
                ],
                "additions": [[*point, additions[point][0], stair]
                              for point in added_steps],
                "replacements": [[*point, *replacements[point]]
                                 for point in replaced_steps],
                "aperture": "two-wide-authored-pier-stair/z260..261",
            }
            for x, y, z, expected in plan["removals"]:
                if expected != "minecraft:smooth_stone":
                    raise RuntimeError(
                        f"B2 clearance source changed at {(x, y, z)}: "
                        f"{expected}")
        elif name == "lower-centre-to-upper-side":
            # The lower and middle tiers already have an authored vertical
            # access chain: ladder x18/z282 y=-430..-424, a hatch at -423,
            # and the existing three-wide stair beyond it.  The old pathfinder
            # did not model ladders and therefore tried to carve through the
            # surrounding machinery.  Preserve that chain and open only its
            # measured two-wide top doorway.
            floor = (22, -411, 272)
            floor_before = state(volume, *floor)
            if not floor_before.startswith(
                    "minecraft:polished_blackstone_brick_wall"):
                raise RuntimeError(
                    f"B3 doorway floor source changed at {floor}: "
                    f"{floor_before}")
            floor_after = "minecraft:chiseled_deepslate"
            replace_exact(volume, reasons, *floor, floor_before, floor_after,
                          "surgical-floor:" + name)
            replacements[floor] = (floor_before, floor_after)
            clear = ((22, -410, 272), (23, -410, 272))
            plan = {
                "found": True,
                "bounds": list(bounds),
                "score": None,
                "path": [[22, -410, 272], [23, -410, 272],
                         [24, -409, 272]],
                "removals": [[*point, state(volume, *point)]
                             for point in clear],
                "replacements": [[*floor, floor_before, floor_after]],
                "aperture": "authored-ladder-stair-top-door/x22..23",
                "preserved_vertical_access": {
                    "ladder": [[18, y, 282] for y in range(-430, -423)],
                    "hatch": [18, -423, 282],
                    "lower_landing": [18, -430, 281],
                    "upper_landing": [19, -423, 282],
                },
            }
            for x, y, z, expected in plan["removals"]:
                if expected != "minecraft:white_concrete":
                    raise RuntimeError(
                        f"B3 doorway source changed at {(x, y, z)}: "
                        f"{expected}")
        elif name == "lower-side-to-centre":
            # Two short iron maintenance bridges join the authored west door
            # landing to the existing ladder core.  Each two-block span is
            # laterally anchored between the original x14 and x17 structures;
            # no machinery, door or ladder voxel is touched.
            lanes = (281, 283)
            floors = (
                (15, -430, 281), (16, -430, 281),
                (16, -430, 283),
            )
            clear = tuple((x, y, z) for z in lanes for x in (15, 17)
                          for y in (-429, -428))
            for point in floors:
                expected = state(volume, *point)
                if expected not in AIR:
                    raise RuntimeError(
                        f"B4 bridge floor source changed at {point}: "
                        f"{expected}")
                replace_exact(volume, reasons, *point, expected,
                              "minecraft:iron_block",
                              "surgical-bridge:" + name)
                additions[point] = (expected, "minecraft:iron_block")
            expected_clear = {
                (15, -429, 281): "minecraft:smooth_stone",
                (15, -428, 281): "minecraft:red_concrete",
                (17, -429, 281): "minecraft:black_concrete",
                (17, -428, 281): "minecraft:smooth_stone",
                (15, -429, 283): "minecraft:smooth_stone",
                (15, -428, 283): "minecraft:stone",
                (17, -429, 283): "minecraft:black_concrete",
                (17, -428, 283): "minecraft:smooth_stone",
            }
            plan = {
                "found": True,
                "bounds": list(bounds),
                "score": None,
                "path": [[x, -429, z] for z in lanes
                         for x in (14, 15, 16, 17)]
                        + [[18, -430, z] for z in lanes],
                "removals": [[*point, state(volume, *point)]
                             for point in clear],
                "additions": [[*point, additions[point][0],
                               "minecraft:iron_block"]
                              for point in floors],
                "aperture": "two-lane-lateral-maintenance-bridge/x14..18",
                "lateral_spans": [
                    {"blocks": [[15, -430, 281], [16, -430, 281]],
                     "anchors": [[14, -430, 281], [17, -430, 281]]},
                    {"blocks": [[16, -430, 283]],
                     "anchors": [[15, -430, 283], [17, -430, 283]]},
                ],
            }
            for x, y, z, expected in plan["removals"]:
                if expected != expected_clear[(x, y, z)]:
                    raise RuntimeError(
                        f"B4 clearance source changed at {(x, y, z)}: "
                        f"{expected}")
        else:
            plan = supported_nonconflicting_path(
                volume, labels, source_id, target_id, bounds)
        if not plan["found"]:
            raise RuntimeError(f"no supported surgical route for {name}")
        plans[name] = plan
        for x, y, z, expected in plan["removals"]:
            point = (x, y, z)
            prior = removals.get(point)
            if prior is not None and prior[0] != expected:
                raise RuntimeError(
                    f"conflicting removal guard at {point}: "
                    f"{prior[0]} != {expected}")
            labels_for_point = set() if prior is None else prior[1]
            labels_for_point.add(name)
            removals[point] = (expected, labels_for_point)
            replace_exact(
                volume, reasons, x, y, z, expected, "minecraft:air",
                "surgical-open:" + name)

        post_standable = volume.masks()["standable"]
        missing = []
        for x, y, z in plan["path"]:
            if not post_standable[
                    x - volume.x0, y - volume.y0, z - volume.z0]:
                missing.append([x, y, z])
        if missing:
            raise RuntimeError(
                f"planned route {name} did not become standable: {missing}")

    return {
        "planner": "existing-supported-floor-dijkstra/v1",
        "routes": plans,
        "unique_removed_voxels": len(removals),
        "added_solid_voxels": len(additions),
        "replaced_solid_voxels": len(replacements),
    }


def put_air(volume: survey.Volume,
            reasons: dict[tuple[int, int, int], str],
            x: int, y: int, z: int, material: str, reason: str) -> bool:
    """Add only into literal air; existing authored and marker cells win."""
    if state(volume, x, y, z) not in AIR:
        return False
    repair.set_proposed(volume, reasons, x, y, z, material, reason)
    return True


def replace_exact(volume: survey.Volume,
                  reasons: dict[tuple[int, int, int], str],
                  x: int, y: int, z: int,
                  expected: str, material: str, reason: str) -> None:
    current = state(volume, x, y, z)
    if current != expected:
        raise RuntimeError(
            f"exact-state guard failed at {(x, y, z)}: "
            f"expected={expected} current={current}")
    repair.set_proposed(volume, reasons, x, y, z, material, reason)


def floor_material(x: int, z: int,
                   x0: int, x1: int, z0: int, z1: int) -> str:
    if x in (x0, x1) or z in (z0, z1):
        return POLISHED
    if (x - x0) % 8 == 4 and (z - z0) % 6 == 3:
        return LIGHT
    return WHITE


def add_floor(volume: survey.Volume,
              reasons: dict[tuple[int, int, int], str],
              x0: int, x1: int, y: int, z0: int, z1: int,
              reason: str,
              exclusions: set[tuple[int, int]] | None = None) -> None:
    exclusions = exclusions or set()
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if (x, z) in exclusions:
                continue
            put_air(volume, reasons, x, y, z,
                    floor_material(x, z, x0, x1, z0, z1), reason)


def add_panel_wall_x(volume: survey.Volume,
                     reasons: dict[tuple[int, int, int], str],
                     x: int, y0: int, y1: int, z0: int, z1: int,
                     reason: str) -> None:
    for y in range(y0, y1 + 1):
        for z in range(z0, z1 + 1):
            frame = (y in (y0, y1) or z in (z0, z1)
                     or (z - z0) % 6 == 0)
            put_air(volume, reasons, x, y, z,
                    POLISHED if frame else GLASS, reason)


def add_panel_wall_z(volume: survey.Volume,
                     reasons: dict[tuple[int, int, int], str],
                     z: int, y0: int, y1: int, x0: int, x1: int,
                     reason: str,
                     opening: tuple[int, int, int, int] | None = None) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (opening is not None
                    and opening[0] <= x <= opening[1]
                    and opening[2] <= y <= opening[3]):
                continue
            frame = (y in (y0, y1) or x in (x0, x1)
                     or (x - x0) % 6 == 0)
            put_air(volume, reasons, x, y, z,
                    POLISHED if frame else GLASS, reason)


def add_lower_concourse(volume: survey.Volume,
                        reasons: dict[tuple[int, int, int], str]) -> None:
    # The central authored outlet is one block below the four outer outlets.
    descent = {(x, z) for x in range(27, 30) for z in range(269, 272)}
    add_floor(volume, reasons, 5, 51, -430, 257, 272,
              "lower-distribution-floor", descent)
    add_floor(volume, reasons, 17, 39, -430, 244, 256,
              "atrium-lower-floor")

    # A measured one-block split-level adapter reaches the centre outlet.
    for x in range(27, 30):
        for z in range(269, 274):
            material = STAIR_SOUTH if z == 269 else WHITE
            put_air(volume, reasons, x, -431, z, material,
                    "centre-lower-split-level-adapter")

    # Two-deep perimeter/grid beams make the new deck read as supported while
    # leaving the later pyramid-bottom programme outside this repair scope.
    for y in (-432, -431):
        for x in range(5, 52):
            for z in range(257, 273):
                if (x in (5, 16, 28, 40, 51)
                        or z in (257, 264, 272)):
                    put_air(volume, reasons, x, y, z, TILES,
                            "lower-concourse-support-grid")

    # Outer shell and the rear closure preserve five exact 3-wide mouths.
    for x in (4, 52):
        for y in range(-430, -424):
            for z in range(256, 273):
                put_air(volume, reasons, x, y, z,
                        POLISHED if y in (-430, -425) else SMOOTH,
                        "lower-concourse-side-shell")

    mouths = set()
    for centre in (8, 13, 28, 43, 48):
        mouths.update(range(centre - 1, centre + 2))
    for y in range(-429, -425):
        for x in range(5, 52):
            if x in mouths:
                continue
            put_air(volume, reasons, x, y, 273,
                    RED if y == -427 else SMOOTH,
                    "five-mouth-rear-closure")

    # Low ceiling only over the two wings; the centre opens into the atrium.
    for x0, x1 in ((5, 16), (40, 51)):
        for x in range(x0, x1 + 1):
            for z in range(257, 273):
                material = LIGHT if (x + z) % 9 == 0 else BLACK
                put_air(volume, reasons, x, -425, z, material,
                        "lower-concourse-wing-ceiling")


def add_atrium_shell(volume: survey.Volume,
                     reasons: dict[tuple[int, int, int], str]) -> None:
    add_panel_wall_x(volume, reasons, 16, -430, -403, 243, 256,
                     "west-atrium-glazed-shell")
    add_panel_wall_x(volume, reasons, 40, -430, -403, 243, 256,
                     "east-atrium-glazed-shell")
    add_panel_wall_z(volume, reasons, 243, -430, -403, 16, 40,
                     "north-atrium-glazed-shell",
                     opening=(26, 30, -413, -409))

    for x in range(17, 40):
        for z in range(244, 257):
            edge = x in (17, 39) or z in (244, 256)
            material = POLISHED if edge else (
                LIGHT if (x + z) % 11 == 0 else BLACK)
            put_air(volume, reasons, x, -403, z, material,
                    "atrium-roof")

    # Full-height frame piers define the volume without turning it into a box
    # of random columns.
    for x, z in ((16, 243), (40, 243), (16, 256), (40, 256)):
        for y in range(-430, -402):
            put_air(volume, reasons, x, y, z, POLISHED,
                    "atrium-frame-pier")


def add_long_stair(volume: survey.Volume,
                   reasons: dict[tuple[int, int, int], str],
                   x0: int, x1: int, reason: str) -> None:
    # Twenty blocks ascend south through the measured empty atrium lane.  The
    # opposite diagonal crosses authored service decks at y=-425..-421; this
    # orientation is the zero-collision route found by the local voxel scan.
    for step in range(20):
        z = 244 + step
        y = -430 + step
        for x in range(x0, x1 + 1):
            put_air(volume, reasons, x, y, z, STAIR_NORTH, reason)
        inner_rail = x1 + 1 if x1 < 28 else x0 - 1
        for rail_x in (x0 - 1, x1 + 1):
            # Open the inner top threshold into the measured side gallery.
            if rail_x == inner_rail and z >= 261:
                continue
            put_air(volume, reasons, rail_x, y + 1, z, GLASS,
                    reason + "-glass-rail")
        for support_y in range(-429, y):
            for support_x in (x0, x1):
                put_air(volume, reasons, support_x, support_y, z, TILES,
                        reason + "-stringer")


def add_upper_connections(volume: survey.Volume,
                          reasons: dict[tuple[int, int, int], str]) -> None:
    add_long_stair(volume, reasons, 19, 21, "west-mirrored-stair")
    add_long_stair(volume, reasons, 35, 37, "east-mirrored-stair")

    # Intermediate landing meets the preserved y=-412 centre bridge.
    add_floor(volume, reasons, 22, 34, -413, 248, 252,
              "existing-centre-bridge-landing")

    # A separate short ramp raises the preserved y=-412 bridge to the
    # y=-409 distribution level without rerouting or deleting the bridge.
    for step, z in enumerate(range(253, 256)):
        y = -412 + step
        for x in range(27, 30):
            put_air(volume, reasons, x, y, z, STAIR_NORTH,
                    "existing-bridge-to-upper-ramp")

    # The authored side corridors are separated from the atrium by uniform
    # wall bands at x=22 and x=34. Open two measured 3x2 thresholds and add
    # proper floors; these are the only non-air cells changed by r01.
    for wall_x in (22, 34):
        for z in range(263, 266):
            replace_exact(volume, reasons, wall_x, -409, z, SMOOTH,
                          "minecraft:air", "side-gallery-doorway")
            replace_exact(volume, reasons, wall_x, -408, z, BLACK,
                          "minecraft:air", "side-gallery-doorway")
            put_air(volume, reasons, wall_x, -410, z, WHITE,
                    "side-gallery-doorway-threshold")

    # Upper gallery joins both side outlets at their measured floor y=-410.
    raised_steps = {(x, z) for x in range(27, 30)
                    for z in range(256, 260)}
    bridge_ramp_clearance = {(x, z) for x in range(27, 30)
                             for z in range(253, 256)}
    add_floor(volume, reasons, 19, 37, -410, 245, 260,
              "upper-side-distribution-gallery",
              raised_steps | bridge_ramp_clearance)
    add_floor(volume, reasons, 22, 25, -410, 258, 264,
              "west-upper-three-wide-adapter")
    add_floor(volume, reasons, 31, 34, -410, 258, 264,
              "east-upper-three-wide-adapter")

    # Three-step central rise matches the centre outlet floor y=-407.
    for step, z in enumerate(range(256, 260)):
        y = -410 + step
        for x in range(27, 30):
            put_air(volume, reasons, x, y, z,
                    STAIR_NORTH if step < 3 else WHITE,
                    "raised-centre-three-step-adapter")
        for support_y in range(-409, y):
            for x in (27, 29):
                put_air(volume, reasons, x, support_y, z, TILES,
                        "raised-centre-adapter-support")
    add_floor(volume, reasons, 27, 29, -407, 259, 264,
              "raised-centre-three-wide-landing")

    # Guard the exposed gallery edges while leaving measured apertures open.
    for x in (18, 38):
        for z in range(245, 261):
            put_air(volume, reasons, x, -409, z, GLASS,
                    "upper-gallery-clear-glass-rail")


def add_compact_rear_network(
        volume: survey.Volume,
        reasons: dict[tuple[int, int, int], str]) -> None:
    """Join the rear outlets without creating an exterior annex volume."""
    # A five-block-deep transverse service corridor sits directly behind the
    # five existing lower mouths.  It is a corridor, not a new floor plate.
    split_level = {(x, z) for x in range(27, 30)
                   for z in range(269, 272)}
    add_floor(volume, reasons, 6, 50, -430, 267, 271,
              "compact-lower-service-floor", split_level)

    # The authored centre mouth is one block lower than the four side mouths.
    # Preserve that fact through a three-wide split-level adapter.
    for x in range(27, 30):
        for z in range(269, 274):
            material = STAIR_SOUTH if z == 269 else WHITE
            put_air(volume, reasons, x, -431, z, material,
                    "compact-centre-split-level")

    mouths = set()
    for centre in (8, 13, 28, 43, 48):
        mouths.update(range(centre - 1, centre + 2))

    # Close and support only the shallow corridor prism.  There is no facade,
    # atrium roof, or full-height wall spanning the pyramid void.
    for x in range(6, 51):
        if x not in mouths:
            for y in range(-429, -425):
                put_air(volume, reasons, x, y, 272,
                        RED if y == -427 else SMOOTH,
                        "compact-five-mouth-wall")
        if not 26 <= x <= 30:
            for y in range(-429, -425):
                put_air(volume, reasons, x, y, 266,
                        BLACK if y == -427 else SMOOTH,
                        "compact-corridor-north-wall")
        for z in range(267, 272):
            material = LIGHT if (x + z) % 13 == 0 else BLACK
            put_air(volume, reasons, x, -425, z, material,
                    "compact-corridor-ceiling")
    for x in (5, 51):
        for y in range(-430, -424):
            for z in range(266, 273):
                put_air(volume, reasons, x, y, z, POLISHED,
                        "compact-corridor-end-wall")
    for x in range(6, 51):
        if x in (6, 16, 27, 29, 40, 50):
            for z in range(267, 272):
                put_air(volume, reasons, x, -431, z, TILES,
                        "compact-corridor-support")

    # One three-wide stair core rises north from the lower centre mouth to the
    # preserved y=-412 bridge.  Its walls and roof follow the stair profile,
    # so the mass stays narrow instead of filling the surrounding void.
    for step in range(19):
        z = 269 - step
        y = -431 + step
        for x in range(27, 30):
            put_air(volume, reasons, x, y, z, STAIR_SOUTH,
                    "compact-central-stair")
            put_air(volume, reasons, x, y + 3, z,
                    LIGHT if step % 6 == 3 else BLACK,
                    "compact-central-stair-ceiling")
        for wall_x in (26, 30):
            for wall_y in range(y + 1, y + 4):
                put_air(volume, reasons, wall_x, wall_y, z,
                        GLASS if wall_y == y + 2 else POLISHED,
                        "compact-central-stair-wall")
        for support_x in (27, 29):
            put_air(volume, reasons, support_x, y - 1, z, TILES,
                    "compact-central-stair-stringer")

    # A small landing merges into the existing centre bridge; only this
    # measured bridge provides the vertical core's north exit.
    add_floor(volume, reasons, 26, 30, -413, 248, 253,
              "compact-centre-bridge-landing")

    # Rise three blocks from the preserved bridge to the side-gallery level.
    for step, z in enumerate(range(253, 257)):
        y = -413 + step
        for x in range(27, 30):
            put_air(volume, reasons, x, y, z,
                    STAIR_NORTH if step < 3 else WHITE,
                    "compact-bridge-upper-ramp")

    # Two exact 3x2 openings join the authored upper side passages.  These are
    # the only existing authored blocks removed by the candidate.
    for wall_x in (22, 34):
        for z in range(263, 266):
            replace_exact(volume, reasons, wall_x, -409, z, SMOOTH,
                          "minecraft:air", "compact-side-doorway")
            replace_exact(volume, reasons, wall_x, -408, z, BLACK,
                          "minecraft:air", "compact-side-doorway")
            put_air(volume, reasons, wall_x, -410, z, WHITE,
                    "compact-side-doorway-threshold")

    # The upper junction is only fifteen blocks wide and seven blocks deep.
    raised = {(x, z) for x in range(27, 30)
              for z in range(256, 260)}
    add_floor(volume, reasons, 21, 35, -410, 257, 263,
              "compact-upper-junction-floor", raised)
    add_floor(volume, reasons, 22, 25, -410, 263, 265,
              "compact-west-upper-adapter")
    add_floor(volume, reasons, 31, 34, -410, 263, 265,
              "compact-east-upper-adapter")
    for x in range(21, 36):
        if not 26 <= x <= 30:
            for y in range(-409, -405):
                put_air(volume, reasons, x, y, 256, SMOOTH,
                        "compact-upper-north-wall")
        for z in range(257, 264):
            if not 26 <= x <= 30:
                put_air(volume, reasons, x, -405, z,
                        LIGHT if (x + z) % 9 == 0 else BLACK,
                        "compact-upper-ceiling")
    for wall_x in (20, 36):
        for y in range(-410, -404):
            for z in range(256, 264):
                put_air(volume, reasons, wall_x, y, z, POLISHED,
                        "compact-upper-end-wall")

    # Three final steps meet the raised centre outlet at feet y=-406.
    for step, z in enumerate(range(256, 260)):
        y = -410 + step
        for x in range(27, 30):
            put_air(volume, reasons, x, y, z,
                    STAIR_NORTH if step < 3 else WHITE,
                    "compact-raised-centre-adapter")
            if step > 0:
                put_air(volume, reasons, x, y - 1, z, TILES,
                        "compact-raised-centre-support")
    add_floor(volume, reasons, 27, 29, -407, 259, 264,
              "compact-raised-centre-landing")


def component_contract(after: survey.Volume,
                       selected: tuple[str, ...] | None = None) -> dict:
    if selected == ("lower-centre-to-upper-side",):
        # Horizontal walk components deliberately do not model ladder motion.
        # Prove both landings attach to their respective route networks and
        # guard every block in the preserved vertical access chain instead.
        standable = after.masks()["standable"]
        labels, components = survey.label_components(
            standable, after, walkable=True)
        def cid(point: tuple[int, int, int]) -> int:
            x, y, z = point
            return int(labels[x - after.x0, y - after.y0, z - after.z0])
        lower = REAR_REPRESENTATIVES["lower_centre"]
        lower_landing = (18, -430, 281)
        upper_landing = (19, -423, 282)
        doorway = (23, -410, 272)
        upper = REAR_REPRESENTATIVES["upper_west"]
        if cid(lower) != cid(lower_landing):
            raise RuntimeError("B3 lower ladder landing is disconnected")
        if cid(doorway) != cid(upper):
            raise RuntimeError("B3 top doorway is disconnected from upper route")
        for y in range(-430, -423):
            ladder = state(after, 18, y, 282)
            if not ladder.startswith("minecraft:ladder"):
                raise RuntimeError(f"B3 ladder changed at y={y}: {ladder}")
        hatch = state(after, 18, -423, 282)
        if not hatch.startswith("minecraft:birch_trapdoor"):
            raise RuntimeError(f"B3 hatch changed: {hatch}")
        for z in (281, 282, 283):
            stair = state(after, 20, -420, z)
            if not stair.startswith("minecraft:stone_stairs"):
                raise RuntimeError(
                    f"B3 authored middle stair changed at z={z}: {stair}")
        return {
            "all_selected_routes_connected": True,
            "selected_connections": list(selected),
            "connection_mode": "preserved-ladder-plus-authored-stair",
            "representatives": {
                "lower_centre": list(lower),
                "lower_landing": list(lower_landing),
                "upper_landing": list(upper_landing),
                "upper_doorway": list(doorway),
                "upper_west": list(upper),
            },
            "component_ids": {
                "lower": cid(lower), "ladder_top": cid(upper_landing),
                "upper": cid(upper),
            },
        }
    if selected is None:
        representatives = dict(REAR_REPRESENTATIVES)
    else:
        representative_names = set()
        for name in selected:
            source, target, _ = CONNECTION_SPECS[name]
            representative_names.update((source, target))
        representatives = {
            name: REAR_REPRESENTATIVES[name]
            for name in sorted(representative_names)
        }
    standable = after.masks()["standable"]
    labels, components = survey.label_components(
        standable, after, walkable=True)
    ids = {}
    for label, (x, y, z) in representatives.items():
        cid = int(labels[x - after.x0, y - after.y0, z - after.z0])
        if cid < 0:
            raise RuntimeError(f"{label} is not standable at {(x, y, z)}")
        ids[label] = cid
    unique = sorted(set(ids.values()))
    if len(unique) != 1:
        raise RuntimeError(f"rear outlets are not one walk component: {ids}")
    component = components[unique[0]]
    return {
        "all_selected_routes_connected": True,
        "selected_connections": list(selected or CONNECTION_SPECS),
        "component_id": unique[0],
        "representatives": {key: list(value)
                            for key, value in representatives.items()},
        "component_cells": int(component["cells"]),
        "component_bbox": component["bbox"],
    }


def print_debug_slice(volume: survey.Volume,
                      spec: tuple[int, int, int, int, int]) -> None:
    """Print one cached feet-level section without reloading the world."""
    x0, x1, z0, z1, feet = spec
    if not (volume.x0 <= x0 <= x1 <= volume.x1
            and volume.z0 <= z0 <= z1 <= volume.z1
            and volume.y0 + 1 <= feet <= volume.y1 - 1):
        raise ValueError(
            f"debug slice {(x0, x1, z0, z1, feet)} is outside "
            f"{(volume.x0, volume.x1, volume.y0, volume.y1, volume.z0, volume.z1)}")
    masks = volume.masks()
    standable = masks["standable"]
    roles = np.asarray(
        [survey.role_of(block_state) for block_state in volume.states],
        dtype=object,
    )[volume.code]
    print(f"DEBUG_SLICE x={x0}..{x1} z={z0}..{z1} feet={feet}")
    print("legend: = standable  # solid/body obstruction  ~ fluid  . void")
    for z in range(z0, z1 + 1):
        row = []
        for x in range(x0, x1 + 1):
            ix, iy, iz = x - volume.x0, feet - volume.y0, z - volume.z0
            if standable[ix, iy, iz]:
                row.append("=")
            elif roles[ix, iy, iz] == "fluid":
                row.append("~")
            elif roles[ix, iy, iz] not in ("air", "fixture", "door"):
                row.append("#")
            else:
                row.append(".")
        print(f"z={z:4d} {''.join(row)}")


def run_debug_slices(world_root: Path,
                     specs: list[tuple[int, int, int, int, int]]) -> None:
    """Load the union of all probes once, then print every requested slice."""
    probe_box = (
        min(spec[0] for spec in specs), max(spec[1] for spec in specs),
        min(spec[4] for spec in specs) - 1,
        max(spec[4] for spec in specs) + 1,
        min(spec[2] for spec in specs), max(spec[3] for spec in specs),
    )
    volume = survey.Volume(world_root, probe_box)
    for spec in specs:
        print_debug_slice(volume, spec)


def run_debug_components(world_root: Path) -> None:
    """Print one compact component report for every declared rear endpoint."""
    volume = survey.Volume(world_root, DEBUG_COMPONENT_BOX)
    standable = volume.masks()["standable"]
    labels, components = survey.label_components(
        standable, volume, walkable=True)
    report = {}
    ids_by_name = {}
    for name, (x, y, z) in REAR_REPRESENTATIVES.items():
        cid = int(labels[x - volume.x0, y - volume.y0, z - volume.z0])
        ids_by_name[name] = cid
        report[name] = {
            "point": [x, y, z],
            "standable": bool(standable[
                x - volume.x0, y - volume.y0, z - volume.z0]),
            "component_id": cid,
            "component": components[cid] if cid >= 0 else None,
        }
    unique_ids = sorted({cid for cid in ids_by_name.values() if cid >= 0})
    points_by_id = {}
    for cid in unique_ids:
        points_by_id[cid] = [volume.world_position(*index)
                             for index in zip(*np.nonzero(labels == cid))]
    nearest_pairs = []
    for offset, cid_a in enumerate(unique_ids):
        for cid_b in unique_ids[offset + 1:]:
            best = min(
                ((abs(a[0] - b[0]) + abs(a[1] - b[1])
                  + abs(a[2] - b[2]), a, b)
                 for a in points_by_id[cid_a]
                 for b in points_by_id[cid_b]),
                key=lambda item: item[0])
            nearest_pairs.append({
                "components": [cid_a, cid_b],
                "manhattan": best[0],
                "points": [list(best[1]), list(best[2])],
            })
    print(json.dumps({
        "endpoints": report,
        "nearest_component_pairs": sorted(
            nearest_pairs, key=lambda item: item["manhattan"]),
    }, indent=2))


def build(world_root: Path, output_root: Path,
          selected: tuple[str, ...] | None = None) -> str:
    before = survey.Volume(world_root, BOX)
    after = survey.Volume(world_root, BOX)
    reasons: dict[tuple[int, int, int], str] = {}

    surgical = add_surgical_connections(after, reasons, selected)

    contract = component_contract(after, selected)
    contract.update({
        "authority_save_written": False,
        "existing_non_air_cells_replaced": (
            surgical["unique_removed_voxels"]
            + surgical["replaced_solid_voxels"]),
        "added_solid_voxels": surgical["added_solid_voxels"],
        "allowed_filled_standable": (
            [[25, -409, 260], [25, -409, 261]]
            if selected == ("upper-side-to-centre",) else []),
        "allowed_lateral_spans": (
            surgical["routes"]["lower-side-to-centre"].get(
                "lateral_spans", [])
            if selected == ("lower-side-to-centre",) else []),
        "deep_y_minus_439_route_created": False,
        "surgical_routes": surgical,
        "validation_ceiling_y": -292,
        "frozen_interfaces": [
            "west external entrance", "east external entrance",
            "front/main-screen route", "lower external entrance",
            "main screen", "controls", "seats", "MAGI",
        ],
    })

    proposal = [
        "Connect only the eight declared rear outlets.",
        "Reuse existing supported floors and authored stepped circulation.",
        "Treat (14,-439,273) as a fall coordinate, not a deep route.",
        "Open only exact guarded obstructions selected by supported-path search.",
        "Allow only the declared one-cell B1 footing on existing solid support.",
        "Do not add a room, deck, facade, roof, wall, or column voxel.",
        "Do not touch main screens, controls, seats, MAGI, doors, or ladders.",
        "Keep west/east/front/lower external interfaces frozen.",
    ]
    repair_id = (BREAKPOINT_IDS[selected[0]]
                 if selected is not None and len(selected) == 1
                 else REPAIR_ID)
    output = output_root / repair_id
    digest = repair.emit_preview(
        world_root, output, repair_id, BOX, ANCHOR,
        before, after, reasons, proposal, contract)
    topology.render_feet_layers(
        before, after, [-430, -429, -423, -414, -412, -410, -409, -406],
        ANCHOR,
        output / "08_feet_levels_before_after.png")
    digest = repair.packet_sha(output)
    print(f"{repair_id} {digest}")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        type=Path,
        default=(ROOT / "run" / "saves" / "SEELE_S20_RECOVERY_R28"
                 / "dimensions" / "projectseele" / "geofront"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "map_previews",
    )
    parser.add_argument(
        "--debug-slice",
        nargs=5,
        type=int,
        action="append",
        metavar=("X0", "X1", "Z0", "Z1", "FEET"),
        help="print a feet-level slice; repeat the flag to reuse one world load",
    )
    parser.add_argument(
        "--debug-components",
        action="store_true",
        help="print one compact component report for all rear endpoints",
    )
    parser.add_argument(
        "--debug-path-plan",
        action="store_true",
        help="print conservative supported-path candidates between components",
    )
    parser.add_argument(
        "--connection",
        action="append",
        choices=tuple(CONNECTION_SPECS),
        help="emit only this independent breakpoint; repeat to combine",
    )
    args = parser.parse_args()
    if not args.world.exists():
        parser.error(f"world does not exist: {args.world}")
    if args.debug_components:
        run_debug_components(args.world)
        return 0
    if args.debug_path_plan:
        run_debug_path_plan(args.world)
        return 0
    if args.debug_slice:
        run_debug_slices(args.world,
                         [tuple(values) for values in args.debug_slice])
        return 0
    selected = tuple(args.connection) if args.connection else None
    build(args.world, args.output, selected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
