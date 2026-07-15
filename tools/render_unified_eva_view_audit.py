#!/usr/bin/env python3
"""Audit the shared world EVA through the current runtime pilot sockets.

The base preview owns the projection implementation.  This entry point exists
so the recovery matrix has an explicit architecture boundary and fails fast if
the base tool ever drifts back to the rejected detached-RenderHand constants.
"""

import render_unit01_rig_preview as rig


EXPECTED_SOCKETS = {
    "standing": {"eye_height": 24.63, "forward": 1.00},
    "crouch": {"eye_height": 19.70, "forward": 0.80},
    "prone": {"eye_height": 7.00, "forward": 12.00},
}

EXPECTED_HIDDEN_ROOTS = {
    "head", "Head", "horn", "Horn", "neck", "Neck",
}
EXPECTED_CAMERA_COVER_PARTS = {
    "standing": {"torso_lower", "torso_upper", "pylon_l", "pylon_r"},
    "crouch": {"torso_lower", "torso_upper", "pylon_l", "pylon_r"},
    "prone": {"torso_lower", "torso_upper", "pylon_l", "pylon_r"},
}


def assert_unified_contract():
    if rig.FIRST_PERSON_SOCKETS != EXPECTED_SOCKETS:
        raise SystemExit("unified audit socket drift: update runtime and audit together")
    if rig.FIRST_PERSON_HIDDEN_ROOTS != EXPECTED_HIDDEN_ROOTS:
        raise SystemExit("unified audit hidden-root drift: only camera-cover bones may hide")
    if rig.FIRST_PERSON_CAMERA_COVER_PARTS != EXPECTED_CAMERA_COVER_PARTS:
        raise SystemExit("unified audit pilot camera clipping contract drift")


if __name__ == "__main__":
    assert_unified_contract()
    rig.main()
