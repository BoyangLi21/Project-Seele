#!/usr/bin/env python3
"""Render and gate the active Tiger EVA third-person weapon poses.

The Tiger horn points toward local -Z.  A pose is therefore rejected when a
hand or weapon drifts behind the torso (+Z), even if its front projection looks
plausible.  Contracts are relative to the animated torso and attachment length
so a harmless model-scale change cannot silently turn into a false failure.
This is deliberately independent from Forge and the Java renderer.
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


def cosine_alignment(a: list[float], b: list[float]) -> float:
    denominator = math.sqrt(sum(value * value for value in a)
                            * sum(value * value for value in b))
    return -1.0 if denominator <= 1.0e-6 else sum(
        a[index] * b[index] for index in range(3)) / denominator


def point_line_distance(point: list[float], origin: list[float],
                        direction: list[float]) -> float:
    length_sqr = sum(value * value for value in direction)
    if length_sqr <= 1.0e-6:
        return float("inf")
    offset = [point[index] - origin[index] for index in range(3)]
    along = sum(offset[index] * direction[index] for index in range(3)) / length_sqr
    closest = [origin[index] + along * direction[index] for index in range(3)]
    return math.sqrt(sum((point[index] - closest[index]) ** 2 for index in range(3)))


def render(assets: Path, animation_json: Path | None, stem: str, pose: str,
           time: float, output: Path, attachment: str = "",
           overlay: str = "", overlay_time: float = 0.0) -> dict:
    suffix = f"_overlay_{overlay}_{overlay_time:.2f}" if overlay else ""
    target = output / stem / f"{pose}_{time:.2f}{suffix}"
    command = [
        sys.executable, str(RENDERER),
        str(assets / "mesh" / f"{stem}.mesh.json"),
        str(assets / "textures/entity" / f"{stem}.png"), str(target),
        "--geo", str(assets / "geo" / f"{stem}.geo.json"),
        "--animation-json", str(animation_json or
                                  (assets / "animations" / f"{stem}.animation.json")),
        "--animation", pose, "--time", str(time),
        "--no-skeleton", "--views", "front", "side", "back",
    ]
    if attachment == "knife":
        unit02 = stem == "eva_unit02"
        command.extend((
            "--attachment-mesh",
            str(assets / "mesh" / ("eva02_knife.mesh.json" if unit02
                                    else "progressive_knife.mesh.json")),
            "--attachment-texture",
            str(assets / "textures/entity" / ("eva02_weapons.png" if unit02
                                               else "progressive_knife.png")),
        ))
    elif attachment == "lance":
        unit02 = stem == "eva_unit02"
        command.extend((
            "--attachment-mesh",
            str(assets / "mesh" / ("eva02_special_weapon.mesh.json" if unit02
                                    else "longinus_lance.mesh.json")),
            "--attachment-texture",
            str(assets / "textures/entity" / ("eva02_weapons.png" if unit02
                                               else "longinus_lance.png")),
        ))
    elif attachment == "cannon":
        command.extend((
            "--attachment-mesh", str(assets / "mesh/positron_cannon.mesh.json"),
            "--attachment-texture",
            str(assets / "textures/entity/positron_cannon.png"),
        ))
    elif attachment == "rifle":
        command.extend((
            "--attachment-mesh", str(assets / "mesh/eva_pallet_smg.mesh.json"),
            "--attachment-texture",
            str(assets / "textures/entity/eva_pallet_smg.png"),
        ))
    elif attachment == "n2":
        command.extend((
            "--attachment-mesh", str(assets / "mesh/eva_n2_device.mesh.json"),
            "--attachment-texture",
            str(assets / "textures/entity/eva_n2_device.png"),
        ))
    if overlay:
        command.extend(("--overlay-animation", overlay,
                        "--overlay-time", str(overlay_time)))
    subprocess.run(command, cwd=REPO, check=True)
    metrics_path = next(target.glob("*_metrics.json"))
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument(
        "--animation-json", type=Path,
        help=("optional animation override; by default each generated Tiger "
              "variant uses its own active resource-pack animation"))
    parser.add_argument("--output", type=Path,
                        default=REPO / "external-assets/work/thirdperson-pose-validation")
    args = parser.parse_args()
    checks: dict[str, bool] = {}
    report: dict[str, object] = {"forward_axis": "local -Z (horn direction)"}

    for stem in ("eva_unit01", "eva_unit00", "eva_unit02"):
        idle = render(args.assets, args.animation_json, stem, "idle", 0.0, args.output)
        aim = render(args.assets, args.animation_json, stem, "aim", 0.0,
                     args.output, "cannon")
        idle_joints = idle["joint_world"]
        aim_joints = aim["joint_world"]
        idle_torso = idle_joints["torso_upper"]
        aim_torso = aim_joints["torso_upper"]
        checks[f"{stem}_idle_hands_not_behind"] = all(
            idle_joints[bone][2] <= idle_torso[2]
            for bone in ("hand_l", "hand_r"))
        checks[f"{stem}_aim_hands_forward"] = all(
            aim_joints[bone][2] <= aim_torso[2] - 40.0
            for bone in ("hand_l", "hand_r"))
        # The support palm closes around the top half of the downloaded
        # receiver, a few pixels above the trigger wrist.  Thirty-six pixels
        # still rejects an arm raised over the shoulder while accepting the
        # visually reviewed fore-end contact at +34.6.
        checks[f"{stem}_aim_chest_height"] = all(
            aim_torso[1] + 12.0 <= aim_joints[bone][1] <= aim_torso[1] + 36.0
            for bone in ("hand_l", "hand_r"))
        checks[f"{stem}_aim_two_hand_contact"] = aim["hand_pivot_distance"] <= 22.0
        checks[f"{stem}_cannon_forward"] = (
            aim_joints["cannon"][2] <= aim_torso[2] - 45.0)
        recoil = render(args.assets, args.animation_json, stem, "aim", 0.0,
                        args.output, "cannon", "cannon_fire", 0.06)
        recoil_joints = recoil["joint_world"]
        checks[f"{stem}_recoil_hands_forward"] = all(
            recoil_joints[bone][2] <= -35.0 for bone in ("hand_l", "hand_r"))
        checks[f"{stem}_recoil_two_hand_contact"] = recoil["hand_pivot_distance"] <= 22.0
        report[stem] = {"idle": idle, "aim": aim, "recoil": recoil}

    knife_report = {}
    knife_samples = (
        ("guard", "knife_ready", 0.0),
        ("contact", "knife", 0.32),
        ("recovery", "knife", 0.48),
        # knife_left deliberately aliases the right-hand clip. Sampling it
        # prevents the old alternating attachment/arm mismatch from returning.
        ("left_alias_contact", "knife_left", 0.32),
    )
    for label, pose, time in knife_samples:
        metrics = render(args.assets, args.animation_json, "eva_unit01", pose,
                         time, args.output, "knife")
        joints = metrics["joint_world"]
        blade = metrics["attachment_endpoints"]["attachment:knife"]
        blade_tip = blade["far_endpoint"]
        hand = joints["hand_r"]
        hand_to_tip = [blade_tip[axis] - hand[axis] for axis in range(3)]
        blade_axis = blade["vector_from_pivot"]
        prefix = f"knife_{label}"
        torso = joints["torso_upper"]
        checks[f"{prefix}_grounded"] = -0.2 <= metrics["overall_min_y"] <= 1.25
        required_reach = 12.0 if label == "guard" else 24.0
        checks[f"{prefix}_right_hand_forward"] = (
            joints["hand_r"][2] <= torso[2] - required_reach)
        # A tucked guard is diagonally down/back along the forearm; the slash
        # phases require a steeper downward blade. Both still leave the
        # little-finger side of the same right fist.
        downward_ratio = -0.50 if label == "guard" else -0.70
        minimum_drop = -15.0 if label == "guard" else -20.0
        checks[f"{prefix}_reverse_grip"] = (
            math.dist(hand, blade["pivot"]) <= 7.0
            and hand_to_tip[1] <= minimum_drop
            and blade_axis[1] / blade["length"] <= downward_ratio
        )
        checks[f"{prefix}_guard_forward"] = (
            joints["hand_l"][2] <= torso[2] - 18.0)
        knife_report[prefix] = metrics
    report["knife"] = knife_report

    lance_report = {}
    lance_samples = (("ready", 0.0, "", 0.0),
                     ("windup", 0.0, "lance_thrust", 0.20),
                     ("contact", 0.0, "lance_thrust", 0.42),
                     ("recovery", 0.0, "lance_thrust", 0.72),
                     ("moving", 0.0, "lance_carry", 0.0))
    for label, base_time, overlay, overlay_time in lance_samples:
        base_pose = "walk" if label == "moving" else "lance_ready"
        metrics = render(args.assets, args.animation_json, "eva_unit01",
                         base_pose, base_time, args.output, "lance",
                         overlay, overlay_time)
        joints = metrics["joint_world"]
        torso_z = joints["torso_upper"][2]
        weapon = metrics["attachment_endpoints"]["attachment:lance"]
        axis = weapon["vector_from_pivot"]
        prefix = f"lance_{label}"
        checks[f"{prefix}_elbows_in_front"] = all(
            joints[bone][2] <= torso_z - 2.0
            for bone in ("forearm_l", "forearm_r"))
        checks[f"{prefix}_hands_in_front"] = all(
            joints[bone][2] <= torso_z - 4.0
            for bone in ("hand_l", "hand_r"))
        checks[f"{prefix}_two_hand_grip"] = (
            9.0 <= metrics["hand_pivot_distance"] <= 36.0
            and abs(joints["hand_l"][2] - joints["hand_r"][2]) >= 7.0
            and point_line_distance(joints["hand_l"], weapon["pivot"], axis) <= 10.0
            and math.dist(joints["hand_r"], weapon["pivot"]) <= 8.0
        )
        checks[f"{prefix}_tip_faces_model_front"] = (
            cosine_alignment(axis, [0.0, 0.0, -1.0]) >= 0.95
            and axis[2] <= -0.90 * weapon["length"]
        )
        if label == "moving":
            checks[f"{prefix}_locomotion_preserved"] = (
                abs(metrics["root_position"][1]) >= 1.0
                and abs(joints["foot_l"][2] - joints["foot_r"][2]) >= 10.0
            )
        lance_report[prefix] = metrics
    report["lance"] = lance_report

    rifle_report = {}
    rifle_samples = (
        ("standing", "aim", 0.0, "", 0.0),
        ("moving", "walk", 0.0, "aim", 0.0),
        ("prone", "prone", 0.0, "prone_aim", 0.0),
    )
    for label, base_pose, base_time, overlay, overlay_time in rifle_samples:
        metrics = render(args.assets, args.animation_json, "eva_unit01",
                         base_pose, base_time, args.output, "rifle",
                         overlay, overlay_time)
        joints = metrics["joint_world"]
        muzzle = metrics["attachment_endpoints"]["attachment:cannon"]
        prefix = f"rifle_{label}"
        checks[f"{prefix}_muzzle_forward"] = (
            cosine_alignment(muzzle["vector_from_pivot"], [0.0, 0.0, -1.0])
            >= (0.995 if label != "moving" else 0.985)
        )
        checks[f"{prefix}_two_hand_pose"] = (
            metrics["hand_pivot_distance"] <= 22.0
            and all(joints[bone][2] <= joints["torso_upper"][2] - 35.0
                    for bone in ("hand_l", "hand_r"))
        )
        checks[f"{prefix}_ground_clearance"] = metrics["overall_min_y"] >= -0.2
        if label == "moving":
            checks[f"{prefix}_locomotion_preserved"] = (
                abs(metrics["root_position"][1]) >= 1.0
                and abs(joints["foot_l"][2] - joints["foot_r"][2]) >= 10.0
            )
        rifle_report[prefix] = metrics
    report["rifle"] = rifle_report

    n2 = render(args.assets, args.animation_json, "eva_unit01", "n2_ready",
                0.0, args.output, "n2")
    n2_joints = n2["joint_world"]
    n2_pivot = n2["attachment_endpoints"]["attachment:n2"]["pivot"]
    checks["n2_right_hand_on_handle"] = (
        math.dist(n2_joints["hand_r"], n2_pivot) <= 6.5)
    checks["n2_left_hand_braces_case"] = (
        math.dist(n2_joints["hand_l"], n2_pivot) <= 11.0)
    checks["n2_two_hand_carry"] = (
        8.0 <= n2["hand_pivot_distance"] <= 18.0
        and n2["overall_min_y"] >= -0.2)
    report["n2"] = n2

    report["checks"] = checks
    report["passed"] = all(checks.values())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = [name for name, passed in checks.items() if not passed]
    print(f"third-person pose validation: {'PASS' if not failed else 'FAIL'}")
    if failed:
        print("failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
