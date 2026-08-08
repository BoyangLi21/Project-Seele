#!/usr/bin/env python3
"""Stage a clean Project SEELE rebuild save without legacy facility chunks.

The failed rescue save mixed two independent facility coordinate systems.  A
clean rebuild must therefore inherit only normal-noise world metadata from a
known local template.  Regions, entities, dimensions, player data and every
old Project SEELE SavedData file are deliberately excluded.
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
TARGET = SAVES / "SEELE_S19_CLEAN"
MARKER_NAME = ".projectseele_s19_clean.json"
AUTHORIZATION_NAME = ".projectseele_s19_build_authorized.json"
SCHEMA = 2
LEVEL_NAME = "Project SEELE - S19 Clean"
TEMPLATE_CANDIDATES = (
    SAVES / "New World",
    SAVES / "New World (38)",
)

DYNAMIC_WORLD_DATA = {
    "session.lock",
    "playerdata",
    "stats",
    "advancements",
    "region",
    "entities",
    "poi",
    "dimensions",
    "data",
    "datapacks",
    "DIM-1",
    "DIM1",
    "serverconfig",
}


def generator_type(path: Path) -> str:
    level_path = path / "level.dat"
    if not level_path.is_file():
        return ""
    level = nbtlib.load(level_path)
    data = level.get("Data", level)
    return str(data.get("WorldGenSettings", {})
               .get("dimensions", {})
               .get("minecraft:overworld", {})
               .get("generator", {})
               .get("type", ""))


def select_template() -> Path:
    candidates = list(TEMPLATE_CANDIDATES)
    candidates.extend(sorted(
        (path for path in SAVES.glob("New World*")
         if path not in candidates),
        key=lambda path: path.name,
    ))
    for candidate in candidates:
        if generator_type(candidate) == "minecraft:noise":
            return candidate
    raise FileNotFoundError(
        "No clean normal-noise 'New World' template is available")


def copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = set(DYNAMIC_WORLD_DATA)
    ignored.update(name for name in names
                   if name.startswith("visual_capture")
                   or name.startswith(".projectseele"))
    return ignored & set(names)


def rewrite_level_dat(path: Path) -> None:
    level_path = path / "level.dat"
    if not level_path.is_file():
        raise FileNotFoundError(f"Template level.dat missing: {level_path}")
    level = nbtlib.load(level_path)
    data = level.get("Data", level)
    data["LevelName"] = String(LEVEL_NAME)
    data["SpawnX"] = Int(0)
    data["SpawnY"] = Int(96)
    data["SpawnZ"] = Int(0)
    data["allowCommands"] = Byte(1)
    data["GameType"] = Int(1)
    data["hardcore"] = Byte(0)
    data["Difficulty"] = Byte(1)
    data["DifficultyLocked"] = Byte(0)
    data["confirmedExperimentalSettings"] = Byte(1)
    data.pop("Player", None)
    level.save(level_path, gzipped=True)


def existing_marker() -> dict | None:
    marker = TARGET / MARKER_NAME
    if not marker.is_file() or not (TARGET / "level.dat").is_file():
        return None
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if value.get("schema") != SCHEMA:
        return None
    return value


def write_authorization() -> None:
    authorization = {
        "schema": 1,
        "world": str(TARGET.resolve()),
        "facility_epoch": 5,
        "coordinate_contract": 3,
        "authorized_pipeline": "facility_v2_staged_build",
        "authorized_programmes": [
            "public_backbone",
            "dogma_backbone",
            "eva_backbone",
            "command_asset_fusion",
            "geofront_fabric",
        ],
        "legacy_repair_authorized": False,
        "private_local_only": True,
    }
    (TARGET / AUTHORIZATION_NAME).write_text(
        json.dumps(authorization, indent=2), encoding="utf-8")


def stage() -> dict:
    current = existing_marker()
    if current is not None:
        write_authorization()
        return current
    if TARGET.exists():
        raise FileExistsError(
            f"Refusing to replace unrecognised save: {TARGET}")

    template = select_template()
    target_parent = TARGET.parent.resolve()
    resolved_target = TARGET.resolve()
    if resolved_target.parent != target_parent:
        raise RuntimeError(f"Unsafe clean-save target: {resolved_target}")

    shutil.copytree(template, TARGET, ignore=copy_ignore)
    rewrite_level_dat(TARGET)
    value = {
        "schema": SCHEMA,
        "world": str(TARGET.resolve()),
        "level_name": LEVEL_NAME,
        "template": str(template.resolve()),
        "template_generator": generator_type(template),
        "world_role": "clean_facility_rebuild",
        "facility_epoch": 5,
        "coordinate_contract": 3,
        "legacy_chunks_copied": False,
        "excluded": sorted(DYNAMIC_WORLD_DATA),
        "facility_state": "SPATIAL_CONTRACT_PENDING",
        "private_local_only": True,
    }
    (TARGET / MARKER_NAME).write_text(
        json.dumps(value, indent=2), encoding="utf-8")
    write_authorization()
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--if-missing",
        action="store_true",
        help="Keep an existing recognised clean rebuild unchanged")
    parser.parse_args()
    print(json.dumps(stage(), indent=2))


if __name__ == "__main__":
    main()
