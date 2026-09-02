#!/usr/bin/env python3
"""Fail closed when a desktop launcher would start stale live-combat code."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MOTION = REPO / "src/main/resources/assets/projectseele/motion"
BUILT_MOTION = REPO / "build/resources/main/assets/projectseele/motion"
CLASS_ROOT = REPO / "build/classes/java/main/com/projectseele"
OUTPUT = REPO / "run/projectseele-desktop-build.json"
FILES = (
    "eva_ordinary_attack_group_c_v1.json",
    "eva_kick_side_left_v1.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("Desktop live-combat preflight failed: " + message)


def main() -> None:
    resources = {}
    for name in FILES:
        source = MOTION / name
        built = BUILT_MOTION / name
        require(source.is_file(), f"missing source resource {name}")
        require(built.is_file(), f"missing built resource {name}")
        source_hash = sha256(source)
        built_hash = sha256(built)
        require(source_hash == built_hash,
                f"built resource is stale: {name}")
        resources[name] = source_hash
    ordinary = json.loads((MOTION / FILES[0]).read_text(encoding="utf-8"))
    kick = json.loads((MOTION / FILES[1]).read_text(encoding="utf-8"))
    require(ordinary["gameplay_contract"]["playback_speed_multiplier"] == 1.5,
            "ordinary attack is not 1.5x")
    require(len(ordinary["clips"]) == 4
            and len(ordinary["bones"]) == 50,
            "ordinary attack must be 4 clips / 50 bones")
    require(kick["gameplay_contract"]["playback_speed_multiplier"] == 1.5,
            "side kick is not 1.5x")
    require(len(kick["clips"]) == 1 and len(kick["bones"]) == 50,
            "side kick must be 1 clip / 50 bones")
    classes = (
        CLASS_ROOT / "entity/EvaUnit01Entity.class",
        CLASS_ROOT / "entity/EvaLiveCombatMotion.class",
        CLASS_ROOT / "client/render/EvaMotionEngineV2.class",
    )
    for path in classes:
        require(path.is_file(), f"missing compiled class {path.name}")
    commit = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
        text=True, encoding="utf-8",
    ).strip()
    result = {
        "schema": 1,
        "result": "PASS",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "ordinary": {"speed": 1.5, "clips": 4, "bones": 50},
        "kick": {"speed": 1.5, "clips": 1, "bones": 50,
                 "input": "B"},
        "resourceSha256": resources,
        "compiledClasses": [str(path) for path in classes],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "[PASS] Desktop live combat is current: "
        f"commit={commit} ordinary=1.5x/4/50 kick=1.5x/1/50 key=B"
    )


if __name__ == "__main__":
    main()
