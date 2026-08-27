#!/usr/bin/env python3
"""Redirect a reviewed lateral hand strike into a forward EVA battering arc."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix


ARM_NAMES = {
    "left": [
        "clavicle_l_protract", "clavicle_l_elevate",
        "shoulder_l_abduct", "shoulder_l_flex", "shoulder_l_twist",
        "elbow_l", "forearm_twist_l", "wrist_l_deviation", "wrist_l_flex",
    ],
    "right": [
        "clavicle_r_protract", "clavicle_r_elevate",
        "shoulder_r_abduct", "shoulder_r_flex", "shoulder_r_twist",
        "elbow_r", "forearm_twist_r", "wrist_r_deviation", "wrist_r_flex",
    ],
}

TARGET_OBJECTS = {
    "abdomen": ("body", "abdomen"), "thorax": ("body", "thorax"),
    "neck": ("body", "neck"), "head": ("body", "head"),
    "shoulder_l": ("body", "upper_arm_l"),
    "elbow_l": ("body", "elbow_link_l"),
    "wrist_l": ("body", "wrist_link_l"),
    "hand_l": ("geom", "knuckle_l"),
    "shoulder_r": ("body", "upper_arm_r"),
    "elbow_r": ("body", "elbow_link_r"),
    "wrist_r": ("body", "wrist_link_r"),
    "hand_r": ("geom", "knuckle_r"),
    "hip_l": ("body", "thigh_l"), "knee_l": ("body", "shin_l"),
    "ankle_l": ("body", "ankle_link_l"), "toe_l": ("body", "toe_l"),
    "hip_r": ("body", "thigh_r"), "knee_r": ("body", "shin_r"),
    "ankle_r": ("body", "ankle_link_r"), "toe_r": ("body", "toe_r"),
}


def metadata(model_path: Path):
    root = ET.parse(model_path).getroot()
    custom = root.find("custom")
    names = next(
        item.attrib["data"].split() for item in custom.findall("text")
        if item.attrib["name"] == "tangent_joint_names"
    )
    numeric = {
        item.attrib["name"]: np.asarray(
            [float(value) for value in item.attrib["data"].split()],
            dtype=np.float64,
        )
        for item in custom.findall("numeric")
    }
    return names, numeric["tangent_joint_lower_rad"], numeric[
        "tangent_joint_upper_rad"
    ]


def smooth(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--side", choices=("left", "right"), default="right")
    parser.add_argument("--contact-phase", type=float, default=0.65)
    parser.add_argument(
        "--target-yaw-degrees", type=float, default=0.0,
        help="Desired horizontal shoulder-to-hand yaw; 0 is straight forward.",
    )
    parser.add_argument("--pose-weight", type=float, default=0.65)
    parser.add_argument("--hand-weight", type=float, default=24.0)
    parser.add_argument("--wrist-weight", type=float, default=12.0)
    parser.add_argument("--elbow-weight", type=float, default=2.5)
    parser.add_argument("--delta-velocity-weight", type=float, default=5.0)
    parser.add_argument("--delta-acceleration-weight", type=float, default=9.0)
    parser.add_argument("--max-nfev", type=int, default=40)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    state = np.load(args.state)
    tangent_names, lower, upper = metadata(args.model)
    if tangent_names != [str(value) for value in state["tangent_names"]]:
        raise RuntimeError("tangent contract mismatch")
    arm_indices = [tangent_names.index(name) for name in ARM_NAMES[args.side]]
    tangent_source = np.asarray(state["tangent"], dtype=np.float64)
    qpos_source = np.asarray(state["qpos"], dtype=np.float64)
    target_names = [str(value) for value in state["target_landmark_names"]]
    desired_source = np.asarray(state["desired_positions"], dtype=np.float64)
    frame_count = len(qpos_source)
    contact = int(round(args.contact_phase * (frame_count - 1)))
    side = "l" if args.side == "left" else "r"
    shoulder_index = target_names.index(f"shoulder_{side}")
    elbow_index = target_names.index(f"elbow_{side}")
    wrist_index = target_names.index(f"wrist_{side}")
    hand_index = target_names.index(f"hand_{side}")
    height = 3.466729315

    joint_groups = {}
    for tangent_index, name in enumerate(tangent_names):
        actuator = model.actuator(f"a_{name}").id
        joint = int(model.actuator_trnid[actuator, 0])
        joint_groups.setdefault(joint, []).append({
            "index": tangent_index,
            "axis": np.asarray(model.actuator_gear[actuator, :3],
                               dtype=np.float64).copy(),
        })

    def set_tangent(value: np.ndarray) -> None:
        for joint, specs in joint_groups.items():
            address = int(model.jnt_qposadr[joint])
            if int(model.jnt_type[joint]) == mujoco.mjtJoint.mjJNT_BALL:
                vector = sum(
                    (spec["axis"] * value[spec["index"]] for spec in specs),
                    np.zeros(3, dtype=np.float64),
                )
                angle = float(np.linalg.norm(vector))
                if angle < 1.0e-10:
                    data.qpos[address:address + 4] = (1.0, 0.0, 0.0, 0.0)
                else:
                    axis = vector / angle
                    data.qpos[address:address + 4] = np.concatenate((
                        [math.cos(angle * 0.5)],
                        axis * math.sin(angle * 0.5),
                    ))
            else:
                data.qpos[address] = value[specs[0]["index"]]

    object_ids = []
    for name in target_names:
        object_type, object_name = TARGET_OBJECTS[name]
        enum = (mujoco.mjtObj.mjOBJ_BODY if object_type == "body"
                else mujoco.mjtObj.mjOBJ_GEOM)
        object_ids.append((object_type,
                           mujoco.mj_name2id(model, enum, object_name)))

    def apply(frame: int, arm_value: np.ndarray):
        full = tangent_source[frame].copy()
        full[arm_indices] = arm_value
        data.qpos[:] = qpos_source[frame]
        set_tangent(full)
        mujoco.mj_forward(model, data)
        actual = np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in object_ids
        ])
        return full, data.qpos.copy(), actual

    baseline_actual = []
    for frame in range(frame_count):
        _, _, actual = apply(frame, tangent_source[frame, arm_indices])
        baseline_actual.append(actual)
    baseline_actual = np.asarray(baseline_actual, dtype=np.float64)
    contact_vector = (
        baseline_actual[contact, hand_index]
        - baseline_actual[contact, shoulder_index]
    )
    source_yaw = math.atan2(contact_vector[1], contact_vector[0])
    target_yaw = math.radians(args.target_yaw_degrees)
    yaw_correction = target_yaw - source_yaw

    target_hand = desired_source[:, hand_index].copy()
    target_wrist = desired_source[:, wrist_index].copy()
    target_elbow = desired_source[:, elbow_index].copy()
    envelopes = []
    for frame in range(frame_count):
        if frame <= contact:
            envelope = smooth(frame / max(1, contact))
        else:
            envelope = smooth(
                (frame_count - 1 - frame)
                / max(1, frame_count - 1 - contact)
            )
        envelopes.append(envelope)
        angle = yaw_correction * envelope
        cosine = math.cos(angle)
        sine = math.sin(angle)
        rotation = np.asarray([
            [cosine, -sine, 0.0],
            [sine, cosine, 0.0],
            [0.0, 0.0, 1.0],
        ])
        shoulder = desired_source[frame, shoulder_index]
        target_hand[frame] = shoulder + rotation @ (
            desired_source[frame, hand_index] - shoulder
        )
        target_wrist[frame] = shoulder + rotation @ (
            desired_source[frame, wrist_index] - shoulder
        )
        target_elbow[frame] = shoulder + rotation @ (
            desired_source[frame, elbow_index] - shoulder
        )
    envelopes = np.asarray(envelopes, dtype=np.float64)

    initial = tangent_source[:, arm_indices].copy()
    x0 = initial.ravel()
    bounds = (
        np.tile(lower[arm_indices], frame_count),
        np.tile(upper[arm_indices], frame_count),
    )
    dependencies = []

    def residual(flat: np.ndarray, record: bool = False):
        values = flat.reshape(frame_count, len(arm_indices))
        rows = []

        def add(array, frames):
            flattened = np.asarray(array, dtype=np.float64).ravel()
            rows.extend(flattened)
            if record:
                dependencies.extend([tuple(frames)] * len(flattened))

        for frame in range(frame_count):
            _, _, actual = apply(frame, values[frame])
            add(args.pose_weight * (values[frame] - initial[frame]), (frame,))
            add(args.hand_weight * (
                actual[hand_index] - target_hand[frame]
            ) / height, (frame,))
            add(args.wrist_weight * (
                actual[wrist_index] - target_wrist[frame]
            ) / height, (frame,))
            add(args.elbow_weight * (
                actual[elbow_index] - target_elbow[frame]
            ) / height, (frame,))
            if frame > 0:
                correction_velocity = (
                    values[frame] - initial[frame]
                    - values[frame - 1] + initial[frame - 1]
                )
                add(args.delta_velocity_weight * correction_velocity,
                    (frame - 1, frame))
            if frame > 1:
                correction_acceleration = (
                    values[frame] - initial[frame]
                    - 2.0 * (values[frame - 1] - initial[frame - 1])
                    + values[frame - 2] - initial[frame - 2]
                )
                add(args.delta_acceleration_weight * correction_acceleration,
                    (frame - 2, frame - 1, frame))
        return np.asarray(rows, dtype=np.float64)

    residual(x0, record=True)
    sparsity = lil_matrix((len(dependencies), len(x0)), dtype=np.int8)
    width = len(arm_indices)
    for row, frames in enumerate(dependencies):
        for frame in frames:
            sparsity[row, frame * width:(frame + 1) * width] = 1
    result = least_squares(
        residual, x0, bounds=bounds, jac_sparsity=sparsity.tocsr(),
        method="trf", max_nfev=args.max_nfev, verbose=1,
        ftol=1.0e-6, xtol=1.0e-6, gtol=1.0e-6,
    )
    solved = result.x.reshape(frame_count, width)
    tangent = tangent_source.copy()
    tangent[:, arm_indices] = solved
    qpos = []
    actual = []
    for frame in range(frame_count):
        _, qpos_row, actual_row = apply(frame, solved[frame])
        qpos.append(qpos_row)
        actual.append(actual_row)
    qpos = np.asarray(qpos, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    dt = float(state["timestep"][0])
    qvel = np.zeros((frame_count, model.nv), dtype=np.float64)
    for frame in range(frame_count):
        before = max(0, frame - 1)
        after = min(frame_count - 1, frame + 1)
        mujoco.mj_differentiatePos(
            model, qvel[frame], max(dt, (after - before) * dt),
            qpos[before], qpos[after],
        )
    desired = desired_source.copy()
    desired[:, hand_index] = target_hand
    desired[:, wrist_index] = target_wrist
    desired[:, elbow_index] = target_elbow
    fields = {key: state[key] for key in state.files}
    fields.update({
        "tangent": tangent, "qpos": qpos, "qvel": qvel,
        "desired_positions": desired, "actual_positions": actual,
        "strike_redirect_envelope": envelopes,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **fields)
    final_vector = actual[contact, hand_index] - actual[contact, shoulder_index]
    report = {
        "schema": 1,
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "side": args.side,
        "contact_frame": contact,
        "source_contact_yaw_degrees": math.degrees(source_yaw),
        "requested_yaw_correction_degrees": math.degrees(yaw_correction),
        "target_yaw_degrees": args.target_yaw_degrees,
        "final_contact_yaw_degrees": math.degrees(math.atan2(
            final_vector[1], final_vector[0]
        )),
        "maximum_arm_tangent_change_rad": float(np.max(np.abs(
            solved - initial
        ))),
        "cost_before": float(0.5 * np.dot(residual(x0), residual(x0))),
        "cost_after": float(result.cost),
        "nfev": int(result.nfev),
        "success": bool(result.success),
        "roots_and_lower_body_changed": False,
        "status": "project_authored_forward_strike_kinematic_candidate",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
