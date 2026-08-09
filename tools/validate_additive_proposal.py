#!/usr/bin/env python3
"""Fail-closed occupancy checks for an additive Minecraft map preview.

The preview packet proves which voxels change.  This validator asks the four
questions that an ``air-only`` edit cannot answer: did it consume existing
walkable air, escape the existing overhead shell, float without support, or
block an authored door / declared route port?  It reads the world once and
prints one complete JSON report; it never writes the world or preview packet.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import survey_facility_target as survey  # noqa: E402


PASSABLE_ROLES = {"air", "fixture", "door"}
FACING = {
    "north": (0, -1),
    "south": (0, 1),
    "west": (-1, 0),
    "east": (1, 0),
}


def role(state: str) -> str:
    return survey.role_of(state)


def solid(state: str) -> bool:
    return role(state) not in PASSABLE_ROLES | {"fluid"}


def passable(state: str) -> bool:
    return role(state) in PASSABLE_ROLES


def bbox(points: list[tuple[int, int, int]]) -> list[int] | None:
    if not points:
        return None
    return [
        min(p[0] for p in points), min(p[1] for p in points),
        min(p[2] for p in points), max(p[0] for p in points),
        max(p[1] for p in points), max(p[2] for p in points),
    ]


def component_summaries(points: list[tuple[int, int, int]]) -> list[dict]:
    remaining = set(points)
    result = []
    while remaining:
        seed = remaining.pop()
        component = {seed}
        stack = [seed]
        while stack:
            x, y, z = stack.pop()
            for neighbor in ((x - 1, y, z), (x + 1, y, z),
                             (x, y - 1, z), (x, y + 1, z),
                             (x, y, z - 1), (x, y, z + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        result.append({"count": len(component), "bbox": bbox(list(component))})
    return sorted(result, key=lambda item: item["count"], reverse=True)


def facing_of(state: str) -> tuple[int, int] | None:
    match = re.search(r"(?:^|,)facing=([^,\]]+)", state)
    return FACING.get(match.group(1)) if match else None


def load_diff(packet: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((packet / "00_manifest.json").read_text(
        encoding="utf-8"))
    with (packet / "block_diff.csv").open(
            "r", encoding="utf-8", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            row["x"], row["y"], row["z"] = (
                int(row["x"]), int(row["y"]), int(row["z"]))
            rows.append(row)
    return manifest, rows


def validate(packet: Path, world: Path, ceiling_y: int | None,
             ports: list[tuple[int, int, int, int, int]]) -> dict:
    manifest, rows = load_diff(packet)
    affected_path = packet / "affected_components.json"
    contract = {}
    if affected_path.exists():
        contract = json.loads(affected_path.read_text(
            encoding="utf-8")).get("contract", {})
    allowed_filled = {
        tuple(int(value) for value in point)
        for point in contract.get("allowed_filled_standable", [])
    }
    allowed_span_blocks = set()
    lateral_spans = contract.get("allowed_lateral_spans", [])
    for span in lateral_spans:
        allowed_span_blocks.update(
            tuple(int(value) for value in point)
            for point in span.get("blocks", []))
    if not rows:
        raise RuntimeError("preview packet contains no voxel changes")

    changed = {(row["x"], row["y"], row["z"]): row for row in rows}
    added = [row for row in rows
             if row["change"] == "added" and solid(row["after"])]
    # Removal-only surgical packets are valid inputs. Their additive occupancy,
    # shell and footing gates are vacuously clean; door/ladder and declared-port
    # checks still run against the complete proposed diff.

    if ceiling_y is None:
        ceiling_y = int(contract.get(
            "validation_ceiling_y",
            manifest.get("validation_ceiling_y", manifest["box"][3])))

    x0 = min(row["x"] for row in rows) - 2
    x1 = max(row["x"] for row in rows) + 2
    y0 = min(row["y"] for row in rows) - 1
    z0 = min(row["z"] for row in rows) - 2
    z1 = max(row["z"] for row in rows) + 2
    if ceiling_y <= y0:
        raise ValueError("ceiling-y must be above the proposal")
    volume = survey.Volume(world, (x0, x1, y0, ceiling_y, z0, z1))

    def original(pos: tuple[int, int, int]) -> str:
        x, y, z = pos
        if not (volume.x0 <= x <= volume.x1
                and volume.y0 <= y <= volume.y1
                and volume.z0 <= z <= volume.z1):
            return "minecraft:air"
        return volume.state(x - volume.x0, y - volume.y0, z - volume.z0)

    def proposed(pos: tuple[int, int, int]) -> str:
        row = changed.get(pos)
        return row["after"] if row else original(pos)

    filled_standable = []
    for row in added:
        pos = (row["x"], row["y"], row["z"])
        x, y, z = pos
        if (passable(original(pos))
                and solid(original((x, y - 1, z)))
                and passable(original((x, y + 1, z)))):
            filled_standable.append(pos)
    undeclared_filled = [
        point for point in filled_standable if point not in allowed_filled]
    declared_filled = [
        point for point in filled_standable if point in allowed_filled]
    if set(declared_filled) != allowed_filled:
        missing = sorted(allowed_filled - set(declared_filled))
        raise RuntimeError(
            f"declared filled-standable conversions not observed: {missing}")

    original_column_top: dict[tuple[int, int], int | None] = {}
    for row in added:
        key = (row["x"], row["z"])
        if key in original_column_top:
            continue
        top = None
        for y in range(ceiling_y, y0 - 1, -1):
            if solid(original((key[0], y, key[1]))):
                top = y
                break
        original_column_top[key] = top

    proposal_column_top = dict(original_column_top)
    for row in added:
        key = (row["x"], row["z"])
        current = proposal_column_top[key]
        if current is None or row["y"] > current:
            proposal_column_top[key] = row["y"]

    # Compare every addition with the original authored shell above it.  The
    # scan ceiling must cover that authored asset (provided by the packet or
    # explicitly on the CLI); stopping at the proposal roof creates false
    # exterior results, while letting the proposal roof itself hides breaches.
    shell_overrun = []
    outside_known_shell = []
    for row in added:
        key = (row["x"], row["z"])
        point = (row["x"], row["y"], row["z"])
        authored_top = original_column_top[key]
        if authored_top is None:
            outside_known_shell.append(point)
        elif row["y"] > authored_top:
            shell_overrun.append(point)
    unroofed = shell_overrun + outside_known_shell

    # Footing is per column, not per global layer: a raised deck whose own
    # lowest block hangs in air is just as unsupported as the bottom slab,
    # and the global minimum y never sees it.
    lowest_by_column: dict[tuple[int, int], int] = {}
    for row in added:
        key = (row["x"], row["z"])
        if key not in lowest_by_column or row["y"] < lowest_by_column[key]:
            lowest_by_column[key] = row["y"]
    footings = [(x, y, z) for (x, z), y in lowest_by_column.items()]
    supported = [footing for footing in footings
                 if solid(proposed((footing[0], footing[1] - 1,
                                    footing[2])))]
    supported_set = set(supported)
    unsupported = [footing for footing in footings
                   if footing not in supported_set]
    accepted_lateral = set()
    for span in lateral_spans:
        blocks = [tuple(int(value) for value in point)
                  for point in span.get("blocks", [])]
        anchors = [tuple(int(value) for value in point)
                   for point in span.get("anchors", [])]
        if (not blocks or len(anchors) != 2
                or any(point not in unsupported for point in blocks)):
            continue
        if not all(solid(proposed(anchor)) for anchor in anchors):
            continue
        if len(blocks) > 2:
            continue
        accepted_lateral.update(blocks)
    undeclared_unsupported = [
        point for point in unsupported if point not in accepted_lateral]
    support_rate = len(supported) / len(footings) if footings else 1.0

    blocked_doors = []
    seen_doors = set()
    for ix in range(volume.sx):
        for iy in range(volume.sy):
            for iz in range(volume.sz):
                state = volume.state(ix, iy, iz)
                bare = state.split("[", 1)[0]
                is_door = (bare.endswith("_door")
                           and not bare.endswith("trapdoor"))
                is_ladder = bare == "minecraft:ladder"
                if not (is_door or is_ladder):
                    continue
                pos = volume.world_position(ix, iy, iz)
                key = (pos[0], pos[2], bare)
                if key in seen_doors:
                    continue
                seen_doors.add(key)
                direction = facing_of(state)
                if direction is None:
                    continue
                dx, dz = direction
                blocked = []
                for step in (1, 2):
                    for dy in (0, 1):
                        check = (pos[0] + dx * step, pos[1] + dy,
                                 pos[2] + dz * step)
                        if check in changed and solid(proposed(check)):
                            blocked.append(check)
                if blocked:
                    blocked_doors.append({
                        "access": "ladder" if is_ladder else "door",
                        "at": list(pos), "state": state,
                        "blocked_cells": [list(p) for p in sorted(set(blocked))],
                    })

    blocked_ports = []
    for x, y, z, dx, dz in ports:
        blocked = []
        for step in (1, 2):
            for dy in (0, 1):
                check = (x + dx * step, y + dy, z + dz * step)
                if check in changed and solid(proposed(check)):
                    blocked.append(check)
        if blocked:
            blocked_ports.append({
                "port": [x, y, z, dx, dz],
                "blocked_cells": [list(p) for p in sorted(set(blocked))],
            })

    z_envelope = []
    for z in sorted({row["z"] for row in added}):
        z_rows = [row for row in added if row["z"] == z]
        new_top = max(row["y"] for row in z_rows)
        existing_tops = [original_column_top[(row["x"], z)]
                         for row in z_rows]
        existing_tops = [value for value in existing_tops
                         if value is not None]
        existing_top = max(existing_tops) if existing_tops else None
        if existing_top is None or new_top > existing_top:
            z_envelope.append({
                "z": z, "existing_highest_solid_y": existing_top,
                "proposal_highest_y": new_top,
                "overrun": None if existing_top is None
                else new_top - existing_top,
            })

    gates = {
        "undeclared_filled_original_standable_cells_zero": (
            len(undeclared_filled) == 0),
        "unroofed_additions_zero": len(unroofed) == 0,
        "column_footing_support_or_declared_lateral_span": (
            len(undeclared_unsupported) == 0),
        "blocked_authored_doors_zero": len(blocked_doors) == 0,
        "blocked_declared_ports_zero": len(blocked_ports) == 0,
    }
    return {
        "validator": "validate_additive_proposal/v1",
        "packet": str(packet.resolve()),
        "repair_id": manifest.get("repair_id"),
        "world": str(world.resolve()),
        "world_files_written": False,
        "validation_ceiling_y": ceiling_y,
        "scan_box": [x0, x1, y0, ceiling_y, z0, z1],
        "added_solid_voxels": len(added),
        "filled_original_standable": {
            "count": len(filled_standable),
            "bbox": bbox(filled_standable),
            "sample": [list(p) for p in filled_standable[:32]],
            "declared_stair_conversions": [
                list(p) for p in declared_filled],
            "undeclared": [list(p) for p in undeclared_filled],
        },
        "unroofed_additions": {
            "count": len(unroofed),
            "bbox": bbox(unroofed),
            "by_after_state": dict(sorted(Counter(
                changed[point]["after"] for point in unroofed).items())),
            "components": component_summaries(unroofed),
            "sample": [list(p) for p in unroofed[:32]],
            "above_existing_column_shell": {
                "count": len(shell_overrun),
                "bbox": bbox(shell_overrun),
            },
            "outside_any_known_column_shell": {
                "count": len(outside_known_shell),
                "bbox": bbox(outside_known_shell),
            },
            "z_envelope_overruns": z_envelope,
        },
        "column_footing_support": {
            "columns": len(footings),
            "supported": len(supported),
            "unsupported": len(unsupported),
            "rate": support_rate,
            "unsupported_bbox": bbox(unsupported),
            "unsupported_sample": [list(p) for p in unsupported[:32]],
            "accepted_lateral_span_blocks": [
                list(p) for p in sorted(accepted_lateral)],
            "undeclared_unsupported": [
                list(p) for p in undeclared_unsupported[:32]],
        },
        "blocked_authored_doors": blocked_doors,
        "blocked_declared_ports": blocked_ports,
        "gates": gates,
        "pass": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument(
        "--world", type=Path, required=True,
        help="dimension directory containing the region folder",
    )
    parser.add_argument(
        "--ceiling-y", type=int,
        help="local envelope ceiling; defaults to packet box Y1",
    )
    parser.add_argument(
        "--port", nargs=5, type=int, action="append", default=[],
        metavar=("X", "Y", "Z", "DX", "DZ"),
        help="declared port feet cell and outward horizontal direction",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.packet.is_dir():
        parser.error(f"packet not found: {args.packet}")
    if not args.world.is_dir():
        parser.error(f"world dimension not found: {args.world}")

    report = validate(args.packet, args.world, args.ceiling_y,
                      [tuple(values) for values in args.port])
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
