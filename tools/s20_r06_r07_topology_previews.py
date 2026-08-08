#!/usr/bin/env python3
"""Build the next two read-only S20 topology repair previews.

The reported F3 coordinates are observation anchors, never edit cuboids.
Every proposal below is derived from a complete repeated cross-section or a
connected iron-bar component.  Both saves and Anvil region files remain
strictly read-only; APPLY is handled by the separate approved-packet tool.

R06 moves the complete launch observation gallery from feet Y=-395 to feet
Y=-418, connects it to the authored command stair at (28,-418,255), retires
the two adapter rows at the old elevation and removes the three complete
launch-well railing components.

R07 removes the complete stepped bridge observed at (98,-398,173), restores
both structures it punched through, removes three connected corridor-railing
components, closes the upper R02 cut plane and clears only the historically
measured R02 lower-tail attachments that do not belong to Unit-02.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import s20_semantic_repair_previews as repair  # noqa: E402
import s20_semantic_selection_boards as selection  # noqa: E402
import survey_facility_target as survey  # noqa: E402


AIR = "minecraft:air"
REINFORCED = "minecraft:reinforced_deepslate"
POLISHED = "minecraft:polished_deepslate"
BLACKSTONE = "minecraft:polished_blackstone_bricks"
TILES = "minecraft:deepslate_tiles"
GRAY_GLASS = "minecraft:gray_stained_glass"
RED = "minecraft:red_concrete"
SEA_LANTERN = "minecraft:sea_lantern"


def state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


def base_state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return survey.base_name(state(volume, x, y, z))


def set_state(volume: survey.Volume,
              reasons: dict[tuple[int, int, int], str],
              x: int, y: int, z: int, value: str, reason: str) -> None:
    repair.set_proposed(volume, reasons, x, y, z, value, reason)


def connected_material_component(
        volume: survey.Volume, anchor: tuple[int, int, int],
        material: str) -> set[tuple[int, int, int]]:
    """Return one exact 6-neighbour material component in world coordinates."""
    if base_state(volume, *anchor) != material:
        raise RuntimeError(
            f"component anchor {anchor} is {state(volume, *anchor)}, "
            f"expected {material}")
    queue = deque([anchor])
    found = {anchor}
    while queue:
        x, y, z = queue.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0),
                           (0, 1, 0), (0, -1, 0),
                           (0, 0, 1), (0, 0, -1)):
            point = (x + dx, y + dy, z + dz)
            if point in found:
                continue
            if not (volume.x0 <= point[0] <= volume.x1
                    and volume.y0 <= point[1] <= volume.y1
                    and volume.z0 <= point[2] <= volume.z1):
                continue
            if base_state(volume, *point) == material:
                found.add(point)
                queue.append(point)
    return found


def bbox(points: set[tuple[int, int, int]]) -> list[int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    return [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]


def render_feet_layers(before: survey.Volume, after: survey.Volume,
                       levels: list[int], anchor: tuple[int, int, int],
                       output: Path) -> None:
    """Render actual standable-air topology at named feet elevations."""
    scale = 6
    panels = []
    for label, volume in (("BEFORE", before), ("AFTER", after)):
        walkable = volume.masks()["standable"]
        for y in levels:
            layer = walkable[:, y - volume.y0, :].transpose(1, 0)
            rgb = np.zeros((volume.sz, volume.sx, 3), dtype=np.uint8)
            rgb[:] = (13, 15, 22)
            rgb[layer] = (68, 194, 118)
            body = Image.fromarray(rgb, "RGB").resize(
                (volume.sx * scale, volume.sz * scale),
                Image.Resampling.NEAREST)
            image = Image.new("RGB", (body.width + 92, body.height + 58),
                              (13, 15, 22))
            image.paste(body, (76, 30))
            draw = ImageDraw.Draw(image)
            survey.add_grid(draw, 76, 30, volume.sx, volume.sz, scale,
                            volume.x0, volume.z0)
            ax, _ay, az = anchor
            px = 76 + (ax - volume.x0) * scale + scale // 2
            pz = 30 + (az - volume.z0) * scale + scale // 2
            draw.ellipse((px - 7, pz - 7, px + 7, pz + 7),
                         outline=(255, 255, 255), width=2)
            draw.text((76, 7), f"{label} / FEET Y={y}",
                      fill=(255, 214, 84))
            panels.append(image)
    survey.combine_panels(panels, len(levels), output)


def component_id_at(volume: survey.Volume,
                    point: tuple[int, int, int]) -> tuple[int, list[dict]]:
    labels, components = survey.label_components(
        volume.masks()["standable"], volume, walkable=True)
    ix = point[0] - volume.x0
    iy = point[1] - volume.y0
    iz = point[2] - volume.z0
    return int(labels[ix, iy, iz]), components


def build_observation_to_command(
        world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R06-OBSERVATION-TO-COMMAND-PREVIEW-r01"
    box = (-40, 100, -423, -388, 199, 260)
    anchor = (28, -418, 255)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}

    # The approved B1 section has support/floor/ceiling at -397/-396/-390.
    # Translate every cell, including interior air, by -23 so no pyramid-shell
    # voxel can survive inside the new pressure corridor.
    for x in range(-36, 93):
        for z in range(238, 245):
            for old_y in range(-397, -389):
                value = state(before, x, old_y, z)
                set_state(after, reasons, x, old_y - 23, z, value,
                          "translate_complete_gallery_section_down_23")
                set_state(after, reasons, x, old_y, z, AIR,
                          "retire_old_gallery_section")

    # Replace the former one/two-block adapter with a sealed east end at the
    # new elevation.  The still-existing east bypass is capped at x=96, so
    # neither retired route ends in open air during the staged recovery.
    for x in range(93, 96):
        for z in range(238, 245):
            for y in range(-397, -389):
                if survey.role_of(state(before, x, y, z)) != "air":
                    set_state(after, reasons, x, y, z, AIR,
                              "retire_old_gallery_adapter")
    for z in range(238, 245):
        set_state(after, reasons, 93, -420, z, REINFORCED,
                  "new_gallery_east_end_support")
        set_state(after, reasons, 93, -419, z, POLISHED,
                  "new_gallery_east_end_floor")
        for y in range(-418, -413):
            value = RED if y == -416 else BLACKSTONE
            set_state(after, reasons, 93, y, z, value,
                      "new_gallery_sealed_east_end")
        set_state(after, reasons, 93, -413, z, TILES,
                  "new_gallery_east_end_ceiling")
    for z in range(239, 244):
        for y in range(-394, -390):
            set_state(after, reasons, 96, y, z, TILES,
                      "cap_retained_upper_east_bypass")

    # Three-wide personnel connector from the gallery's south wall to the
    # authored three-wide command stair landing at z=255.  The total pressure
    # shell is five blocks wide, with support and ceiling included.
    for x in range(27, 30):
        for y in range(-418, -413):
            set_state(after, reasons, x, y, 244, AIR,
                      "open_gallery_command_connector")
    for z in range(245, 255):
        for x in range(26, 31):
            set_state(after, reasons, x, -420, z, REINFORCED,
                      "command_connector_support")
            floor = BLACKSTONE if x in (26, 30) else POLISHED
            set_state(after, reasons, x, -419, z, floor,
                      "command_connector_floor")
            for y in range(-418, -413):
                if x in (26, 30):
                    wall = GRAY_GLASS if y in (-417, -416) else TILES
                    set_state(after, reasons, x, y, z, wall,
                              "command_connector_side_wall")
                else:
                    set_state(after, reasons, x, y, z, AIR,
                              "command_connector_clearance")
            ceiling = SEA_LANTERN if x == 28 and z in (248, 253) else TILES
            set_state(after, reasons, x, -413, z, ceiling,
                      "command_connector_ceiling")

    # Remove only the three complete launch-well perimeter railing components.
    railing_contract = []
    for component_anchor in ((-29, -394, 203),
                             (13, -394, 203),
                             (55, -394, 203)):
        points = connected_material_component(
            before, component_anchor, "minecraft:iron_bars")
        if len(points) != 136:
            raise RuntimeError(
                f"launch railing at {component_anchor} changed: {len(points)}")
        railing_contract.append({
            "anchor": list(component_anchor),
            "cells": len(points),
            "bbox": bbox(points),
        })
        for x, y, z in points:
            set_state(after, reasons, x, y, z, AIR,
                      "remove_complete_launch_well_railing_component")

    old_id, _ = component_id_at(after, (28, -395, 242))
    gallery_id, components = component_id_at(after, (28, -418, 242))
    target_id, _ = component_id_at(after, anchor)
    if gallery_id < 0 or gallery_id != target_id:
        raise RuntimeError(
            "new gallery and authored command corridor are not walk-connected")
    if old_id >= 0:
        raise RuntimeError("retired observation elevation remains walkable")
    for item in railing_contract:
        ax, ay, az = item["anchor"]
        if base_state(after, ax, ay, az) == "minecraft:iron_bars":
            raise RuntimeError("targeted launch railing survived proposal")

    contract = {
        "reported_target_is_feet_y": -418,
        "reported_target_floor_y": -419,
        "old_gallery_feet_y": -395,
        "vertical_translation": -23,
        "translated_complete_section": {
            "x": [-36, 92], "z": [238, 244],
            "source_y": [-397, -390], "target_y": [-420, -413],
            "interior_air_is_translated": True,
        },
        "new_east_end_x": 93,
        "retired_old_adapter_x": [93, 95],
        "retained_upper_bypass_cap_x": 96,
        "connector": {
            "interior_x": [27, 29], "shell_x": [26, 30],
            "z": [244, 254], "joins_authored_route_at_z": 255,
        },
        "after_walk_component": {
            "id": gallery_id,
            "cells": int(components[gallery_id]["cells"]),
            "gallery_and_command_anchor_same_component": True,
        },
        "removed_railing_components": railing_contract,
        "scope_exclusion": (
            "east bypass remains structurally present but sealed at x=96; "
            "its separate retirement requires its own reviewed component"
        ),
    }
    digest = repair.emit_preview(
        world_root, output_root / repair_id, repair_id, box, anchor,
        before, after, reasons,
        [
            "Translate the complete launch observation pressure section down "
            "23 blocks so the player feet elevation is exactly Y=-418.",
            "Carve and shell one orthogonal three-wide connector into the "
            "authored command route at (28,-418,255).",
            "Retire the old gallery/adapter and remove only three measured "
            "launch-well railing components.",
        ], contract)
    render_feet_layers(before, after, [-395, -418], anchor,
                       output_root / repair_id /
                       "08_exact_feet_levels_before_after.png")
    # The extra evidence image becomes part of the approval hash.
    digest = repair.packet_sha(output_root / repair_id)
    return repair_id, digest


def historical_r02_retained(world_root: Path) -> dict[tuple[int, int, int], str]:
    archive = (ROOT / "run" / "saves" / "_archive" /
               "SEELE_S20_REBUILD-post-handoff-reconcile-20260801-150700" /
               "dimensions" / "projectseele" / "geofront")
    if not archive.exists():
        raise RuntimeError("R02 authority archive is unavailable")
    evidence = survey.Volume(archive, (48, 124, -435, -388, 125, 246))
    route = selection.selected_route(evidence, (97, -425, 201))
    candidates: dict[tuple[int, int, int], str] = {}
    for raw in np.argwhere(route):
        point = tuple(int(value) for value in raw)
        tag = selection.route_candidate(point, evidence)
        if tag in {"A", "B", "C"}:
            candidates[evidence.world_position(*point)] = tag

    retained: dict[tuple[int, int, int], str] = {}
    for x, y, z in candidates:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if any((x + dx, y + dy, z + dz) in candidates
                   for dy in (-1, 0, 1)):
                continue
            for yy in range(y, y + 4):
                qx, qz = x + dx, z + dz
                value = state(evidence, qx, yy, qz)
                if (survey.role_of(value) != "air"
                        and survey.base_name(value)
                        != "minecraft:gray_concrete"):
                    retained[(qx, yy, qz)] = value
    return retained


def build_orphan_route_cleanup(
        world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R07-ORPHAN-ROUTE-CLEANUP-PREVIEW-r01"
    box = (60, 122, -430, -386, 125, 210)
    anchor = (98, -398, 173)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}

    allowed_bridge = {
        "minecraft:reinforced_deepslate",
        "minecraft:polished_deepslate",
        "minecraft:deepslate_tiles",
        "minecraft:gray_stained_glass",
        "minecraft:orange_concrete",
        "minecraft:sea_lantern",
    }
    removed_bridge_cells = 0
    for x in range(93, 104):
        floor_y = -399 if x <= 100 else -399 + (x - 100)
        shell = []
        for z in range(171, 176):
            shell.extend(((x, floor_y, z), (x, floor_y + 5, z)))
        for z in (170, 176):
            shell.extend((x, y, z) for y in range(floor_y, floor_y + 6))
        for point in shell:
            value = state(before, *point)
            if survey.role_of(value) == "air":
                continue
            if survey.base_name(value) not in allowed_bridge:
                raise RuntimeError(
                    f"unexpected bridge-shell state at {point}: {value}")
            set_state(after, reasons, *point, AIR,
                      "remove_complete_98_398_173_stepped_bridge")
            removed_bridge_cells += 1

    # Restore the cage wall and the retained north/south personnel corridor
    # wall at the two semantic cut planes.
    for z in range(170, 177):
        west_material = BLACKSTONE if z == 175 else REINFORCED
        for y in range(-399, -393):
            set_state(after, reasons, 92, y, z, west_material,
                      "restore_unit02_cage_east_wall")
        set_state(after, reasons, 104, -395, z, AIR,
                  "remove_bridge_floor_at_east_cut")
        for y in range(-394, -390):
            set_state(after, reasons, 104, y, z, REINFORCED,
                      "restore_retained_corridor_west_wall")
        set_state(after, reasons, 104, -390, z, AIR,
                  "remove_bridge_ceiling_at_east_cut")

    # Remove complete railing components belonging to the upper corridor;
    # wet-cage railings are separate components and remain untouched.
    railing_contract = []
    for component_anchor, expected in (
            ((66, -394, 127), 43),
            ((96, -394, 131), 67),
            ((110, -394, 129), 53)):
        points = connected_material_component(
            before, component_anchor, "minecraft:iron_bars")
        if len(points) != expected:
            raise RuntimeError(
                f"corridor railing at {component_anchor} changed: "
                f"{len(points)} != {expected}")
        railing_contract.append({
            "anchor": list(component_anchor),
            "cells": len(points),
            "bbox": bbox(points),
        })
        for x, y, z in points:
            set_state(after, reasons, x, y, z, AIR,
                      "remove_complete_corridor_railing_component")

    # Close the abandoned upper R02 stair opening rather than leaving seven
    # quartz steps and a hole.  The existing iron-block ceiling is preserved.
    for x in range(97, 104):
        if base_state(before, x, -395, 139) \
                != "minecraft:smooth_quartz_stairs":
            raise RuntimeError(f"R02 upper stair changed at {(x, -395, 139)}")
        set_state(after, reasons, x, -395, 139, POLISHED,
                  "replace_r02_upper_stair_stub_with_floor")
        for y in range(-394, -390):
            set_state(after, reasons, x, y, 140, GRAY_GLASS,
                      "seal_r02_upper_cut_plane_with_glass")

    # R02 intentionally retained 104 non-contract adjacent solids.  Only the
    # measured lower-tail attachments are now retired: Unit-02's x=89 wall
    # and the x=96 upper interface frame remain protected, while the upper
    # stair is handled by the semantic cap above.
    historical = historical_r02_retained(world_root)
    residual_targets = {
        point: value for point, value in historical.items()
        if point[2] != 139
        and not (point[0] == 96 and point[2] == 140)
        and point[0] != 89
    }
    removed_residuals = 0
    for point, expected in sorted(residual_targets.items()):
        current = state(before, *point)
        if survey.base_name(current) != survey.base_name(expected):
            raise RuntimeError(
                f"R02 retained attachment changed at {point}: "
                f"{current} != {expected}")
        set_state(after, reasons, *point, AIR,
                  "remove_measured_r02_lower_tail_attachment")
        removed_residuals += 1

    # Semantic postconditions.
    anchor_id, _ = component_id_at(after, anchor)
    retained_route_id, _ = component_id_at(after, (108, -394, 160))
    if anchor_id >= 0:
        raise RuntimeError("cancelled bridge remains walkable at report anchor")
    if retained_route_id < 0:
        raise RuntimeError("legal north/south corridor was damaged")
    if base_state(after, 89, -394, 141) != "minecraft:iron_bars":
        raise RuntimeError("protected Unit-02 wet-cage railing was removed")
    for point in residual_targets:
        if survey.role_of(state(after, *point)) != "air":
            raise RuntimeError(f"R02 residual survived at {point}")

    contract = {
        "reported_anchor": list(anchor),
        "bridge_cross_section": {
            "x": [93, 103], "z_interior": [171, 175],
            "z_side_walls": [170, 176],
            "floor_profile": "x93..100=-399; x101=-398; "
                             "x102=-397; x103=-396",
            "removed_shell_cells": removed_bridge_cells,
        },
        "semantic_caps": {
            "unit02_wall_x": 92,
            "retained_corridor_wall_x": 104,
            "r02_upper_floor_z": 139,
            "r02_upper_glass_cap_z": 140,
        },
        "removed_corridor_railing_components": railing_contract,
        "r02_historical_retained_count": len(historical),
        "r02_lower_tail_attachments_removed": removed_residuals,
        "r02_protected": [
            "Unit-02 wall attachments on x=89",
            "upper interface frame on x=96,z=140",
        ],
        "retained_wet_cage_railing_probe": [89, -394, 141],
    }
    digest = repair.emit_preview(
        world_root, output_root / repair_id, repair_id, box, anchor,
        before, after, reasons,
        [
            "Remove the complete stepped bridge observed at "
            "(98,-398,173), then restore both pierced wall planes.",
            "Remove three complete connected iron-bar components owned by "
            "the retired upper corridor; preserve wet-cage railings.",
            "Close R02's upper stair opening and clear only its measured "
            "lower-tail attachments, not the Unit-02 wall.",
        ], contract)
    render_feet_layers(before, after, [-398, -394], anchor,
                       output_root / repair_id /
                       "08_exact_feet_levels_before_after.png")
    digest = repair.packet_sha(output_root / repair_id)
    return repair_id, digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", default="SEELE_S20_RECOVERY_R02_R04_R05")
    parser.add_argument("--emit-root", default="artifacts/map_previews")
    parser.add_argument("--only", choices=("observation", "route", "all"),
                        default="all")
    args = parser.parse_args()
    world_root = (ROOT / "run" / "saves" / args.world /
                  "dimensions" / "projectseele" / "geofront")
    output_root = ROOT / args.emit_root
    output_root.mkdir(parents=True, exist_ok=True)
    builders = {
        "observation": build_observation_to_command,
        "route": build_orphan_route_cleanup,
    }
    selected = builders if args.only == "all" else {
        args.only: builders[args.only]
    }
    for name, builder in selected.items():
        repair_id, digest = builder(world_root, output_root)
        print(f"[{name}] {repair_id} sha256={digest}")


if __name__ == "__main__":
    main()
