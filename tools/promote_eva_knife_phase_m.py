#!/usr/bin/env python3
"""Promote the two project-owner-approved Phase-M knife clips to live play."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_mocap_combat_phase_m_review_v1.json"
)
DEFAULT_OUTPUT = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_knife_attacks_phase_m_v1.json"
)
CLIPS = (
    ("eva_locked_knife_stab_twist_forward", "left_click", 60.0, 12),
    ("eva_short_knife_stab_twist_reverse", "right_click", 80.0, 60),
)


def compact(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    if source.get("schema") != 2 or source.get("sample_rate") != 60.0:
        raise RuntimeError("Phase-M source must be schema 2 at 60 Hz")
    review = source.get("human_review", {})
    decisions = review.get("decisions", {})
    expected = {
        CLIPS[0][0]: "APPROVED_LOCKED_LEFT_CLICK",
        CLIPS[1][0]: "APPROVED_LOCKED_RIGHT_CLICK",
    }
    if any(decisions.get(name) != decision
           for name, decision in expected.items()):
        raise RuntimeError("Phase-M knife approvals are missing")

    clips = {}
    gameplay = []
    locked = review.get("locked_frame_sha256", {})
    for name, input_name, damage, cooldown in CLIPS:
        clip = copy.deepcopy(source["clips"][name])
        frames = clip["frames"]
        clip["role"] = "live_project_owner_approved_knife_attack"
        clip["frame_sha256"] = hashlib.sha256(compact(frames)).hexdigest()
        clip["review_locked_frame_sha256"] = locked[name]
        clips[name] = clip
        gameplay.append({
            "input": input_name,
            "clip": name,
            "frames": len(frames),
            "duration_seconds": round((len(frames) - 1) / 60.0, 7),
            "damage": damage,
            "legacy_cooldown_ticks": cooldown,
        })

    output = {
        "schema": 2,
        "coordinate_system": source["coordinate_system"],
        "quaternion_order": source["quaternion_order"],
        "sample_rate": source["sample_rate"],
        "preview_only": False,
        "live_gameplay_replacement": True,
        "authority": "project_owner_approved_phase_m_knife_live_runtime",
        "human_review": {
            "status": "HUMAN_APPROVED_FOR_LIVE_GAMEPLAY",
            "bindings": review["knife_bindings"],
            "locked_frame_sha256": locked,
            "date": "2026-09-01",
        },
        "root_authority": "SERVER_ENTITY_XZ_YAW_CAPTURED_ROOT_Y_ONLY",
        "sources": source["sources"],
        "bones": source["bones"],
        "gameplay_contract": {
            "playback_speed_multiplier": 1.0,
            "attacks": gameplay,
            "damage_authority": "existing_server_melee_resolution",
            "world_root_authority": "server_entity",
        },
        "knife_base_transform": source["knife_base_transform"],
        "clips": clips,
        "root_contact_stabilization": source.get(
            "root_contact_stabilization"),
        "exact_grounding": source.get("exact_grounding"),
        "provenance": {
            "review_resource": str(args.source.relative_to(REPO)).replace(
                "\\", "/"),
            "review_resource_sha256": hashlib.sha256(
                args.source.read_bytes()).hexdigest(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        "promoted Phase-M knives: clips=2 bones="
        f"{len(source['bones'])} frames={sum(len(c['frames']) for c in clips.values())}"
    )


if __name__ == "__main__":
    main()
