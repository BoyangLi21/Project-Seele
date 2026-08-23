#!/usr/bin/env python3
"""Create the isolated flat SEELE EVA motion-lab save."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import nbtlib
from nbtlib import Byte, Int, Long, String


ROOT = Path(__file__).resolve().parents[1]
SAVES = (ROOT / "run" / "saves").resolve()
SOURCE = SAVES / "SEELE_VISUAL_TEST_2"
TARGET = SAVES / "SEELE_EVA_MOTION_LAB"
LEVEL_NAME = "Project SEELE - EVA Motion Lab"


def write_datapack(world: Path) -> None:
    pack = world / "datapacks" / "seele_motion_lab"
    (pack / "data" / "minecraft" / "tags" / "functions").mkdir(
        parents=True, exist_ok=True
    )
    (pack / "data" / "projectseele" / "functions").mkdir(
        parents=True, exist_ok=True
    )
    (pack / "pack.mcmeta").write_text(
        json.dumps(
            {
                "pack": {
                    "pack_format": 15,
                    "description": "Project SEELE isolated EVA motion lab",
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (pack / "data" / "minecraft" / "tags" / "functions" / "load.json").write_text(
        json.dumps({"values": ["projectseele:motion_lab_load"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (pack / "data" / "projectseele" / "functions" / "motion_lab_load.mcfunction").write_text(
        "seele motionlab setup\n",
        encoding="utf-8",
    )


def create_world(force: bool) -> None:
    if not (SOURCE / "level.dat").is_file():
        raise FileNotFoundError(f"Missing flat-world template: {SOURCE}")
    target = TARGET.resolve()
    if target.parent != SAVES or target.name != "SEELE_EVA_MOTION_LAB":
        raise RuntimeError(f"Refusing unsafe target: {target}")
    if target.exists():
        if not force:
            return
        shutil.rmtree(target)
    target.mkdir(parents=True)

    level = nbtlib.load(SOURCE / "level.dat")
    # A new disposable world must not inherit the template's historical Forge
    # numeric registry snapshot; Forge writes a fresh mapping on first open.
    level.pop("fml", None)
    data = level["Data"]
    data["LevelName"] = String(LEVEL_NAME)
    data["SpawnX"] = Int(0)
    data["SpawnY"] = Int(-59)
    data["SpawnZ"] = Int(-150)
    data["SpawnAngle"] = nbtlib.Float(0.0)
    data["GameType"] = Int(1)
    data["allowCommands"] = Byte(1)
    data["hardcore"] = Byte(0)
    data["Difficulty"] = Byte(1)
    data["DifficultyLocked"] = Byte(0)
    data["DayTime"] = Long(6000)
    data["Time"] = Long(6000)
    data["clearWeatherTime"] = Int(12000)
    data["rainTime"] = Int(0)
    data["raining"] = Byte(0)
    data["thunderTime"] = Int(0)
    data["thundering"] = Byte(0)
    data["LastPlayed"] = Long(int(time.time() * 1000))
    data.pop("Player", None)
    settings = data.get("WorldGenSettings")
    if settings is not None:
        settings["seed"] = Long(2026082301)
    level.save(target / "level.dat", gzipped=True)
    shutil.copy2(target / "level.dat", target / "level.dat_old")
    if (SOURCE / "icon.png").is_file():
        shutil.copy2(SOURCE / "icon.png", target / "icon.png")
    write_datapack(target)
    (target / "MOTION_LAB.txt").write_text(
        "Project SEELE isolated EVA motion laboratory.\n"
        "The load function builds only this disposable world.\n"
        "Authority save SEELE_S20_RECOVERY_R28 is never read or modified.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--if-missing", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.if_missing and (TARGET / "level.dat").is_file():
        print(f"[PASS] motion lab already exists: {TARGET}")
        return 0
    create_world(args.force)
    print(f"[PASS] motion lab ready: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
