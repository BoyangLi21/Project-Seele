#!/usr/bin/env python3
"""Read-only source-of-truth preview for missing command hierarchy trim.

The private ``nerv_command_left.nbt`` is the sole visual master.  This tool
maps it with the measured S20 direct transform, then proposes only authored
non-air voxels whose current world cell is air inside the bounded Gendo /
Fuyutsuki / operator hierarchy.  It never replaces an existing world block
and never enters either sloped screen mask or the command sightline cut.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path
import shutil
import sys

import nbtlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import s20_semantic_repair_previews as repair  # noqa: E402
import survey_facility_target as survey  # noqa: E402


ORIGIN = (2, -465, 223)
BOX = (10, 46, -434, -398, 268, 307)
ANCHOR = (28, -406, 277)
SOURCE = (ROOT / "artifacts" / "claude_audit_s19_20260729"
          / "local_evidence" / "nerv_command_left.nbt")
CHAIRS = {
    "ikari": (28, -406, 277),
    "fuyutsuki": (25, -409, 286),
    "operator_left": (36, -422, 291),
    "operator_centre": (28, -424, 299),
    "operator_right": (20, -422, 291),
}

FOCUS_VIEWS = {
    "09_commander_guard_focus.png": {
        "box": (18, 38, -421, -398, 268, 293),
        "anchor": CHAIRS["ikari"],
        "title": "GENDO / FUYUTSUKI AUTHORED GUARD RESTORE",
    },
    "10_operator_guard_focus.png": {
        "box": (12, 44, -434, -414, 282, 307),
        "anchor": CHAIRS["operator_centre"],
        "title": "OPERATOR TIER AUTHORED GUARD RESTORE",
    },
}


def state_from_palette(entry) -> str:
    name = str(entry["Name"])
    properties = entry.get("Properties")
    if not properties:
        return name
    values = ",".join(
        f"{key}={properties[key]}" for key in sorted(properties)
    )
    return f"{name}[{values}]"


def load_source() -> dict[tuple[int, int, int], str]:
    root = nbtlib.load(SOURCE, gzipped=True)
    palette = [state_from_palette(entry) for entry in root["palette"]]
    voxels: dict[tuple[int, int, int], str] = {}
    ox, oy, oz = ORIGIN
    for block in root["blocks"]:
        local = [int(value) for value in block["pos"]]
        index = int(block["state"])
        voxels[(ox + local[0], oy + local[1], oz + local[2])] = (
            palette[index]
        )
    return voxels


def in_box(point: tuple[int, int, int]) -> bool:
    x, y, z = point
    x0, x1, y0, y1, z0, z1 = BOX
    return x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1


def components(points: set[tuple[int, int, int]],
               expected: dict[tuple[int, int, int], str]) -> list[dict]:
    unseen = set(points)
    result = []
    while unseen:
        seed = min(unseen)
        queue = deque([seed])
        unseen.remove(seed)
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
        xs = [point[0] for point in found]
        ys = [point[1] for point in found]
        zs = [point[2] for point in found]
        materials = Counter(survey.base_name(expected[p]) for p in found)
        result.append({
            "cells": len(found),
            "bbox": [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)],
            "materials": dict(materials.most_common()),
            "nearest_chair": min(
                CHAIRS,
                key=lambda name: min(
                    abs(p[0] - CHAIRS[name][0])
                    + abs(p[1] - CHAIRS[name][1])
                    + abs(p[2] - CHAIRS[name][2]) for p in found)),
        })
    result.sort(key=lambda item: item["cells"], reverse=True)
    return result


def render_focus_views(world_root: Path,
                       output: Path,
                       source: dict[tuple[int, int, int], str]) -> None:
    """Render close evidence without widening the approved candidate box."""
    for filename, spec in FOCUS_VIEWS.items():
        box = spec["box"]
        anchor = spec["anchor"]
        title = spec["title"]
        before = survey.Volume(world_root, box)
        after = survey.Volume(world_root, box)
        overlay = survey.Volume(world_root, box)
        focus_reasons: dict[tuple[int, int, int], str] = {}
        for point, authored in source.items():
            x, y, z = point
            if not (box[0] <= x <= box[1]
                    and box[2] <= y <= box[3]
                    and box[4] <= z <= box[5]):
                continue
            current = before.state(x - before.x0, y - before.y0,
                                   z - before.z0)
            if survey.role_of(current) != "air":
                continue
            repair.set_proposed(after, focus_reasons, x, y, z, authored,
                                "focus-authored-restore")
            repair.set_proposed(overlay, focus_reasons, x, y, z,
                                "minecraft:lime_concrete",
                                "focus-diff-overlay")
        panels = [
            survey.iso_projection(before, before.masks(), anchor, 1, 1,
                                  title + " / BEFORE"),
            survey.iso_projection(after, after.masks(), anchor, 1, 1,
                                  title + " / PROPOSAL"),
            survey.iso_projection(overlay, overlay.masks(), anchor, 1, 1,
                                  title + " / ADDED GREEN +X/+Z"),
            survey.iso_projection(overlay, overlay.masks(), anchor, -1, -1,
                                  title + " / ADDED GREEN -X/-Z"),
        ]
        survey.combine_panels(panels, 2, output / filename)


def build(world_root: Path, output_root: Path) -> tuple[str, str]:
    repair_id = "S20-R13-COMMAND-HIERARCHY-SOURCE-RESTORE-PREVIEW-r01"
    source = load_source()
    before = survey.Volume(world_root, BOX)
    after = survey.Volume(world_root, BOX)
    reasons: dict[tuple[int, int, int], str] = {}
    missing: set[tuple[int, int, int]] = set()
    expected: dict[tuple[int, int, int], str] = {}

    # Five independently measured chair fingerprints prove the transform.
    chair_fingerprints = {}
    for name, point in CHAIRS.items():
        current = before.state(point[0] - before.x0,
                               point[1] - before.y0,
                               point[2] - before.z0)
        authored = source.get(point)
        chair_fingerprints[name] = {
            "point": list(point), "authored": authored, "current": current,
            "base_match": (authored is not None
                           and survey.base_name(authored)
                           == survey.base_name(current)),
        }
    if not all(item["base_match"] for item in chair_fingerprints.values()):
        raise RuntimeError(
            "command NBT transform rejected by chair fingerprints"
        )

    for point, authored in source.items():
        if not in_box(point):
            continue
        x, y, z = point
        current = before.state(x - before.x0, y - before.y0,
                               z - before.z0)
        if survey.role_of(current) != "air":
            continue
        missing.add(point)
        expected[point] = authored
        repair.set_proposed(
            after, reasons, x, y, z, authored,
            "restore-authored-command-hierarchy-air-gap:"
            + survey.base_name(authored)
        )

    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "transform_origin": list(ORIGIN),
        "bounded_hierarchy_box": list(BOX),
        "screen_masks_touched": False,
        "sightline_cut_touched": False,
        "existing_non_air_replaced": 0,
        "missing_authored_cells": len(missing),
        "missing_by_material": dict(Counter(
            survey.base_name(value) for value in expected.values()
        ).most_common()),
        "chair_fingerprints": chair_fingerprints,
        "components": components(missing, expected),
    }
    output = output_root / repair_id
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "08_missing_component_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    repair.emit_preview(
        world_root, output, repair_id, BOX, ANCHOR,
        before, after, reasons,
        [
            "restore only source-NBT non-air cells that are currently air",
            "bound the change to the Gendo/Fuyutsuki/operator hierarchy",
            "replace no existing block and touch no screen or sightline cell",
        ],
        {
            "authority": "private nerv_command_left.nbt",
            "transform_origin": list(ORIGIN),
            "chair_fingerprints": chair_fingerprints,
            "existing_non_air_replaced": 0,
            "screen_masks_touched": False,
            "sightline_cut_touched": False,
        }
    )
    render_focus_views(world_root, output, source)
    digest = repair.packet_sha(output)
    return repair_id, digest


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
