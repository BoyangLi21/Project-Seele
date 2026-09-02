#!/usr/bin/env python3
"""Build the current deterministic EVA pose-authority contracts.

The historical filename is retained because Phase A established the contract
files.  It now emits the Phase-B enforcing post-Gecko authority.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
OUTPUT = REPO / "src/main/resources/assets/projectseele/eva"
ANIMATION = REPO / (
    "src/main/resources/assets/projectseele/animations/"
    "eva_unit01.animation.json")
ANIMATION_REPO_PATH = (
    "src/main/resources/assets/projectseele/animations/"
    "eva_unit01.animation.json")
ROLLBACK = REPO / "tools/eva_pre_mocap_gameplay_rollback.json"
ACTION_LOCKS = OUTPUT / "eva_approved_actions.json"
LIVE_ORDINARY = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_ordinary_attack_group_c_v1.json")
LIVE_ORDINARY_REPO_PATH = (
    "src/main/resources/assets/projectseele/motion/"
    "eva_ordinary_attack_group_c_v1.json")
LIVE_KICK = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_kick_side_left_v1.json")
LIVE_KICK_REPO_PATH = (
    "src/main/resources/assets/projectseele/motion/"
    "eva_kick_side_left_v1.json")
VARIANTS = ("eva_unit00", "eva_unit01", "eva_unit02")
RIG_VERSION = "eva_tiger_canonical_r01"
POSE_GRAPH_VERSION = "eva_pose_graph_enforced_r03"
MIGRATION_BASELINE_COMMIT = "cee87f58ab6118f49e8baf80e324e96d0f446cbb"


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_at_commit(commit: str, repo_path: str) -> dict:
    result = subprocess.run(
        ["git", "show", f"{commit}:{repo_path}"], cwd=REPO,
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return json.loads(result.stdout.decode("utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def category(name: str) -> str:
    if name in {"root", "torso_lower", "leg_l", "shin_l", "ankle_l",
                "foot_l", "leg_r", "shin_r", "ankle_r", "foot_r"}:
        return "LOWER_BODY"
    if name in {"torso_upper", "neck", "head", "clavicle_l", "arm_l",
                "forearm_l", "wrist_l", "hand_l", "clavicle_r", "arm_r",
                "forearm_r", "wrist_r", "hand_r"}:
        return "UPPER_BODY"
    if name == "aim_pitch":
        return "AIM_ADAPTER"
    if name.startswith("finger_"):
        return "GRIP"
    if name in {"knife", "cannon", "lance", "n2"}:
        return "WEAPON_SOCKET"
    return "RIGID_ATTACHMENT"


def default_owner(name: str) -> str:
    if name == "aim_pitch":
        return "POSE_GRAPH_WEAPON_AIM"
    return "GECKO_COMPOSITE"


def build_rig_schema(geometries: dict[str, dict]) -> dict:
    rows = {
        variant: geometry["minecraft:geometry"][0]["bones"]
        for variant, geometry in geometries.items()
    }
    names = [row["name"] for row in rows["eva_unit01"]]
    parents = {row["name"]: row.get("parent")
               for row in rows["eva_unit01"]}
    order_matches = {}
    variant_extras = {}
    canonical_names = set(names)
    for variant, bones in rows.items():
        variant_names = [row["name"] for row in bones]
        missing = canonical_names - set(variant_names)
        if missing:
            raise RuntimeError(
                f"{variant} misses canonical bones: {sorted(missing)}")
        variant_extras[variant] = sorted(set(variant_names) - canonical_names)
        order_matches[variant] = [
            name for name in variant_names if name in canonical_names
        ] == names
        variant_parents = {row["name"]: row.get("parent") for row in bones}
        if any(variant_parents.get(name) != parent
               for name, parent in parents.items()):
            raise RuntimeError(f"{variant} canonical parent map differs")
    unit01 = {row["name"]: row for row in rows["eva_unit01"]}
    bones = []
    for name in names:
        row = unit01[name]
        bones.append({
            "name": name,
            "parent": row.get("parent"),
            "pivot": row.get("pivot", [0.0, 0.0, 0.0]),
            "bindRotationDegrees": row.get("rotation", [0.0, 0.0, 0.0]),
            "category": category(name),
            "defaultOwner": default_owner(name),
        })
    return {
        "schema": 1,
        "rigVersion": RIG_VERSION,
        "status": "CANONICAL_POST_GECKO_AUTHORITY_CONTRACT",
        "coordinateSystem": {
            "source": "Bedrock model space, Y up, runtime reflected X",
            "rotationOrder": "XYZ degrees",
            "matrixStorage": "JOML column-major float[16]",
        },
        "worldTransformAuthority": "SERVER_EVA_ENTITY",
        "canonicalBoneOrderMustMatch": True,
        "variantCanonicalBoneOrderMatches": order_matches,
        "variantExtraBones": variant_extras,
        "boneCount": len(bones),
        "bones": bones,
        "variantGeometrySemanticSha256": {
            variant: canonical_sha256(geometry)
            for variant, geometry in geometries.items()
        },
    }


def build_pose_authority(rig: dict) -> dict:
    masks: dict[str, list[str]] = {}
    for bone in rig["bones"]:
        masks.setdefault(bone["category"], []).append(bone["name"])
    return {
        "schema": 1,
        "poseGraphVersion": POSE_GRAPH_VERSION,
        "rigVersion": RIG_VERSION,
        "phase": "B",
        "mode": "ENFORCE_POST_GECKO_SINGLE_COMMIT",
        "migrationBaselineCommit": MIGRATION_BASELINE_COMMIT,
        "rules": [
            "one bone has exactly one absolute-rotation owner per frame",
            "IK and limits are final constraints inside the owning pose node",
            "render layers may hide geometry but may not claim body rotation",
            "official captures reject Motion Lab preview/demo pose authority",
            "human-selected live-test actions may own their declared bone mask",
            "Gecko controllers are one upstream composite at the Phase-B boundary",
            "all post-Gecko writes are orchestrated by EvaPoseGraph.commit",
        ],
        "upstreamBoundary": {
            "owner": "GECKO_COMPOSITE",
            "knownControllers": ["base", "arms", "strike"],
            "controllerInternalProvenance": "NOT_SEPARATED_IN_PHASE_B",
        },
        "commitOrder": [
            "GECKO_COMPOSITE",
            "MOTION_ENGINE_PREVIEW",
            "MOTION_ENGINE_LIVE_ACTION",
            "POSE_GRAPH_WEAPON_AIM",
            "POSE_GRAPH_PILOT_AIM",
        ],
        "ownedChannels": ["rotation", "position", "scale"],
        "ownerPriority": [
            "MOTION_ENGINE_LIVE_ACTION",
            "MOTION_ENGINE_PREVIEW",
            "POSE_GRAPH_PILOT_AIM",
            "POSE_GRAPH_WEAPON_AIM",
            "GECKO_COMPOSITE",
        ],
        "boneMasks": masks,
        "lowLevelWriters": {
            "EvaMotionEngineV2": {
                "owners": [
                    "MOTION_ENGINE_PREVIEW",
                    "MOTION_ENGINE_LIVE_ACTION",
                ],
                "invokedOnlyBy": "EvaPoseGraph.commit",
                "reportsChannelsSeparately": True,
                "officialCaptureAllowedOwners": [
                    "MOTION_ENGINE_LIVE_ACTION",
                ],
            },
            "EvaPoseGraph.weaponAim": {
                "owner": "POSE_GRAPH_WEAPON_AIM",
                "bones": ["aim_pitch"],
            },
            "EvaPoseGraph.pilotAim": {
                "owner": "POSE_GRAPH_PILOT_AIM",
                "bones": ["head"],
            },
        },
        "rendererPolicy": {
            "may": ["invoke EvaPoseGraph.commit", "change visibility"],
            "mayNot": ["write bone transforms", "invoke MotionEngine directly"],
        },
        "worldAuthority": {
            "owner": "SERVER_EVA_ENTITY",
            "fields": ["position", "yaw", "velocity", "AABB"],
            "renderMay": ["interpolate"],
            "renderMayNot": ["write entity transform"],
        },
        "officialCapture": {
            "motionLabPhysicsPreviewMustBe": 0,
            "visualPoseMustBe": 0,
            "allowedMotionOwner": "MOTION_ENGINE_LIVE_ACTION",
            "recordFinalPostControllerMatrices": True,
            "finalOwnerConflictsMustBeEmptyFor": [
                "rotation", "position", "scale"],
            "resultVocabulary": ["FAIL", "ELIGIBLE_FOR_HUMAN_REVIEW"],
            "forbiddenResult": "VISUALLY_APPROVED",
        },
    }


def build_action_lock(animation: dict, baseline_animation: dict,
                      rollback: dict, live_ordinary: dict, live_kick: dict,
                      existing: dict | None = None) -> dict:
    animations = animation["animations"]
    baseline_animations = baseline_animation["animations"]
    groups = {
        "idle": ["idle"],
        "walk": ["walk"],
        "run": ["run"],
        "jump_landing": ["takeoff", "jump", "land"],
        "unarmed_attack": ["melee", "melee_left"],
        "kick_attack": [],
        "unarmed_smash": ["smash"],
        "progressive_knife": ["knife_ready", "knife", "knife_heavy"],
        "crouch": ["crouch", "crouch_walk"],
        "prone_crawl": ["prone", "crawl"],
    }
    actions = {}
    existing_actions = (existing or {}).get("actions", {})
    for action, suffixes in groups.items():
        keys = [f"animation.eva_unit01.{suffix}" for suffix in suffixes]
        baseline_gecko = {key: baseline_animations[key] for key in keys}
        observed_gecko = {key: animations[key] for key in keys}
        if action == "unarmed_attack":
            baseline_payload = {
                "geckoFallback": baseline_gecko,
                "runtimeMotion": None,
            }
            observed_payload = {
                "geckoFallback": observed_gecko,
                "runtimeMotion": live_ordinary,
            }
        elif action == "kick_attack":
            baseline_payload = {"runtimeMotion": None}
            observed_payload = {"runtimeMotion": live_kick}
        else:
            baseline_payload = baseline_gecko
            observed_payload = observed_gecko
        baseline_hash = canonical_sha256(baseline_payload)
        observed_hash = canonical_sha256(observed_payload)
        matches = baseline_hash == observed_hash
        previous = existing_actions.get(action, {})
        live_resource = (live_ordinary if action == "unarmed_attack"
                         else live_kick if action == "kick_attack" else None)
        expected_selection = (
            "ordinary_group_c" if action == "unarmed_attack"
            else "K1_SIDE_LEFT" if action == "kick_attack" else None)
        live_receipt = live_resource is not None and (
            live_resource.get("human_review", {}).get("status")
            == "HUMAN_SELECTED_FOR_LIVE_GAMEPLAY"
            and live_resource.get("human_review", {}).get("selected")
            == expected_selection
            and live_resource.get("gameplay_contract", {}).get(
                "playback_speed_multiplier") == 1.5
        )
        approval_matches = not live_receipt and (
            previous.get("status") == "VISUALLY_APPROVED"
            and previous.get("approvedSemanticSha256") == observed_hash
            and previous.get("approvedBy")
        )
        actions[action] = {
            "status": ("HUMAN_SELECTED_LIVE_CANDIDATE" if live_receipt else
                       "VISUALLY_APPROVED" if approval_matches else
                       "FROZEN_BASELINE_NOT_VISUALLY_APPROVED" if matches else
                       "CANDIDATE_HASH_CHANGED"),
            "animationKeys": keys,
            "baselineSemanticSha256": baseline_hash,
            "observedSemanticSha256": observed_hash,
            "approvedSemanticSha256": (
                observed_hash if approval_matches else None),
            "candidateReason": (
                "RUNTIME_GAME_REVIEW_REQUIRED" if live_receipt
                else None if approval_matches or matches
                else "ANIMATION_HASH_CHANGED"),
            "approvedBy": (previous.get("approvedBy") if approval_matches
                else None),
            "approvedAt": (previous.get("approvedAt") if approval_matches
                else None),
            "humanReviewRequired": not approval_matches,
        }
        if action in {"unarmed_attack", "kick_attack"}:
            resource_path = (LIVE_ORDINARY_REPO_PATH
                             if action == "unarmed_attack"
                             else LIVE_KICK_REPO_PATH)
            actions[action].update({
                "runtimeMotionResource": resource_path,
                "runtimeMotionSemanticSha256": canonical_sha256(
                    live_resource),
                "selectedGroup": expected_selection,
                "playbackSpeedMultiplier": 1.5,
                "geckoFallbackPolicy": (
                    "standing_fists_only_uses_runtime"
                    if action == "unarmed_attack"
                    else "standing_fists_key_b_uses_runtime"),
                "selectedSemanticSha256": observed_hash,
                "selectedBy": "project_owner",
                "selectedAt": live_resource["human_review"]["date"],
                "runtimeGameReviewRequired": True,
            })
    return {
        "schema": 1,
        "rigVersion": RIG_VERSION,
        "poseGraphVersion": POSE_GRAPH_VERSION,
        "baselineCommit": rollback["source_commit"],
        "baselineDecision": "user_requested_pre_mocap_rollback",
        "policy": {
            "generatorMayOverwriteFrozenAction": False,
            "hashChangeReturnsStatusTo": "CANDIDATE",
            "automaticApprovalAllowed": False,
        },
        "rollbackPatchSemanticSha256": canonical_sha256(rollback),
        "actions": actions,
    }


def main() -> None:
    geometries = {
        variant: read_json(RUNTIME / "geo" / f"{variant}.geo.json")
        for variant in VARIANTS
    }
    source_animation = read_json(ANIMATION)
    runtime_animation = read_json(
        RUNTIME / "animations/eva_unit01.animation.json")
    if canonical_sha256(source_animation) != canonical_sha256(
            runtime_animation):
        raise RuntimeError(
            "active eva_real_model animation differs from source baseline")
    rig = build_rig_schema(geometries)
    authority = build_pose_authority(rig)
    rollback = read_json(ROLLBACK)
    baseline_animation = read_json_at_commit(
        rollback["source_commit"], ANIMATION_REPO_PATH)
    existing_actions = read_json(ACTION_LOCKS) if ACTION_LOCKS.is_file() else None
    live_ordinary = read_json(LIVE_ORDINARY)
    live_kick = read_json(LIVE_KICK)
    actions = build_action_lock(
        source_animation, baseline_animation, rollback, live_ordinary,
        live_kick, existing_actions)
    write_json(OUTPUT / "eva_rig_schema.json", rig)
    write_json(OUTPUT / "eva_pose_authority_contract.json", authority)
    write_json(OUTPUT / "eva_approved_actions.json", actions)
    print(json.dumps({
        "phase": "B",
        "rigVersion": RIG_VERSION,
        "poseGraphVersion": POSE_GRAPH_VERSION,
        "mode": authority["mode"],
        "bones": rig["boneCount"],
        "actionLocks": len(actions["actions"]),
        "output": str(OUTPUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
