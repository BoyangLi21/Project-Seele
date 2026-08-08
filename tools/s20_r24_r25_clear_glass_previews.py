#!/usr/bin/env python3
"""Read-only clear-glass material previews for the human-edited S20 world.

R24 replaces only the measured 492-block vanilla-glass command front panel.
R25 replaces only gray/light-gray structural glazing inside the measured EVA
hangar and launch-observation plant.  Neither packet changes geometry,
buttons, coloured unit-address glass, block entities, routes or supports.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


CLEAR_GLASS = "projectseele:clear_glass"
R24_ID = "S20-R24-COMMAND-FRONT-CLEAR-GLASS-PREVIEW-r01"
R25_ID = "S20-R25-HANGAR-OBSERVATION-CLEAR-GLASS-PREVIEW-r01"
R24_BOX = (8, 48, -417, -399, 360, 363)
R25_BOX = (-35, 122, -443, -377, 130, 269)
PLANT_ALLOWED = {
    "minecraft:gray_stained_glass",
    "minecraft:light_gray_stained_glass",
}


def state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


def clean(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def build_r24(world: Path, output_root: Path) -> tuple[str, str]:
    before = survey.Volume(world, R24_BOX)
    after = survey.Volume(world, R24_BOX)
    reasons: dict[tuple[int, int, int], str] = {}
    selected = []
    for x in range(10, 47):
        for y in range(-415, -400):
            if state(before, x, y, 362) == "minecraft:glass":
                selected.append((x, y, 362))
                repair.set_proposed(after, reasons, x, y, 362, CLEAR_GLASS,
                                    "command_front_scratch_free_glazing")
    if len(selected) != 492:
        raise RuntimeError(
            f"R24 command glass changed: expected 492, got {len(selected)}"
        )
    if before.block_entities.keys() & set(selected):
        raise RuntimeError("R24 refuses to replace a block entity")

    output = output_root / R24_ID
    clean(output)
    sha = repair.emit_preview(
        world, output, R24_ID, R24_BOX, (39, -407, 361),
        before, after, reasons,
        [
            "Replace the complete measured command-front vanilla-glass panel",
            "Preserve the panel silhouette, frame, screen backing and all controls",
            "Use Project SEELE scratch-free structural glass only",
        ],
        {
            "selected_blocks": len(selected),
            "before_material": "minecraft:glass",
            "after_material": CLEAR_GLASS,
            "geometry_changes": 0,
            "button_changes": 0,
            "coloured_unit_glass_changes": 0,
        },
    )
    return R24_ID, sha


def build_r25(world: Path, output_root: Path) -> tuple[str, str]:
    before = survey.Volume(world, R25_BOX)
    after = survey.Volume(world, R25_BOX)
    reasons: dict[tuple[int, int, int], str] = {}
    selected: set[tuple[int, int, int]] = set()
    source_materials: Counter[str] = Counter()

    for y in range(R25_BOX[2], R25_BOX[3] + 1):
        for z in range(R25_BOX[4], R25_BOX[5] + 1):
            for x in range(R25_BOX[0], R25_BOX[1] + 1):
                current = state(before, x, y, z)
                if current not in PLANT_ALLOWED:
                    continue
                in_hangar_observation_plant = z <= 245
                in_east_observation_edge = (
                    100 <= x <= 115
                    and -443 <= y <= -430
                    and 224 <= z <= 269
                )
                if not (in_hangar_observation_plant
                        or in_east_observation_edge):
                    continue
                point = (x, y, z)
                selected.add(point)
                source_materials[current] += 1
                repair.set_proposed(
                    after, reasons, x, y, z, CLEAR_GLASS,
                    "hangar_observation_scratch_free_glazing",
                )

    if len(selected) != 9050:
        raise RuntimeError(
            f"R25 plant glass changed: expected 9050, got {len(selected)}"
        )
    if before.block_entities.keys() & selected:
        raise RuntimeError("R25 refuses to replace a block entity")

    output = output_root / R25_ID
    clean(output)
    sha = repair.emit_preview(
        world, output, R25_ID, R25_BOX, (52, -394, 237),
        before, after, reasons,
        [
            "Replace structural glazing throughout all three EVA hangars",
            "Replace structural glazing throughout the launch observation hall",
            "Include the measured east observation-edge glass run",
            "Preserve coloured unit glass, LCL, buttons, routes and geometry",
        ],
        {
            "selected_blocks": len(selected),
            "source_materials": dict(source_materials),
            "after_material": CLEAR_GLASS,
            "hangar_observation_z_max": 245,
            "east_edge_box": [100, 115, -443, -430, 224, 269],
            "geometry_changes": 0,
            "button_changes": 0,
            "coloured_unit_glass_changes": 0,
        },
    )
    return R25_ID, sha


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        default=str(
            ROOT / "run" / "saves" / "SEELE_S20_RECOVERY_R23"
            / "dimensions" / "projectseele" / "geofront"
        ),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "artifacts" / "map_previews"),
    )
    args = parser.parse_args()
    world = Path(args.world).resolve()
    output = Path(args.output).resolve()
    for builder in (build_r24, build_r25):
        repair_id, sha = builder(world, output)
        print(f"{repair_id} {sha}")


if __name__ == "__main__":
    main()
