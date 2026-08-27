#!/usr/bin/env python3
"""Ground a kinematic EVA reference by vertical free-root correction only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from audit_eva_physical_retarget import geom_bottom


TARGET_OBJECTS = {
    "abdomen": ("body", "abdomen"),
    "thorax": ("body", "thorax"),
    "neck": ("body", "neck"),
    "head": ("body", "head"),
    "shoulder_l": ("body", "upper_arm_l"),
    "elbow_l": ("body", "elbow_link_l"),
    "wrist_l": ("body", "wrist_link_l"),
    "hand_l": ("geom", "knuckle_l"),
    "shoulder_r": ("body", "upper_arm_r"),
    "elbow_r": ("body", "elbow_link_r"),
    "wrist_r": ("body", "wrist_link_r"),
    "hand_r": ("geom", "knuckle_r"),
    "hip_l": ("body", "thigh_l"),
    "knee_l": ("body", "shin_l"),
    "ankle_l": ("body", "ankle_link_l"),
    "toe_l": ("body", "toe_l"),
    "hip_r": ("body", "thigh_r"),
    "knee_r": ("body", "shin_r"),
    "ankle_r": ("body", "ankle_link_r"),
    "toe_r": ("body", "toe_r"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--uniform-depth-m", type=float, default=0.0,
        help="Optional small negative contact depth to guarantee manifolds.",
    )
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    source = np.load(args.state)
    qpos = np.asarray(source["qpos"], dtype=np.float64).copy()
    desired = np.asarray(source["desired_positions"], dtype=np.float64).copy()
    contacts = np.asarray(source["foot_contact"], dtype=np.bool_)
    contact_blend = (
        np.asarray(source["contact_blend"], dtype=np.float64)
        if "contact_blend" in source.files
        else np.ones_like(contacts, dtype=np.float64)
    )
    names = [str(value) for value in source["target_landmark_names"]]
    ground_z = 0.0
    contact_corrections = np.full(len(qpos), np.nan, dtype=np.float64)
    penetration_corrections = np.zeros(len(qpos), dtype=np.float64)
    for frame_index, row in enumerate(qpos):
        data.qpos[:] = row
        mujoco.mj_forward(model, data)
        side_bottoms = [
            min(
                geom_bottom(model, data, f"heel_{side}"),
                geom_bottom(model, data, f"forefoot_{side}"),
                geom_bottom(model, data, f"toe_{side}_collision"),
            )
            for side in ("l", "r")
        ]
        penetration_corrections[frame_index] = max(
            0.0, ground_z - min(side_bottoms)
        )
        stable_sides = [
            side_index for side_index in range(2)
            if (contacts[frame_index, side_index]
                and contact_blend[frame_index, side_index] >= 0.999)
        ]
        if stable_sides:
            contact_corrections[frame_index] = (
                ground_z - min(side_bottoms[index]
                               for index in stable_sides)
            )
    valid = np.flatnonzero(np.isfinite(contact_corrections))
    if len(valid):
        corrections = np.interp(
            np.arange(len(qpos), dtype=np.float64),
            valid.astype(np.float64), contact_corrections[valid],
        )
    else:
        corrections = np.zeros(len(qpos), dtype=np.float64)
    corrections = np.maximum(corrections, penetration_corrections)
    corrections += args.uniform_depth_m
    qpos[:, 2] += corrections
    desired[:, :, 2] += corrections[:, None]

    objects = []
    for name in names:
        object_type, object_name = TARGET_OBJECTS[name]
        object_id = mujoco.mj_name2id(
            model,
            (mujoco.mjtObj.mjOBJ_BODY if object_type == "body"
             else mujoco.mjtObj.mjOBJ_GEOM),
            object_name,
        )
        objects.append((object_type, object_id))
    actual = []
    for row in qpos:
        data.qpos[:] = row
        mujoco.mj_forward(model, data)
        actual.append(np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in objects
        ]))
    actual = np.asarray(actual, dtype=np.float64)
    dt = float(source["timestep"][0])
    qvel = np.zeros((len(qpos), model.nv), dtype=np.float64)
    for index in range(1, len(qpos)):
        mujoco.mj_differentiatePos(
            model, qvel[index], dt, qpos[index - 1], qpos[index]
        )
    if len(qpos) > 1:
        qvel[0] = qvel[1]

    output_fields = {key: source[key] for key in source.files}
    output_fields.update({
        "qpos": qpos,
        "qvel": qvel,
        "desired_positions": desired,
        "actual_positions": actual,
        "root_ground_correction_m": corrections,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **output_fields)
    step = np.abs(np.diff(corrections))
    acceleration = np.abs(np.diff(corrections, n=2))
    report = {
        "schema": 1,
        "model": str(args.model.resolve()),
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "method": (
            "stable-contact vertical free-root grounding, interpolated "
            "through flight and clamped only to prevent penetration; joint "
            "coordinates unchanged"
        ),
        "correction_m": {
            "minimum": float(np.min(corrections)),
            "maximum": float(np.max(corrections)),
            "maximum_frame_step": float(np.max(step, initial=0.0)),
            "p95_frame_step": float(
                np.percentile(step, 95.0) if len(step) else 0.0
            ),
            "p95_second_difference": float(
                np.percentile(acceleration, 95.0)
                if len(acceleration) else 0.0
            ),
        },
        "joint_coordinates_changed": False,
        "uniform_depth_m": args.uniform_depth_m,
        "runtime_root_write_authorized": False,
        "status": "offline_reference_grounding_not_runtime_root_control",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
