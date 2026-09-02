#!/usr/bin/env python3
"""Validate the Phase-A foundation under the current Phase-B authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RESOURCE = REPO / "src/main/resources/assets/projectseele/eva"
RUNTIME = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
RIG = RESOURCE / "eva_rig_schema.json"
AUTHORITY = RESOURCE / "eva_pose_authority_contract.json"
ACTIONS = RESOURCE / "eva_approved_actions.json"
ANIMATION = REPO / (
    "src/main/resources/assets/projectseele/animations/"
    "eva_unit01.animation.json")
ANIMATION_REPO_PATH = (
    "src/main/resources/assets/projectseele/animations/"
    "eva_unit01.animation.json")
ROLLBACK = REPO / "tools/eva_pre_mocap_gameplay_rollback.json"
LIVE_ORDINARY = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_ordinary_attack_group_c_v1.json")
LIVE_KICK = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_kick_side_left_v1.json")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_at_commit(commit: str, repo_path: str) -> dict:
    result = subprocess.run(
        ["git", "show", f"{commit}:{repo_path}"], cwd=REPO,
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return json.loads(result.stdout.decode("utf-8"))


def read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("EVA Phase-A contract invalid: " + message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--committed-animation", action="store_true",
        help="validate combat locks against HEAD while preserving dirty actions",
    )
    args = parser.parse_args()
    rig = read_json(RIG)
    authority = read_json(AUTHORITY)
    actions = read_json(ACTIONS)
    animation = (
        read_json_at_commit("HEAD", ANIMATION_REPO_PATH)["animations"]
        if args.committed_animation
        else read_json(ANIMATION)["animations"]
    )
    rollback = read_json(ROLLBACK)
    live_ordinary = read_json(LIVE_ORDINARY)
    live_kick = read_json(LIVE_KICK)
    baseline_animation = read_json_at_commit(
        rollback["source_commit"], ANIMATION_REPO_PATH)["animations"]

    require(rig.get("schema") == 1, "rig schema is not 1")
    require(rig.get("rigVersion") == "eva_tiger_canonical_r01",
            "unexpected rig version")
    bones = rig.get("bones", [])
    require(rig.get("boneCount") == 70 == len(bones),
            "canonical rig must contain exactly 70 Unit-01 bones")
    names = [bone["name"] for bone in bones]
    require(len(names) == len(set(names)), "duplicate canonical bone")
    by_name = {bone["name"]: bone for bone in bones}
    require(names[0] == "root" and by_name["root"].get("parent") is None,
            "root hierarchy is invalid")
    for bone in bones[1:]:
        require(bone.get("parent") in by_name,
                f"unknown parent for {bone['name']}")
        seen = {bone["name"]}
        parent = bone.get("parent")
        while parent is not None:
            require(parent not in seen,
                    f"cycle in canonical hierarchy at {bone['name']}")
            seen.add(parent)
            parent = by_name[parent].get("parent")
    require(rig["variantExtraBones"]["eva_unit00"] == ["shield"],
            "Unit-00 shield must remain an explicit variant extra")
    require(rig["canonicalBoneOrderMustMatch"]
            and all(rig["variantCanonicalBoneOrderMatches"].values()),
            "variant canonical bone subsequences must match Unit-01")
    require(all(bone["defaultOwner"] ==
                ("POSE_GRAPH_WEAPON_AIM" if bone["name"] == "aim_pitch"
                 else "GECKO_COMPOSITE") for bone in bones),
            "canonical default owners do not match Phase-B boundary")
    canonical_names = set(names)
    if not args.committed_animation:
        for variant in ("eva_unit00", "eva_unit01", "eva_unit02"):
            geometry = read_json(RUNTIME / "geo" / f"{variant}.geo.json")
            require(rig["variantGeometrySemanticSha256"][variant] ==
                    canonical_sha256(geometry),
                    f"{variant} geometry hash differs from canonical rig")
            rows = geometry["minecraft:geometry"][0]["bones"]
            variant_names = [row["name"] for row in rows]
            require([name for name in variant_names
                     if name in canonical_names] == names,
                    f"{variant} canonical bone order differs")
            require(sorted(set(variant_names) - canonical_names) ==
                    rig["variantExtraBones"][variant],
                    f"{variant} extra bone declaration differs")
            variant_parents = {row["name"]: row.get("parent") for row in rows}
            require(all(variant_parents[name] == by_name[name].get("parent")
                        for name in names),
                    f"{variant} canonical parent map differs")

    if not args.committed_animation:
        runtime_animation = read_json(
            RUNTIME / "animations/eva_unit01.animation.json")
        require(canonical_sha256(runtime_animation) ==
                canonical_sha256(read_json(ANIMATION)),
                "active eva_real_model animation differs from source baseline")

    require(authority.get("schema") == 1,
            "authority schema is not 1")
    require(authority.get("rigVersion") == rig["rigVersion"],
            "authority rig version differs")
    require(authority.get("poseGraphVersion") ==
            "eva_pose_graph_enforced_r03", "unexpected pose graph version")
    require(authority.get("phase") == "B"
            and authority.get("mode") ==
            "ENFORCE_POST_GECKO_SINGLE_COMMIT",
            "Phase-B pose graph is not the enforcing single commit point")
    require(authority.get("migrationBaselineCommit") ==
            "cee87f58ab6118f49e8baf80e324e96d0f446cbb",
            "Phase-B migration baseline differs")
    require(authority.get("commitOrder") == [
        "GECKO_COMPOSITE", "MOTION_ENGINE_PREVIEW",
        "MOTION_ENGINE_LIVE_ACTION",
        "POSE_GRAPH_WEAPON_AIM", "POSE_GRAPH_PILOT_AIM"],
        "Phase-B commit order differs")
    require(authority.get("ownedChannels") ==
            ["rotation", "position", "scale"],
            "Phase-B transform-channel ownership differs")
    masks = authority.get("boneMasks", {})
    masked = [name for values in masks.values() for name in values]
    require(len(masked) == len(set(masked)) == 70,
            "bone masks must partition the canonical rig exactly once")
    require(set(masked) == set(names), "bone masks miss canonical bones")
    capture = authority["officialCapture"]
    require(capture["motionLabPhysicsPreviewMustBe"] == 0
            and capture["visualPoseMustBe"] == 0,
            "official capture must reject preview authority")
    require(capture["allowedMotionOwner"] ==
            "MOTION_ENGINE_LIVE_ACTION",
            "official capture does not declare the approved live owner")
    require(capture["finalOwnerConflictsMustBeEmptyFor"] ==
            ["rotation", "position", "scale"],
            "official capture permits final owner conflicts")
    require(capture["resultVocabulary"] ==
            ["FAIL", "ELIGIBLE_FOR_HUMAN_REVIEW"],
            "automatic result vocabulary drifted")
    require(capture["forbiddenResult"] == "VISUALLY_APPROVED",
            "visual approval must remain human-only")

    require(actions.get("schema") == 1, "action lock schema is not 1")
    require(actions["rigVersion"] == rig["rigVersion"]
            and actions["poseGraphVersion"] ==
            authority["poseGraphVersion"], "action lock versions differ")
    require(actions["baselineCommit"] == rollback["source_commit"],
            "action baseline commit differs from rollback")
    require(not actions["policy"]["generatorMayOverwriteFrozenAction"]
            and not actions["policy"]["automaticApprovalAllowed"],
            "frozen actions are not fail-closed")
    require(actions["rollbackPatchSemanticSha256"] ==
            canonical_sha256(rollback), "rollback patch hash differs")
    candidate_actions = []
    approved_actions = []
    selected_live_actions = []
    for action, contract in actions["actions"].items():
        baseline_gecko = {
            key: baseline_animation[key]
            for key in contract["animationKeys"]
        }
        observed_gecko = {
            key: animation[key] for key in contract["animationKeys"]
        }
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
        require(contract["baselineSemanticSha256"] == baseline_hash,
                f"{action} baseline hash is not anchored to rollback")
        require(contract["observedSemanticSha256"] == observed_hash,
                f"{action} observed hash differs from live animation")
        approved = contract["status"] == "VISUALLY_APPROVED"
        selected_live = (
            contract["status"] == "HUMAN_SELECTED_LIVE_CANDIDATE")
        if approved:
            require(contract["approvedSemanticSha256"] == observed_hash
                    and contract["approvedBy"] == "project_owner"
                    and contract["approvedAt"] == "2026-08-31"
                    and not contract["humanReviewRequired"]
                    and contract["candidateReason"] is None,
                    f"{action} visual approval receipt is incomplete")
            approved_actions.append(action)
        else:
            require(contract["approvedSemanticSha256"] is None
                    and contract["approvedBy"] is None
                    and contract["approvedAt"] is None
                    and contract["humanReviewRequired"],
                    f"{action} bypasses human review")
        if selected_live:
            selected_resource = (
                live_ordinary if action == "unarmed_attack"
                else live_kick if action == "kick_attack" else None)
            expected_path = (
                "src/main/resources/assets/projectseele/motion/"
                "eva_ordinary_attack_group_c_v1.json"
                if action == "unarmed_attack"
                else "src/main/resources/assets/projectseele/motion/"
                "eva_kick_side_left_v1.json")
            expected_group = (
                "ordinary_group_c" if action == "unarmed_attack"
                else "K1_SIDE_LEFT")
            expected_date = (
                "2026-09-01" if action == "unarmed_attack"
                else "2026-09-02")
            require(action in {"unarmed_attack", "kick_attack"}
                    and contract["runtimeMotionResource"] == expected_path
                    and contract["runtimeMotionSemanticSha256"] ==
                    canonical_sha256(selected_resource)
                    and contract["selectedGroup"] == expected_group
                    and contract["playbackSpeedMultiplier"] == 1.5
                    and contract["selectedSemanticSha256"] == observed_hash
                    and contract["selectedBy"] == "project_owner"
                    and contract["selectedAt"] == expected_date
                    and contract["runtimeGameReviewRequired"]
                    and contract["candidateReason"] ==
                    "RUNTIME_GAME_REVIEW_REQUIRED",
                    "ordinary attack live-selection receipt is incomplete")
            selected_live_actions.append(action)
        if observed_hash == baseline_hash:
            require((approved or contract["status"] ==
                     "FROZEN_BASELINE_NOT_VISUALLY_APPROVED")
                    and contract["candidateReason"] is None,
                    f"{action} has a false baseline status")
        else:
            require(approved or selected_live or (
                    contract["status"] == "CANDIDATE_HASH_CHANGED"
                    and contract["candidateReason"] ==
                    "ANIMATION_HASH_CHANGED"),
                    f"{action} drift did not return to candidate status")
            if not approved and not selected_live:
                candidate_actions.append(action)
    require(set(approved_actions) == {
        "idle", "walk", "run", "jump_landing",
    }, "recorded human action approvals differ")
    require(set(selected_live_actions) == {
        "unarmed_attack", "kick_attack",
    }, "live-test combat selections differ")
    require(not candidate_actions,
            "frozen action drift requires human review: "
            + ", ".join(candidate_actions))

    graph_source = read(
        "src/main/java/com/projectseele/client/render/EvaPoseGraph.java")
    recorder_source = read(
        "src/main/java/com/projectseele/client/render/"
        "EvaPoseRuntimeRecorder.java")
    renderer_source = read(
        "src/main/java/com/projectseele/client/render/EvaUnit01Renderer.java")
    motion_source = read(
        "src/main/java/com/projectseele/client/render/EvaMotionEngineV2.java")
    command_source = read(
        "src/main/java/com/projectseele/visual/EvaMotionLabCommands.java")
    network_source = read(
        "src/main/java/com/projectseele/network/SeeleNetwork.java")
    entity_source = read(
        "src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    require("ENFORCE_POST_GECKO_SINGLE_COMMIT" in graph_source
            and "public static Snapshot commit(" in graph_source
            and "EvaMotionEngineV2.apply(" in graph_source,
            "enforcing PoseGraph commit is missing")
    require("POSE_GRAPH_WEAPON_AIM" in graph_source
            and "POSE_GRAPH_PILOT_AIM" in graph_source
            and "MOTION_ENGINE_LIVE_ACTION" in motion_source,
            "Phase-B aim owners are missing")
    require("positionOwners" in graph_source
            and "scaleOwners" in graph_source
            and "BoneWrites" in graph_source,
            "Phase-B channel ownership ledger is missing")
    require("record BoneWrites" in motion_source
            and "rotationBones" in motion_source
            and "positionBones" in motion_source
            and "String owner" in motion_source,
            "MotionEngine does not report channel-specific writes")
    for forbidden in (".setRotX(", ".setRotY(", ".setRotZ(",
                      ".setPosX(", ".setPosY(", ".setPosZ(",
                      ".setScaleX(", ".setScaleY(", ".setScaleZ("):
        require(forbidden not in renderer_source,
                "renderer still writes runtime bones: " + forbidden)
    require("EvaMotionEngineV2.apply(" not in renderer_source,
            "renderer still invokes MotionEngine directly")
    java_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO / "src/main/java").rglob("*.java")
    )
    require(java_sources.count("EvaMotionEngineV2.apply(") == 1,
            "MotionEngine has a post-Gecko caller outside EvaPoseGraph")
    for token in ("getLocalSpaceMatrix()", "getModelSpaceMatrix()",
                  "getWorldSpaceMatrix()", "boneOwnerTimeline",
                  "boneRotationOwnerTimeline",
                  "bonePositionOwnerTimeline", "boneScaleOwnerTimeline",
                  "FINAL_POST_CONTROLLER_GECKO_MATRICES",
                  "automaticVisualApproval", "MAX_FRAMES = 900"):
        require(token in recorder_source,
                "recorder contract missing " + token)
    for token in ("beginFrame(entity, partialTick)",
                  "captureBone(animatable, bone, isReRender)",
                  "endFrame(entity)", "trackMatrices(bone)",
                  "requestsSmokeRender()"):
        require(token in renderer_source,
                "renderer final-matrix hook missing " + token)
    require("Commands.literal(\"record\")" in command_source
            and "Official pose recording rejects demo/preview authority"
            in command_source
            and "EvaPilotResolver.controlTarget(player)" in command_source,
            "Motion Lab recorder bypasses normal pilot authority")
    require("ClientboundEvaPoseRecorderPacket" in network_source
            and 'PROTOCOL_VERSION = "23"' in network_source,
            "pose recorder packet is not registered")
    require("getAimDirectionForPoseCapture" in entity_source
            and "getMuzzlePositionForPoseCapture" in entity_source,
            "final gameplay sockets are not exposed read-only")

    print("EVA Phase-B pose authority contract passed: "
          f"rig={rig['rigVersion']} bones=70 locks={len(actions['actions'])} "
          "mode=ENFORCE_POST_GECKO_SINGLE_COMMIT")


if __name__ == "__main__":
    main()
