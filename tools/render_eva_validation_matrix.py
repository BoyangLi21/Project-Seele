#!/usr/bin/env python3
"""Render fail-closed offline evidence for the current EVA visual contract.

The first-person rows use the same complete world mesh, Gecko skeleton and
animation as the third-person rows. Camera-cover head/horn/neck roots may hide;
in crouch/prone only, the two exact torso mesh parts enclosing the camera are
clipped without hiding their bones or children. This tool deliberately does
not implement or approve the rejected RenderHand arm viewmodel.

Offline PASS proves inputs, camera direction, visibility contracts and static
geometry only.  It never replaces a tagged Minecraft capture reviewed by a
human.
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
WORLD_RENDERER = REPO / "tools/render_unit01_rig_preview.py"
UNIFIED_AUDIT = REPO / "tools/render_unified_eva_view_audit.py"

UNITS = ("unit01", "unit00", "unit02")
ALLOWED_CAMERA_COVER_BONES = {
    "head", "Head", "horn", "Horn", "neck", "Neck",
}
ALWAYS_FORBIDDEN_HIDDEN_BONES = {
    "root", "pylon_l", "pylon_r",
    "arm_l", "forearm_l", "hand_l", "arm_r", "forearm_r", "hand_r",
}
LOW_STANCE_EXACT_HIDDEN_PARTS = {
    "crouch": {"torso_lower", "torso_upper"},
    "prone": {"torso_lower", "torso_upper"},
}
HEAD_SOCKET_OFFSET_RANGES = {
    # Camera minus animated head-joint coordinates, in model pixels. The head
    # joint is at the neck pivot, not at the eyes, so a non-zero offset is the
    # intended contract and is shared by all three Tiger bodies.
    "standing": ((-2.0, 2.0), (-3.0, 3.0), (-26.0, -18.0)),
    "crouch": ((-2.0, 2.0), (7.0, 13.0), (-12.0, -6.0)),
    "prone": ((-2.0, 2.0), (17.0, 24.0), (-18.0, -11.0)),
}

# Every Unit must produce both exterior and pilot-eye evidence for these rows.
# Knife is sampled at contact; prone aim is the same controller layering used
# by the game (prone base plus prone_aim arm overlay).
POSE_CASES = (
    {"name": "standing", "animation": "idle", "time": 0.0,
     "stance": "standing"},
    {"name": "crouch", "animation": "crouch", "time": 0.0,
     "stance": "crouch"},
    {"name": "prone", "animation": "prone", "time": 0.0,
     "stance": "prone"},
    {"name": "knife", "animation": "knife", "time": 0.28,
     "stance": "standing", "geo_cube_bones": ("knife",),
     "weapon_bone": "knife"},
    {"name": "aim", "animation": "aim", "time": 0.0,
     "stance": "standing", "cannon": True, "weapon_bone": "cannon"},
    {"name": "prone_aim", "animation": "prone", "time": 0.0,
     "stance": "prone", "overlay": "prone_aim", "cannon": True,
     "weapon_bone": "cannon"},
)

MASS_POSES = (
    ("animation.entity_mp.idle_1", "idle", 0.0, True),
    ("animation.entity_mp.move", "move", 0.25, True),
    ("animation.entity_mp.visual_attack", "attack", 0.14, True),
    ("animation.entity_mp.revive", "revive", 0.75, False),
    ("animation.entity_mp.ritual", "ritual", 0.0, False),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(command: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(
        command, cwd=REPO, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    return completed.returncode == 0, completed.stdout.strip()


def render_command(assets: Path, stem: str, case: dict, output: Path,
                   first_person: bool) -> list[str]:
    command = [
        sys.executable, str(UNIFIED_AUDIT if first_person else WORLD_RENDERER),
        str(assets / "mesh" / f"{stem}.mesh.json"),
        str(assets / "textures/entity" / f"{stem}.png"),
        str(output), "--geo", str(assets / "geo" / f"{stem}.geo.json"),
        "--animation-json",
        str(assets / "animations" / f"{stem}.animation.json"),
        "--animation", case["animation"], "--time", str(case["time"]),
        "--no-skeleton",
    ]
    if case.get("overlay"):
        command.extend(("--overlay-animation", case["overlay"],
                        "--overlay-time", "0.0"))
    if case.get("cannon"):
        command.extend((
            "--attachment-mesh",
            str(assets / "mesh/positron_cannon.mesh.json"),
            "--attachment-texture",
            str(assets / "textures/entity/positron_cannon.png"),
        ))
    for bone in case.get("geo_cube_bones", ()):
        command.extend(("--geo-cube-bone", bone))
    if first_person:
        command.extend(("--first-person-stance", case["stance"],
                        "--first-person-views", "forward", "pitch_down"))
    else:
        command.extend(("--views", "front", "side", "back"))
    return command


def read_single_metrics(output: Path) -> dict:
    matches = list(output.glob("*_metrics.json"))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one metrics JSON in {output}, found {len(matches)}")
    return json.loads(matches[0].read_text(encoding="utf-8"))


def expected_png_count(output: Path, expected: int) -> bool:
    return len(list(output.glob("*.png"))) == expected


def validate_world_pose(metrics: dict, label: str,
                        require_hands: bool = True) -> list[str]:
    failures = []
    minimum_y = float(metrics["overall_min_y"])
    if minimum_y < -1.0:
        failures.append(f"{label}: ground penetration {minimum_y:.3f}px")
    if require_hands:
        for hand in ("hand_l", "hand_r"):
            if hand not in metrics.get("joint_world", {}):
                failures.append(f"{label}: missing {hand} joint from shared skeleton")
    return failures


def validate_unified_view(metrics: dict, label: str, stance: str,
                          weapon_bone: str | None) -> tuple[list[str], dict]:
    failures = []
    views = metrics.get("first_person", {})
    if set(views) != {"forward", "pitch_down"}:
        failures.append(f"{label}: expected forward and pitch_down pilot-eye views")

    readable_view = False
    weapon_visible = weapon_bone is None
    view_summary = {}
    camera_position = None
    for name in ("forward", "pitch_down"):
        view = views.get(name)
        if not isinstance(view, dict):
            continue
        contract = view.get("source_contract", {})
        hidden = set(contract.get("hidden_bones", ()))
        camera_cover = set(contract.get("camera_cover_hidden_bones", ()))
        exact_hidden = set(contract.get("exact_hidden_mesh_parts", ()))
        if not camera_cover.issubset(ALLOWED_CAMERA_COVER_BONES):
            failures.append(
                f"{label}/{name}: non-camera-cover bones hidden: "
                f"{sorted(camera_cover - ALLOWED_CAMERA_COVER_BONES)}")
        expected_exact = LOW_STANCE_EXACT_HIDDEN_PARTS.get(stance, set())
        if exact_hidden != expected_exact:
            failures.append(
                f"{label}/{name}: exact camera-clipped mesh parts "
                f"{sorted(exact_hidden)} != {sorted(expected_exact)}")
        if hidden != camera_cover | exact_hidden:
            failures.append(f"{label}/{name}: hidden mesh contract is not auditable")
        if hidden & ALWAYS_FORBIDDEN_HIDDEN_BONES:
            failures.append(
                f"{label}/{name}: world body/arm bones hidden: "
                f"{sorted(hidden & ALWAYS_FORBIDDEN_HIDDEN_BONES)}")
        if contract.get("model_forward_axis") != "local -Z (horn direction)":
            failures.append(f"{label}/{name}: local -Z forward contract missing")
        camera = contract.get("camera_local_position_model_pixels")
        signed_forward = contract.get("forward_blocks")
        pixels_per_block = contract.get("model_pixels_per_block")
        if (not isinstance(camera, list) or len(camera) != 3
                or signed_forward is None or pixels_per_block is None
                or abs(float(camera[2])
                       + float(signed_forward) * float(pixels_per_block)) > 0.01):
            failures.append(f"{label}/{name}: camera does not match signed rider socket")
        elif camera_position is None:
            camera_position = [float(value) for value in camera]
        view_forward = contract.get("view_forward_model")
        if (not isinstance(view_forward, list) or len(view_forward) != 3
                or float(view_forward[2]) >= 0.0):
            failures.append(f"{label}/{name}: pilot view is not looking along local -Z")

        both = bool(view.get("both_arm_regions_visible"))
        opposite = bool(view.get("arms_read_on_opposite_sides"))
        readable_view = readable_view or (both and opposite)
        visibility = view.get("bone_visibility", {})
        if weapon_bone is not None:
            weapon = visibility.get(weapon_bone, {})
            weapon_visible = weapon_visible or int(weapon.get("visible_polygons", 0)) > 0
        view_summary[name] = {
            "camera_cover_hidden_bones": sorted(camera_cover),
            "exact_hidden_mesh_parts": sorted(exact_hidden),
            "all_hidden_mesh_parts": sorted(hidden),
            "both_arm_regions_visible": both,
            "arms_read_on_opposite_sides": opposite,
            "visible_bones": sorted(visibility),
        }

    if not readable_view:
        failures.append(
            f"{label}: neither pilot-eye view shows both attached arms on opposite sides")
    if not weapon_visible:
        failures.append(f"{label}: {weapon_bone} is absent from both pilot-eye views")
    head = metrics.get("joint_world", {}).get("head")
    head_bounds = metrics.get("bone_bounds", {}).get("head", {})
    minimum = head_bounds.get("min_xyz")
    maximum = head_bounds.get("max_xyz")
    if (camera_position is None or not isinstance(head, list) or len(head) != 3
            or not isinstance(minimum, list) or len(minimum) != 3
            or not isinstance(maximum, list) or len(maximum) != 3):
        failures.append(f"{label}: camera/head socket evidence is incomplete")
    else:
        delta = [camera_position[index] - float(head[index]) for index in range(3)]
        distance = sum(value * value for value in delta) ** 0.5
        outside = [
            max(float(minimum[index]) - camera_position[index],
                camera_position[index] - float(maximum[index]), 0.0)
            for index in range(3)
        ]
        inside_head = max(outside) <= 1.0
        view_summary["head_socket"] = {
            "camera_model_pixels": [round(value, 4) for value in camera_position],
            "head_joint_model_pixels": [round(float(value), 4) for value in head],
            "delta_model_pixels": [round(value, 4) for value in delta],
            "distance_model_pixels": round(distance, 4),
            "head_mesh_min_model_pixels": minimum,
            "head_mesh_max_model_pixels": maximum,
            "inside_head_mesh_with_1px_tolerance": inside_head,
        }
        ranges = HEAD_SOCKET_OFFSET_RANGES[stance]
        if any(not ranges[axis][0] <= delta[axis] <= ranges[axis][1]
               for axis in range(3)):
            failures.append(
                f"{label}: {stance} camera/head-joint offset {delta} outside contract")
    return failures, view_summary


def render_unit(assets: Path, batch: Path, unit: str,
                failures: list[str], records: list[dict]) -> None:
    stem = f"eva_{unit}"
    for case in POSE_CASES:
        for view_kind, first_person in (("third_person", False),
                                        ("first_person", True)):
            label = f"{unit}/{view_kind}/{case['name']}"
            output = batch / unit / view_kind / case["name"]
            output.mkdir(parents=True, exist_ok=False)
            ok, log = run_command(render_command(
                assets, stem, case, output, first_person))
            if not ok:
                failures.append(f"{label}: renderer failed: {log[-500:]}")
                records.append({"subject": unit, "view": view_kind,
                                "pose": case["name"], "result": "ERROR"})
                continue
            try:
                metrics = read_single_metrics(output)
            except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as error:
                failures.append(f"{label}: {error}")
                continue
            expected = 3 if first_person else 4
            if not expected_png_count(output, expected):
                failures.append(
                    f"{label}: expected {expected} PNG evidence files, found "
                    f"{len(list(output.glob('*.png')))}")
            row_failures = validate_world_pose(metrics, label)
            summary = None
            if first_person:
                unified_failures, summary = validate_unified_view(
                    metrics, label, case["stance"], case.get("weapon_bone"))
                row_failures.extend(unified_failures)
            failures.extend(row_failures)
            records.append({
                "subject": unit,
                "view": view_kind,
                "pose": case["name"],
                "animation": case["animation"],
                "stance": case["stance"] if first_person else None,
                "minimum_y": metrics.get("overall_min_y"),
                "hand_pivot_distance": metrics.get("hand_pivot_distance"),
                "unified_view": summary,
                "result": "FAIL" if row_failures else "PASS",
            })


def render_mass(assets: Path, batch: Path,
                failures: list[str], records: list[dict]) -> None:
    hashes = {}
    for animation, pose, sample_time, with_lance in MASS_POSES:
        output = batch / "mass" / pose
        output.mkdir(parents=True, exist_ok=False)
        case = {"animation": animation, "time": sample_time,
                "geo_cube_bones": ("replica_lance",) if with_lance else ()}
        ok, log = run_command(render_command(
            assets, "mass_production_eva", case, output, False))
        label = f"mass/third_person/{pose}"
        if not ok:
            failures.append(f"{label}: renderer failed: {log[-500:]}")
            continue
        try:
            metrics = read_single_metrics(output)
        except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as error:
            failures.append(f"{label}: {error}")
            continue
        if pose != "revive":
            failures.extend(validate_world_pose(metrics, label, require_hands=False))
        sheets = list(output.glob("*_sheet.png"))
        if len(sheets) != 1:
            failures.append(f"{label}: expected one contact sheet")
        else:
            hashes[pose] = digest(sheets[0])
        records.append({"subject": "mass", "view": "third_person",
                        "pose": pose, "minimum_y": metrics.get("overall_min_y")})
    if len(hashes) != len(MASS_POSES):
        failures.append("mass: incomplete five-state evidence")
    elif len(set(hashes.values())) != len(hashes):
        failures.append("mass: two or more state contact sheets are identical")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--output", type=Path,
                        default=REPO / "external-assets/work/eva-offline-validation")
    args = parser.parse_args()

    batch = args.output / datetime.now().strftime("%Y%m%d-%H%M%S")
    batch.mkdir(parents=True, exist_ok=False)
    failures: list[str] = []
    records: list[dict] = []

    required = [WORLD_RENDERER, UNIFIED_AUDIT]
    for unit in UNITS:
        stem = f"eva_{unit}"
        required.extend((
            args.assets / "mesh" / f"{stem}.mesh.json",
            args.assets / "geo" / f"{stem}.geo.json",
            args.assets / "animations" / f"{stem}.animation.json",
            args.assets / "textures/entity" / f"{stem}.png",
        ))
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        failures.append("missing required input: " + ", ".join(missing))
    else:
        for unit in UNITS:
            render_unit(args.assets, batch, unit, failures, records)
        render_mass(args.assets, batch, failures, records)

    evidence = [
        {"path": str(path.relative_to(batch)), "sha256": digest(path)}
        for path in sorted(batch.rglob("*.png"))
    ]
    manifest = {
        "batch": batch.name,
        "result": "FAIL" if failures else "PASS",
        "architecture": {
            "render_source": "one complete world entity",
            "pose_source": "one Gecko skeleton and animation evaluation",
            "pilot_camera": "EVA eye socket looking along local -Z",
            "hidden_roots_allowed": sorted(ALLOWED_CAMERA_COVER_BONES),
            "low_stance_exact_camera_clip_parts": {
                stance: sorted(parts)
                for stance, parts in LOW_STANCE_EXACT_HIDDEN_PARTS.items()
            },
            "head_socket_offset_ranges_model_pixels": HEAD_SOCKET_OFFSET_RANGES,
            "render_hand": "cancel vanilla player hand only; no EVA arm pass",
            "negative_viewmodel_scale": "rejected",
        },
        "failures": failures,
        "records": records,
        "evidence": evidence,
        "note": ("Offline static evidence only. PASS is not a Minecraft runtime "
                 "or human visual acceptance result."),
    }
    (batch / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"EVA unified offline matrix: {manifest['result']} -> {batch}")
    for failure in failures:
        print(f"  FAIL: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
