#!/usr/bin/env python3
"""Render and gate Unit-01's human, belly-down low-crawl cycle.

The old prone animation could pass build checks while both legs folded in
front of the pelvis and the arms swept behind the back.  This validator uses
the authored mesh and Gecko animation, then checks a military low-crawl
contract: the head and chest stay forward, one forearm and the opposite lower
leg carry each support phase, and the pulling arm/tucked leg swap sides.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parent.parent
RENDERER = REPO / "tools/render_unit01_rig_preview.py"
DEFAULT_ASSETS = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
DEFAULT_ANIMATION = DEFAULT_ASSETS / "animations/eva_unit01.animation.json"
SAMPLES = (("support_a", 0.0), ("passing_a", 0.35),
           ("support_b", 0.70), ("passing_b", 1.05))


def render(assets: Path, animation: Path, output: Path,
           label: str, time: float) -> dict:
    target = output / f"{label}_{time:.2f}"
    command = [
        sys.executable, str(RENDERER),
        str(assets / "mesh/eva_unit01.mesh.json"),
        str(assets / "textures/entity/eva_unit01.png"), str(target),
        "--geo", str(assets / "geo/eva_unit01.geo.json"),
        "--animation-json", str(animation),
        "--animation", "crawl", "--time", str(time),
        "--views", "front", "side", "back",
    ]
    subprocess.run(command, cwd=REPO, check=True)
    metrics_path = next(target.glob("*_metrics.json"))
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def render_first_person(assets: Path, animation: Path, output: Path,
                        label: str, time: float) -> dict:
    target = output / f"{label}_{time:.2f}_first_person"
    command = [
        sys.executable, str(RENDERER),
        str(assets / "mesh/eva_unit01.mesh.json"),
        str(assets / "textures/entity/eva_unit01.png"), str(target),
        "--geo", str(assets / "geo/eva_unit01.geo.json"),
        "--animation-json", str(animation),
        "--animation", "crawl", "--time", str(time),
        "--first-person-stance", "prone",
        "--first-person-views", "forward",
        "--no-skeleton",
    ]
    subprocess.run(command, cwd=REPO, check=True)
    metrics_path = next(target.glob("*_metrics.json"))
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--animation-json", type=Path, default=DEFAULT_ANIMATION)
    parser.add_argument("--output", type=Path,
                        default=REPO / "external-assets/work/crawl-pose-validation")
    args = parser.parse_args()
    metrics = {label: render(args.assets, args.animation_json, args.output, label, time)
               for label, time in SAMPLES}
    first_person = {
        label: render_first_person(args.assets, args.animation_json, args.output,
                                   label, time)
        for label, time in (SAMPLES[0], SAMPLES[2])
    }
    checks: dict[str, bool] = {}
    diagnostics: dict[str, object] = {}

    for label, sample in metrics.items():
        joints = sample["joint_world"]
        bounds = sample["bone_bounds"]
        contacts = {
            "forearm_l": bounds["forearm_l"]["min_y"] <= 0.25,
            "forearm_r": bounds["forearm_r"]["min_y"] <= 0.25,
            "shin_l": bounds["shin_l"]["min_y"] <= 3.25,
            "shin_r": bounds["shin_r"]["min_y"] <= 3.25,
        }
        # A passing frame may lift roughly five model pixels as the body glides
        # through neutral.  Anything lower than -0.25 is visible penetration.
        checks[f"{label}_ground_plane"] = (
            -0.25 <= sample["overall_min_y"] <= 5.25)
        checks[f"{label}_head_chest_face_forward"] = (
            joints["head"][2] < joints["torso_upper"][2] - 20.0
            and joints["torso_upper"][2] < joints["torso_lower"][2] - 20.0)
        checks[f"{label}_arms_ahead"] = all(
            joints[bone][2] <= joints["torso_upper"][2] - 20.0
            for bone in ("forearm_l", "forearm_r", "hand_l", "hand_r"))
        checks[f"{label}_feet_behind"] = all(
            joints[bone][2] >= joints["torso_lower"][2] + 55.0
            for bone in ("foot_l", "foot_r"))
        checks[f"{label}_level_back"] = abs(
            joints["torso_upper"][1] - joints["torso_lower"][1]) <= 8.0
        diagnostics[label] = {
            "contacts": contacts,
            "overall_min_y": sample["overall_min_y"],
            "hand_z": {side: joints[f"hand_{side}"][2]
                       for side in ("l", "r")},
            "shin_x": {side: joints[f"shin_{side}"][0]
                       for side in ("l", "r")},
            "foot_z": {side: joints[f"foot_{side}"][2]
                       for side in ("l", "r")},
        }

    support_a = metrics["support_a"]
    support_b = metrics["support_b"]
    joints_a = support_a["joint_world"]
    joints_b = support_b["joint_world"]
    contacts_a = diagnostics["support_a"]["contacts"]
    contacts_b = diagnostics["support_b"]["contacts"]
    checks["support_a_opposite_forearm_and_shin"] = (
        contacts_a["forearm_r"] and contacts_a["shin_l"]
        and not contacts_a["forearm_l"] and not contacts_a["shin_r"])
    checks["support_b_opposite_forearm_and_shin"] = (
        contacts_b["forearm_l"] and contacts_b["shin_r"]
        and not contacts_b["forearm_r"] and not contacts_b["shin_l"])
    checks["cycle_pulling_arm_swaps"] = (
        joints_a["hand_l"][2] <= joints_a["hand_r"][2] - 6.0
        and joints_b["hand_r"][2] <= joints_b["hand_l"][2] - 6.0)
    checks["cycle_tucked_leg_swaps"] = (
        joints_a["foot_l"][2] <= joints_a["foot_r"][2] - 4.0
        and joints_b["foot_r"][2] <= joints_b["foot_l"][2] - 4.0)
    checks["cycle_knee_opens_outward_and_swaps"] = (
        abs(joints_a["shin_l"][0]) >= abs(joints_a["shin_r"][0]) + 8.0
        and abs(joints_b["shin_r"][0]) >= abs(joints_b["shin_l"][0]) + 8.0)
    checks["cycle_weight_shift"] = abs(
        joints_a["torso_lower"][0] - joints_b["torso_lower"][0]) >= 0.4
    for label, sample in first_person.items():
        view = sample["first_person"]["forward"]
        checks[f"{label}_first_person_both_arms_visible"] = (
            view["both_arm_regions_visible"])
        checks[f"{label}_first_person_arms_keep_own_sides"] = (
            view["arms_read_on_opposite_sides"])
        diagnostics[label]["first_person_arm_centres"] = {
            "left": view["left_arm"]["horizontal_centre"],
            "right": view["right_arm"]["horizontal_centre"],
        }
    for label in ("passing_a", "passing_b"):
        joints = metrics[label]["joint_world"]
        checks[f"{label}_near_neutral"] = (
            abs(joints["hand_l"][2] - joints["hand_r"][2]) <= 4.0
            and abs(joints["foot_l"][2] - joints["foot_r"][2]) <= 4.0)
        checks[f"{label}_limbs_clear_ground"] = (
            not any(diagnostics[label]["contacts"].values()))

    report = {
        "contract": "human belly-down low crawl; model forward is local -Z",
        "samples": metrics,
        "first_person_samples": first_person,
        "diagnostics": diagnostics,
        "checks": checks,
        "passed": all(checks.values()),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = [name for name, passed in checks.items() if not passed]
    print(f"crawl pose validation: {'PASS' if not failed else 'FAIL'}")
    if failed:
        print("failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
