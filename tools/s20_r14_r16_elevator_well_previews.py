#!/usr/bin/env python3
"""Read-only previews for corrected S20 lifts and launch-well decks.

The active R13 save contains the user's latest in-game corridor edits.  This
compiler reads those exact voxels and mutates only in-memory volumes:

* R14 installs the observation/hangar lift on the measured gap at x=94,z=241;
* R15 reverses only still-exact cells from the wrongly placed R11 west lift;
* R16 completes the missing walk deck at y=-443 in all three launch wells.

There is intentionally no APPLY mode in this file.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_r06_r07_topology_previews as topology  # noqa: E402
import s20_r10_r12_facility_previews as prior  # noqa: E402
import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


AIR = "minecraft:air"
POLISHED = "minecraft:polished_deepslate"
REINFORCED = "minecraft:reinforced_deepslate"
HUMAN_CLEARED_EAST_ROUTE = prior.HUMAN_CLEARED_EAST_ROUTE
R11_PACKET = (ROOT / "artifacts" / "map_previews"
              / "S20-R11-OBSERVATION-HANGAR-LIFT-PREVIEW-r01")


def state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


def clean_output(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)


def protected_overlap(
        reasons: dict[tuple[int, int, int], str]) -> int:
    x0, x1, y0, y1, z0, z1 = HUMAN_CLEARED_EAST_ROUTE
    return sum(1 for x, y, z in reasons
               if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1)


def clear_lift_sweep(volume: survey.Volume,
                     reasons: dict[tuple[int, int, int], str],
                     cx: int, cz: int, lower_y: int, upper_y: int) -> None:
    """Clear only the moving 5x5 cabin envelope, never the 7x7 shell."""
    for x in range(cx - 2, cx + 3):
        for y in range(lower_y - 1, upper_y + 5):
            for z in range(cz - 2, cz + 3):
                if survey.role_of(state(volume, x, y, z)) != "air":
                    repair.set_proposed(
                        volume, reasons, x, y, z, AIR,
                        "correct-observation-lift:clear-exact-cabin-sweep")


def assert_walkable(volume: survey.Volume,
                    point: tuple[int, int, int], label: str) -> None:
    x, y, z = point
    below = state(volume, x, y - 1, z)
    feet = state(volume, x, y, z)
    head = state(volume, x, y + 1, z)
    if (survey.role_of(below) in {"air", "fluid"}
            or survey.role_of(feet) != "air"
            or survey.role_of(head) != "air"):
        raise RuntimeError(
            f"{label} is not a supported two-high route handoff at {point}: "
            f"below={below} feet={feet} head={head}")


def build_r14(world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R14-CORRECT-OBSERVATION-HANGAR-LIFT-PREVIEW-r01"
    box = (86, 102, -423, -389, 233, 249)
    anchor = (94, -406, 241)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}

    # The two human-reported route endpoints reveal one intentional shaft gap:
    # lower platform ends at x=92, upper platform starts at x=96.
    clear_lift_sweep(after, reasons, 94, 241, -418, -394)
    prior.build_physical_lift(
        after, reasons, 94, 241, -418, -394,
        "west", "east", "correct-observation-hangar-lift")

    lower_handoff = (87, -418, 241)
    upper_handoff = (101, -394, 241)
    assert_walkable(after, lower_handoff, "lower observation handoff")
    assert_walkable(after, upper_handoff, "upper hangar handoff")
    overlap = protected_overlap(reasons)
    if overlap:
        raise RuntimeError(
            f"R14 enters human-cleared east route: {overlap}")

    output = output_root / repair_id
    clean_output(output)
    repair.emit_preview(
        world_root, output, repair_id, box, anchor,
        before, after, reasons,
        [
            "place one physical lift on measured axis x=94,z=241",
            "lower door faces west onto (92,-418,241) observation platform",
            "upper door faces east through (98,-394,241) hangar platform",
            "clear only the moving 5x5 cabin sweep and preserve both routes",
        ],
        {
            "axis": [94, 241],
            "walk_y": [-418, -394],
            "lower_exit": "west",
            "upper_exit": "east",
            "human_reported_endpoints": [
                [92, -418, 241], [98, -394, 241]],
            "verified_route_handoffs": [
                list(lower_handoff), list(upper_handoff)],
            "human_cleared_overlap_count": overlap,
        })
    topology.render_feet_layers(
        before, after, [-418, -394], anchor,
        output / "08_endpoint_walkspace.png")
    return repair_id, repair.packet_sha(output)


def build_r15(world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R15-ROLLBACK-WRONG-WEST-LIFT-PREVIEW-r01"
    manifest = json.loads(
        (R11_PACKET / "00_manifest.json").read_text(encoding="utf-8"))
    box = tuple(manifest["box"])
    anchor = (-40, -406, 200)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}
    conflicts = []
    already_reverted = 0
    with (R11_PACKET / "block_diff.csv").open(
            "r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            x, y, z = int(row["x"]), int(row["y"]), int(row["z"])
            current = state(before, x, y, z)
            if current == row["after"]:
                repair.set_proposed(
                    after, reasons, x, y, z, row["before"],
                    "rollback-exact-wrong-r11-cell")
            elif current == row["before"]:
                already_reverted += 1
            else:
                conflicts.append({
                    "point": [x, y, z], "current": current,
                    "r11_before": row["before"],
                    "r11_after": row["after"],
                })
    if conflicts:
        raise RuntimeError(
            "R15 refuses to overwrite post-R11 edits: "
            + json.dumps(conflicts[:8], ensure_ascii=False))
    overlap = protected_overlap(reasons)
    if overlap:
        raise RuntimeError(
            f"R15 enters human-cleared east route: {overlap}")

    output = output_root / repair_id
    clean_output(output)
    digest = repair.emit_preview(
        world_root, output, repair_id, box, anchor,
        before, after, reasons,
        [
            "reverse only cells still exactly equal to the approved wrong R11 result",
            "restore each cell to its recorded pre-R11 state",
            "abort on any post-R11 human edit instead of guessing",
        ],
        {
            "reversed_packet": manifest["repair_id"],
            "wrong_axis": [-40, 200],
            "conflicts": len(conflicts),
            "already_reverted": already_reverted,
            "human_cleared_overlap_count": overlap,
        })
    return repair_id, digest


def build_r16(world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R16-THREE-LAUNCH-WELL-WALK-DECKS-PREVIEW-r01"
    box = (-31, 89, -443, -443, 203, 237)
    anchor = (30, -443, 220)
    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    reasons: dict[tuple[int, int, int], str] = {}
    additions_by_well = {}
    for cx in (-12, 30, 72):
        additions = 0
        for dx in range(-17, 18):
            for dz in range(-17, 18):
                x, y, z = cx + dx, -443, 220 + dz
                if survey.role_of(state(after, x, y, z)) not in {
                        "air", "fluid", "natural"}:
                    continue
                beam = (abs(dx) == 17 or abs(dz) == 17
                        or dx % 8 == 0 or dz % 8 == 0)
                repair.set_proposed(
                    after, reasons, x, y, z,
                    REINFORCED if beam else POLISHED,
                    f"launch-well-{cx}:complete-y-443-walk-deck")
                additions += 1
        additions_by_well[str(cx)] = additions
    overlap = protected_overlap(reasons)
    if overlap:
        raise RuntimeError(
            f"R16 enters human-cleared east route: {overlap}")

    output = output_root / repair_id
    clean_output(output)
    digest = repair.emit_preview(
        world_root, output, repair_id, box, anchor,
        before, after, reasons,
        [
            "complete the actual y=-443 floor in all three launch wells",
            "add only into air/fluid/natural cells and preserve every existing block",
            "use reinforced perimeter/grid beams with polished deck infill",
        ],
        {
            "well_centres": [[-12, 220], [30, 220], [72, 220]],
            "walk_deck_y": -443,
            "additions_by_well": additions_by_well,
            "existing_non_air_replaced": 0,
            "human_cleared_overlap_count": overlap,
        })
    return repair_id, digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True,
                        help="Path to dimensions/projectseele/geofront")
    parser.add_argument("--emit-root", default="artifacts/map_previews")
    args = parser.parse_args()
    world = Path(args.world).resolve()
    output = Path(args.emit_root).resolve()
    for builder in (build_r14, build_r15, build_r16):
        repair_id, digest = builder(world, output)
        print(f"{repair_id} {digest}")


if __name__ == "__main__":
    main()
