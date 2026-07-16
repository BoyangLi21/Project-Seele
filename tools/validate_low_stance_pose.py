#!/usr/bin/env python3
"""Fail-closed geometry gate for crouched and prone EVA action layering."""

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


def alignment(a: list[float], b: list[float]) -> float:
    denominator = math.sqrt(sum(v * v for v in a) * sum(v * v for v in b))
    return -1.0 if denominator <= 1.0e-6 else sum(
        a[index] * b[index] for index in range(3)) / denominator


def render(assets: Path, output: Path, label: str, animation: str,
           time: float, overlay: str = "", overlay_time: float = 0.0,
           attachment: str = "") -> dict:
    target = output / label
    command = [
        sys.executable, str(RENDERER),
        str(assets / "mesh/eva_unit01.mesh.json"),
        str(assets / "textures/entity/eva_unit01.png"), str(target),
        "--geo", str(assets / "geo/eva_unit01.geo.json"),
        "--animation-json", str(assets / "animations/eva_unit01.animation.json"),
        "--animation", animation, "--time", str(time),
        "--views", "front", "side", "back", "--no-skeleton",
    ]
    if overlay:
        command.extend(("--overlay-animation", overlay,
                        "--overlay-time", str(overlay_time)))
    attachments = {
        "knife": ("progressive_knife.mesh.json", "progressive_knife.png"),
        "lance": ("longinus_lance.mesh.json", "longinus_lance.png"),
        "rifle": ("eva_pallet_smg.mesh.json", "eva_pallet_smg.png"),
        "cannon": ("positron_cannon.mesh.json", "positron_cannon.png"),
    }
    if attachment:
        mesh, texture = attachments[attachment]
        command.extend((
            "--attachment-mesh", str(assets / "mesh" / mesh),
            "--attachment-texture", str(assets / "textures/entity" / texture),
        ))
    subprocess.run(command, cwd=REPO, check=True)
    metrics_path = next(target.glob("*_metrics.json"))
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def render_first_person(assets: Path, output: Path, label: str,
                        animation: str, time: float) -> dict:
    target = output / f"{label}_first_person"
    command = [
        sys.executable, str(RENDERER),
        str(assets / "mesh/eva_unit01.mesh.json"),
        str(assets / "textures/entity/eva_unit01.png"), str(target),
        "--geo", str(assets / "geo/eva_unit01.geo.json"),
        "--animation-json", str(assets / "animations/eva_unit01.animation.json"),
        "--animation", animation, "--time", str(time),
        "--first-person-stance", "crouch",
        "--first-person-views", "forward", "--no-skeleton",
    ]
    subprocess.run(command, cwd=REPO, check=True)
    metrics_path = next(target.glob("*_metrics.json"))
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--output", type=Path,
                        default=REPO / "external-assets/work/low-stance-validation")
    args = parser.parse_args()
    checks: dict[str, bool] = {}
    samples: dict[str, dict] = {}

    samples["crouch"] = render(
        args.assets, args.output, "crouch", "crouch", 0.0)
    for label, time in (("contact_a", 0.0), ("passing_a", 0.25),
                        ("contact_b", 0.5), ("passing_b", 0.75)):
        samples[f"crouch_walk_{label}"] = render(
            args.assets, args.output, f"crouch_walk_{label}",
            "crouch_walk", time)
    first_person_samples = {
        "crouch": render_first_person(
            args.assets, args.output, "crouch", "crouch", 0.0),
        "crouch_walk_contact_a": render_first_person(
            args.assets, args.output, "crouch_walk_contact_a",
            "crouch_walk", 0.0),
        "crouch_walk_contact_b": render_first_person(
            args.assets, args.output, "crouch_walk_contact_b",
            "crouch_walk", 0.5),
    }

    static = samples["crouch"]
    static_pelvis = static["joint_world"]["torso_lower"][1]
    checks["crouch_static_grounded"] = -0.2 <= static["overall_min_y"] <= 0.3
    for label in ("contact_a", "passing_a", "contact_b", "passing_b"):
        sample = samples[f"crouch_walk_{label}"]
        pelvis = sample["joint_world"]["torso_lower"][1]
        checks[f"crouch_walk_{label}_grounded"] = (
            -0.2 <= sample["overall_min_y"] <= 0.35)
        checks[f"crouch_walk_{label}_stays_low"] = (
            3.0 <= pelvis - static_pelvis <= 9.0
            and sample["overall_max_y"] <= static["overall_max_y"] + 8.0)
    contact_a = samples["crouch_walk_contact_a"]["joint_world"]
    contact_b = samples["crouch_walk_contact_b"]["joint_world"]
    checks["crouch_walk_stride_swaps"] = (
        contact_a["foot_l"][2] <= contact_a["foot_r"][2] - 20.0
        and contact_b["foot_r"][2] <= contact_b["foot_l"][2] - 20.0)
    for label, sample in first_person_samples.items():
        view = sample["first_person"]["forward"]
        left = view["left_arm"]["horizontal_centre"]
        right = view["right_arm"]["horizontal_centre"]
        checks[f"{label}_first_person_both_arms_visible"] = (
            view["both_arm_regions_visible"])
        checks[f"{label}_first_person_arms_keep_own_sides"] = (
            view["arms_read_on_opposite_sides"]
            and left is not None and right is not None
            and left <= -0.30 and right >= 0.30)
    for label in ("passing_a", "passing_b"):
        bounds = samples[f"crouch_walk_{label}"]["bone_bounds"]
        lifted = "foot_l" if label == "passing_a" else "foot_r"
        planted = "foot_r" if label == "passing_a" else "foot_l"
        checks[f"crouch_walk_{label}_one_foot_lifts"] = (
            bounds[lifted]["min_y"] >= 2.5
            and bounds[planted]["min_y"] <= 0.25)

    crouch_actions = (
        ("melee", "crouch_melee", 0.30, ""),
        ("knife", "crouch_knife", 0.32, "knife"),
        ("lance", "crouch_lance_thrust", 0.42, "lance"),
        ("smash", "crouch_smash", 0.40, ""),
        ("rifle_move", "aim", 0.0, "rifle"),
    )
    for label, overlay, overlay_time, attachment in crouch_actions:
        base_animation = "crouch_walk" if label == "rifle_move" else "crouch"
        sample = render(args.assets, args.output, f"crouch_{label}",
                        base_animation, 0.0, overlay, overlay_time, attachment)
        samples[f"crouch_{label}"] = sample
        checks[f"crouch_{label}_keeps_pelvis"] = (
            abs(sample["joint_world"]["torso_lower"][1]
                - (samples["crouch_walk_contact_a"]["joint_world"]["torso_lower"][1]
                   if label == "rifle_move" else static_pelvis)) <= 0.15)
        checks[f"crouch_{label}_keeps_ground"] = (
            -0.25 <= sample["overall_min_y"] <= 0.35)
        if attachment in {"rifle", "lance"}:
            endpoint = sample["attachment_endpoints"][
                "attachment:cannon" if attachment == "rifle"
                else "attachment:lance"]
            checks[f"crouch_{label}_weapon_faces_forward"] = (
                alignment(endpoint["vector_from_pivot"], [0.0, 0.0, -1.0])
                >= (0.98 if attachment == "rifle" else 0.90))

    prone_actions = (
        ("knife_ready", "prone_knife_ready", 0.0, "knife", True),
        ("lance_ready", "prone_lance_ready", 0.0, "lance", True),
        ("knife_attack", "prone_knife", 0.34, "knife", False),
        ("lance_attack", "prone_lance_thrust", 0.42, "lance", False),
        ("melee_attack", "prone_melee", 0.30, "", False),
        ("cannon_fire", "prone_cannon_fire", 0.06, "cannon", True),
    )
    crawl = render(args.assets, args.output, "crawl_reference", "crawl", 0.0)
    samples["crawl_reference"] = crawl
    for label, overlay, overlay_time, attachment, preserves_crawl in prone_actions:
        sample = render(args.assets, args.output, f"prone_{label}",
                        "crawl", 0.0, overlay, overlay_time, attachment)
        samples[f"prone_{label}"] = sample
        checks[f"prone_{label}_never_stands"] = (
            sample["overall_max_y"] <= 64.0
            and sample["joint_world"]["torso_lower"][1] <= 30.0)
        checks[f"prone_{label}_ground_clearance"] = sample["overall_min_y"] >= -0.25
        if preserves_crawl:
            checks[f"prone_{label}_preserves_crawl_root"] = (
                abs(sample["root_position"][1] - crawl["root_position"][1]) <= 0.15)

    source = (REPO / "src/main/java/com/projectseele/entity/EvaUnit01Entity.java"
              ).read_text(encoding="utf-8")
    checks["strike_controller_releases_pose"] = (
        'new AnimationController<>(this, "strike", 3,' in source
        and "state.getController().stop()" in source
        and "isPlayingTriggeredAnimation()" in source
        and "? PlayState.CONTINUE : PlayState.STOP" in source
        and ".receiveTriggeredAnimations()" in source)
    checks["locomotion_speed_tracks_chassis"] = (
        "setAnimationSpeedHandler" in source
        and "blocksPerSecond * WALK_CYCLE_SECONDS / WALK_STRIDE_BLOCKS" in source
        and "blocksPerSecond * RUN_CYCLE_SECONDS / RUN_STRIDE_BLOCKS" in source
        and "blocksPerSecond * CROUCH_CYCLE_SECONDS / CROUCH_STRIDE_BLOCKS" in source
        and "blocksPerSecond * CRAWL_CYCLE_SECONDS / CRAWL_STRIDE_BLOCKS" in source)

    report = {
        "contract": (
            "moving crouch remains within 3-9 px of kneel pelvis; triggered "
            "low attacks never own lower-body channels or stand the EVA up"),
        "checks": checks,
        "samples": samples,
        "first_person_samples": first_person_samples,
        "passed": all(checks.values()),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = [name for name, passed in checks.items() if not passed]
    print(f"low-stance pose validation: {'PASS' if not failed else 'FAIL'}")
    if failed:
        print("failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
