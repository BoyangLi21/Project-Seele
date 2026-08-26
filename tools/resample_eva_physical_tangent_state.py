#!/usr/bin/env python3
"""Resample a 41-DOF EVA tangent-state trajectory without quaternion lerp."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation, Slerp


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
        "tangent_joint_upper_rad"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--fps", type=float, default=60.0)
    parser.add_argument(
        "--allow-contact-interpolation-research",
        action="store_true",
        help=("Permit a known-nonproduction interpolation across contact "
              "frames. Contact-bearing motions must normally be solved "
              "directly at the target rate."),
    )
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    state = np.load(args.state)
    source_dt = float(state["timestep"][0])
    tangent = np.asarray(state["tangent"], dtype=np.float64)
    tangent_names = [str(value) for value in state["tangent_names"]]
    contract_names, lower, upper = metadata(args.model)
    if tangent_names != contract_names:
        raise RuntimeError("state tangent order does not match model contract")
    source_qpos = np.asarray(state["qpos"], dtype=np.float64)
    source_contacts = np.asarray(state["foot_contact"], dtype=np.bool_)
    if (np.any(source_contacts)
            and not args.allow_contact_interpolation_research):
        raise RuntimeError(
            "contact-bearing trajectories cannot be resampled by tangent "
            "PCHIP: solve IK directly at the target rate instead"
        )
    source_times = np.arange(len(source_qpos), dtype=np.float64) * source_dt
    duration = source_times[-1]
    target_dt = 1.0 / args.fps
    target_times = np.arange(
        0.0, duration + target_dt * 0.25, target_dt, dtype=np.float64
    )
    target_times[-1] = min(target_times[-1], duration)

    tangent_resampled = PchipInterpolator(
        source_times, tangent, axis=0
    )(target_times)
    tangent_resampled = np.clip(tangent_resampled, lower, upper)
    root_position = PchipInterpolator(
        source_times, source_qpos[:, :3], axis=0
    )(target_times)
    source_quaternion = source_qpos[:, 3:7].copy()
    for index in range(1, len(source_quaternion)):
        if np.dot(source_quaternion[index - 1], source_quaternion[index]) < 0.0:
            source_quaternion[index] *= -1.0
    rotation = Rotation.from_quat(np.column_stack((
        source_quaternion[:, 1], source_quaternion[:, 2],
        source_quaternion[:, 3], source_quaternion[:, 0],
    )))
    root_xyzw = Slerp(source_times, rotation)(target_times).as_quat()
    root_quaternion = np.column_stack((
        root_xyzw[:, 3], root_xyzw[:, 0], root_xyzw[:, 1], root_xyzw[:, 2]
    ))

    joint_groups = {}
    for index, name in enumerate(contract_names):
        actuator = model.actuator(f"a_{name}").id
        joint = int(model.actuator_trnid[actuator, 0])
        joint_groups.setdefault(joint, []).append({
            "index": index,
            "axis": np.asarray(model.actuator_gear[actuator, :3],
                               dtype=np.float64).copy(),
        })

    def set_tangent(value: np.ndarray) -> None:
        for joint, specs in joint_groups.items():
            address = int(model.jnt_qposadr[joint])
            joint_type = int(model.jnt_type[joint])
            if joint_type == mujoco.mjtJoint.mjJNT_BALL:
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

    target_names = [str(value) for value in state["target_landmark_names"]]
    object_ids = []
    for name in target_names:
        object_type, object_name = TARGET_OBJECTS[name]
        enum = (mujoco.mjtObj.mjOBJ_BODY if object_type == "body"
                else mujoco.mjtObj.mjOBJ_GEOM)
        object_ids.append((
            object_type,
            mujoco.mj_name2id(model, enum, object_name),
        ))
    qpos = []
    actual = []
    for position, quaternion, tangent_row in zip(
            root_position, root_quaternion, tangent_resampled):
        data.qpos[:] = model.qpos0
        data.qpos[:3] = position
        data.qpos[3:7] = quaternion
        set_tangent(tangent_row)
        mujoco.mj_forward(model, data)
        qpos.append(data.qpos.copy())
        actual.append(np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in object_ids
        ]))
    qpos = np.asarray(qpos, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    qvel = np.zeros((len(qpos), model.nv), dtype=np.float64)
    for index in range(1, len(qpos)):
        mujoco.mj_differentiatePos(
            model, qvel[index], target_dt, qpos[index - 1], qpos[index]
        )
    if len(qpos) > 1:
        qvel[0] = qvel[1]

    desired = PchipInterpolator(
        source_times,
        np.asarray(state["desired_positions"], dtype=np.float64),
        axis=0,
    )(target_times)
    contact_indices = np.minimum(
        np.floor(target_times / source_dt + 1.0e-8).astype(int),
        len(source_contacts) - 1,
    )
    contacts = source_contacts[contact_indices]
    contact_blend = None
    if "contact_blend" in state.files:
        source_blend = np.asarray(state["contact_blend"], dtype=np.float64)
        contact_blend = PchipInterpolator(
            source_times, source_blend, axis=0
        )(target_times)
        contact_blend = np.clip(contact_blend, 0.0, 1.0)
    source_frames = np.asarray(state["source_frames"], dtype=np.float64)
    frame_values = np.interp(target_times, source_times, source_frames)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_fields = dict(
        qpos=qpos,
        qvel=qvel,
        timestep=np.asarray([target_dt], dtype=np.float64),
        source_frames=frame_values,
        foot_contact=contacts,
        tangent=tangent_resampled,
        tangent_names=np.asarray(tangent_names),
        target_landmark_names=np.asarray(target_names),
        desired_positions=desired,
        actual_positions=actual,
    )
    if contact_blend is not None:
        output_fields["contact_blend"] = contact_blend
    np.savez_compressed(args.output, **output_fields)
    report = {
        "schema": 1,
        "model": str(args.model.resolve()),
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "source_fps": 1.0 / source_dt,
        "output_fps": args.fps,
        "source_frames": len(source_qpos),
        "output_frames": len(qpos),
        "duration_seconds": duration,
        "method": "PCHIP tangent/root translation plus quaternion Slerp",
        "contact_interpolation_research_only": bool(np.any(source_contacts)),
        "maximum_tangent_frame_step": float(np.max(
            np.abs(np.diff(tangent_resampled, axis=0)), initial=0.0
        )),
        "limit_violation_count": int(np.sum(
            (tangent_resampled < lower) | (tangent_resampled > upper)
        )),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
