#!/usr/bin/env python3
"""Static fail-closed validator for the Phase-F review capture pipeline."""

from __future__ import annotations

import json
import py_compile
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CONTRACT = REPO / (
    "src/main/resources/assets/projectseele/eva/"
    "eva_foundation_review_contract.json")
ACTION_LOCKS = REPO / (
    "src/main/resources/assets/projectseele/eva/"
    "eva_approved_actions.json")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(contract["schema"] == 1 and contract["phase"] == "F",
            "Phase-F contract identity differs")
    actions = contract["actions"]
    require([(item["pose"], item["framesPerView"]) for item in actions]
            == [("idle", 60), ("walk_contact", 30),
                ("run_contact", 24), ("live_jump", 120),
                ("live_melee", 30), ("live_knife", 40)],
            "six-action review catalogue differs")
    require(contract["views"]
            == ["front_close", "side_close", "back_close"],
            "review camera catalogue differs")
    require(contract["render"] == {
        "source": "ACTUAL_GAME_FRAMEBUFFER_AFTER_POSE_GRAPH",
        "manifoldAuditOnly": True,
        "tigerBodyVisible": True,
        "debugOverlayVisible": False,
    }, "review render truth contract differs")
    require(not contract["manualReview"].get("visuallyApproved", False)
            and contract["manualReview"]["promotionRequiresHumanAcceptance"],
            "automatic pipeline may not grant visual approval")
    locks = json.loads(ACTION_LOCKS.read_text(encoding="utf-8"))
    approved = {"idle", "walk", "run", "jump_landing"}
    require(all(locks["actions"][key]["status"] == "VISUALLY_APPROVED"
                and locks["actions"][key]["approvedBy"] == "project_owner"
                and not locks["actions"][key]["humanReviewRequired"]
                for key in approved),
            "accepted Phase-F foundation action lost its human approval")
    require(all(value["status"]
                == "FROZEN_BASELINE_NOT_VISUALLY_APPROVED"
                for key, value in locks["actions"].items()
                if key not in approved),
            "a non-approved action changed its frozen status")
    decision = contract["manualReview"]["humanDecision"]
    require(set(decision["acceptedActions"]) == approved
            and set(decision["replacementRequired"]) == {
                "unarmed_attack", "progressive_knife",
            }, "Phase-F manual decision differs")

    gradle = read("build.gradle")
    capture = read(
        "src/main/java/com/projectseele/client/visual/"
        "VisualCaptureManager.java")
    audit = read(
        "src/main/java/com/projectseele/client/visual/"
        "EvaFoundationReviewAudit.java")
    commands = read(
        "src/main/java/com/projectseele/visual/VisualLabCommands.java")
    automation = read(
        "src/main/java/com/projectseele/visual/VisualLabAutomation.java")
    manifold = read(
        "src/main/java/com/projectseele/client/render/"
        "EvaManifoldInnerBody.java")
    require("projectseele.manifoldInnerAuditOnly" in gradle
            and "projectseele.foundationVideoCapture" in gradle,
            "foundation userdev properties are missing")
    require("Screenshot.grab" in capture
            and "EvaFoundationReviewAudit.record" in capture,
            "game framebuffer and matrix audit are not paired")
    for token in ("ACTION_SPRINT_START", "ACTION_JUMP", "ACTION_MELEE"):
        require(token in capture, f"formal gameplay input missing: {token}")
    require("input.forwardImpulse = moving ? 1.0F : 0.0F" in capture
            and "player.zza = moving ? 1.0F : 0.0F" in capture,
            "walk/run do not populate normal ridden-player input")
    require("unit.setVisualPose(EvaUnit01Entity.VISUAL_NORMAL)" in commands,
            "foundation capture does not return to gameplay pose authority")
    require("unit.prepareForMotionLab()" in commands
            and "EvaMotionLabDirector.ENTITY_TAG" in commands,
            "Visual Lab capture target is not powered and authorized")
    require("POSE_INTERVAL = FOUNDATION_VIDEO ? 460 : 140" in automation,
            "automation interval does not contain the complete sequences")
    require("root.add(\"bones\", bones)" in audit,
            "frame audit omits complete final bone matrices")
    for token in ("entityPosition", "pilotSprinting",
                  "visuallyAirborne", "powerTicks"):
        require(token in audit, f"frame audit omits motion evidence: {token}")
    require("auditOnly()" in manifold
            and "if (!auditOnly())" in manifold,
            "clean review capture still draws the engineering overlay")
    require("correctOrientations(" in manifold
            and "ORIENTATION_MAX_VERTEX_DELTA" in manifold
            and "maximumOrientationCorrection" in audit,
            "bounded orientation correction evidence is missing")
    require(not any(token in manifold for token in
                    (".setRotX(", ".setRotY(", ".setRotZ(",
                     ".setPosX(", ".setPosY(", ".setPosZ(")),
            "foundation manifold audit writes pose bones")
    for script in ("tools/audit_eva_foundation_capture.py",
                   "tools/build_eva_foundation_review_package.py",
                   "tools/stabilize_eva_foundation_landing.py"):
        py_compile.compile(str(REPO / script), doraise=True)
    print("EVA Phase-F foundation pipeline passed: actions=6 views=3 "
          "actualGameInputs=true finalMatrices=true redChronology=true "
          "automaticVisualApproval=false")


if __name__ == "__main__":
    main()
