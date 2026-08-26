#!/usr/bin/env python3
"""Audit a kinematic source-to-EVA physical-rig retarget candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np


GROUPS = {
    "effectors": [
        "head", "wrist_l", "hand_l", "wrist_r", "hand_r",
        "ankle_l", "toe_l", "ankle_r", "toe_r",
    ],
    "articulation_guides": ["elbow_l", "elbow_r", "knee_l", "knee_r"],
    "morphology_guides": [
        "abdomen", "thorax", "neck", "shoulder_l", "shoulder_r",
        "hip_l", "hip_r",
    ],
}


def runs(values: np.ndarray) -> list[tuple[int, int]]:
    result = []
    first = None
    for index, value in enumerate(values):
        if value and first is None:
            first = index
        if first is not None and (not value or index == len(values) - 1):
            last = index if value and index == len(values) - 1 else index - 1
            if last - first + 1 >= 3:
                result.append((first, last))
            first = None
    return result


def geom_lowest_point(model: mujoco.MjModel, data: mujoco.MjData,
                      geom_name: str) -> np.ndarray:
    geom_id = model.geom(geom_name).id
    rotation = data.geom_xmat[geom_id].reshape(3, 3)
    size = np.asarray(model.geom_size[geom_id], dtype=np.float64)
    geom_type = int(model.geom_type[geom_id])
    if geom_type == mujoco.mjtGeom.mjGEOM_BOX:
        local = -np.sign(rotation[2]) * size
        point = data.geom_xpos[geom_id] + rotation @ local
    elif geom_type == mujoco.mjtGeom.mjGEOM_ELLIPSOID:
        local_down = -(rotation.T @ np.asarray((0.0, 0.0, 1.0)))
        denominator = float(np.sqrt(np.sum((size * local_down) ** 2)))
        local = (size * size * local_down) / max(denominator, 1.0e-12)
        point = data.geom_xpos[geom_id] + rotation @ local
    else:
        raise RuntimeError(f"unsupported sole geometry {geom_name}")
    return np.asarray(point, dtype=np.float64)


def geom_bottom(model: mujoco.MjModel, data: mujoco.MjData,
                geom_name: str) -> float:
    return float(geom_lowest_point(model, data, geom_name)[2])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--profile", choices=("combat", "pounce"),
                        default="combat")
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    state = np.load(args.state)
    qpos = np.asarray(state["qpos"], dtype=np.float64)
    qvel = np.asarray(state["qvel"], dtype=np.float64)
    dt = float(state["timestep"][0])
    contacts = np.asarray(state["foot_contact"], dtype=np.bool_)
    contact_blend = (
        np.asarray(state["contact_blend"], dtype=np.float64)
        if "contact_blend" in state else np.ones_like(contacts, dtype=np.float64)
    )
    stable_contacts = contacts & (contact_blend >= 0.999)
    names = [str(value) for value in state["target_landmark_names"]]
    desired = np.asarray(state["desired_positions"], dtype=np.float64)
    actual = np.asarray(state["actual_positions"], dtype=np.float64)
    errors = np.linalg.norm(actual - desired, axis=2)

    mujoco.mj_forward(model, data)
    height = float(
        data.xpos[model.body("head").id, 2]
        - min(data.xpos[model.body("foot_l").id, 2],
              data.xpos[model.body("foot_r").id, 2])
    )
    errors_h = errors / height
    group_report = {}
    for group_name, group_landmarks in GROUPS.items():
        indices = [names.index(name) for name in group_landmarks]
        values = errors_h[:, indices]
        per_landmark = {
            name: {
                "mean_H": float(np.mean(errors_h[:, names.index(name)])),
                "p95_H": float(np.percentile(
                    errors_h[:, names.index(name)], 95.0
                )),
                "maximum_H": float(np.max(
                    errors_h[:, names.index(name)]
                )),
            }
            for name in group_landmarks
        }
        worst = max(
            per_landmark,
            key=lambda name: per_landmark[name]["p95_H"],
        )
        group_report[group_name] = {
            "mean_H": float(np.mean(values)),
            "p95_H": float(np.percentile(values, 95.0)),
            "maximum_H": float(np.max(values)),
            "worst_landmark_p95": worst,
            "worst_landmark_p95_H": per_landmark[worst]["p95_H"],
            "per_landmark": per_landmark,
        }

    foot_positions = {"l": [], "r": []}
    foot_bottoms = {"l": [], "r": []}
    patch_names = ("heel", "forefoot", "toe")
    foot_patches = {
        side: {patch: [] for patch in patch_names}
        for side in ("l", "r")
    }
    ground_z = float(data.geom_xpos[model.geom("ground").id, 2])
    root_positions = []
    for row, velocity in zip(qpos, qvel):
        data.qpos[:] = row
        data.qvel[:] = velocity
        mujoco.mj_forward(model, data)
        root_positions.append(data.xpos[model.body("pelvis").id].copy())
        for side in ("l", "r"):
            ankle = data.xpos[model.body(f"foot_{side}").id]
            toe = data.xpos[model.body(f"toe_{side}").id]
            foot_positions[side].append((ankle + toe) * 0.5)
            foot_bottoms[side].append(min(
                geom_bottom(model, data, f"heel_{side}"),
                geom_bottom(model, data, f"forefoot_{side}"),
                geom_bottom(model, data, f"toe_{side}_collision"),
            ) - ground_z)
            for patch in patch_names:
                geom_name = (f"toe_{side}_collision" if patch == "toe"
                             else f"{patch}_{side}")
                geom_id = model.geom(geom_name).id
                patch_point = data.geom_xpos[geom_id].copy()
                patch_point[2] = geom_bottom(model, data, geom_name)
                foot_patches[side][patch].append(patch_point)
    root_positions = np.asarray(root_positions)
    foot_report = {}
    for side_index, side in enumerate(("l", "r")):
        values = np.asarray(foot_positions[side])
        bottom = np.asarray(foot_bottoms[side], dtype=np.float64) / height
        stable_bottom = bottom[stable_contacts[:, side_index]]
        drift_rows = []
        patch_report = {}
        for patch in patch_names:
            patch_values = np.asarray(foot_patches[side][patch])
            patch_clearance = (
                patch_values[:, 2] - ground_z
            ) / height
            patch_active = (
                stable_contacts[:, side_index]
                & (np.abs(patch_clearance) <= 0.005)
            )
            patch_velocity = np.zeros(len(patch_values), dtype=np.float64)
            if len(patch_values) > 1:
                patch_velocity[1:] = np.linalg.norm(
                    np.diff(patch_values[:, :2], axis=0), axis=1
                ) / dt / height
                patch_velocity[0] = patch_velocity[1]
            patch_rows = []
            for first, last in runs(patch_active):
                relative = (
                    patch_values[first:last + 1, :2]
                    - patch_values[first, :2]
                )
                row = {
                    "patch": patch,
                    "frames": [int(first), int(last)],
                    "maximum_drift_H": float(
                        np.max(np.linalg.norm(relative, axis=1)) / height
                    ),
                    "speed_p95_H_per_s": float(np.percentile(
                        patch_velocity[first:last + 1], 95.0
                    )),
                }
                patch_rows.append(row)
                drift_rows.append(row)
            patch_report[patch] = {
                "active_fraction": float(np.mean(patch_active)),
                "segments": patch_rows,
            }
        foot_report[side] = {
            "contact_fraction": float(np.mean(contacts[:, side_index])),
            "stable_contact_fraction": float(np.mean(
                stable_contacts[:, side_index]
            )),
            "segments": drift_rows,
            "patches": patch_report,
            "maximum_contact_drift_H": max(
                (row["maximum_drift_H"] for row in drift_rows), default=None
            ),
            "maximum_segment_speed_p95_H_per_s": max(
                (row["speed_p95_H_per_s"] for row in drift_rows), default=None
            ),
            "grounding": {
                "stable_samples": int(len(stable_bottom)),
                "stable_mean_signed_clearance_H": (
                    float(np.mean(stable_bottom))
                    if len(stable_bottom) else None
                ),
                "stable_mean_absolute_clearance_H": (
                    float(np.mean(np.abs(stable_bottom)))
                    if len(stable_bottom) else None
                ),
                "stable_absolute_clearance_p95_H": (
                    float(np.percentile(np.abs(stable_bottom), 95.0))
                    if len(stable_bottom) else None
                ),
                "maximum_hover_H": float(np.max(bottom)),
                "maximum_penetration_H": float(max(0.0, -np.min(bottom))),
            },
        }

    root_steps = np.linalg.norm(np.diff(root_positions, axis=0), axis=1) / height
    tangent_report = None
    if "tangent" in state:
        tangent = np.asarray(state["tangent"], dtype=np.float64)
        tangent_names = [str(value) for value in state["tangent_names"]]
        # The solver already enforces component bounds. Saturation is reported
        # separately because it usually indicates a bad bind/target, not a
        # formal limit violation.
        span = np.maximum(np.ptp(tangent, axis=0), 1.0e-8)
        steps = np.abs(np.diff(tangent, axis=0))
        maximum_step_index = (
            np.unravel_index(np.argmax(steps), steps.shape)
            if steps.size else (0, 0)
        )
        tangent_report = {
            "names": tangent_names,
            "range_observed": {
                name: [float(np.min(tangent[:, index])),
                       float(np.max(tangent[:, index]))]
                for index, name in enumerate(tangent_names)
            },
            "maximum_frame_step": float(np.max(steps, initial=0.0)),
            "maximum_frame_step_tangent": (
                tangent_names[maximum_step_index[1]] if steps.size else None
            ),
            "maximum_frame_step_destination_frame": (
                int(maximum_step_index[0] + 1) if steps.size else None
            ),
            "frame_step_p95": float(
                np.percentile(steps, 95.0) if steps.size else 0.0
            ),
            "observed_span": {
                name: float(span[index]) for index, name in enumerate(tangent_names)
            },
        }

    failures = []
    if group_report["effectors"]["p95_H"] > 0.02:
        failures.append("effector_p95_over_0_02H")
    individual_effector_limit = 0.035 if args.profile == "pounce" else 0.03
    if group_report["effectors"][
            "worst_landmark_p95_H"] > individual_effector_limit:
        failures.append("individual_effector_p95_over_profile_limit")
    if group_report["articulation_guides"]["p95_H"] > 0.05:
        failures.append("articulation_p95_over_0_05H")
    if group_report["articulation_guides"][
            "worst_landmark_p95_H"] > 0.06:
        failures.append("individual_articulation_p95_over_0_06H")
    for side, row in foot_report.items():
        if row["maximum_contact_drift_H"] is not None and (
                row["maximum_contact_drift_H"] > 0.005):
            failures.append(f"{side}_contact_drift_over_0_005H")
        if row["maximum_segment_speed_p95_H_per_s"] is not None and (
                row["maximum_segment_speed_p95_H_per_s"] > 0.02):
            failures.append(f"{side}_contact_speed_over_0_02H_per_s")
        grounding = row["grounding"]
        if row["stable_contact_fraction"] > 0.0 and (
                grounding["stable_samples"] == 0):
            failures.append(f"{side}_missing_stable_ground_samples")
        if (grounding["stable_mean_absolute_clearance_H"] is not None
                and grounding["stable_mean_absolute_clearance_H"] > 0.002):
            failures.append(f"{side}_contact_mean_clearance_over_0_002H")
        if (grounding["stable_absolute_clearance_p95_H"] is not None
                and grounding["stable_absolute_clearance_p95_H"] > 0.005):
            failures.append(f"{side}_contact_clearance_p95_over_0_005H")
        if grounding["maximum_penetration_H"] > 0.004:
            failures.append(f"{side}_penetration_over_0_004H")
    root_step_limit = 0.06 if args.profile == "pounce" else 0.025
    if float(np.max(root_steps, initial=0.0)) > root_step_limit:
        failures.append("root_step_over_profile_limit")
    if tangent_report is not None:
        tangent_step_limit = 0.30 if args.profile == "pounce" else 0.25
        if tangent_report["maximum_frame_step"] > tangent_step_limit:
            failures.append("tangent_frame_step_over_profile_limit")

    report = {
        "schema": 1,
        "model": str(args.model.resolve()),
        "state": str(args.state.resolve()),
        "frames": len(qpos),
        "fps": 1.0 / dt,
        "body_height_units": height,
        "profile": args.profile,
        "limits": {
            "individual_effector_p95_H": individual_effector_limit,
            "root_step_H": root_step_limit,
            "tangent_frame_step": (
                0.30 if args.profile == "pounce" else 0.25
            ),
            "contact_mean_absolute_clearance_H": 0.002,
            "contact_absolute_clearance_p95_H": 0.005,
            "maximum_penetration_H": 0.004,
        },
        "groups": group_report,
        "feet": foot_report,
        "maximum_root_step_H": float(np.max(root_steps, initial=0.0)),
        "tangent": tangent_report,
        "failures": failures,
        "passed": not failures,
        "status": "kinematic_retarget_audit_not_physical_tracking",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "passed": report["passed"],
        "effectors_p95_H": group_report["effectors"]["p95_H"],
        "articulation_p95_H": group_report["articulation_guides"]["p95_H"],
        "left_drift_H": foot_report["l"]["maximum_contact_drift_H"],
        "right_drift_H": foot_report["r"]["maximum_contact_drift_H"],
        "failures": failures,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
