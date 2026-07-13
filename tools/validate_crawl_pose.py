#!/usr/bin/env python3
"""Render and gate Unit-01's human, load-bearing quadruped crawl cycle.

The old prone animation could pass build checks while both legs folded in
front of the pelvis and the arms swept behind the back.  This validator uses
the authored mesh and Gecko animation, then checks real world-space joints and
contact surfaces at the two diagonal support phases and both passing phases.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parent.parent
RENDERER = REPO / "tools/render_unit01_rig_preview.py"
DEFAULT_ASSETS = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
DEFAULT_ANIMATION = REPO / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json"
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


def angle_degrees(a: list[float], centre: list[float], b: list[float]) -> float:
    first = [a[index] - centre[index] for index in range(3)]
    second = [b[index] - centre[index] for index in range(3)]
    denominator = math.sqrt(sum(value * value for value in first)
                            * sum(value * value for value in second))
    if denominator <= 1.0e-6:
        return 180.0
    cosine = max(-1.0, min(1.0, sum(first[index] * second[index]
                                    for index in range(3)) / denominator))
    return math.degrees(math.acos(cosine))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--animation-json", type=Path, default=DEFAULT_ANIMATION)
    parser.add_argument("--output", type=Path,
                        default=REPO / "external-assets/work/crawl-pose-validation")
    args = parser.parse_args()
    metrics = {label: render(args.assets, args.animation_json, args.output, label, time)
               for label, time in SAMPLES}
    checks: dict[str, bool] = {}
    diagnostics: dict[str, object] = {}

    for label, sample in metrics.items():
        joints = sample["joint_world"]
        bounds = sample["bone_bounds"]
        contacts = {
            bone: bounds[bone]["min_y"] <= 1.0
            for bone in ("hand_l", "hand_r", "shin_l", "shin_r")
        }
        knee_angles = {
            side: angle_degrees(joints[f"leg_{side}"], joints[f"shin_{side}"],
                                joints[f"foot_{side}"])
            for side in ("l", "r")
        }
        checks[f"{label}_ground_plane"] = -0.25 <= sample["overall_min_y"] <= 0.75
        checks[f"{label}_three_point_support"] = sum(contacts.values()) >= 3
        checks[f"{label}_palms_keep_sides"] = (
            joints["hand_l"][0] >= 12.0 and joints["hand_r"][0] <= -12.0)
        checks[f"{label}_palms_ahead"] = all(
            joints[bone][2] <= joints["torso_upper"][2] - 15.0
            for bone in ("hand_l", "hand_r"))
        checks[f"{label}_feet_behind"] = all(
            joints[bone][2] >= joints["torso_lower"][2] + 25.0
            for bone in ("foot_l", "foot_r"))
        checks[f"{label}_level_back"] = abs(
            joints["torso_upper"][1] - joints["torso_lower"][1]) <= 8.0
        checks[f"{label}_right_angle_knees"] = all(
            55.0 <= angle <= 115.0 for angle in knee_angles.values())
        diagnostics[label] = {"contacts": contacts, "knee_angles": knee_angles}

    support_a = metrics["support_a"]
    support_b = metrics["support_b"]
    joints_a = support_a["joint_world"]
    joints_b = support_b["joint_world"]
    checks["cycle_hands_change_support"] = all(
        abs(joints_a[bone][2] - joints_b[bone][2]) >= 8.0
        for bone in ("hand_l", "hand_r"))
    checks["cycle_feet_change_support"] = all(
        abs(joints_a[bone][2] - joints_b[bone][2]) >= 8.0
        for bone in ("foot_l", "foot_r"))
    checks["cycle_diagonal_support_a"] = (
        (joints_a["hand_l"][2] - joints_a["hand_r"][2])
        * (joints_a["foot_l"][2] - joints_a["foot_r"][2]) < -40.0)
    checks["cycle_diagonal_support_b"] = (
        (joints_b["hand_l"][2] - joints_b["hand_r"][2])
        * (joints_b["foot_l"][2] - joints_b["foot_r"][2]) < -40.0)
    checks["cycle_weight_shift"] = abs(
        joints_a["torso_lower"][0] - joints_b["torso_lower"][0]) >= 1.0
    for label in ("passing_a", "passing_b"):
        joints = metrics[label]["joint_world"]
        checks[f"{label}_near_neutral"] = (
            abs(joints["hand_l"][2] - joints["hand_r"][2]) <= 4.0
            and abs(joints["foot_l"][2] - joints["foot_r"][2]) <= 4.0)

    report = {
        "contract": "human quadruped crawl; model forward is local -Z",
        "samples": metrics,
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
