#!/usr/bin/env python3
"""Render a timestamped offline evidence matrix for every current EVA body.

This does not replace an in-game acceptance capture.  It does make model,
skeleton and animation regressions visible before Forge starts, using the same
local mesh/texture/Gecko JSON consumed by the renderer.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parent.parent
DEFAULT_ASSETS = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
RENDERER = REPO / "tools/render_unit01_rig_preview.py"
UNIT_POSES = (
    ("idle", 0.0), ("walk", 0.0), ("crouch", 0.0),
    ("prone", 0.0), ("aim", 0.0), ("crucified", 0.0),
    ("activation", 1.2), ("lance_ready", 0.0),
    ("visual_lance_windup", 0.0), ("visual_lance_contact", 0.0),
    ("visual_lance_recovery", 0.0),
)
FIRST_PERSON = (
    ("idle", "standing"), ("crouch", "crouch"),
    ("prone", "prone"), ("aim", "standing"),
)
MASS_POSES = (
    ("animation.entity_mp.idle_1", "idle", 0.0),
    ("animation.entity_mp.move", "move", 0.25),
    ("animation.entity_mp.visual_attack", "attack", 0.14),
    ("animation.entity_mp.revive", "revive", 0.75),
    ("animation.entity_mp.ritual", "ritual", 0.0),
)


def run_render(assets: Path, stem: str, animation: str, time: float,
               output: Path, first_person: str | None = None,
               with_cannon: bool = False, overlay: str | None = None,
               camera_forward: float | None = None,
               geo_cube_bones: tuple[str, ...] = ()) -> None:
    command = [
        sys.executable, str(RENDERER),
        str(assets / "mesh" / f"{stem}.mesh.json"),
        str(assets / "textures/entity" / f"{stem}.png"),
        str(output),
        "--geo", str(assets / "geo" / f"{stem}.geo.json"),
        "--animation-json", str(assets / "animations" / f"{stem}.animation.json"),
        "--animation", animation, "--time", str(time), "--no-skeleton",
    ]
    if with_cannon:
        command.extend((
            "--attachment-mesh", str(assets / "mesh/positron_cannon.mesh.json"),
            "--attachment-texture", str(assets / "textures/entity/positron_cannon.png"),
        ))
    if overlay is not None:
        command.extend(("--overlay-animation", overlay, "--overlay-time", "0.0"))
    for bone in geo_cube_bones:
        command.extend(("--geo-cube-bone", bone))
    if first_person is None:
        command.extend(("--views", "front", "side", "back"))
    else:
        command.extend(("--first-person-stance", first_person,
                        "--first-person-views", "forward", "pitch_down"))
        if camera_forward is not None:
            command.extend(("--camera-forward", str(camera_forward)))
    subprocess.run(command, cwd=REPO, check=True)


def read_metrics(directory: Path) -> dict:
    matches = list(directory.glob("*_metrics.json"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one metrics file in {directory}, found {len(matches)}")
    return json.loads(matches[0].read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--output", type=Path,
                        default=REPO / "external-assets/work/eva-offline-validation")
    args = parser.parse_args()
    batch = args.output / datetime.now().strftime("%Y%m%d-%H%M%S")
    batch.mkdir(parents=True, exist_ok=False)
    failures: list[str] = []
    records: list[dict] = []

    for unit in ("unit01", "unit00", "unit02"):
        stem = f"eva_{unit}"
        for pose, sample_time in UNIT_POSES:
            output = batch / unit / "third_person" / pose
            run_render(args.assets, stem, pose, sample_time, output,
                       with_cannon=pose == "aim",
                       geo_cube_bones=("lance",) if "lance" in pose else ())
            metrics = read_metrics(output)
            minimum_y = float(metrics["overall_min_y"])
            if pose != "crucified" and minimum_y < -1.0:
                failures.append(f"{unit}/{pose}: ground penetration {minimum_y:.3f}px")
            records.append({"subject": unit, "view": "third_person", "pose": pose,
                            "time": sample_time, "minimum_y": minimum_y})

        if unit == "unit00":
            output = batch / unit / "third_person" / "shield_brace"
            run_render(args.assets, stem, "crouch", 0.0, output,
                       overlay="shield_brace", geo_cube_bones=("shield",))
            metrics = read_metrics(output)
            minimum_y = float(metrics["overall_min_y"])
            if minimum_y < -1.0:
                failures.append(
                    f"{unit}/shield_brace: ground penetration {minimum_y:.3f}px")
            records.append({"subject": unit, "view": "third_person",
                            "pose": "shield_brace", "time": 0.0,
                            "minimum_y": minimum_y})
        for pose, stance in FIRST_PERSON:
            output = batch / unit / "first_person" / pose
            run_render(args.assets, stem, pose, 0.0, output, stance,
                       with_cannon=pose == "aim")
            metrics = read_metrics(output)
            forward = metrics["first_person"]["forward"]
            if stance in ("crouch", "prone"):
                if not forward["both_arm_regions_visible"]:
                    failures.append(f"{unit}/{pose}: forward view misses one arm region")
                if not forward["arms_read_on_opposite_sides"]:
                    failures.append(f"{unit}/{pose}: arms do not occupy opposite sides")
            records.append({
                "subject": unit, "view": "first_person", "pose": pose,
                "stance": stance,
                "both_arms": forward["both_arm_regions_visible"],
                "opposite_sides": forward["arms_read_on_opposite_sides"],
            })

        # The game layers the arms controller over the all-fours base pose.
        # Validate that exact composite with the real cannon mesh instead of
        # accepting the two animations independently.
        output = batch / unit / "third_person" / "prone_cannon"
        run_render(args.assets, stem, "prone", 0.0, output,
                   with_cannon=True, overlay="prone_aim")
        metrics = read_metrics(output)
        minimum_y = float(metrics["overall_min_y"])
        if minimum_y < -1.0:
            failures.append(f"{unit}/prone_cannon: ground penetration {minimum_y:.3f}px")
        records.append({"subject": unit, "view": "third_person",
                        "pose": "prone_cannon", "time": 0.0,
                        "minimum_y": minimum_y})

        output = batch / unit / "first_person" / "prone_cannon"
        run_render(args.assets, stem, "prone", 0.0, output, "prone",
                   with_cannon=True, overlay="prone_aim", camera_forward=3.5)
        metrics = read_metrics(output)
        forward = metrics["first_person"]["forward"]
        if not forward["both_arm_regions_visible"]:
            failures.append(f"{unit}/prone_cannon: forward view misses one arm region")
        if not forward["arms_read_on_opposite_sides"]:
            failures.append(f"{unit}/prone_cannon: arms do not occupy opposite sides")
        records.append({"subject": unit, "view": "first_person",
                        "pose": "prone_cannon", "stance": "prone",
                        "camera_forward": 3.5,
                        "both_arms": forward["both_arm_regions_visible"],
                        "opposite_sides": forward["arms_read_on_opposite_sides"]})

    mass_hashes: dict[str, str] = {}
    for animation, pose, sample_time in MASS_POSES:
        output = batch / "mass" / pose
        run_render(args.assets, "mass_production_eva", animation, sample_time, output,
                   geo_cube_bones=(() if pose in ("revive", "ritual")
                                   else ("replica_lance",)))
        metrics = read_metrics(output)
        minimum_y = float(metrics["overall_min_y"])
        if pose != "revive" and minimum_y < -1.0:
            failures.append(f"mass/{pose}: ground penetration {minimum_y:.3f}px")
        sheets = list(output.glob("*_sheet.png"))
        if len(sheets) != 1:
            failures.append(f"mass/{pose}: expected one contact sheet")
            continue
        mass_hashes[pose] = digest(sheets[0])
        records.append({"subject": "mass", "view": "third_person", "pose": pose,
                        "time": sample_time, "minimum_y": minimum_y,
                        "sheet_sha256": mass_hashes[pose]})
    if len(set(mass_hashes.values())) != len(MASS_POSES):
        failures.append("mass: two or more requested visual states render identically")

    evidence = []
    for path in sorted(batch.rglob("*.png")):
        evidence.append({"path": str(path.relative_to(batch)), "sha256": digest(path)})
    manifest = {
        "batch": batch.name,
        "assets": str(args.assets.resolve()),
        "result": "FAIL" if failures else "PASS",
        "failures": failures,
        "records": records,
        "evidence": evidence,
        "note": "Offline geometry evidence only; tagged Minecraft screenshots remain required.",
    }
    (batch / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"EVA offline validation matrix: {manifest['result']} -> {batch}")
    for failure in failures:
        print(f"  FAIL: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
