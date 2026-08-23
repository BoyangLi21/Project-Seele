#!/usr/bin/env python3
"""Create a fresh coastal migration save without copying any old chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import nbtlib
from nbtlib import Byte, Int, Long, String


ROOT = Path(__file__).resolve().parents[1]
SAVES = ROOT / "run/saves"
TEMPLATE = SAVES / "New World (38)"
TARGET = SAVES / "SEELE_S24_COASTAL_REBUILD"
AUTHORITY = SAVES / "SEELE_S20_RECOVERY_R28"
FROZEN_BACKUP = ROOT / "backups/SEELE_R28_FROZEN_PRE_S22_20260821_121615"
LEVEL_NAME = "Project SEELE - Coastal Rebuild"
COASTAL_MARKER = ".projectseele_s22_coastal.json"
S24_MARKER = ".projectseele_s24_coastal.json"
FREEZE_MARKER = ".projectseele_s22_migration_frozen.json"
R28_SEED = 421391710818770726

EXCLUDED = {
    "session.lock", "level.dat_old", "playerdata", "stats",
    "advancements", "region", "entities", "poi", "dimensions", "data",
    "datapacks", "DIM-1", "DIM1", "serverconfig", "mtr",
}


def ignore_dynamic(_directory: str, names: list[str]) -> set[str]:
    return EXCLUDED & set(names)


def selected_metrics(report: Path | None, seed: int) -> dict | None:
    if report is None or not report.is_file():
        return None
    value = json.loads(report.read_text(encoding="utf-8"))
    for candidate in value.get("candidates", []):
        if int(candidate.get("seed")) == seed:
            result = dict(candidate)
            result.pop("grid", None)
            return result
    return None


def stage(seed: int, target: Path, report: Path | None,
          anchor_x: int, anchor_z: int, deck_y: int) -> dict:
    if seed == R28_SEED:
        raise RuntimeError("The coastal save must use a seed different from R28")
    if target.exists():
        raise FileExistsError(f"Refusing to replace existing target: {target}")
    if not (TEMPLATE / "level.dat").is_file():
        raise FileNotFoundError(f"Normal-world template missing: {TEMPLATE}")
    if not (AUTHORITY / "level.dat").is_file() or not FROZEN_BACKUP.is_dir():
        raise FileNotFoundError("R28 authority or its frozen backup is missing")

    shutil.copytree(TEMPLATE, target, ignore=ignore_dynamic)
    level_path = target / "level.dat"
    level = nbtlib.load(level_path)
    data = level.get("Data", level)
    settings = data.get("WorldGenSettings")
    if settings is None:
        raise RuntimeError("Template has no WorldGenSettings")
    settings["seed"] = Long(seed)
    settings["generate_features"] = Byte(1)
    settings["bonus_chest"] = Byte(0)
    data["RandomSeed"] = Long(seed)
    data["LevelName"] = String(LEVEL_NAME)
    data["SpawnX"] = Int(anchor_x)
    data["SpawnY"] = Int(deck_y + 16)
    data["SpawnZ"] = Int(anchor_z)
    data["allowCommands"] = Byte(1)
    data["GameType"] = Int(1)
    data["hardcore"] = Byte(0)
    data["Difficulty"] = Byte(1)
    data["DifficultyLocked"] = Byte(0)
    data["confirmedExperimentalSettings"] = Byte(1)
    data.pop("Player", None)
    level.save(level_path, gzipped=True)

    marker = {
        "schema": 2,
        "role": "coastal_migration_target",
        "world": str(target.resolve()),
        "level_name": LEVEL_NAME,
        "seed": seed,
        "seed_is_different_from_r28": True,
        "selected_metrics": selected_metrics(report, seed),
        "authority_source": str(AUTHORITY.resolve()),
        "authority_frozen_backup": str(FROZEN_BACKUP.resolve()),
        "terrain_chunks_copied": False,
        "entities_copied": False,
        "saved_data_copied": False,
        "source_anchor": [30, 80, 296],
        "target_anchor": [anchor_x, deck_y, anchor_z],
        "transform": [anchor_x - 30, deck_y - 80, anchor_z - 296],
        "surface_datum": deck_y,
        "facility_centre_xz": [anchor_x, anchor_z],
        "migration_writers_frozen": True,
        "private_local_only": True,
    }
    text = json.dumps(marker, indent=2) + "\n"
    (target / COASTAL_MARKER).write_text(text, encoding="utf-8")
    (target / S24_MARKER).write_text(text, encoding="utf-8")
    (target / FREEZE_MARKER).write_text(json.dumps({
        "schema": 1,
        "reason": "approved assets are being transplanted into fresh terrain",
        "automatic_map_writers": "disabled until cutover audit passes",
    }, indent=2) + "\n", encoding="utf-8")
    return marker


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--scout-report", type=Path)
    parser.add_argument("--anchor-x", type=int, required=True)
    parser.add_argument("--anchor-z", type=int, required=True)
    parser.add_argument("--deck-y", type=int, default=68)
    args = parser.parse_args()
    result = stage(args.seed, args.target.resolve(), args.scout_report,
                   args.anchor_x, args.anchor_z, args.deck_y)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
