#!/usr/bin/env python3
"""Validate Blender-equivalent quaternion decoding and approved live knives."""

from __future__ import annotations

import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MOTION = REPO / "src/main/resources/assets/projectseele/motion"
REVIEW = MOTION / "eva_mocap_combat_phase_m_review_v1.json"
LIVE = MOTION / "eva_knife_attacks_phase_m_v1.json"
CLIPS = (
    "eva_locked_knife_stab_twist_forward",
    "eva_short_knife_stab_twist_reverse",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("EVA live-pose basis/knife invalid: " + message)


def blender_xyz(q: tuple[float, float, float, float]) -> tuple[float, ...]:
    w, x, y, z = q
    return (
        math.atan2(2.0 * (w * x + y * z),
                   1.0 - 2.0 * (x * x + y * y)),
        math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x)))),
        math.atan2(2.0 * (w * z + x * y),
                   1.0 - 2.0 * (y * y + z * z)),
    )


def main() -> None:
    # Values were independently emitted by Blender 5.1 mathutils
    # Quaternion.to_euler("XYZ"); Y-sign errors here fold shoulders and hips.
    references = (
        ((0.9865132, 0.0828137, -0.0904349, -0.1084209),
         (0.186485544, -0.161169812, -0.234031692)),
        ((0.6092018, -0.3748028, 0.0076297, 0.6988118),
         (-0.555258393, 0.562295020, 1.543361783)),
        ((0.6569713, -0.5623668, -0.0242092, -0.5015439),
         (-1.097126484, -0.638401747, -0.905469596)),
    )
    maximum_error = max(
        abs(actual - expected)
        for quaternion, expected_euler in references
        for actual, expected in zip(blender_xyz(quaternion), expected_euler)
    )
    require(maximum_error < 1.0e-6,
            "reference quaternion conversion differs from Blender")

    engine = (REPO / "src/main/java/com/projectseele/client/render/"
              "EvaMotionEngineV2.java").read_text(encoding="utf-8")
    entity = (REPO / "src/main/java/com/projectseele/entity/"
              "EvaUnit01Entity.java").read_text(encoding="utf-8")
    client = (REPO / "src/main/java/com/projectseele/client/"
              "ClientForgeEvents.java").read_text(encoding="utf-8")
    require("getEulerAnglesXYZ" not in engine
            and "motionQuaternionToAuthoredEuler" in engine
            and "w * x + y * z" in engine
            and "w * y - z * x" in engine,
            "runtime does not use the Blender XYZ formula")
    require("LIVE_KNIFE_DATABASE" in engine
            and "bone_position_xyz" in engine
            and "getKnifeMotionType" in engine,
            "live knife rotations or authored socket positions are not read")
    require("EvaLiveCombatMotion.knife" in entity
            and "applyKnifeRootMotion" in entity,
            "server-authoritative knife root motion is missing")
    require("ScreenEvent.Opening" in client
            and "AbstractContainerScreen" in client
            and "keyInventory.setDown(false)" in client,
            "cockpit inventory/backpack lock is missing")

    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    require(live.get("live_gameplay_replacement") is True
            and live.get("preview_only") is False,
            "approved knives remain preview-only")
    require(live.get("human_review", {}).get("status") ==
            "HUMAN_APPROVED_FOR_LIVE_GAMEPLAY",
            "live knife human approval receipt is missing")
    require(set(live["clips"]) == set(CLIPS),
            "live resource contains rejected or missing clips")
    require(live["bones"] == review["bones"]
            and len(live["bones"]) == 51,
            "live knife bone order differs from reviewed data")
    for clip in CLIPS:
        require(live["clips"][clip]["frames"] ==
                review["clips"][clip]["frames"],
                f"{clip} frames differ from the approved MP4 source")
        for frame in live["clips"][clip]["frames"]:
            require("knife" in frame.get("bone_position_xyz", {}),
                    f"{clip} omits the reviewed knife socket position")

    total_frames = sum(len(live["clips"][clip]["frames"])
                       for clip in CLIPS)
    print("EVA live-pose basis/knife passed: "
          f"basisError={maximum_error:.3e} clips=2 bones=51 "
          f"frames={total_frames} cockpitContainers=blocked")


if __name__ == "__main__":
    main()
