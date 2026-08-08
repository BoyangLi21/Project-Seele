#!/usr/bin/env python3
"""Build a read-only semantic packet for authored personnel circulation.

The input coordinate is an observation anchor, never an edit bound.  The
packet converts standable air cells into a route graph and records a complete
cross-section signature for each stable route segment.  It writes artifacts
only; it never mutates an Anvil save.

This is deliberately stricter than solid-block component analysis.  A single
wall can belong to a launch well, an observation gallery and a stair adapter,
while the player route through those structures still has a clear topology.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import survey_facility_target as survey  # noqa: E402


ROLE_COLOURS = {
    "air": (13, 13, 19),
    "fluid": (222, 104, 24),
    "natural": (84, 67, 48),
    "glass": (120, 205, 225),
    "stair": (104, 186, 118),
    "door": (219, 120, 210),
    "fixture": (232, 211, 105),
    "structure": (94, 99, 111),
}
ROLE_LETTERS = {
    "air": "A", "fluid": "F", "natural": "N", "glass": "G",
    "stair": "T", "door": "D", "fixture": "f", "structure": "S",
}
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def state_role(volume: survey.Volume, ix: int, iy: int, iz: int) -> str:
    if not (0 <= ix < volume.sx and 0 <= iy < volume.sy
            and 0 <= iz < volume.sz):
        return "outside"
    return survey.role_of(volume.state(ix, iy, iz))


def state_base(volume: survey.Volume, ix: int, iy: int, iz: int) -> str:
    if not (0 <= ix < volume.sx and 0 <= iy < volume.sy
            and 0 <= iz < volume.sz):
        return "outside"
    return survey.base_name(volume.state(ix, iy, iz))


def selected_component(volume: survey.Volume, standable: np.ndarray,
                       anchor: tuple[int, int, int]):
    labels, components = survey.label_components(
        standable, volume, walkable=True)
    ax = anchor[0] - volume.x0
    ay = anchor[1] - volume.y0
    az = anchor[2] - volume.z0
    ranked = []
    for component in components:
        cid = component["id"]
        points = np.argwhere(labels == cid)
        if not len(points):
            continue
        distance = np.abs(points[:, 0] - ax) + np.abs(points[:, 2] - az) \
            + 2 * np.abs(points[:, 1] - ay)
        ranked.append((int(distance.min()), -component["cells"], cid))
    if not ranked:
        raise RuntimeError("no standable route component in survey")
    ranked.sort()
    cid = ranked[0][2]
    return labels, components, cid, labels == cid


def anchor_level_sheet(route: np.ndarray, volume: survey.Volume,
                       anchor: tuple[int, int, int]):
    """Return the nearest continuous walk-height sheet around the anchor.

    Embedded floor lights and slabs can move the valid feet cell by one block,
    so an exact-Y slice falsely breaks a real corridor every few metres.  Pick
    the closest standable Y in each X/Z column, then retain the nearest 2-D
    component whose neighbouring heights differ by at most one block.
    """
    target_y = anchor[1] - volume.y0
    height = np.full((volume.sx, volume.sz), -1, dtype=np.int32)
    for ix, iz in zip(*np.nonzero(route.any(axis=1))):
        ys = np.nonzero(route[ix, :, iz])[0]
        if len(ys):
            height[ix, iz] = int(min(ys, key=lambda value:
                                     abs(int(value) - target_y)))
    labels = np.full(height.shape, -1, dtype=np.int32)
    components = []
    for raw in np.argwhere(height >= 0):
        start = tuple(int(value) for value in raw)
        if labels[start] >= 0:
            continue
        cid = len(components)
        labels[start] = cid
        queue = deque([start])
        points = []
        while queue:
            x, z = queue.popleft()
            points.append((x, z))
            for dx, dz in NEIGHBOURS:
                nx, nz = x + dx, z + dz
                if (0 <= nx < height.shape[0] and 0 <= nz < height.shape[1]
                        and height[nx, nz] >= 0
                        and abs(int(height[nx, nz]) - int(height[x, z])) <= 1
                        and labels[nx, nz] < 0):
                    labels[nx, nz] = cid
                    queue.append((nx, nz))
        components.append(points)
    if not components:
        return route, "STEPPED_COMPONENT"
    ax, az = anchor[0] - volume.x0, anchor[2] - volume.z0
    ranked = sorted((min(abs(x - ax) + abs(z - az) for x, z in points),
                     -len(points), cid)
                    for cid, points in enumerate(components))
    points = components[ranked[0][2]]
    if len(points) < 24:
        return route, "STEPPED_COMPONENT"
    sheet = np.zeros_like(route)
    for x, z in points:
        sheet[x, height[x, z], z] = True
    return sheet, "ANCHOR_NEAREST_HEIGHT_FIELD"


def step_along(mask: np.ndarray, point: tuple[int, int, int],
               dx: int, dz: int):
    x, y, z = point
    nx, nz = x + dx, z + dz
    if not (0 <= nx < mask.shape[0] and 0 <= nz < mask.shape[2]):
        return None
    for dy in (0, 1, -1):
        ny = y + dy
        if 0 <= ny < mask.shape[1] and mask[nx, ny, nz]:
            return nx, ny, nz
    return None


def straight_score(mask: np.ndarray, point: tuple[int, int, int],
                   dx: int, dz: int, limit: int = 14) -> int:
    score = 0
    current = point
    for _ in range(limit):
        current = step_along(mask, current, dx, dz)
        if current is None:
            break
        score += 1
    return score


def lateral_run(mask: np.ndarray, point: tuple[int, int, int],
                axis: str, limit: int = 16):
    if axis == "X":
        minus, plus = (0, -1), (0, 1)
    else:
        minus, plus = (-1, 0), (1, 0)
    left = right = 0
    current = point
    for _ in range(limit):
        nxt = step_along(mask, current, *minus)
        if nxt is None:
            break
        left += 1
        current = nxt
    current = point
    for _ in range(limit):
        nxt = step_along(mask, current, *plus)
        if nxt is None:
            break
        right += 1
        current = nxt
    return left, right


def clearance(volume: survey.Volume, point: tuple[int, int, int],
              limit: int = 14):
    x, y, z = point
    clear = 0
    for dy in range(0, limit):
        role = state_role(volume, x, y + dy, z)
        if role in {"air", "fixture", "door"}:
            clear += 1
            continue
        return clear, role, state_base(volume, x, y + dy, z)
    return limit, "open_or_outside", "open_or_outside"


def boundary_profile(volume: survey.Volume,
                     point: tuple[int, int, int], axis: str,
                     left: int, right: int, clear: int):
    x, y, z = point
    if axis == "X":
        offsets = ((0, -(left + 1)), (0, right + 1))
    else:
        offsets = ((-(left + 1), 0), (right + 1, 0))
    profiles = []
    materials = []
    height = max(3, min(10, clear + 1))
    for dx, dz in offsets:
        roles = []
        mats = []
        for dy in range(-1, height):
            role = state_role(volume, x + dx, y + dy, z + dz)
            roles.append(ROLE_LETTERS.get(role, "?"))
            mats.append(state_base(volume, x + dx, y + dy, z + dz))
        profiles.append("".join(roles))
        materials.append(mats)
    return profiles, materials


def describe_cell(volume: survey.Volume, route: np.ndarray,
                  point: tuple[int, int, int]):
    sx = straight_score(route, point, 1, 0) \
        + straight_score(route, point, -1, 0)
    sz = straight_score(route, point, 0, 1) \
        + straight_score(route, point, 0, -1)
    if sx >= sz + 2:
        axis = "X"
    elif sz >= sx + 2:
        axis = "Z"
    else:
        axis = "JUNCTION_OR_OPEN"
    if axis == "JUNCTION_OR_OPEN":
        left = right = 0
        width = min(31, 1 + min(sx, sz))
        profiles = ["?", "?"]
        boundary_materials = [[], []]
    else:
        left, right = lateral_run(route, point, axis)
        width = left + 1 + right
        profiles, boundary_materials = boundary_profile(
            volume, point, axis, left, right,
            clearance(volume, point)[0])
    clear, ceiling_role, ceiling_material = clearance(volume, point)
    x, y, z = point
    floor_role = state_role(volume, x, y - 1, z)
    floor_material = state_base(volume, x, y - 1, z)
    signature = (
        axis,
        int(min(width, 31)),
        int(min(clear, 14)),
        floor_role,
        profiles[0],
        profiles[1],
        ceiling_role,
    )
    return {
        "axis": axis,
        "longitudinal_score_x": int(sx),
        "longitudinal_score_z": int(sz),
        "width": int(width),
        "left_cells": int(left),
        "right_cells": int(right),
        "clearance": int(clear),
        "floor_role": floor_role,
        "floor_material": floor_material,
        "left_profile": profiles[0],
        "right_profile": profiles[1],
        "left_materials": boundary_materials[0],
        "right_materials": boundary_materials[1],
        "ceiling_role": ceiling_role,
        "ceiling_material": ceiling_material,
        "signature": signature,
    }


def label_segments(volume: survey.Volume, route: np.ndarray):
    descriptions = {}
    groups = defaultdict(list)
    for raw in np.argwhere(route):
        point = tuple(int(value) for value in raw)
        desc = describe_cell(volume, route, point)
        descriptions[point] = desc
        groups[desc["signature"]].append(point)

    segment_labels = np.full(route.shape, -1, dtype=np.int32)
    segments = []
    for signature, points in groups.items():
        pending = set(points)
        while pending:
            start = pending.pop()
            queue = deque([start])
            cells = [start]
            while queue:
                point = queue.popleft()
                for dx, dz in NEIGHBOURS:
                    nxt = step_along(route, point, dx, dz)
                    if nxt in pending and descriptions[nxt]["signature"] == signature:
                        pending.remove(nxt)
                        queue.append(nxt)
                        cells.append(nxt)
            sid = len(segments)
            for point in cells:
                segment_labels[point] = sid
            world = [volume.world_position(*point) for point in cells]
            mins = [min(p[i] for p in world) for i in range(3)]
            maxs = [max(p[i] for p in world) for i in range(3)]
            representative = min(
                cells,
                key=lambda p: sum(abs(p[i] - np.mean(
                    [q[i] for q in cells])) for i in range(3)))
            rep_desc = descriptions[representative]
            segments.append({
                "id": sid,
                "cells": len(cells),
                "bbox": [mins[0], maxs[0], mins[1], maxs[1],
                         mins[2], maxs[2]],
                "representative": list(volume.world_position(*representative)),
                "signature": {
                    key: value for key, value in rep_desc.items()
                    if key != "signature"
                },
            })

    edge_contacts = Counter()
    for point in descriptions:
        sid = int(segment_labels[point])
        for dx, dz in ((1, 0), (0, 1)):
            nxt = step_along(route, point, dx, dz)
            if nxt is None:
                continue
            other = int(segment_labels[nxt])
            if other >= 0 and other != sid:
                edge_contacts[tuple(sorted((sid, other)))] += 1
    edges = [{"a": a, "b": b, "contacts": count}
             for (a, b), count in sorted(edge_contacts.items())]
    return segment_labels, segments, edges


def label_dominant_runs(volume: survey.Volume, route: np.ndarray,
                        axis: str):
    """Collapse a long corridor into stable whole cross-section runs.

    Per-cell signatures fragment a five-wide corridor because an edge cell and
    a centre cell see different lateral spans.  For a clearly elongated route
    the semantic unit is instead the complete YZ or XY cut at one longitudinal
    coordinate.  Adjacent equal cuts form one segment.
    """
    longitudinal_index = 0 if axis == "X" else 2
    lateral_index = 2 if axis == "X" else 0
    by_longitudinal = defaultdict(list)
    for raw in np.argwhere(route):
        point = tuple(int(value) for value in raw)
        by_longitudinal[point[longitudinal_index]].append(point)

    sections = []
    for longitudinal in sorted(by_longitudinal):
        points = by_longitudinal[longitudinal]
        lateral_values = sorted({point[lateral_index] for point in points})
        y_values = sorted({point[1] for point in points})
        centre_lateral = lateral_values[len(lateral_values) // 2]
        centre_y = y_values[len(y_values) // 2]
        representative = min(
            points,
            key=lambda point: (abs(point[lateral_index] - centre_lateral)
                               + 2 * abs(point[1] - centre_y)))
        desc = describe_cell(volume, route, representative)
        floor_roles = Counter(
            state_role(volume, point[0], point[1] - 1, point[2])
            for point in points)
        clearances = Counter(clearance(volume, point)[0] for point in points)
        # Absolute elevation is recorded but excluded from the equality key;
        # otherwise every tread of a valid stair becomes a separate segment.
        # The macro route does not split at every lamp, column or window mullion.
        # Those cross-section variants remain recorded below, but the stable
        # segment key is the walk sheet shape and support family.
        signature = (
            int(max(lateral_values) - min(lateral_values) + 1),
            floor_roles.most_common(1)[0][0],
        )
        sections.append({
            "longitudinal": longitudinal,
            "points": points,
            "representative": representative,
            "feet_y": [volume.y0 + min(y_values),
                       volume.y0 + max(y_values)],
            "signature_key": signature,
            "signature": desc,
        })

    runs = []
    current = []
    for section in sections:
        if (current
                and (section["longitudinal"]
                     != current[-1]["longitudinal"] + 1
                     or section["signature_key"]
                     != current[-1]["signature_key"])):
            runs.append(current)
            current = []
        current.append(section)
    if current:
        runs.append(current)

    segment_labels = np.full(route.shape, -1, dtype=np.int32)
    segments = []
    for sid, run in enumerate(runs):
        cells = [point for section in run for point in section["points"]]
        for point in cells:
            segment_labels[point] = sid
        world = [volume.world_position(*point) for point in cells]
        mins = [min(point[index] for point in world) for index in range(3)]
        maxs = [max(point[index] for point in world) for index in range(3)]
        middle = run[len(run) // 2]
        representative = volume.world_position(*middle["representative"])
        entry_signature = {
            key: value for key, value in middle["signature"].items()
            if key != "signature"
        }
        entry_signature["dominant_axis"] = axis
        entry_signature["feet_y_span_across_run"] = [
            min(section["feet_y"][0] for section in run),
            max(section["feet_y"][1] for section in run),
        ]
        variants = Counter(
            (section["signature"]["clearance"],
             section["signature"]["left_profile"],
             section["signature"]["right_profile"],
             section["signature"]["ceiling_role"])
            for section in run)
        entry_signature["cross_section_variants"] = [
            {
                "clearance": key[0],
                "left_profile": key[1],
                "right_profile": key[2],
                "ceiling_role": key[3],
                "longitudinal_slices": count,
            }
            for key, count in variants.most_common()
        ]
        segments.append({
            "id": sid,
            "cells": len(cells),
            "longitudinal_range": [
                volume.x0 + run[0]["longitudinal"]
                if axis == "X" else volume.z0 + run[0]["longitudinal"],
                volume.x0 + run[-1]["longitudinal"]
                if axis == "X" else volume.z0 + run[-1]["longitudinal"],
            ],
            "bbox": [mins[0], maxs[0], mins[1], maxs[1],
                     mins[2], maxs[2]],
            "representative": list(representative),
            "signature": entry_signature,
        })
    edges = [{"a": sid, "b": sid + 1, "contacts": 1}
             for sid in range(max(0, len(segments) - 1))]
    return segment_labels, segments, edges


def add_coordinate_grid(draw: ImageDraw.ImageDraw, left: int, top: int,
                        horizontal0: int, horizontal_count: int,
                        y0: int, y_count: int, scale: int,
                        horizontal_name: str):
    for value in range(math.ceil(horizontal0 / 8) * 8,
                       horizontal0 + horizontal_count, 8):
        px = left + (value - horizontal0) * scale
        draw.line((px, top, px, top + y_count * scale), fill=(65, 65, 78))
        draw.text((px + 2, top + 2), f"{horizontal_name}{value}",
                  fill=(205, 205, 215))
    for value in range(math.ceil(y0 / 8) * 8, y0 + y_count, 8):
        py = top + (y0 + y_count - 1 - value) * scale
        draw.line((left, py, left + horizontal_count * scale, py),
                  fill=(65, 65, 78))
        draw.text((2, py + 2), f"y{value}", fill=(205, 205, 215))


def section_panel(volume: survey.Volume, route: np.ndarray,
                  segment_labels: np.ndarray, plane_axis: str,
                  coordinate: int, anchor: tuple[int, int, int],
                  scale: int = 4):
    if plane_axis == "X":
        local = coordinate - volume.x0
        codes = volume.code[local, :, :].transpose(1, 0)
        selected = route[local, :, :].transpose(1, 0)
        segs = segment_labels[local, :, :].transpose(1, 0)
        h0, count, name = volume.z0, volume.sz, "z"
    else:
        local = coordinate - volume.z0
        codes = volume.code[:, :, local].transpose(1, 0)
        selected = route[:, :, local].transpose(1, 0)
        segs = segment_labels[:, :, local].transpose(1, 0)
        h0, count, name = volume.x0, volume.sx, "x"
    colours = np.asarray(
        [ROLE_COLOURS[survey.role_of(state)] for state in volume.states],
        dtype=np.uint8)
    rgb = colours[codes]
    rgb[selected] = (28, 225, 218)
    rgb = rgb[::-1, :, :]
    body = Image.fromarray(rgb, "RGB").resize(
        (count * scale, volume.sy * scale), Image.Resampling.NEAREST)
    image = Image.new("RGB", (body.width + 78, body.height + 48),
                      (13, 13, 19))
    left, top = 62, 24
    image.paste(body, (left, top))
    draw = ImageDraw.Draw(image)
    add_coordinate_grid(draw, left, top, h0, count, volume.y0, volume.sy,
                        scale, name)
    draw.text((left, 4), f"{plane_axis}-SECTION {plane_axis}={coordinate}",
              fill=(255, 214, 84))
    # Label only sizeable route segments intersecting this cut.
    for sid in sorted(int(v) for v in np.unique(segs) if v >= 0):
        pts = np.argwhere(segs == sid)
        if len(pts) < 2:
            continue
        py0, ph0 = pts[len(pts) // 2]
        px = left + ph0 * scale + scale // 2
        py = top + (volume.sy - 1 - py0) * scale + scale // 2
        draw.text((px + 3, py - 8), f"S{sid:03d}", fill=(255, 255, 255))
    draw.text((left, image.height - 18),
              "CYAN=selected standable-air route; no editable mask",
              fill=(225, 225, 232))
    return image


def route_plan(volume: survey.Volume, route: np.ndarray,
               segment_labels: np.ndarray, segments: list[dict],
               anchor: tuple[int, int, int], scale: int = 6):
    rgb = np.zeros((volume.sz, volume.sx, 3), dtype=np.uint8)
    rgb[:] = (13, 13, 19)
    chosen_sid = np.full((volume.sx, volume.sz), -1, dtype=np.int32)
    chosen_y = np.full((volume.sx, volume.sz), -100000, dtype=np.int32)
    for ix, iy, iz in np.argwhere(route):
        world_y = volume.y0 + int(iy)
        if abs(world_y - anchor[1]) < abs(chosen_y[ix, iz] - anchor[1]):
            chosen_y[ix, iz] = world_y
            chosen_sid[ix, iz] = segment_labels[ix, iy, iz]
    for ix, iz in zip(*np.nonzero(chosen_sid >= 0)):
        rgb[iz, ix] = survey.component_colour(int(chosen_sid[ix, iz]))
    body = Image.fromarray(rgb, "RGB").resize(
        (volume.sx * scale, volume.sz * scale), Image.Resampling.NEAREST)
    image = Image.new("RGB", (body.width + 100, body.height + 62),
                      (13, 13, 19))
    left, top = 80, 28
    image.paste(body, (left, top))
    draw = ImageDraw.Draw(image)
    survey.add_grid(draw, left, top, volume.sx, volume.sz, scale,
                    volume.x0, volume.z0)
    ax, ay, az = anchor
    px = left + (ax - volume.x0) * scale + scale // 2
    pz = top + (az - volume.z0) * scale + scale // 2
    draw.ellipse((px - 8, pz - 8, px + 8, pz + 8),
                 outline=(255, 255, 255), width=2)
    draw.line((px - 11, pz, px + 11, pz), fill=(255, 70, 70), width=2)
    draw.line((px, pz - 11, px, pz + 11), fill=(255, 70, 70), width=2)
    for entry in sorted(segments, key=lambda item: item["cells"],
                        reverse=True)[:36]:
        x, _y, z = entry["representative"]
        lx = left + (x - volume.x0) * scale + 2
        lz = top + (z - volume.z0) * scale - 7
        draw.text((lx, lz), f"S{entry['id']:03d}", fill=(255, 255, 255))
    draw.text((left, 5), "WALKABLE-AIR SEGMENT GRAPH / TOP VIEW",
              fill=(255, 214, 84))
    draw.text((5, image.height - 20),
              f"ANCHOR=({ax},{ay},{az}) is observation only; EDITABLE MASK=EMPTY",
              fill=(232, 232, 238))
    return image


def write_sha(directory: Path) -> str:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "packet.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
                        f"{path.relative_to(directory).as_posix()}")
    payload = "\n".join(rows) + "\n"
    (directory / "packet.sha256").write_text(payload, encoding="ascii")
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True)
    parser.add_argument("--anchor", nargs=3, type=int, required=True)
    parser.add_argument("--horizontal", type=int, default=48)
    parser.add_argument("--vertical", type=int, default=32)
    parser.add_argument("--repair-id", required=True)
    parser.add_argument("--emit", required=True)
    parser.add_argument("--screenshot")
    args = parser.parse_args()

    anchor = tuple(args.anchor)
    box = (anchor[0] - args.horizontal, anchor[0] + args.horizontal,
           anchor[1] - args.vertical, anchor[1] + args.vertical,
           anchor[2] - args.horizontal, anchor[2] + args.horizontal)
    dimension = "dimensions/projectseele/geofront"
    world_root = ROOT / "run" / "saves" / args.world / dimension
    output = ROOT / args.emit
    output.mkdir(parents=True, exist_ok=True)

    volume = survey.Volume(world_root, box)
    masks = volume.masks()
    labels, components, cid, stepped_route = selected_component(
        volume, masks["standable"], anchor)
    route, route_sheet_mode = anchor_level_sheet(
        stepped_route, volume, anchor)
    selected_points = np.argwhere(route)
    extents = selected_points.max(axis=0) - selected_points.min(axis=0)
    if extents[0] >= max(8, 2 * extents[2]):
        semantic_axis = "X"
        segment_labels, segments, edges = label_dominant_runs(
            volume, route, semantic_axis)
    elif extents[2] >= max(8, 2 * extents[0]):
        semantic_axis = "Z"
        segment_labels, segments, edges = label_dominant_runs(
            volume, route, semantic_axis)
    else:
        semantic_axis = "BRANCHED_OR_OPEN"
        segment_labels, segments, edges = label_segments(volume, route)

    plan = route_plan(volume, route, segment_labels, segments, anchor)
    plan.save(output / "01_walkable_segment_plan.png")

    offsets = (-24, -16, -8, 0, 8, 16, 24)
    x_planes = sorted({anchor[0] + offset for offset in offsets
                       if volume.x0 <= anchor[0] + offset <= volume.x1})
    z_planes = sorted({anchor[2] + offset for offset in offsets
                       if volume.z0 <= anchor[2] + offset <= volume.z1})
    x_panels = [section_panel(volume, route, segment_labels, "X", value,
                              anchor) for value in x_planes]
    z_panels = [section_panel(volume, route, segment_labels, "Z", value,
                              anchor) for value in z_planes]
    survey.combine_panels(x_panels, 2, output / "02_x_sections.png")
    survey.combine_panels(z_panels, 2, output / "03_z_sections.png")

    survey.output_anchor = anchor
    iso = [
        survey.iso_projection(volume, masks, anchor, 1, 1,
                              "BASE +X/+Z / NO EDIT MASK"),
        survey.iso_projection(volume, masks, anchor, -1, -1,
                              "BASE -X/-Z / NO EDIT MASK"),
    ]
    survey.combine_panels(iso, 2, output / "04_iso_context.png")

    selected = next(item for item in components if item["id"] == cid)
    ax, ay, az = anchor
    for entry in segments:
        x, y, z = entry["representative"]
        entry["distance_to_observation_anchor"] = (
            abs(x - ax) + 2 * abs(y - ay) + abs(z - az))
    payload = {
        "repair_id": args.repair_id,
        "mode": "READ_ONLY_SEMANTIC_SURVEY",
        "world_files_written": False,
        "editable_mask": [],
        "source_save": args.world,
        "source_dimension": dimension,
        "source_screenshot": args.screenshot,
        "observation_anchor": list(anchor),
        "observation_anchor_is_edit_target": False,
        "survey_box": list(box),
        "selected_walk_component": selected,
        "selected_walk_component_touches_boundary":
            selected["touches_survey_boundary"],
        "semantic_model": (
            "standable-air route graph + complete local cross-section "
            "signature; solid adjacency is not treated as building ownership"),
        "semantic_axis": semantic_axis,
        "route_sheet_mode": route_sheet_mode,
        "segment_count": len(segments),
        "segments": sorted(segments, key=lambda item: item["id"]),
        "segment_edges": edges,
        "candidate_x_cut_planes": x_planes,
        "candidate_z_cut_planes": z_planes,
        "automatic_decision": "STOP",
        "stop_conditions": [
            "human has not selected the wrong route segment IDs",
            "human has not selected cut planes and protected shared walls",
            "builder ownership is not assigned per decisive interface",
            "a complete reference cross-section/adapter outline is not selected",
            ("selected walk component touches the survey boundary; expand the "
             "survey before any topology-completeness claim")
            if selected["touches_survey_boundary"] else
            "no edit is authorised by a semantic survey alone",
        ],
        "region_file_hashes": volume.region_hashes(),
        "chunk_voxel_hashes": volume.chunk_hashes(),
    }
    (output / "00_manifest.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    digest = write_sha(output)
    print(f"[semantic] repair={args.repair_id} route={selected['cells']} "
          f"segments={len(segments)} edges={len(edges)} sha256={digest}")


if __name__ == "__main__":
    main()
