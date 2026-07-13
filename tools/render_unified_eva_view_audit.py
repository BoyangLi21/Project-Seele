#!/usr/bin/env python3
"""Audit the shared world EVA through the current runtime pilot sockets.

The base preview owns the projection implementation.  This entry point exists
so the recovery matrix has an explicit architecture boundary and fails fast if
the base tool ever drifts back to the rejected detached-RenderHand constants.
"""

import render_unit01_rig_preview as rig


EXPECTED_SOCKETS = {
    "standing": {"eye_height": 24.63, "forward": 3.70},
    "crouch": {"eye_height": 19.70, "forward": 0.80},
    "prone": {"eye_height": 10.80, "forward": 10.33},
}

EXPECTED_HIDDEN_ROOTS = {
    "head", "Head", "horn", "Horn", "neck", "Neck",
}
EXPECTED_LOW_STANCE_HIDDEN_PARTS = {
    "crouch": {"torso_lower", "torso_upper"},
    "prone": {"torso_lower", "torso_upper"},
}


def assert_unified_contract():
    if rig.FIRST_PERSON_SOCKETS != EXPECTED_SOCKETS:
        raise SystemExit("unified audit socket drift: update runtime and audit together")
    if rig.FIRST_PERSON_HIDDEN_ROOTS != EXPECTED_HIDDEN_ROOTS:
        raise SystemExit("unified audit hidden-root drift: only camera-cover bones may hide")
    if rig.LOW_STANCE_FIRST_PERSON_HIDDEN_PARTS != EXPECTED_LOW_STANCE_HIDDEN_PARTS:
        raise SystemExit("unified audit low-stance camera clipping contract drift")


if __name__ == "__main__":
    assert_unified_contract()
    rig.main()
