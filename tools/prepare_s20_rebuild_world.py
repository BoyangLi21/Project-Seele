#!/usr/bin/env python3
"""Create the S20 visual rebuild from the last human-approved GeoFront base.

S19 is not a migration source.  Its geometry was generated from clearance
owners and must never be copied into another save.  S20 deliberately clones
the coherent block geometry from SEELE_TOKYO3_REBUILT, then drops players,
entities and Project SEELE SavedData so no old fleet receipt or moving actor
can be mistaken for part of the new facility.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import nbtlib
from nbtlib import Byte, Int, String


ROOT = Path(__file__).resolve().parents[1]
SAVES = ROOT / "run" / "saves"
SOURCE = SAVES / "SEELE_TOKYO3_REBUILT"
TARGET = SAVES / "SEELE_S20_REBUILD"
MARKER_NAME = ".projectseele_s20_rebuild.json"
LEVEL_NAME = "Project SEELE - S20 Rebuild"
SCHEMA = 1

ROOT_RUNTIME_FOLDERS = {
    "advancements",
    "entities",
    "playerdata",
    "poi",
    "stats",
}


def recognised_target() -> dict | None:
    marker = TARGET / MARKER_NAME
    level = TARGET / "level.dat"
    if not marker.is_file() or not level.is_file():
        return None
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if value.get("schema") != SCHEMA:
        return None
    if Path(value.get("source", "")).resolve() != SOURCE.resolve():
        return None
    return value


def ignore_runtime(directory: str, names: list[str]) -> set[str]:
    path = Path(directory).resolve()
    ignored: set[str] = set()
    if path == SOURCE.resolve():
        ignored.update(ROOT_RUNTIME_FOLDERS)
        ignored.update({
            "session.lock",
            "level.dat_old",
            ".projectseele_s19_clean.json",
            ".projectseele_s19_build_authorized.json",
        })
    # Entity and POI region files are runtime state in every dimension.
    if path.name in {"entities", "poi"}:
        ignored.update(names)
    return ignored & set(names)


def clear_project_saved_data(target: Path) -> list[str]:
    removed: list[str] = []
    data = target / "data"
    if not data.is_dir():
        return removed
    for candidate in data.glob("projectseele_*.dat"):
        candidate.unlink()
        removed.append(candidate.name)
    return sorted(removed)


def rewrite_level_dat(target: Path) -> None:
    level_path = target / "level.dat"
    level = nbtlib.load(level_path)
    data = level.get("Data", level)
    data["LevelName"] = String(LEVEL_NAME)
    data["allowCommands"] = Byte(1)
    data["GameType"] = Int(1)
    data["hardcore"] = Byte(0)
    data["Difficulty"] = Byte(1)
    data["DifficultyLocked"] = Byte(0)
    data["confirmedExperimentalSettings"] = Byte(1)

    # Keep the last measured GeoFront position, but reset the two creative
    # flight flags which previously left the human reviewer drifting.
    player = data.get("Player")
    if player is not None:
        player["playerGameType"] = Int(1)
        player["OnGround"] = Byte(1)
        player["FallDistance"] = nbtlib.Float(0.0)
        player["Motion"] = nbtlib.List[nbtlib.Double](
            [nbtlib.Double(0.0), nbtlib.Double(0.0), nbtlib.Double(0.0)])
        abilities = player.get("abilities")
        if abilities is not None:
            abilities["flying"] = Byte(0)
            abilities["mayfly"] = Byte(1)

    level.save(level_path, gzipped=True)


def region_inventory(root: Path) -> dict:
    # Only block-region files define the visual/layout base. Entity and POI
    # MCA files are deliberately excluded from S20.
    files = sorted(path for path in root.rglob("r.*.*.mca")
                   if path.parent.name == "region")
    return {
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files),
    }


def stage() -> dict:
    current = recognised_target()
    if current is not None:
        return current
    if TARGET.exists():
        raise FileExistsError(
            f"Refusing to replace unrecognised S20 save: {TARGET}")
    if not (SOURCE / "level.dat").is_file():
        raise FileNotFoundError(
            f"Measured GeoFront source is missing: {SOURCE}")
    if (SOURCE / ".projectseele_s19_clean.json").exists():
        raise RuntimeError("S19 must never be used as the S20 source")

    target_parent = TARGET.parent.resolve()
    resolved_target = TARGET.resolve()
    if resolved_target.parent != target_parent:
        raise RuntimeError(f"Unsafe S20 target: {resolved_target}")

    source_inventory = region_inventory(SOURCE)
    shutil.copytree(SOURCE, TARGET, ignore=ignore_runtime)
    removed_saved_data = clear_project_saved_data(TARGET)
    rewrite_level_dat(TARGET)
    target_inventory = region_inventory(TARGET)
    if target_inventory != source_inventory:
        raise RuntimeError(
            "S20 block-region clone is incomplete: "
            f"source={source_inventory} target={target_inventory}")

    value = {
        "schema": SCHEMA,
        "world": str(TARGET.resolve()),
        "level_name": LEVEL_NAME,
        "source": str(SOURCE.resolve()),
        "source_role": "human_approved_geofront_layout_reference",
        "block_regions": target_inventory,
        "s19_geometry_copied": False,
        "runtime_entities_copied": False,
        "project_saved_data_removed": removed_saved_data,
        "runtime_architecture_writers": "disabled",
        "command_visual_master": "nerv_command_left.nbt",
        "private_local_only": True,
    }
    (TARGET / MARKER_NAME).write_text(
        json.dumps(value, indent=2), encoding="utf-8")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--if-missing",
        action="store_true",
        help="Keep an existing recognised S20 rebuild unchanged")
    parser.parse_args()
    print(json.dumps(stage(), indent=2))


if __name__ == "__main__":
    main()
