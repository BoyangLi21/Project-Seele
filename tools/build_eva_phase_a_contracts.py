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
VARIANTS = ("eva_unit00", "eva_unit01", "eva_unit02")
RIG_VERSION = "eva_tiger_canonical_r01"
POSE_GRAPH_VERSION = "eva_pose_graph_enforced_r02"
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
            "POSE_GRAPH_WEAPON_AIM",
            "POSE_GRAPH_PILOT_AIM",
        ],
        "ownedChannels": ["rotation", "position", "scale"],
        "ownerPriority": [
            "POSE_GRAPH_PILOT_AIM",
            "POSE_GRAPH_WEAPON_AIM",
            "MOTION_ENGINE_PREVIEW",
            "GECKO_COMPOSITE",
        ],
        "boneMasks": masks,
        "lowLevelWriters": {
            "EvaMotionEngineV2": {
                "owner": "MOTION_ENGINE_PREVIEW",
                "invokedOnlyBy": "EvaPoseGraph.commit",
                "reportsChannelsSeparately": True,
                "officialCaptureAllowed": False,
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
            "recordFinalPostControllerMatrices": True,
            "finalOwnerConflictsMustBeEmptyFor": [
                "rotation", "position", "scale"],
            "resultVocabulary": ["FAIL", "ELIGIBLE_FOR_HUMAN_REVIEW"],
            "forbiddenResult": "VISUALLY_APPROVED",
        },
    }


def build_action_lock(animation: dict, baseline_animation: dict,
                      rollback: dict) -> dict:
    animations = animation["animations"]
    baseline_animations = baseline_animation["animations"]
    groups = {
        "idle": ["idle"],
        "walk": ["walk"],
        "run": ["run"],
        "jump_landing": ["takeoff", "jump", "land"],
        "unarmed_attack": ["melee", "melee_left", "smash"],
        "progressive_knife": ["knife_ready", "knife", "knife_heavy"],
        "crouch": ["crouch", "crouch_walk"],
        "prone_crawl": ["prone", "crawl"],
    }
    actions = {}
    for action, suffixes in groups.items():
        keys = [f"animation.eva_unit01.{suffix}" for suffix in suffixes]
        baseline_payload = {key: baseline_animations[key] for key in keys}
        observed_payload = {key: animations[key] for key in keys}
        baseline_hash = canonical_sha256(baseline_payload)
        observed_hash = canonical_sha256(observed_payload)
        matches = baseline_hash == observed_hash
        actions[action] = {
            "status": ("FROZEN_BASELINE_NOT_VISUALLY_APPROVED" if matches
                       else "CANDIDATE_HASH_CHANGED"),
            "animationKeys": keys,
            "baselineSemanticSha256": baseline_hash,
            "observedSemanticSha256": observed_hash,
            "candidateReason": None if matches else "ANIMATION_HASH_CHANGED",
            "approvedBy": None,
            "humanReviewRequired": True,
        }
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
    actions = build_action_lock(
        source_animation, baseline_animation, rollback)
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
