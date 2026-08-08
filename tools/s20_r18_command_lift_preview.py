#!/usr/bin/env python3
"""Read-only R18 preview for the measured command-lift endpoint correction.

The current R17 save contains the approved lower station and the user's
authored command-room route.  R10 placed the upper station at y=-406 facing
north; the real voxel survey proves the supported command-room threshold is
at y=-423 facing south.  This compiler:

* reverses only R10 upper-lift cells that still exactly equal R10's output;
* refuses to overwrite any later/manual edit;
* re-authors the same physical lift with the measured y=-423 south endpoint;
* writes evidence only, never a world save.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_r06_r07_topology_previews as topology  # noqa: E402
import s20_r10_r12_facility_previews as prior  # noqa: E402
import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


R10_PACKET = (ROOT / "artifacts" / "map_previews"
              / "S20-R10-COMMAND-LIFT-RELOCATION-PREVIEW-r01")
R10_BASELINE = (ROOT / "run" / "saves" / "SEELE_S20_RECOVERY_R06_R07"
                / "dimensions" / "projectseele" / "geofront")
REPAIR_ID = "S20-R18-COMMAND-LIFT-MEASURED-ENDPOINT-PREVIEW-r01"
BOX = (6, 18, -452, -398, 244, 263)
ANCHOR = (12, -423, 257)


def state(volume: survey.Volume, x: int, y: int, z: int) -> str:
    return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)


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
            f"{label} is not supported two-high walkspace at {point}: "
            f"below={below} feet={feet} head={head}")


def add_missing_inner_threshold_floor(
        volume: survey.Volume,
        reasons: dict[tuple[int, int, int], str],
        walk_y: int, reason: str) -> None:
    """Mirror Java's depth 3..4 landing floor omitted by the old preview."""
    for depth in (3, 4):
        for side in range(-2, 3):
            material = (prior.SEA_LANTERN
                        if (side + depth) % 7 == 0 else prior.POLISHED)
            repair.set_proposed(
                volume, reasons, 12 + side, walk_y - 1, 253 + depth,
                material, reason)


def build(world_root: Path, output_root: Path) -> str:
    before = survey.Volume(world_root, BOX)
    after = survey.Volume(world_root, BOX)
    baseline = survey.Volume(R10_BASELINE, BOX)
    reasons: dict[tuple[int, int, int], str] = {}
    reverted = 0
    already_restored = 0
    preserved_manual_air = 0
    retired_runtime_threshold = 0
    conflicts: list[dict] = []

    with (R10_PACKET / "block_diff.csv").open(
            "r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if (not row["reason"].startswith("relocated-command-lift")
                    or int(row["y"]) < -418):
                continue
            x, y, z = int(row["x"]), int(row["y"]), int(row["z"])
            current = state(before, x, y, z)
            if current == row["after"]:
                repair.set_proposed(
                    after, reasons, x, y, z, row["before"],
                    "retire-exact-r10-wrong-upper-endpoint")
                reverted += 1
            elif current == row["before"]:
                already_restored += 1
            elif current == "minecraft:air" and row["after"] != current:
                # A later human cleanup already removed this old lift cell.
                # Keeping air is strictly less invasive than resurrecting the
                # pre-R10 block and preserves the manual edit.
                preserved_manual_air += 1
            elif (y == -407 and z == 250 and 10 <= x <= 14
                  and current in {prior.POLISHED, prior.SEA_LANTERN}):
                # Java repaired the inner depth-3 floor that the old Python
                # preview omitted.  This is a deterministic v3 lift overlay,
                # not a human-authored cell.
                repair.set_proposed(
                    after, reasons, x, y, z, row["before"],
                    "retire-java-v3-upper-threshold-floor")
                retired_runtime_threshold += 1
            else:
                conflicts.append({
                    "point": [x, y, z],
                    "current": current,
                    "r10_before": row["before"],
                    "r10_after": row["after"],
                })
    if conflicts:
        raise RuntimeError(
            "R18 refuses to overwrite post-R10 edits: "
            + repr(conflicts[:12]))

    # The second Java-only inner floor row never appeared in R10's CSV, so
    # restore these five cells from the immutable pre-R10 baseline only when
    # they still carry the exact lift-floor palette.
    for x in range(10, 15):
        y, z = -407, 249
        current = state(before, x, y, z)
        if current not in {prior.POLISHED, prior.SEA_LANTERN}:
            raise RuntimeError(
                "R18 refuses unknown edit in old Java threshold at "
                f"{(x, y, z)}: {current}")
        original = state(baseline, x, y, z)
        repair.set_proposed(
            after, reasons, x, y, z, original,
            "retire-java-v3-upper-threshold-floor")
        retired_runtime_threshold += 1

    # Keep the already approved lower station/cabin and the retained shaft
    # below y=-423 byte-for-byte.  Only cut the new south door aperture and
    # author its measured upper landing.
    for side in range(-2, 3):
        for dy in range(3):
            repair.set_proposed(
                after, reasons, 12 + side, -423 + dy, 256,
                "minecraft:air",
                "measured-command-lift-v4:upper-shaft-aperture")
    prior.build_landing(
        after, reasons, 12, -423, 253, "south", False,
        "measured-command-lift-v4:upper")
    add_missing_inner_threshold_floor(
        after, reasons, -423,
        "measured-command-lift-v4:upper-inner-threshold-floor")
    add_missing_inner_threshold_floor(
        after, reasons, -448,
        "measured-command-lift-v4:lower-inner-threshold-floor")

    # z=257 is the authored doorway threshold; supported circulation begins
    # at z=258 and the runtime route contract hands off at distance seven.
    if survey.role_of(state(after, 12, -424, 257)) in {"air", "fluid"}:
        raise RuntimeError("upper closed door has no supporting threshold")
    assert_walkable(after, (12, -423, 260), "upper route handoff")
    assert_walkable(after, (12, -448, 260), "lower route handoff")

    output = output_root / REPAIR_ID
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    repair.emit_preview(
        world_root, output, REPAIR_ID, BOX, ANCHOR,
        before, after, reasons,
        [
            "retire only exact R10 upper-station cells at y=-418..-402",
            "keep the approved lower station at x=12,z=253,y=-448",
            "move the upper walk level from y=-406 to measured y=-423",
            "open the upper door south toward the authored command-room route",
            "preserve every later/manual voxel by failing on any conflict",
        ],
        {
            "axis": [12, 253],
            "old_upper": [12, -406, 253, "north"],
            "new_upper": [12, -423, 253, "south"],
            "door_threshold": [12, -423, 257],
            "route_handoff": [12, -423, 260],
            "r10_cells_reverted": reverted,
            "r10_cells_already_restored": already_restored,
            "manual_air_cells_preserved": preserved_manual_air,
            "java_v3_threshold_cells_retired": retired_runtime_threshold,
            "post_r10_conflicts": len(conflicts),
        })
    topology.render_feet_layers(
        before, after, [-448, -423, -406], ANCHOR,
        output / "08_endpoint_walkspace.png")
    return repair.packet_sha(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        default=str(ROOT / "run" / "saves" / "SEELE_S20_RECOVERY_R17"
                    / "dimensions" / "projectseele" / "geofront"))
    parser.add_argument(
        "--output-root",
        default=str(ROOT / "artifacts" / "map_previews"))
    args = parser.parse_args()
    digest = build(Path(args.world), Path(args.output_root))
    print(f"{REPAIR_ID} {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
