#!/usr/bin/env python3
"""Read-only preview for the S20 lower command wall and upper controls.

The proposal is built from the approved R21/R22 recovery save.
It never opens an Anvil file for writing.  Every transition is emitted to the
same exact CSV/hash approval format as the earlier semantic repairs.

R23 has three deliberately small ownership masks:

* complete the lower half and seal the two remaining upper seams of the
  existing z=362 command-room wall;
* replace only measured ``minecraft:stone`` guard blocks around the three
  upper staff seats with Project SEELE clear glass;
* place eleven floor-mounted controls on existing white-concrete console
  tiles (city rise/lower plus prepare/launch/recover for EVA-00/01/02).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


REPAIR_ID = "S20-R23-COMMAND-WALL-CONTROLS-CLEAR-GLASS-PREVIEW-r02"
BOX = (4, 52, -440, -397, 272, 364)
ANCHOR = (28, -407, 290)

AIR = "minecraft:air"
CLEAR_GLASS = "projectseele:clear_glass"
WALL_Z = 362


def state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


def put(volume: survey.Volume,
        reasons: dict[tuple[int, int, int], str],
        x: int, y: int, z: int, target: str, reason: str,
        expected: set[str] | None = None) -> None:
    old = state(volume, x, y, z)
    if expected is not None and old not in expected:
        raise RuntimeError(
            f"R23 source changed at {(x, y, z)}: expected "
            f"{sorted(expected)}, got {old}"
        )
    if old == target:
        return
    repair.set_proposed(volume, reasons, x, y, z, target, reason)


def build_wall(after: survey.Volume,
               reasons: dict[tuple[int, int, int], str]) -> None:
    # The upper wall already occupies z=362 from y=-419 upward.  This lower
    # panel lands on the measured two-layer foundation at y=-440/-439 and
    # stops one block below that authored upper wall; no existing voxel is
    # selected by the main plane.
    for x in range(6, 51):
        for y in range(-438, -419):
            edge = x in {6, 50} or y in {-438, -420}
            inner_edge = x in {7, 49} or y in {-437, -421}
            if edge:
                target = "minecraft:polished_deepslate"
                reason = "lower_front_wall_outer_frame"
            elif inner_edge:
                target = "minecraft:deepslate_tiles"
                reason = "lower_front_wall_inner_frame"
            elif y in {-436, -422}:
                target = ("minecraft:sea_lantern"
                          if (x - 8) % 4 == 0
                          else "minecraft:black_concrete")
                reason = "lower_front_wall_light_header"
            elif x in {8, 48}:
                target = "minecraft:orange_concrete"
                reason = "lower_front_wall_nerv_accent"
            else:
                target = "minecraft:black_concrete"
                reason = "tokyo3_status_screen_backing"
            put(after, reasons, x, y, WALL_Z, target, reason, {AIR})

    # Close the two eleven-block returns between the measured side walls
    # (ending at z=351) and the new front plane.  Copying each row's exact
    # z=351 material keeps the source wall stratification instead of inventing
    # a second palette.  Existing decorative voxels remain untouched.
    for x in (6, 50):
        for y in range(-438, -419):
            reference = state(after, x, y, 351)
            if reference == AIR:
                reference = "minecraft:polished_deepslate"
            for z in range(352, WALL_Z):
                if state(after, x, y, z) == AIR:
                    put(after, reasons, x, y, z, reference,
                        "lower_front_wall_side_return", {AIR})

    # R23-r01 stopped immediately below the authored upper wall, but the
    # authored trapezoid itself contains two open centre rows at its lower
    # edge.  Those are the remaining visible perforations the human called
    # out.  Seal the exact measured interior spans while preserving the
    # stepped exterior silhouette and every existing upper-screen voxel.
    upper_seams = {
        -419: (17, 39, "minecraft:polished_deepslate"),
        -418: (18, 38, "minecraft:deepslate_tiles"),
    }
    for y, (min_x, max_x, target) in upper_seams.items():
        left = state(after, min_x - 1, y, WALL_Z)
        right = state(after, max_x + 1, y, WALL_Z)
        if survey.role_of(left) == "air" or survey.role_of(right) == "air":
            raise RuntimeError(
                f"R23 upper seam boundaries changed at y={y}: "
                f"left={left}, right={right}"
            )
        for x in range(min_x, max_x + 1):
            put(after, reasons, x, y, WALL_Z, target,
                "seal_authored_upper_front_wall_seam", {AIR})


def replace_upper_guard_glass(
        after: survey.Volume,
        reasons: dict[tuple[int, int, int], str]) -> None:
    # These bounds cover the stone guard/skirt around the three seats at
    # (25,-409,286), (28,-409,288), (31,-409,286).  White console blocks,
    # copper chairs, buttons, signs, walls and ladders are explicitly outside
    # the selector.
    changed = 0
    for x in range(21, 36):
        for y in range(-410, -407):
            for z in range(279, 292):
                if state(after, x, y, z) != "minecraft:stone":
                    continue
                put(after, reasons, x, y, z, CLEAR_GLASS,
                    "three_seat_clear_guard",
                    {"minecraft:stone"})
                changed += 1
    if changed < 20:
        raise RuntimeError(
            f"R23 clear guard selector found only {changed} stone blocks"
        )


def install_controls(after: survey.Volume,
                     reasons: dict[tuple[int, int, int], str]) -> None:
    floor_button = (
        "minecraft:polished_blackstone_button"
        "[face=floor,facing=south,powered=false]"
    )
    controls = [
        # action, position, coloured physical address tile
        ("city_rise", (26, -409, 280), "minecraft:lime_concrete"),
        ("city_lower", (30, -409, 280), "minecraft:orange_concrete"),
        ("unit00_prepare", (24, -409, 282), "minecraft:orange_concrete"),
        ("unit00_launch", (24, -409, 284), "minecraft:orange_concrete"),
        ("unit00_recover", (24, -409, 285), "minecraft:orange_concrete"),
        ("unit01_prepare", (28, -409, 282), "minecraft:purple_concrete"),
        ("unit01_launch", (28, -409, 284), "minecraft:purple_concrete"),
        ("unit01_recover", (28, -409, 285), "minecraft:purple_concrete"),
        ("unit02_prepare", (32, -409, 282), "minecraft:red_concrete"),
        ("unit02_launch", (32, -409, 284), "minecraft:red_concrete"),
        ("unit02_recover", (32, -409, 285), "minecraft:red_concrete"),
    ]
    for action, (x, y, z), base in controls:
        put(after, reasons, x, y, z, floor_button,
            f"physical_control_{action}", {AIR})
        put(after, reasons, x, y - 1, z, base,
            f"address_tile_{action}", {"minecraft:white_concrete"})


def build(world: Path, output_root: Path) -> tuple[str, str]:
    before = survey.Volume(world, BOX)
    after = survey.Volume(world, BOX)
    reasons: dict[tuple[int, int, int], str] = {}

    # Fail closed against the two measured anchors that define this proposal.
    if state(before, 42, -438, 362) != AIR:
        raise RuntimeError("R23 lower front-wall anchor is no longer air")
    if state(before, 28, -407, 290) != AIR:
        raise RuntimeError("R23 upper-control observation anchor changed")

    build_wall(after, reasons)
    replace_upper_guard_glass(after, reasons)
    install_controls(after, reasons)

    output = output_root / REPAIR_ID
    if output.exists():
        shutil.rmtree(output)
    sha = repair.emit_preview(
        world, output, REPAIR_ID, BOX, ANCHOR, before, after, reasons,
        [
            "Complete the lower half of the existing z=362 command wall",
            "Seal both remaining centre seams inside the authored upper-wall silhouette",
            "Provide a framed opaque surface for the live Tokyo-3 status screen",
            "Replace only stone guard voxels around the three upper seats with clear glass",
            "Install eleven supported floor controls on existing console tiles",
        ],
        {
            "main_wall_before_state": "air only",
            "side_returns": "air gaps only; row palette copied from z=351",
            "clear_guard_before_state": "minecraft:stone only",
            "control_before_state": "air above minecraft:white_concrete",
            "existing_authored_blocks_removed": 0,
            "upper_wall_seams_sealed": {
                "y_-419": [17, 39],
                "y_-418": [18, 38],
                "remaining_air_inside_measured_spans": 0,
            },
            "screen_render_surface": {
                "centre": [28.0, -429.0, 361.48],
                "width": 36.0,
                "height": 12.0,
                "faces": "toward command seats (-Z)",
            },
        },
    )
    return REPAIR_ID, sha


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        default=str(ROOT / "run" / "saves"
                    / "SEELE_S20_RECOVERY_R21_R22"
                    / "dimensions" / "projectseele" / "geofront"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "artifacts" / "map_previews"),
    )
    args = parser.parse_args()
    repair_id, sha = build(Path(args.world), Path(args.output))
    print(f"{repair_id} {sha}")


if __name__ == "__main__":
    main()
