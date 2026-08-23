#!/usr/bin/env python3
"""Stage a genuinely new coastal Project SEELE world.

Only normal-world metadata is inherited from a local template.  Terrain,
entities, POI, players, dimensions and Project SEELE runtime data are never
copied.  The selected seed is intentionally different from the R28 authority
save; the GeoFront dimension therefore generates fresh terrain from the same
seed when it is first entered.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import nbtlib
from nbtlib import Byte, Double, Float, Int, List, Long, String


ROOT = Path(__file__).resolve().parents[1]
SAVES = ROOT / "run" / "saves"
TEMPLATE = SAVES / "New World (38)"
TARGET = SAVES / "SEELE_S22_COASTAL"
MARKER = ".projectseele_s22_coastal.json"
LEVEL_NAME = "Project SEELE - Coastal GeoFront"
SEED = 8608349212919703279
R28_SEED = 421391710818770726

EXCLUDED = {
    "session.lock", "level.dat_old", "playerdata", "stats",
    "advancements", "region", "entities", "poi", "dimensions", "data",
    "datapacks", "DIM-1", "DIM1", "serverconfig",
}


def ignore_dynamic(_directory: str, names: list[str]) -> set[str]:
    return EXCLUDED & set(names)


def rewrite_level_dat() -> None:
    path = TARGET / "level.dat"
    level = nbtlib.load(path)
    data = level.get("Data", level)
    settings = data.get("WorldGenSettings")
    if settings is None:
        raise RuntimeError("Template has no WorldGenSettings")
    if SEED == R28_SEED:
        raise RuntimeError("S22 seed must differ from R28")
    settings["seed"] = Long(SEED)
    settings["generate_features"] = Byte(1)
    settings["bonus_chest"] = Byte(0)
    data["RandomSeed"] = Long(SEED)
    data["LevelName"] = String(LEVEL_NAME)
    data["SpawnX"] = Int(30)
    data["SpawnY"] = Int(80)
    data["SpawnZ"] = Int(296)
    data["allowCommands"] = Byte(1)
    data["GameType"] = Int(1)
    data["hardcore"] = Byte(0)
    data["Difficulty"] = Byte(1)
    data["DifficultyLocked"] = Byte(0)
    data["confirmedExperimentalSettings"] = Byte(1)
    data.pop("Player", None)
    level.save(path, gzipped=True)


def stage() -> dict:
    marker_path = TARGET / MARKER
    if marker_path.is_file() and (TARGET / "level.dat").is_file():
        return json.loads(marker_path.read_text(encoding="utf-8"))
    if TARGET.exists():
        raise FileExistsError(f"Refusing to replace unknown target: {TARGET}")
    if not (TEMPLATE / "level.dat").is_file():
        raise FileNotFoundError(f"Normal-noise template missing: {TEMPLATE}")

    shutil.copytree(TEMPLATE, TARGET, ignore=ignore_dynamic)
    rewrite_level_dat()
    value = {
        "schema": 1,
        "world": str(TARGET.resolve()),
        "level_name": LEVEL_NAME,
        "seed": SEED,
        "r28_seed": R28_SEED,
        "seed_is_different": SEED != R28_SEED,
        "template": str(TEMPLATE.resolve()),
        "terrain_or_dimensions_copied": False,
        "target_facility_centre": [30, 296],
        "site_intent": "broad coastal plains measured before transplant",
        "authority_source": str((SAVES / "SEELE_S20_RECOVERY_R28").resolve()),
        "authority_source_frozen": True,
        "private_local_only": True,
    }
    marker_path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return value


def place_player(dimension: str, x: float, y: float, z: float) -> None:
    """Place the existing local player for bounded terrain generation."""
    path = TARGET / "level.dat"
    level = nbtlib.load(path)
    data = level.get("Data", level)
    player = data.get("Player")
    if player is None:
        raise RuntimeError("Open S22 once before placing its local player")
    player["Dimension"] = String(dimension)
    player["Pos"] = List[Double]([Double(x), Double(y), Double(z)])
    player["Rotation"] = List[Float]([Float(0.0), Float(15.0)])
    abilities = player.get("abilities")
    if abilities is not None:
        abilities["mayfly"] = Byte(1)
        abilities["flying"] = Byte(1)
    level.save(path, gzipped=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-missing", action="store_true")
    parser.add_argument("--enter-geofront", action="store_true")
    parser.add_argument("--enter-overworld", action="store_true")
    parser.add_argument("--position", nargs=3, type=float,
                        metavar=("X", "Y", "Z"),
                        help="override the selected dimension's player position")
    args = parser.parse_args()
    result = stage()
    if args.enter_geofront:
        position = args.position or (30.5, -452.0, 296.5)
        place_player("projectseele:geofront", *position)
        result["player"] = ["projectseele:geofront", *position]
    elif args.enter_overworld:
        position = args.position or (30.5, 80.0, 296.5)
        place_player("minecraft:overworld", *position)
        result["player"] = ["minecraft:overworld", *position]
    elif args.position:
        parser.error("--position requires --enter-geofront or --enter-overworld")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
