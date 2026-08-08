#!/usr/bin/env python3
"""Read-only previews for the corrected pyramid and Tokyo-3 cleanups.

R19 mistook the roof of a protruding service box for the whole defect.  R21
reconstructs the pyramid skin per Y layer from the intact Z spans on both
sides of that box, then removes only voxels outside the measured skin.

R22 removes the two deterministic generated towers reported by the human.
It preserves the exact non-air voxels of the private rotated skyscraper and
the exact fixed blocks of the public-lift pavilion.  No road or ground layer
is selected.  This file has no APPLY mode and never writes a save.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import shutil
import sys

import nbtlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


AIR = "minecraft:air"
R21_ID = "S20-R21-PYRAMID-SLOPE-BOX-RESTORE-PREVIEW-r01"
R22_ID = "S20-R22-TOKYO3-TWO-CONFLICT-TOWERS-PREVIEW-r01"
R21_BOX = (-24, -8, -366, -352, 348, 372)
R22_BOX = (92, 146, 79, 164, 244, 316)

SKYSCRAPER_NBT = (
    ROOT / "run" / "projectseele-local-maps" / "tokyo3_skyscraper.nbt"
)


def clean_output(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


def build_r21(world: Path, output_root: Path) -> tuple[str, str]:
    before = survey.Volume(world, R21_BOX)
    after = survey.Volume(world, R21_BOX)
    reasons: dict[tuple[int, int, int], str] = {}

    # These are not guessed target states.  Each row is measured identically
    # in the six intact columns immediately north and five intact columns
    # immediately south of the protruding box.
    skin = {
        -363: (-18, "minecraft:black_concrete"),
        -362: (-17, "minecraft:polished_blackstone"),
        -361: (-17, "minecraft:polished_blackstone"),
        -360: (-16, "minecraft:black_concrete"),
        -359: (-15, "minecraft:black_concrete"),
        -358: (-15, "minecraft:polished_blackstone"),
        -357: (-14, "minecraft:polished_blackstone"),
        -356: (-13, "minecraft:black_concrete"),
    }
    reference_z = tuple(range(350, 356)) + tuple(range(365, 370))
    for y, (surface_x, expected) in skin.items():
        for z in reference_z:
            actual = state(before, surface_x, y, z)
            if actual != expected:
                raise RuntimeError(
                    "R21 intact slope reference changed at "
                    f"{(surface_x, y, z)}: expected {expected}, got {actual}"
                )
            for x in range(-22, surface_x):
                outside = state(before, x, y, z)
                if survey.role_of(outside) not in {"air", "fixture"}:
                    raise RuntimeError(
                        "R21 reference has a second exterior solid at "
                        f"{(x, y, z)}: {outside}"
                    )

    before_materials: Counter[str] = Counter()
    for y, (surface_x, expected) in skin.items():
        for z in range(356, 365):
            for x in range(-18, surface_x):
                old = state(before, x, y, z)
                if old != AIR:
                    before_materials[old] += 1
                repair.set_proposed(
                    after, reasons, x, y, z, AIR,
                    "remove-protruding-box-outside-measured-pyramid-skin",
                )
            old_skin = state(before, surface_x, y, z)
            if old_skin != expected:
                before_materials[old_skin] += 1
            repair.set_proposed(
                after, reasons, surface_x, y, z, expected,
                "restore-pyramid-skin-from-two-sided-intact-reference",
            )

    # The restored surface must be exactly one solid voxel per row in this
    # exterior strip, with air on its west/outside side.
    for y, (surface_x, expected) in skin.items():
        for z in range(356, 365):
            if state(after, surface_x, y, z) != expected:
                raise RuntimeError("R21 failed to restore measured skin")
            for x in range(-22, surface_x):
                if survey.role_of(state(after, x, y, z)) not in {
                    "air", "fixture"
                }:
                    raise RuntimeError(
                        f"R21 left exterior solid at {(x, y, z)}"
                    )

    output = output_root / R21_ID
    clean_output(output)
    repair.emit_preview(
        world, output, R21_ID, R21_BOX, (-16, -359, 360),
        before, after, reasons,
        [
            "reject R19's disconnected-roof interpretation",
            "restore the complete eight-layer pyramid slope across z=356..364",
            "derive every skin X/material from intact spans on both sides",
            "remove only box voxels west/outside the reconstructed skin",
        ],
        {
            "rejected_packet": "S20-R19-PYRAMID-EXTERIOR-RESIDUE-PREVIEW-r01",
            "measured_defect_box": [-18, -13, -363, -356, 356, 364],
            "reference_z": [350, 355, 365, 369],
            "skin_by_y": {
                str(y): {"x": value[0], "state": value[1]}
                for y, value in skin.items()
            },
            "defect_materials_encountered": dict(before_materials),
            "interior_cells_east_of_skin_touched": 0,
        },
    )
    return R21_ID, repair.packet_sha(output)


def private_skyscraper_cells() -> set[tuple[int, int, int]]:
    if not SKYSCRAPER_NBT.is_file():
        raise RuntimeError(f"private skyscraper source is missing: {SKYSCRAPER_NBT}")
    root = nbtlib.load(SKYSCRAPER_NBT)
    palette = root.get("palette", [])
    blocks = root.get("blocks", [])
    names = [str(entry.get("Name", "minecraft:air")) for entry in palette]
    result: set[tuple[int, int, int]] = set()
    # Placement index 2: Tokyo-3 origin (30,80,220) + (112,1,82),
    # CLOCKWISE_180 around the structure origin.
    base_x, base_y, base_z = 142, 81, 302
    for block in blocks:
        palette_index = int(block.get("state", -1))
        if not 0 <= palette_index < len(names):
            raise RuntimeError("invalid skyscraper palette index")
        if names[palette_index] in {
            "minecraft:air", "minecraft:cave_air", "minecraft:void_air"
        }:
            continue
        pos = block.get("pos", [])
        if len(pos) != 3:
            raise RuntimeError("invalid skyscraper block position")
        lx, ly, lz = map(int, pos)
        result.add((base_x - lx, base_y + ly, base_z - lz))
    if len(result) != 5996:
        raise RuntimeError(
            f"private skyscraper source changed: expected 5996, got {len(result)}"
        )
    return result


def surface_pavilion_solids() -> set[tuple[int, int, int]]:
    result: set[tuple[int, int, int]] = set()
    axis_x, axis_z = 130, 273
    min_x, max_x = axis_x - 14, axis_x + 6
    min_z, max_z = axis_z - 6, axis_z + 6
    walk_y, floor_y, roof_y = 81, 80, 87
    for x in range(min_x, max_x + 1):
        for z in range(min_z, max_z + 1):
            result.add((x, floor_y, z))
            result.add((x, roof_y, z))
            edge = x in {min_x, max_x} or z in {min_z, max_z}
            for y in range(walk_y, roof_y):
                west_entrance = (
                    x == min_x and abs(z - axis_z) <= 2 and y <= walk_y + 3
                )
                if edge and not west_entrance:
                    result.add((x, y, z))
    for x in range(min_x - 2, axis_x - 7 + 1):
        for z in range(axis_z - 2, axis_z + 3):
            result.add((x, floor_y, z))
    return result


def clear_conflict_tower(
    before: survey.Volume,
    after: survey.Volume,
    reasons: dict[tuple[int, int, int], str],
    centre_x: int,
    centre_z: int,
    height: int,
    protected: set[tuple[int, int, int]],
    reason: str,
) -> tuple[int, int, Counter[str]]:
    selected = 0
    protected_present = 0
    materials: Counter[str] = Counter()
    for x in range(centre_x - 12, centre_x + 13):
        for z in range(centre_z - 12, centre_z + 13):
            for y in range(81, 80 + height + 1):
                current = state(before, x, y, z)
                if (x, y, z) in protected:
                    if current != AIR:
                        protected_present += 1
                    continue
                if current == AIR:
                    continue
                if (x, y, z) in before.block_entities:
                    raise RuntimeError(
                        f"R22 refuses block entity at {(x, y, z)}"
                    )
                materials[current] += 1
                repair.set_proposed(after, reasons, x, y, z, AIR, reason)
                selected += 1
    return selected, protected_present, materials


def build_r22(world: Path, output_root: Path) -> tuple[str, str]:
    before = survey.Volume(world, R22_BOX)
    after = survey.Volume(world, R22_BOX)
    reasons: dict[tuple[int, int, int], str] = {}

    imported = private_skyscraper_cells()
    pavilion = surface_pavilion_solids()
    # (80,80) -> height 22 + three cleanup layers; (80,40) -> 26 + three.
    small = clear_conflict_tower(
        before, after, reasons, 110, 300, 25, imported,
        "remove-generated-small-tower-overlapping-private-highrise",
    )
    lift = clear_conflict_tower(
        before, after, reasons, 110, 260, 29, pavilion,
        "remove-generated-tower-overlapping-public-lift-pavilion",
    )

    # Ground/roads and every protected source voxel must be byte-identical in
    # the proposal.  This is the main safety gate missing from the runtime
    # broad-cuboid cleanup.
    for x in range(98, 123):
        for z in range(248, 313):
            if state(before, x, 80, z) != state(after, x, 80, z):
                raise RuntimeError(f"R22 changed ground at {(x, 80, z)}")
    for point in imported | pavilion:
        x, y, z = point
        if not (R22_BOX[0] <= x <= R22_BOX[1]
                and R22_BOX[2] <= y <= R22_BOX[3]
                and R22_BOX[4] <= z <= R22_BOX[5]):
            continue
        if state(before, x, y, z) != state(after, x, y, z):
            raise RuntimeError(f"R22 changed protected voxel at {point}")

    if small[0] < 1000 or lift[0] < 1000:
        raise RuntimeError(
            f"R22 tower selection unexpectedly small: small={small[0]} lift={lift[0]}"
        )

    output = output_root / R22_ID
    clean_output(output)
    repair.emit_preview(
        world, output, R22_ID, R22_BOX, (121, 104, 294),
        before, after, reasons,
        [
            "remove the smaller generated building colliding at (121,104,294)",
            "remove the generated lot shell colliding with the public lift near (115,88,273)",
            "preserve all 5,996 private-skyscraper source voxels",
            "preserve exact public-lift pavilion solids and the y=80 ground/road layer",
        ],
        {
            "small_tower_prism": [98, 122, 81, 105, 288, 312],
            "lift_tower_prism": [98, 122, 81, 109, 248, 272],
            "small_tower_selected": small[0],
            "lift_tower_selected": lift[0],
            "private_skyscraper_voxels_protected": len(imported),
            "private_voxels_present_in_prism": small[1],
            "pavilion_voxels_present_in_prism": lift[1],
            "small_removed_materials": dict(small[2]),
            "lift_removed_materials": dict(lift[2]),
            "ground_y80_cells_changed": 0,
            "protected_cells_changed": 0,
        },
    )
    return R22_ID, repair.packet_sha(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        default=str(
            ROOT / "run" / "saves" / "SEELE_S20_RECOVERY_R18_R20"
            / "dimensions" / "projectseele" / "geofront"
        ),
    )
    parser.add_argument(
        "--output-root", default=str(ROOT / "artifacts" / "map_previews")
    )
    args = parser.parse_args()
    world = Path(args.world).resolve()
    output_root = Path(args.output_root).resolve()
    for builder in (build_r21, build_r22):
        repair_id, digest = builder(world, output_root)
        print(f"{repair_id} {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
