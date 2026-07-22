#!/usr/bin/env python3
"""Fail-closed audit for Project SEELE command-room display entities."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from inspect_map_assets import region_chunks


EXPECTED_TAGS = {
    "projectseele.magi_maintenance.melchior",
    "projectseele.magi_maintenance.balthasar",
    "projectseele.magi_maintenance.casper",
    "projectseele.nerv_control.system",
    "projectseele.nerv_control.unit00",
    "projectseele.nerv_control.unit01",
    "projectseele.nerv_control.unit02",
    "projectseele.nerv_control.armour",
    "projectseele.nerv_control.yashima",
    "projectseele.nerv_control.abort",
    "projectseele.nerv_telemetry.strategic",
    "projectseele.nerv_telemetry.unit00",
    "projectseele.nerv_telemetry.unit01",
    "projectseele.nerv_telemetry.unit02",
    "projectseele.nerv_telemetry.sensor",
}


def scan(entity_directory: Path) -> dict:
    tagged = []
    for region in sorted(entity_directory.glob("r.*.*.mca")):
        _, raw_x, raw_z = region.stem.split(".")
        region_x, region_z = int(raw_x), int(raw_z)
        bounds = (
            region_x * 32, region_x * 32 + 31,
            region_z * 32, region_z * 32 + 31,
        )
        for chunk_x, chunk_z, chunk in region_chunks(region, bounds):
            entities = chunk.get("Entities", chunk.get("entities", []))
            for entity in entities:
                if str(entity.get("id", "")) != "minecraft:text_display":
                    continue
                tags = tuple(str(value) for value in entity.get("Tags", []))
                project_tags = tuple(
                    value for value in tags
                    if value.startswith("projectseele.")
                )
                if not project_tags:
                    continue
                uuid = tuple(int(value) for value in entity.get("UUID", []))
                position = tuple(
                    round(float(value), 3)
                    for value in entity.get("Pos", [])
                )
                tagged.append({
                    "tags": project_tags,
                    "uuid": uuid,
                    "position": position,
                    "chunk": (chunk_x, chunk_z),
                })

    counts = Counter(
        tag for entity in tagged for tag in entity["tags"]
    )
    uuid_counts = Counter(
        entity["uuid"] for entity in tagged if entity["uuid"]
    )
    missing = sorted(tag for tag in EXPECTED_TAGS if counts[tag] == 0)
    duplicated = {
        tag: counts[tag] for tag in sorted(EXPECTED_TAGS)
        if counts[tag] > 1
    }
    unexpected = sorted(
        tag for tag in counts if tag not in EXPECTED_TAGS
    )
    duplicate_uuids = sum(
        amount - 1 for amount in uuid_counts.values() if amount > 1
    )
    valid = (
        not missing
        and not duplicated
        and not unexpected
        and duplicate_uuids == 0
        and len(tagged) == len(EXPECTED_TAGS)
    )
    return {
        "valid": valid,
        "expected": len(EXPECTED_TAGS),
        "found": len(tagged),
        "missing": missing,
        "duplicated": duplicated,
        "unexpected": unexpected,
        "duplicateUuids": duplicate_uuids,
        "counts": dict(sorted(counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        type=Path,
        default=Path("run/saves/SEELE_TOKYO3_REBUILT"),
    )
    arguments = parser.parse_args()
    entity_directory = (
        arguments.world
        / "dimensions/projectseele/geofront/entities"
    )
    if not entity_directory.is_dir():
        print(f"Missing GeoFront entity directory: {entity_directory}")
        return 2

    report = scan(entity_directory)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
