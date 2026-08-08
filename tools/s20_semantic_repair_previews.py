#!/usr/bin/env python3
"""Build exact, read-only S20 semantic repair previews.

The script reads the disaster-free Anvil archive and mutates only in-memory
``Volume`` objects.  It has no APPLY mode and never opens a region for writing.

The three proposals in this file are intentionally independent:

* R02 removes the human-selected A/B/C orphan stair shell by following its
  standable-air path and accepting only the repeated route material contract;
* R04 rebuilds two orthogonal hall turns from the union of their two legal
  walkable cross-sections, adding missing outside corners and removing only
  overlapping inside wall columns;
* R05 implements observation semantic B1 as a complete section: floor,
  support, window/wall lower edge and one straight end adapter.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import s20_recovery_preview as preview  # noqa: E402
import s20_semantic_selection_boards as selection  # noqa: E402
import survey_facility_target as survey  # noqa: E402


AIR = "minecraft:air"
FLOOR = "minecraft:polished_deepslate"
SUPPORT = "minecraft:reinforced_deepslate"
WALL = "minecraft:deepslate_tiles"
GLASS = "minecraft:gray_stained_glass"
WALL_FLOOR = "minecraft:polished_blackstone_bricks"
STAIR_EAST = (
    "minecraft:polished_deepslate_stairs"
    "[facing=east,half=bottom,shape=straight,waterlogged=false]"
)

REMOVED = preview.REMOVED
ADDED = preview.ADDED
REPLACED = preview.REPLACED


def set_proposed(volume: survey.Volume,
                 reasons: dict[tuple[int, int, int], str],
                 x: int, y: int, z: int, state: str, reason: str) -> None:
    preview.set_state(volume, x, y, z, state)
    reasons[(x, y, z)] = reason


def packet_sha(directory: Path) -> str:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "packet.sha256":
            rows.append(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
                f"{path.relative_to(directory).as_posix()}"
            )
    payload = "\n".join(rows) + "\n"
    (directory / "packet.sha256").write_text(payload, encoding="ascii")
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def component_excerpt(components: list[dict], ids: set[int]) -> list[dict]:
    result = []
    for cid in sorted(ids):
        if not (0 <= cid < len(components)):
            continue
        item = components[cid]
        result.append({
            "id": cid,
            "cells": int(item.get("cells", 0)),
            "bbox": item.get("bbox"),
            "touches_boundary": bool(item.get("touches_boundary", False)),
        })
    return result


def affected_walk_components(volume: survey.Volume,
                             changed: np.ndarray) -> dict:
    masks = volume.masks()
    labels, components = survey.label_components(
        masks["standable"], volume, walkable=True)
    ids: set[int] = set()
    for ix, iy, iz in zip(*np.nonzero(changed)):
        for dx, dy, dz in (
                (0, 0, 0), (0, 1, 0), (0, 2, 0),
                (1, 1, 0), (-1, 1, 0), (0, 1, 1), (0, 1, -1)):
            x, y, z = ix + dx, iy + dy, iz + dz
            if (0 <= x < labels.shape[0] and 0 <= y < labels.shape[1]
                    and 0 <= z < labels.shape[2]):
                cid = int(labels[x, y, z])
                if cid >= 0:
                    ids.add(cid)
    return {
        "component_count_in_survey": len(components),
        "components_touching_diff": component_excerpt(components, ids),
    }


def diff_iso_overlay(world_root: Path, box, changed: np.ndarray,
                     diff: np.ndarray, anchor, output: Path) -> None:
    overlay = survey.Volume(world_root, box)
    colours = {
        REMOVED: "minecraft:red_concrete",
        ADDED: "minecraft:lime_concrete",
        REPLACED: "minecraft:yellow_concrete",
    }
    for ix, iy, iz in zip(*np.nonzero(changed)):
        x, y, z = overlay.world_position(ix, iy, iz)
        preview.set_state(overlay, x, y, z,
                          colours[int(diff[ix, iy, iz])])
    masks = overlay.masks()
    panels = [
        survey.iso_projection(overlay, masks, anchor, 1, 1,
                              "DIFF X-RAY +X/+Z"),
        survey.iso_projection(overlay, masks, anchor, -1, -1,
                              "DIFF X-RAY -X/-Z"),
    ]
    survey.combine_panels(panels, 2, output)


def render_walkspace_comparison(before: survey.Volume,
                                after: survey.Volume,
                                anchor: tuple[int, int, int],
                                output: Path) -> None:
    before_walk = before.masks()["standable"]
    after_walk = after.masks()["standable"]
    # Collapse all feet elevations into one X/Z evidence sheet.  The image is
    # deliberately topology-only; real block context remains in the iso views.
    b = before_walk.any(axis=1)
    a = after_walk.any(axis=1)
    scale = 5
    panels = []
    for title, mask in (("BEFORE WALKABLE AIR", b),
                        ("AFTER WALKABLE AIR", a)):
        rgb = np.zeros((before.sz, before.sx, 3), dtype=np.uint8)
        rgb[:] = (13, 15, 22)
        rgb[mask.transpose(1, 0)] = (68, 194, 118)
        body = Image.fromarray(rgb, "RGB").resize(
            (before.sx * scale, before.sz * scale),
            Image.Resampling.NEAREST)
        image = Image.new("RGB", (body.width + 84, body.height + 52),
                          (13, 15, 22))
        image.paste(body, (72, 28))
        draw = ImageDraw.Draw(image)
        survey.add_grid(draw, 72, 28, before.sx, before.sz, scale,
                        before.x0, before.z0)
        px = 72 + (anchor[0] - before.x0) * scale + scale // 2
        pz = 28 + (anchor[2] - before.z0) * scale + scale // 2
        draw.ellipse((px - 6, pz - 6, px + 6, pz + 6),
                     outline=(255, 255, 255), width=2)
        draw.text((72, 6), title, fill=(255, 214, 84))
        panels.append(image)
    survey.combine_panels(panels, 2, output)


def emit_preview(world_root: Path, output: Path, repair_id: str,
                 box, anchor: tuple[int, int, int],
                 before: survey.Volume, after: survey.Volume,
                 reasons: dict[tuple[int, int, int], str],
                 proposal: list[str], contract: dict) -> str:
    output.mkdir(parents=True, exist_ok=True)
    layers_dir = output / "layers"
    layers_dir.mkdir(exist_ok=True)

    states, before_code, after_code = preview.canonical_codes(before, after)
    changed = before_code != after_code
    roles = np.asarray([survey.role_of(state) for state in states])
    before_air = roles[before_code] == "air"
    after_air = roles[after_code] == "air"
    diff = np.zeros(changed.shape, dtype=np.uint8)
    diff[changed & ~before_air & after_air] = REMOVED
    diff[changed & before_air & ~after_air] = ADDED
    diff[changed & ~before_air & ~after_air] = REPLACED
    diff[changed & (diff == 0)] = REPLACED

    transitions = Counter()
    by_reason = Counter()
    by_y = Counter()
    touched = [10**9, 10**9, 10**9, -10**9, -10**9, -10**9]
    rows = 0
    with (output / "block_diff.csv").open(
            "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("x", "y", "z", "before", "after", "change",
                         "reason"))
        for ix, iy, iz in zip(*np.nonzero(changed)):
            x, y, z = before.world_position(ix, iy, iz)
            old = states[int(before_code[ix, iy, iz])]
            new = states[int(after_code[ix, iy, iz])]
            kind = {REMOVED: "removed", ADDED: "added",
                    REPLACED: "replaced"}[int(diff[ix, iy, iz])]
            reason = reasons.get((x, y, z), "proposal")
            writer.writerow((x, y, z, old, new, kind, reason))
            transitions[(old, new)] += 1
            by_reason[reason] += 1
            by_y[y] += 1
            touched[0] = min(touched[0], x)
            touched[1] = min(touched[1], y)
            touched[2] = min(touched[2], z)
            touched[3] = max(touched[3], x)
            touched[4] = max(touched[4], y)
            touched[5] = max(touched[5], z)
            rows += 1

    pages = []
    for y in sorted(by_y):
        image = preview.render_diff_plan(
            diff, box, y, anchor, repair_id, scale=5)
        image.save(layers_dir / f"y{y}.png")
        pages.append(image)
    if pages:
        pages[0].save(output / "03_diff_layers.pdf", "PDF", save_all=True,
                      append_images=pages[1:], resolution=120.0)

    before_masks = before.masks()
    after_masks = after.masks()
    survey.orthographic_packet(before, before_masks,
                               survey.colour_table(before), anchor,
                               output / "01_before_orthos.png")
    survey.orthographic_packet(after, after_masks,
                               survey.colour_table(after), anchor,
                               output / "02_after_orthos.png")
    panels = [
        survey.iso_projection(before, before_masks, anchor, 1, 1,
                              "BEFORE +X/+Z"),
        survey.iso_projection(before, before_masks, anchor, -1, -1,
                              "BEFORE -X/-Z"),
        survey.iso_projection(after, after_masks, anchor, 1, 1,
                              "PROPOSAL +X/+Z"),
        survey.iso_projection(after, after_masks, anchor, -1, -1,
                              "PROPOSAL -X/-Z"),
    ]
    survey.combine_panels(panels, 2,
                          output / "04_before_after_same_views.png")
    diff_iso_overlay(world_root, box, changed, diff, anchor,
                     output / "05_diff_iso_overlay.png")
    render_walkspace_comparison(before, after, anchor,
                                output / "06_walkspace_before_after.png")
    survey.write_glb(after, after_masks, output / "07_after_preview.glb")

    affected = {
        "before": affected_walk_components(before, changed),
        "after": affected_walk_components(after, changed),
        "contract": contract,
    }
    (output / "affected_components.json").write_text(
        json.dumps(affected, indent=2), encoding="utf-8")

    manifest = {
        "repair_id": repair_id,
        "revision": 1,
        "mode": "READ_ONLY_IN_MEMORY_PREVIEW",
        "world_files_written": False,
        "source_save": world_root.parents[2].name,
        "source_dimension": "dimensions/projectseele/geofront",
        "box": list(box),
        "anchor": list(anchor),
        "proposal": proposal,
        "changed_blocks": rows,
        "removed": int((diff == REMOVED).sum()),
        "added": int((diff == ADDED).sum()),
        "replaced": int((diff == REPLACED).sum()),
        "touched_extent": touched if rows else None,
        "changed_by_reason": dict(sorted(by_reason.items())),
        "changed_by_y": {str(y): by_y[y] for y in sorted(by_y)},
        "top_transitions": [
            {"before": old, "after": new, "count": count}
            for (old, new), count in transitions.most_common(40)
        ],
        "region_file_hashes": before.region_hashes(),
        "chunk_voxel_hashes": before.chunk_hashes(),
        "approval_gate": (
            "PREVIEW ONLY. Apply is forbidden until the user approves this "
            "repair ID, revision, baseline hashes and packet SHA."
        ),
        "runtime_world_writers": "disabled by read-only marker",
    }
    (output / "00_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "preview_summary.md").write_text(
        "# " + repair_id + "\n\n"
        + "World writes: **0**\n\n"
        + "Changed blocks: **" + str(rows) + "**\n\n"
        + "- removed: " + str(manifest["removed"]) + "\n"
        + "- added: " + str(manifest["added"]) + "\n"
        + "- replaced: " + str(manifest["replaced"]) + "\n\n"
        + "Approval is required for this exact packet hash before APPLY.\n",
        encoding="utf-8")
    return packet_sha(output)


def build_route_preview(world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R02-WRONG-ROUTE-ABC-PREVIEW-r01"
    box = (84, 108, -432, -388, 136, 210)
    anchor = (97, -425, 201)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}

    evidence = survey.Volume(world_root,
                             (48, 124, -435, -388, 125, 246))
    route = selection.selected_route(evidence, anchor)
    candidates: dict[tuple[int, int, int], str] = {}
    for raw in np.argwhere(route):
        point = tuple(int(value) for value in raw)
        tag = selection.route_candidate(point, evidence)
        if tag in {"A", "B", "C"}:
            candidates[evidence.world_position(*point)] = tag

    floor_materials = {
        "minecraft:polished_deepslate",
        "minecraft:purple_concrete",
        "minecraft:smooth_quartz_stairs",
        "minecraft:sea_lantern",
    }
    wall_materials = {"minecraft:gray_concrete"}
    ceiling_materials = {"minecraft:iron_block"}
    protected = []

    def neighbour_selected(x: int, y: int, z: int,
                           dx: int, dz: int) -> bool:
        return any((x + dx, y + dy, z + dz) in candidates
                   for dy in (-1, 0, 1))

    for (x, y, z), tag in sorted(candidates.items()):
        for yy, role, allowed in (
                (y - 1, "floor", floor_materials),
                (y + 4, "ceiling", ceiling_materials)):
            state = before.state(x - before.x0, yy - before.y0,
                                 z - before.z0)
            if survey.base_name(state) in allowed:
                set_proposed(after, reasons, x, yy, z, AIR,
                             f"route_{tag}_{role}")
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if neighbour_selected(x, y, z, dx, dz):
                continue
            for yy in range(y, y + 4):
                qx, qz = x + dx, z + dz
                state = before.state(qx - before.x0, yy - before.y0,
                                     qz - before.z0)
                if survey.base_name(state) in wall_materials:
                    set_proposed(after, reasons, qx, yy, qz, AIR,
                                 f"route_{tag}_exclusive_wall")
                elif survey.role_of(state) != "air":
                    protected.append((qx, yy, qz, state))

    # The east wall of the Unit-02 well is protected even when it borders a
    # selected tail cell.  No route material may override this veto.
    for x, y, z, _state in protected:
        if 55 <= x <= 89 and 203 <= z <= 237:
            preview.set_state(after, x, y, z,
                              before.state(x - before.x0,
                                           y - before.y0,
                                           z - before.z0))
            reasons.pop((x, y, z), None)

    contract = {
        "human_selection": ["A", "B", "C"],
        "cut_planes": ["z=139/140", "z=205/206"],
        "shell_rule": (
            "selected standable air + direct route floor + four-block "
            "exclusive gray-concrete side wall + iron-block ceiling"
        ),
        "allowed_floor_materials": sorted(floor_materials),
        "allowed_wall_materials": sorted(wall_materials),
        "allowed_ceiling_materials": sorted(ceiling_materials),
        "unit02_protection": [55, 89, -445, -366, 203, 237],
        "non_route_adjacent_solids_retained": len(set(protected)),
        "interface_cap": "not included in r01; inspect the exposed upper edge",
    }
    digest = emit_preview(
        world_root, output_root / repair_id, repair_id, box, anchor,
        before, after, reasons,
        [
            "Remove the complete human-selected A/B/C orphan stair shell.",
            "Retain all neighbouring solids that do not match the measured "
            "route material contract.",
            "Hard-protect the Unit-02 launch-well shell.",
        ], contract)
    return repair_id, digest


def corridor_footprints() -> tuple[set[tuple[int, int]],
                                   set[tuple[int, int]]]:
    interior: set[tuple[int, int]] = set()
    for x in range(108, 119):
        for z in range(183, 188):
            interior.add((x, z))
    for x in range(116, 121):
        for z in range(185, 242):
            interior.add((x, z))
    for x in range(96, 119):
        for z in range(239, 244):
            interior.add((x, z))

    boundary: set[tuple[int, int]] = set()
    for x, z in interior:
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                candidate = (x + dx, z + dz)
                if (candidate not in interior
                        and 96 <= candidate[0] <= 121):
                    boundary.add(candidate)
    return interior, boundary


def build_east_corridor_preview(world_root: Path,
                                output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R04-EAST-CORRIDOR-CORNERS-PREVIEW-r01"
    box = (92, 123, -397, -389, 178, 247)
    anchor = (119, -392, 182)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}
    interior, boundary = corridor_footprints()
    turns = ((118, 185), (118, 241))

    missing_columns = []
    for x, z in sorted(boundary):
        if min(abs(x - tx) + abs(z - tz) for tx, tz in turns) > 8:
            continue
        middle = before.state(x - before.x0, -392 - before.y0,
                              z - before.z0)
        if survey.role_of(middle) != "air":
            continue
        missing_columns.append((x, z))
        canonical = {
            -396: SUPPORT,
            -395: WALL_FLOOR,
            -394: WALL,
            -393: GLASS,
            -392: GLASS,
            -391: WALL,
            -390: WALL,
        }
        for y, state in canonical.items():
            set_proposed(after, reasons, x, y, z, state,
                         "missing_outer_corner_shell")

    overlap_columns = []
    allowed_overlap = {WALL, GLASS}
    for x, z in sorted(interior):
        solids = []
        for y in range(-394, -390):
            state = before.state(x - before.x0, y - before.y0,
                                 z - before.z0)
            if state in allowed_overlap:
                solids.append(y)
        if len(solids) != 4:
            continue
        overlap_columns.append((x, z))
        for y in solids:
            set_proposed(after, reasons, x, y, z, AIR,
                         "overlapping_internal_side_wall")
        floor_state = before.state(x - before.x0, -395 - before.y0,
                                   z - before.z0)
        if floor_state == WALL_FLOOR:
            set_proposed(after, reasons, x, -395, z, FLOOR,
                         "restore_walkable_floor_under_removed_wall")

    contract = {
        "derivation": (
            "union of three legal five-wide walkable rectangles; outer "
            "Chebyshev boundary closes voxel corners; internal shared walls "
            "are removed only when all four wall layers match exactly"
        ),
        "missing_outer_corner_columns": missing_columns,
        "overlapping_internal_wall_columns": overlap_columns,
        "reported_gap_anchors": [[119, -392, 182], [119, -392, 244]],
        "reported_extra_anchors": [[117, -394, 237], [114, -394, 187]],
        "expected_missing_columns": 10,
        "expected_overlap_columns": 6,
    }
    if len(missing_columns) != 10 or len(overlap_columns) != 6:
        raise RuntimeError(
            "east corridor topology no longer matches the reviewed contract: "
            f"missing={len(missing_columns)} overlap={len(overlap_columns)}")
    digest = emit_preview(
        world_root, output_root / repair_id, repair_id, box, anchor,
        before, after, reasons,
        [
            "Close the two missing outside corner shells at the orthogonal "
            "north/south turns.",
            "Remove only the six duplicated side-wall columns that currently "
            "protrude into the legal walkable union.",
            "Do not rewrite any unaffected corridor slice or decoration.",
        ], contract)
    return repair_id, digest


def build_observation_b1_preview(world_root: Path,
                                 output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R05-OBSERVATION-B1-PREVIEW-r01"
    box = (-40, 100, -399, -388, 234, 248)
    anchor = (52, -394, 242)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}

    # Lower the long straight interior, stopping before the east handoff.
    for x in range(-35, 93):
        for z in range(239, 244):
            old_floor = before.state(x - before.x0, -395 - before.y0,
                                     z - before.z0)
            set_proposed(after, reasons, x, -395, z, AIR,
                         "b1_clear_old_floor_plane")
            set_proposed(after, reasons, x, -396, z, old_floor,
                         "b1_lower_floor_with_original_material_pattern")
            set_proposed(after, reasons, x, -397, z, SUPPORT,
                         "b1_new_structural_support")
        for z in (238, 244):
            old_floor = before.state(x - before.x0, -395 - before.y0,
                                     z - before.z0)
            old_lower_wall = before.state(
                x - before.x0, -394 - before.y0, z - before.z0)
            set_proposed(after, reasons, x, -395, z, old_lower_wall,
                         "b1_extend_window_or_side_wall_down")
            set_proposed(after, reasons, x, -396, z, old_floor,
                         "b1_lower_boundary_floor")
            set_proposed(after, reasons, x, -397, z, SUPPORT,
                         "b1_new_boundary_support")

    # Extend the sealed west end downward as part of the same section.
    for z in range(238, 245):
        old_floor = before.state(-36 - before.x0, -395 - before.y0,
                                 z - before.z0)
        old_lower_wall = before.state(-36 - before.x0, -394 - before.y0,
                                      z - before.z0)
        set_proposed(after, reasons, -36, -395, z, old_lower_wall,
                     "b1_extend_west_end_wall_down")
        set_proposed(after, reasons, -36, -396, z, old_floor,
                     "b1_lower_west_end_floor")
        set_proposed(after, reasons, -36, -397, z, SUPPORT,
                     "b1_new_west_end_support")

    # One straight five-wide stair row returns to the unchanged east handoff.
    for z in range(239, 244):
        set_proposed(after, reasons, 93, -395, z, AIR,
                     "b1_east_adapter_headroom")
        set_proposed(after, reasons, 93, -396, z, STAIR_EAST,
                     "b1_east_adapter_stair")
        set_proposed(after, reasons, 93, -397, z, SUPPORT,
                     "b1_east_adapter_support")
    for z in (238, 244):
        old_floor = before.state(93 - before.x0, -395 - before.y0,
                                 z - before.z0)
        old_lower_wall = before.state(93 - before.x0, -394 - before.y0,
                                      z - before.z0)
        set_proposed(after, reasons, 93, -395, z, old_lower_wall,
                     "b1_extend_adapter_side_wall_down")
        set_proposed(after, reasons, 93, -396, z, old_floor,
                     "b1_lower_adapter_boundary_floor")
        set_proposed(after, reasons, 93, -397, z, SUPPORT,
                     "b1_adapter_boundary_support")

    contract = {
        "human_selection": "B1",
        "flat_lowered_section": {
            "x": [-35, 92], "z": [238, 244],
            "old_floor_y": -395, "new_floor_y": -396,
            "new_support_y": -397,
        },
        "ceiling": "unchanged at y=-390",
        "window_top": "unchanged",
        "wall_window_extension": "one block downward at z=238 and z=244",
        "sealed_west_end_extended": True,
        "east_adapter": "five-wide straight stair row at x=93",
        "unchanged_east_handoff_starts": 94,
    }
    digest = emit_preview(
        world_root, output_root / repair_id, repair_id, box, anchor,
        before, after, reasons,
        [
            "Implement the approved B1 semantic over the complete observation "
            "section, not the floor alone.",
            "Lower floor/support one block while retaining the ceiling and "
            "window top.",
            "Extend both side boundaries and the west end downward, then "
            "return to the old east floor with one straight adapter row.",
        ], contract)
    return repair_id, digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        default=("_archive/SEELE_S20_REBUILD-"
                 "post-handoff-reconcile-20260801-150700"))
    parser.add_argument(
        "--emit-root", default="artifacts/map_previews")
    parser.add_argument(
        "--only", choices=("route", "east", "observation", "all"),
        default="all")
    args = parser.parse_args()

    world_root = (ROOT / "run" / "saves" / args.world
                  / "dimensions" / "projectseele" / "geofront")
    output_root = ROOT / args.emit_root
    output_root.mkdir(parents=True, exist_ok=True)
    builders = {
        "route": build_route_preview,
        "east": build_east_corridor_preview,
        "observation": build_observation_b1_preview,
    }
    selected = builders if args.only == "all" else {args.only: builders[args.only]}
    for name, builder in selected.items():
        repair_id, digest = builder(world_root, output_root)
        print(f"[{name}] {repair_id} sha256={digest}")


if __name__ == "__main__":
    main()
