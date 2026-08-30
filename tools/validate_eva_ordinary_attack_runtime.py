#!/usr/bin/env python3
"""Fail closed unless rejected fist mocap stays isolated from live combat."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MOTION = ROOT / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_ordinary_attack_v1.json"
)
ENGINE = ROOT / (
    "src/main/java/com/projectseele/client/render/EvaMotionEngineV2.java"
)
ENTITY = ROOT / (
    "src/main/java/com/projectseele/entity/EvaUnit01Entity.java"
)
CLIPS = {
    "ordinary_attack_jab_left",
    "ordinary_attack_cross_right",
    "ordinary_attack_hook_right",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("EVA ordinary attack runtime invalid: " + message)


def main() -> None:
    motion = json.loads(MOTION.read_text(encoding="utf-8"))
    require(motion.get("schema") == 2, "motion schema is not 2")
    require(motion.get("preview_only") is False,
            "runtime resource is still marked preview-only")
    require(motion.get("authority") ==
            "client_visual_mocap_server_combat_remains_authoritative",
            "motion authority contract drifted")
    require(set(motion.get("clips", {})) == CLIPS,
            "expected exactly the three promoted attack clips")
    require(len(motion.get("bones", [])) == 50,
            "expected 50 runtime bones")
    frames = sum(len(clip.get("frames", []))
                 for clip in motion["clips"].values())
    require(frames == 243, "expected 243 total frames")
    require(all(clip.get("role") == "ordinary_attack_runtime_visual"
                for clip in motion["clips"].values()),
            "a clip is not marked as a runtime visual")

    engine = ENGINE.read_text(encoding="utf-8")
    entity = ENTITY.read_text(encoding="utf-8")
    for token in (
            '"motion/eva_ordinary_attack_v1.json"',
            "boolean gameplayOrdinaryAttack = false;",
            'case 0 -> "ordinary_attack_jab_left"',
            'case 1 -> "ordinary_attack_cross_right"',
            'default -> "ordinary_attack_hook_right"'):
        require(token in engine, f"engine wiring missing {token}")
    for token in (
            "DATA_ORDINARY_ATTACK_STAGE",
            "MELEE_INPUT_BUFFER_TICKS = 16",
            'this.triggerAnim("strike", animation)'):
        require(token in entity, f"entity wiring missing {token}")
    require('"fist_heavy"' not in entity,
            "post-mocap replacement heavy attack is still registered")
    require("this.ordinaryAttackCycle = (stage + 1) % 3" not in entity,
            "rejected three-stage cycle is still wired to live fists")
    require("MELEE_COOLDOWN_TICKS = 12" in entity,
            "server melee cooldown changed")
    old = MOTION.with_name("eva_ordinary_attack_review_v1.json")
    require(not old.exists(), "superseded preview resource still exists")
    print("EVA ordinary attack quarantine validation passed: "
          "clips=3 bones=50 frames=243 cooldown=12t gameplay=false")


if __name__ == "__main__":
    main()
