#!/usr/bin/env python3
"""Read-only R17 preview for the authored command-room enclosure.

The private ``nerv_command_left.nbt`` remains the sole visual authority.  The
script restores only symmetric exterior wall components that are missing from
the current R14/R16 world, then adds one backing layer directly below the
already-complete authored command floor.  It never writes an Anvil region and
never replaces a non-air world block.

The screen dummy masks, sightline, command-lift approach and the central front
openings are deliberately outside the selection.  A separate outlet report
copies the read-only whole-facility detector results so floating routes can be
reviewed independently instead of being guessed into this repair.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_r13_command_trim_previews as source_trim  # noqa: E402
import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


REPAIR_ID = "S20-R17-COMMAND-AUTHORED-ENCLOSURE-PREVIEW-r01"
BOX = (2, 54, -450, -389, 223, 351)
ANCHOR = (28, -406, 287)
AUTHORED_FLOOR_Y = -449
BACKING_Y = -450
BACKING = "minecraft:reinforced_deepslate"
SHELL_MATERIALS = {
    "minecraft:stone",
    "minecraft:tuff",
    "minecraft:deepslate",
}
OUTLET_SCAN = (ROOT / "artifacts" / "map_understanding"
               / "S20-R17-COMMAND-ENCLOSURE-AND-OUTLETS-r02"
               / "candidates.json")


def state(volume: survey.Volume, point: tuple[int, int, int]) -> str:
    x, y, z = point
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


def connected_components(points: set[tuple[int, int, int]]) -> list[set]:
    unseen = set(points)
    result: list[set[tuple[int, int, int]]] = []
    while unseen:
        seed = min(unseen)
        unseen.remove(seed)
        queue = deque([seed])
        found = {seed}
        while queue:
            x, y, z = queue.popleft()
            for neighbour in ((x + 1, y, z), (x - 1, y, z),
                              (x, y + 1, z), (x, y - 1, z),
                              (x, y, z + 1), (x, y, z - 1)):
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    found.add(neighbour)
                    queue.append(neighbour)
        result.append(found)
    return result


def bounds(points: set[tuple[int, int, int]]) -> list[int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    return [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]


def is_exterior_side_component(
        points: set[tuple[int, int, int]],
        source: dict[tuple[int, int, int], str]) -> bool:
    """Select only the measured symmetric side/rear shell.

    The missing front fragments at z=267 can coincide with current personnel
    routes, while the central x=20..37 components are the two screen dummy
    masks.  Exterior source-wall components all stay near a side and extend
    into the rear half of the room (z >= 308).
    """
    if len(points) < 5:
        return False
    box = bounds(points)
    materials = {survey.base_name(source[point]) for point in points}
    near_side = box[1] <= 17 or box[0] >= 39
    reaches_rear = box[5] >= 308
    return materials <= SHELL_MATERIALS and near_side and reaches_rear


def component_entry(points: set[tuple[int, int, int]],
                    source: dict[tuple[int, int, int], str]) -> dict:
    return {
        "cells": len(points),
        "bbox": bounds(points),
        "materials": dict(Counter(
            survey.base_name(source[point]) for point in points
        ).most_common()),
    }


def classify_outlet(candidate: dict) -> str:
    x, y, z = candidate["at"]
    if 20 <= x <= 36 and 274 <= z <= 300:
        return "INTERNAL_TIER_EDGE_NOT_AN_OUTLET"
    if y <= -442 and z < 260:
        return "LOWER_PYRAMID_ROUTE_OUTSIDE_COMMAND_SCOPE"
    if x in range(5, 52) and z >= 264:
        return "COMMAND_OUTLET_REQUIRES_HUMAN_ROUTE_DECISION"
    return "FACILITY_ROUTE_REQUIRES_SEPARATE_REVIEW"


def write_outlet_report(output: Path) -> dict:
    if not OUTLET_SCAN.is_file():
        report = {
            "source": str(OUTLET_SCAN.relative_to(ROOT)),
            "available": False,
            "corridor_to_air": [],
        }
    else:
        raw = json.loads(OUTLET_SCAN.read_text(encoding="utf-8"))
        candidates = []
        for item in raw.get("candidates", []):
            if item.get("type") != "corridor_to_air":
                continue
            candidate = dict(item)
            candidate["classification"] = classify_outlet(candidate)
            candidates.append(candidate)
        report = {
            "source": str(OUTLET_SCAN.relative_to(ROOT)),
            "available": True,
            "world": raw.get("world"),
            "scan_box": raw.get("box"),
            "note": (
                "Detector hits are observations, not repair authority. "
                "No outlet voxel is changed by R17."),
            "corridor_to_air": candidates,
            "counts": dict(Counter(
                item["classification"] for item in candidates)),
        }
    (output / "10_outlet_scan_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return report


def render_outlet_board(world_root: Path, output: Path,
                        outlet_report: dict) -> None:
    box = (-8, 72, -450, -389, 252, 368)
    volume = survey.Volume(world_root, box)
    levels = (-442, -429, -423, -418, -412, -405)
    candidates = outlet_report.get("corridor_to_air", [])
    panels = []
    colours = survey.colour_table(volume)
    class_colours = {
        "COMMAND_OUTLET_REQUIRES_HUMAN_ROUTE_DECISION": (255, 72, 72),
        "FACILITY_ROUTE_REQUIRES_SEPARATE_REVIEW": (255, 174, 64),
        "LOWER_PYRAMID_ROUTE_OUTSIDE_COMMAND_SCOPE": (120, 170, 255),
        "INTERNAL_TIER_EDGE_NOT_AN_OUTLET": (155, 155, 165),
    }
    for level in levels:
        image = survey.plan_image(
            volume, level, colours, ANCHOR, scale=5,
            title=f"COMMAND OUTLET EVIDENCE y={level}")
        draw = ImageDraw.Draw(image)
        for item in candidates:
            x, y, z = item["at"]
            if abs(y - level) > 1:
                continue
            px = 80 + (x - volume.x0) * 5 + 2
            pz = 28 + (z - volume.z0) * 5 + 2
            colour = class_colours[item["classification"]]
            draw.rectangle((px - 5, pz - 5, px + 5, pz + 5),
                           outline=colour, width=2)
            draw.text((px + 7, pz - 6), f"{x},{y},{z}", fill=colour)
        panels.append(image)
    survey.combine_panels(panels, 2, output / "11_outlet_scan_board.png")


def render_focus(world_root: Path, output: Path,
                 before: survey.Volume, after: survey.Volume,
                 reasons: dict[tuple[int, int, int], str]) -> None:
    overlay = survey.Volume(world_root, BOX)
    for point in reasons:
        repair.set_proposed(
            overlay, {}, *point, "minecraft:lime_concrete", "overlay")
    panels = [
        survey.iso_projection(before, before.masks(), ANCHOR, 1, 1,
                              "COMMAND SHELL BEFORE +X/+Z"),
        survey.iso_projection(after, after.masks(), ANCHOR, 1, 1,
                              "COMMAND SHELL PROPOSAL +X/+Z"),
        survey.iso_projection(overlay, overlay.masks(), ANCHOR, 1, 1,
                              "R17 ADDED CELLS +X/+Z"),
        survey.iso_projection(overlay, overlay.masks(), ANCHOR, -1, -1,
                              "R17 ADDED CELLS -X/-Z"),
    ]
    survey.combine_panels(panels, 2, output / "08_enclosure_focus.png")

    floor_box = (4, 52, -452, -447, 265, 353)
    floor_before = survey.Volume(world_root, floor_box)
    floor_after = survey.Volume(world_root, floor_box)
    floor_overlay = survey.Volume(world_root, floor_box)
    for point, reason in reasons.items():
        x, y, z = point
        if y != BACKING_Y:
            continue
        repair.set_proposed(floor_after, {}, x, y, z, BACKING, reason)
        repair.set_proposed(floor_overlay, {}, x, y, z,
                            "minecraft:lime_concrete", "overlay")
    floor_anchor = (28, BACKING_Y, 307)
    floor_panels = [
        survey.iso_projection(floor_before, floor_before.masks(),
                              floor_anchor, 1, 1,
                              "UNDERSIDE BEFORE"),
        survey.iso_projection(floor_after, floor_after.masks(),
                              floor_anchor, 1, 1,
                              "ONE-LAYER BACKING PROPOSAL"),
        survey.iso_projection(floor_overlay, floor_overlay.masks(),
                              floor_anchor, 1, 1,
                              "BACKING CELLS ONLY"),
    ]
    survey.combine_panels(floor_panels, 3,
                          output / "09_floor_backing_focus.png")


def build(world_root: Path, output_root: Path) -> tuple[str, str]:
    source = source_trim.load_source()
    before = survey.Volume(world_root, BOX)
    after = survey.Volume(world_root, BOX)
    reasons: dict[tuple[int, int, int], str] = {}

    missing = {
        point for point, authored in source.items()
        if (BOX[0] <= point[0] <= BOX[1]
            and BOX[2] <= point[1] <= BOX[3]
            and BOX[4] <= point[2] <= BOX[5]
            and survey.role_of(authored) != "air"
            and survey.role_of(state(before, point)) == "air")
    }
    all_components = connected_components(missing)
    selected_components = [
        points for points in all_components
        if is_exterior_side_component(points, source)
    ]
    selected_wall = set().union(*selected_components)

    # The detector found two still-unclassified openings in the missing side
    # wall at (6/-438/336) and (50/-438/336).  Preserve a five-wide,
    # three-high portal around each one.  R17 restores containment around the
    # openings but does not decide whether those authored routes should be
    # joined, supported or closed.
    outlet_clearance: set[tuple[int, int, int]] = set()
    if OUTLET_SCAN.is_file():
        raw_outlets = json.loads(OUTLET_SCAN.read_text(encoding="utf-8"))
        for item in raw_outlets.get("candidates", []):
            if item.get("type") != "corridor_to_air":
                continue
            x, y, z = (int(value) for value in item["at"])
            if x not in (6, 50) or not (BOX[4] <= z <= BOX[5]):
                continue
            for yy in range(y, y + 3):
                for zz in range(z - 2, z + 3):
                    outlet_clearance.add((x, yy, zz))
    protected_wall_cells = selected_wall & outlet_clearance
    selected_wall -= outlet_clearance
    for point in sorted(selected_wall):
        repair.set_proposed(
            after, reasons, *point, source[point],
            "restore-source-authored-symmetric-exterior-shell")

    source_floor = {
        point for point, authored in source.items()
        if point[1] == AUTHORED_FLOOR_Y
        and 6 <= point[0] <= 50 and 267 <= point[2] <= 351
        and survey.role_of(authored) not in {"air", "natural", "fluid"}
    }
    blocked_walk_cells = []
    masks = before.masks()
    backing_cells = set()
    for x, _, z in sorted(source_floor):
        point = (x, BACKING_Y, z)
        if survey.role_of(state(before, point)) != "air":
            continue
        # A route with feet one block below would use this candidate as its
        # head-space.  Refuse instead of silently blocking that route.
        ix = x - before.x0
        iy = (BACKING_Y - 1) - before.y0
        iz = z - before.z0
        if 0 <= iy < before.sy and bool(masks["standable"][ix, iy, iz]):
            blocked_walk_cells.append((x, BACKING_Y - 1, z))
            continue
        repair.set_proposed(
            after, reasons, *point, BACKING,
            "one-layer-backing-below-authored-command-floor")
        backing_cells.add(point)

    if blocked_walk_cells:
        raise RuntimeError(
            "R17 floor backing would block a standable route: "
            + repr(blocked_walk_cells[:12]))
    if any(point in before.block_entities for point in reasons):
        raise RuntimeError("R17 intersects a block entity")
    if any(survey.role_of(state(before, point)) != "air"
           for point in reasons):
        raise RuntimeError("R17 attempts to replace a non-air world block")

    output = output_root / REPAIR_ID
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    floor_current_missing = sum(
        1 for point in source_floor
        if survey.role_of(state(before, point)) == "air")
    report = {
        "authority": str(source_trim.SOURCE.relative_to(ROOT)),
        "transform_origin": list(source_trim.ORIGIN),
        "selected_wall_cells": len(selected_wall),
        "selected_wall_components_before_outlet_clearance": [
            component_entry(points, source)
            for points in sorted(selected_components,
                                 key=lambda item: (-len(item), bounds(item)))
        ],
        "outlet_clearance_cells_withheld": len(protected_wall_cells),
        "outlet_clearance_points": [list(point) for point in sorted(
            protected_wall_cells)],
        "source_floor_y": AUTHORED_FLOOR_Y,
        "source_floor_cells": len(source_floor),
        "source_floor_missing_in_current_world": floor_current_missing,
        "backing_y": BACKING_Y,
        "backing_cells": len(backing_cells),
        "would_block_standable_route": len(blocked_walk_cells),
        "existing_non_air_replaced": 0,
        "block_entities_touched": 0,
        "central_screen_dummy_components_selected": 0,
        "gold_cells_selected": 0,
        "front_route_fragments_selected": 0,
    }
    (output / "07_enclosure_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    outlet_report = write_outlet_report(output)

    repair.emit_preview(
        world_root, output, REPAIR_ID, BOX, ANCHOR,
        before, after, reasons,
        [
            "restore only measured symmetric side/rear source-wall components",
            "add one backing layer below the already-complete authored floor",
            "replace no existing block and block no standable route",
            "leave screens, sightline, central front openings and all outlets unchanged",
        ],
        {
            "authority": "private nerv_command_left.nbt",
            "transform_origin": list(source_trim.ORIGIN),
            "selected_wall_cells": len(selected_wall),
            "backing_cells": len(backing_cells),
            "existing_non_air_replaced": 0,
            "screen_dummy_cells_selected": 0,
            "outlet_clearance_cells_withheld": len(protected_wall_cells),
            "outlet_cells_changed": 0,
            "outlet_candidate_count": len(
                outlet_report.get("corridor_to_air", [])),
        })
    render_focus(world_root, output, before, after, reasons)
    render_outlet_board(world_root, output, outlet_report)
    return REPAIR_ID, repair.packet_sha(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True,
                        help="Path to dimensions/projectseele/geofront")
    parser.add_argument("--emit-root", default="artifacts/map_previews")
    args = parser.parse_args()
    repair_id, digest = build(Path(args.world).resolve(),
                              Path(args.emit_root).resolve())
    print(f"{repair_id} {digest}")


if __name__ == "__main__":
    main()
