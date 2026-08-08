#!/usr/bin/env python3
"""Read-only exact previews for the reported S20 exterior residues.

R19 removes one measured 17-cell disconnected service fragment from the
pyramid slope.  R20 removes only recognisable old Tokyo-3 tower components
and the one-block residual curtain columns above the historical surface
datum; roads, terrain and the current city north edge are not selected.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


AIR = "minecraft:air"
R19_ID = "S20-R19-PYRAMID-EXTERIOR-RESIDUE-PREVIEW-r01"
R20_ID = "S20-R20-NORTH-PERIPHERY-RESIDUE-PREVIEW-r01"
R19_BOX = (-51, 21, -384, -328, 328, 400)
R20_BOX = (-205, 220, 97, 192, -176, -28)


def clean_output(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def component_cells(labels: np.ndarray, component_id: int):
    for ix, iy, iz in zip(*np.nonzero(labels == component_id)):
        yield int(ix), int(iy), int(iz)


def build_r19(world: Path, output_root: Path) -> tuple[str, str]:
    before = survey.Volume(world, R19_BOX)
    after = survey.Volume(world, R19_BOX)
    labels, components = survey.label_components(
        before.masks()["authored"], before)
    seed = (-17, -356, 357)
    component_id = int(labels[
        seed[0] - before.x0,
        seed[1] - before.y0,
        seed[2] - before.z0])
    if component_id < 0:
        raise RuntimeError(f"R19 seed is not authored solid: {seed}")
    component = components[component_id]
    expected_bbox = [-17, -15, -356, -356, 357, 362]
    expected_materials = {
        "minecraft:polished_deepslate": 15,
        "minecraft:sea_lantern": 2,
    }
    if (component["cells"] != 17
            or component["bbox"] != expected_bbox
            or component.get("materials") != expected_materials):
        raise RuntimeError(
            "R19 measured component changed; refusing cleanup: "
            + repr(component))

    reasons: dict[tuple[int, int, int], str] = {}
    for ix, iy, iz in component_cells(labels, component_id):
        x, y, z = before.world_position(ix, iy, iz)
        repair.set_proposed(
            after, reasons, x, y, z, AIR,
            "remove-exact-disconnected-pyramid-service-fragment")

    output = output_root / R19_ID
    clean_output(output)
    repair.emit_preview(
        world, output, R19_ID, R19_BOX, (-15, -356, 364),
        before, after, reasons,
        [
            "remove only the disconnected 17-cell fragment beside the pyramid slope",
            "leave the connected pyramid shell, bands and interior untouched",
            "replace no neighbouring exterior block and open no new route",
        ],
        {
            "selected_component_id": component_id,
            "selected_cells": component["cells"],
            "selected_bbox": component["bbox"],
            "selected_materials": component["materials"],
            "connected_pyramid_components_changed": 0,
        })
    return R19_ID, repair.packet_sha(output)


def build_r20(world: Path, output_root: Path) -> tuple[str, str]:
    before = survey.Volume(world, R20_BOX)
    after = survey.Volume(world, R20_BOX)
    labels, components = survey.label_components(
        before.masks()["authored"], before)

    selected: list[tuple[dict, str]] = []
    rejected_grid_mismatch: list[dict] = []
    for component in components:
        bbox = component["bbox"]
        sx = bbox[1] - bbox[0] + 1
        sy = bbox[3] - bbox[2] + 1
        sz = bbox[5] - bbox[4] + 1
        materials = component.get("materials", {})
        smooth = materials.get("minecraft:smooth_stone", 0)
        glass = sum(count for state, count in materials.items()
                    if "stained_glass" in state)
        rod_palette = set(materials).issubset({
            "minecraft:reinforced_deepslate",
            "minecraft:orange_concrete",
        })
        is_rod = (sx == 1 and sz == 1 and sy >= 75
                  and component["cells"] <= 100 and rod_palette)
        is_tower = (component["cells"] >= 1000
                    and smooth >= 400 and glass >= 300
                    and sx <= 30 and sz <= 30)
        if not (is_rod or is_tower):
            continue
        horizontally_or_top_clipped = (
            bbox[0] == R20_BOX[0] or bbox[1] == R20_BOX[1]
            or bbox[4] == R20_BOX[4] or bbox[5] == R20_BOX[5]
            or bbox[3] == R20_BOX[3])
        if horizontally_or_top_clipped:
            raise RuntimeError(
                "R20 selected a clipped component; enlarge survey: "
                + repr(component))
        if is_tower:
            cx = (bbox[0] + bbox[1]) / 2.0
            cz = (bbox[4] + bbox[5]) / 2.0
            nearest_x = round(cx / 40.0) * 40
            nearest_z = min((-160, -120, -80, -40),
                            key=lambda value: abs(cz - value))
            if abs(cx - nearest_x) > 1.0 or abs(cz - nearest_z) > 3.0:
                rejected_grid_mismatch.append(component)
                continue
        selected.append((component, "curtain-column" if is_rod
                         else "legacy-tower"))

    if rejected_grid_mismatch:
        raise RuntimeError(
            "R20 tower-like component is off the measured old 40-block grid: "
            + repr(rejected_grid_mismatch[:4]))
    tower_count = sum(kind == "legacy-tower" for _, kind in selected)
    rod_count = sum(kind == "curtain-column" for _, kind in selected)
    if tower_count != 30 or rod_count < 70:
        raise RuntimeError(
            f"R20 selection contract changed: towers={tower_count} rods={rod_count}")

    reasons: dict[tuple[int, int, int], str] = {}
    selected_cells = 0
    for component, kind in selected:
        for ix, iy, iz in component_cells(labels, int(component["id"])):
            x, y, z = before.world_position(ix, iy, iz)
            repair.set_proposed(
                after, reasons, x, y, z, AIR,
                f"remove-measured-north-periphery:{kind}")
            selected_cells += 1

    output = output_root / R20_ID
    clean_output(output)
    repair.emit_preview(
        world, output, R20_ID, R20_BOX, (37, 132, -75),
        before, after, reasons,
        [
            "remove 30 complete old-grid tower components north of the current city",
            "remove only isolated one-block curtain columns visible above y=96",
            "preserve roads, terrain, rails and every non-matching component",
            "stop south of z=-28 so the authoritative city edge at z=20 is untouched",
        ],
        {
            "selection_box": list(R20_BOX),
            "legacy_tower_components": tower_count,
            "curtain_column_components": rod_count,
            "selected_cells": selected_cells,
            "selected_components": len(selected),
            "horizontal_or_top_clipped_components": 0,
            "lower_y_clipping_is_intentional": True,
            "visible_cleanup_min_y": 97,
            "authoritative_city_north_edge_z": 20,
            "cleanup_max_z": -28,
            "terrain_or_road_components_selected": 0,
        })
    return R20_ID, repair.packet_sha(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        default=str(ROOT / "run" / "saves" / "SEELE_S20_RECOVERY_R17"
                    / "dimensions" / "projectseele" / "geofront"))
    parser.add_argument("--emit-root", default="artifacts/map_previews")
    args = parser.parse_args()
    world = Path(args.world).resolve()
    output_root = Path(args.emit_root).resolve()
    for builder in (build_r19, build_r20):
        repair_id, digest = builder(world, output_root)
        print(f"{repair_id} {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
