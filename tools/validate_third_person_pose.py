#!/usr/bin/env python3
"""Render and gate SmOd third-person arm, cannon and knife direction.

The SmOd horn points toward local -Z.  A pose is therefore rejected when a
hand or weapon drifts behind the torso (+Z), even if its front projection looks
plausible.  This is deliberately independent from Forge and the Java renderer.
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
DEFAULT_ANIMATION = REPO / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json"


def render(assets: Path, animation_json: Path, stem: str, pose: str,
           time: float, output: Path, attachment: str = "",
           overlay: str = "", overlay_time: float = 0.0) -> dict:
    suffix = f"_overlay_{overlay}_{overlay_time:.2f}" if overlay else ""
    target = output / stem / f"{pose}_{time:.2f}{suffix}"
    command = [
        sys.executable, str(RENDERER),
        str(assets / "mesh" / f"{stem}.mesh.json"),
        str(assets / "textures/entity" / f"{stem}.png"), str(target),
        "--geo", str(assets / "geo" / f"{stem}.geo.json"),
        "--animation-json", str(animation_json),
        "--animation", pose, "--time", str(time),
        "--no-skeleton", "--views", "front", "side", "back",
    ]
    if attachment == "knife":
        command.extend(("--geo-cube-bone", "knife"))
    elif attachment == "cannon":
        command.extend((
            "--attachment-mesh", str(assets / "mesh/positron_cannon.mesh.json"),
            "--attachment-texture",
            str(assets / "textures/entity/positron_cannon.png"),
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
    parser.add_argument("--animation-json", type=Path, default=DEFAULT_ANIMATION)
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
        checks[f"{stem}_idle_hands_forward"] = all(
            idle_joints[bone][2] <= -4.0 for bone in ("hand_l", "hand_r"))
        checks[f"{stem}_aim_hands_forward"] = all(
            aim_joints[bone][2] <= -35.0 for bone in ("hand_l", "hand_r"))
        checks[f"{stem}_aim_chest_height"] = all(
            128.0 <= aim_joints[bone][1] <= 150.0
            for bone in ("hand_l", "hand_r"))
        checks[f"{stem}_aim_two_hand_contact"] = aim["hand_pivot_distance"] <= 20.0
        checks[f"{stem}_cannon_forward"] = aim_joints["cannon"][2] <= -45.0
        recoil = render(args.assets, args.animation_json, stem, "aim", 0.0,
                        args.output, "cannon", "cannon_fire", 0.06)
        recoil_joints = recoil["joint_world"]
        checks[f"{stem}_recoil_hands_forward"] = all(
            recoil_joints[bone][2] <= -35.0 for bone in ("hand_l", "hand_r"))
        checks[f"{stem}_recoil_two_hand_contact"] = recoil["hand_pivot_distance"] <= 22.0
        report[stem] = {"idle": idle, "aim": aim}

    knife_report = {}
    for pose in ("knife", "knife_left"):
        for label, time in (("guard", 0.12), ("contact", 0.28), ("recovery", 0.42)):
            metrics = render(args.assets, args.animation_json, "eva_unit01", pose,
                             time, args.output, "knife")
            joints = metrics["joint_world"]
            prefix = f"{pose}_{label}"
            checks[f"{prefix}_grounded"] = -0.15 <= metrics["overall_min_y"] <= 0.15
            checks[f"{prefix}_right_hand_forward"] = joints["hand_r"][2] <= -35.0
            checks[f"{prefix}_blade_forward"] = joints["knife"][2] <= -40.0
            checks[f"{prefix}_guard_forward"] = joints["hand_l"][2] <= -30.0
            knife_report[prefix] = metrics
    report["knife"] = knife_report
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
