#!/usr/bin/env python3
"""Update only live combat receipts without touching unrelated dirty actions."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
LOCK = REPO / "src/main/resources/assets/projectseele/eva/eva_approved_actions.json"
ROLLBACK = REPO / "tools/eva_pre_mocap_gameplay_rollback.json"
ANIMATION_PATH = (
    "src/main/resources/assets/projectseele/animations/"
    "eva_unit01.animation.json"
)
ORDINARY_PATH = (
    "src/main/resources/assets/projectseele/motion/"
    "eva_ordinary_attack_group_c_v1.json"
)
KICK_PATH = (
    "src/main/resources/assets/projectseele/motion/"
    "eva_kick_side_left_v1.json"
)
KNIFE_PATH = (
    "src/main/resources/assets/projectseele/motion/"
    "eva_knife_attacks_phase_m_v1.json"
)


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def json_at(revision: str, path: str) -> dict:
    payload = subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=REPO
    )
    return json.loads(payload.decode("utf-8"))


def live_entry(*, action: str, keys: list[str], baseline: dict,
               observed: dict, resource: dict, resource_path: str,
               selected_group: str, selected_at: str,
               fallback_policy: str) -> dict:
    if action == "kick_attack":
        baseline_payload = {"runtimeMotion": None}
        observed_payload = {"runtimeMotion": resource}
    else:
        baseline_payload = {
            "geckoFallback": {key: baseline[key] for key in keys},
            "runtimeMotion": None,
        }
        observed_payload = {
            "geckoFallback": {key: observed[key] for key in keys},
            "runtimeMotion": resource,
        }
    baseline_hash = canonical_sha256(baseline_payload)
    observed_hash = canonical_sha256(observed_payload)
    return {
        "status": "HUMAN_SELECTED_LIVE_CANDIDATE",
        "animationKeys": keys,
        "baselineSemanticSha256": baseline_hash,
        "observedSemanticSha256": observed_hash,
        "approvedSemanticSha256": None,
        "candidateReason": "RUNTIME_GAME_REVIEW_REQUIRED",
        "approvedBy": None,
        "approvedAt": None,
        "humanReviewRequired": True,
        "runtimeMotionResource": resource_path,
        "runtimeMotionSemanticSha256": canonical_sha256(resource),
        "selectedGroup": selected_group,
        "playbackSpeedMultiplier": resource.get(
            "gameplay_contract", {}).get("playback_speed_multiplier", 1.0),
        "geckoFallbackPolicy": fallback_policy,
        "selectedSemanticSha256": observed_hash,
        "selectedBy": "project_owner",
        "selectedAt": selected_at,
        "runtimeGameReviewRequired": True,
    }


def main() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    rollback = json.loads(ROLLBACK.read_text(encoding="utf-8"))
    baseline = json_at(
        rollback["source_commit"], ANIMATION_PATH)["animations"]
    # Use committed Gecko fallbacks deliberately. The working tree may carry
    # a separate uncommitted land candidate that this combat-only update must
    # neither approve nor hash into the committed combat receipt.
    observed = json_at("HEAD", ANIMATION_PATH)["animations"]
    ordinary = json.loads((REPO / ORDINARY_PATH).read_text(encoding="utf-8"))
    kick = json.loads((REPO / KICK_PATH).read_text(encoding="utf-8"))
    knife = json.loads((REPO / KNIFE_PATH).read_text(encoding="utf-8"))
    ordinary_keys = [
        "animation.eva_unit01.melee",
        "animation.eva_unit01.melee_left",
    ]
    ordinary_entry = live_entry(
        action="unarmed_attack", keys=ordinary_keys,
        baseline=baseline, observed=observed, resource=ordinary,
        resource_path=ORDINARY_PATH, selected_group="ordinary_group_c",
        selected_at="2026-09-01",
        fallback_policy="standing_fists_only_uses_runtime",
    )
    kick_entry = live_entry(
        action="kick_attack", keys=[], baseline=baseline,
        observed=observed, resource=kick, resource_path=KICK_PATH,
        selected_group="K1_SIDE_LEFT", selected_at="2026-09-02",
        fallback_policy="standing_fists_key_b_uses_runtime",
    )
    knife_forward_entry = live_entry(
        action="knife_attack_forward",
        keys=["animation.eva_unit01.knife"], baseline=baseline,
        observed=observed, resource=knife, resource_path=KNIFE_PATH,
        selected_group="eva_locked_knife_stab_twist_forward",
        selected_at="2026-09-01",
        fallback_policy="standing_knife_left_click_uses_runtime",
    )
    knife_reverse_entry = live_entry(
        action="knife_attack_reverse",
        keys=["animation.eva_unit01.knife_heavy"], baseline=baseline,
        observed=observed, resource=knife, resource_path=KNIFE_PATH,
        selected_group="eva_short_knife_stab_twist_reverse",
        selected_at="2026-09-01",
        fallback_policy="standing_knife_right_click_uses_runtime",
    )
    actions = {}
    for name, entry in lock["actions"].items():
        if name == "unarmed_attack":
            actions[name] = ordinary_entry
            actions["kick_attack"] = kick_entry
        elif name != "kick_attack":
            actions[name] = entry
    actions["knife_attack_forward"] = knife_forward_entry
    actions["knife_attack_reverse"] = knife_reverse_entry
    lock["actions"] = actions
    LOCK.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "actions": len(actions),
        "ordinarySpeed": ordinary_entry["playbackSpeedMultiplier"],
        "kickSpeed": kick_entry["playbackSpeedMultiplier"],
        "knifeSpeed": knife_forward_entry["playbackSpeedMultiplier"],
        "dirtyAnimationIgnored": ANIMATION_PATH,
        "output": str(LOCK),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
