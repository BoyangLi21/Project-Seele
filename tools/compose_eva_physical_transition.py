#!/usr/bin/env python3
"""Compose two EVA physical references with a velocity-aware transition."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation, Slerp


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


def rotation_from_wxyz(value: np.ndarray) -> Rotation:
    return Rotation.from_quat((value[1], value[2], value[3], value[0]))


def wxyz_from_rotation(value: Rotation) -> np.ndarray:
    x, y, z, w = value.as_quat()
    return np.asarray((w, x, y, z), dtype=np.float64)


def yaw(value: Rotation) -> float:
    forward = value.apply((1.0, 0.0, 0.0))
    return math.atan2(float(forward[1]), float(forward[0]))


def hermite(first, first_velocity, last, last_velocity,
            phase: float, duration: float):
    u = phase
    h00 = 2.0 * u ** 3 - 3.0 * u ** 2 + 1.0
    h10 = u ** 3 - 2.0 * u ** 2 + u
    h01 = -2.0 * u ** 3 + 3.0 * u ** 2
    h11 = u ** 3 - u ** 2
    return (h00 * first + h10 * duration * first_velocity
            + h01 * last + h11 * duration * last_velocity)


def tangent_limits(model_path: Path, names: list[str]):
    root = ET.parse(model_path).getroot()
    custom = root.find("custom")
    contract_names = next(
        item.attrib["data"].split() for item in custom.findall("text")
        if item.attrib["name"] == "tangent_joint_names"
    )
    if contract_names != names:
        raise RuntimeError("model tangent contract differs from state")
    numeric = {
        item.attrib["name"]: np.asarray(
            [float(value) for value in item.attrib["data"].split()],
            dtype=np.float64,
        )
        for item in custom.findall("numeric")
    }
    return (numeric["tangent_joint_lower_rad"],
            numeric["tangent_joint_upper_rad"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--first", required=True, type=Path)
    parser.add_argument("--second", required=True, type=Path)
    parser.add_argument("--transition-frames", type=int, default=7)
    parser.add_argument("--contact-settle-frames", type=int, default=8)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    first = np.load(args.first)
    second = np.load(args.second)
    tangent_names = [str(value) for value in first["tangent_names"]]
    if tangent_names != [str(value) for value in second["tangent_names"]]:
        raise RuntimeError("tangent contracts differ")
    target_names = [str(value) for value in first["target_landmark_names"]]
    if target_names != [str(value) for value in second["target_landmark_names"]]:
        raise RuntimeError("target landmark contracts differ")
    dt = float(first["timestep"][0])
    if abs(dt - float(second["timestep"][0])) > 1.0e-9:
        raise RuntimeError("sample rates differ")
    transition_frames = max(1, args.transition_frames)
    contact_settle_frames = max(0, args.contact_settle_frames)

    tangent_first = np.asarray(first["tangent"], dtype=np.float64)
    tangent_second = np.asarray(second["tangent"], dtype=np.float64)
    qpos_first = np.asarray(first["qpos"], dtype=np.float64)
    qpos_second = np.asarray(second["qpos"], dtype=np.float64).copy()
    desired_first = np.asarray(first["desired_positions"], dtype=np.float64)
    desired_second = np.asarray(second["desired_positions"], dtype=np.float64)

    rotation_first_end = rotation_from_wxyz(qpos_first[-1, 3:7])
    rotation_second_start = rotation_from_wxyz(qpos_second[0, 3:7])
    alignment = Rotation.from_euler(
        "z", yaw(rotation_first_end) - yaw(rotation_second_start)
    )
    second_origin = qpos_second[0, :3].copy()
    aligned_origin = qpos_first[-1, :3].copy()
    qpos_second[:, :3] = (
        alignment.apply(qpos_second[:, :3] - second_origin)
        + aligned_origin
    )
    aligned_rotations = []
    for row in qpos_second:
        aligned = alignment * rotation_from_wxyz(row[3:7])
        row[3:7] = wxyz_from_rotation(aligned)
        aligned_rotations.append(aligned)
    desired_second_aligned = (
        alignment.apply(
            (desired_second - second_origin[None, None, :]).reshape(-1, 3)
        ).reshape(desired_second.shape)
        + aligned_origin[None, None, :]
    )

    tangent_velocity_first = (
        tangent_first[-1] - tangent_first[-2]
    ) / dt
    tangent_velocity_second = (
        tangent_second[1] - tangent_second[0]
    ) / dt
    root_velocity_first = (
        qpos_first[-1, :3] - qpos_first[-2, :3]
    ) / dt
    root_velocity_second = (
        qpos_second[1, :3] - qpos_second[0, :3]
    ) / dt
    duration = (transition_frames + 1) * dt
    phases = np.arange(1, transition_frames + 1, dtype=np.float64)
    phases /= transition_frames + 1
    transition_tangent = np.stack([
        hermite(tangent_first[-1], tangent_velocity_first,
                tangent_second[0], tangent_velocity_second,
                phase, duration)
        for phase in phases
    ])
    tangent_lower, tangent_upper = tangent_limits(args.model, tangent_names)
    raw_transition_tangent = transition_tangent.copy()
    transition_tangent = np.clip(
        transition_tangent, tangent_lower, tangent_upper
    )
    tangent_clamp = np.abs(transition_tangent - raw_transition_tangent)
    transition_root = np.stack([
        hermite(qpos_first[-1, :3], root_velocity_first,
                qpos_second[0, :3], root_velocity_second,
                phase, duration)
        for phase in phases
    ])
    slerp = Slerp(
        [0.0, 1.0],
        Rotation.concatenate((rotation_first_end, aligned_rotations[0])),
    )
    transition_rotation = slerp(phases)

    joint_groups = {}
    for tangent_index, name in enumerate(tangent_names):
        actuator_id = model.actuator(f"a_{name}").id
        joint_id = int(model.actuator_trnid[actuator_id, 0])
        joint_groups.setdefault(joint_id, []).append({
            "index": tangent_index,
            "axis": np.asarray(model.actuator_gear[actuator_id, :3],
                               dtype=np.float64).copy(),
        })

    def set_tangent(value):
        for joint_id, specs in joint_groups.items():
            address = int(model.jnt_qposadr[joint_id])
            if int(model.jnt_type[joint_id]) == mujoco.mjtJoint.mjJNT_BALL:
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
        object_id = mujoco.mj_name2id(
            model,
            (mujoco.mjtObj.mjOBJ_BODY if object_type == "body"
             else mujoco.mjtObj.mjOBJ_GEOM), object_name,
        )
        object_ids.append((object_type, object_id))

    transition_qpos = []
    transition_actual = []
    for position, rotation, tangent in zip(
            transition_root, transition_rotation, transition_tangent):
        data.qpos[:] = model.qpos0
        data.qpos[:3] = position
        data.qpos[3:7] = wxyz_from_rotation(rotation)
        set_tangent(tangent)
        mujoco.mj_forward(model, data)
        transition_qpos.append(data.qpos.copy())
        transition_actual.append(np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in object_ids
        ]))
    transition_qpos = np.asarray(transition_qpos, dtype=np.float64)
    transition_actual = np.asarray(transition_actual, dtype=np.float64)

    # A generated transition's FK trajectory is its explicit reference. The
    # source clips retain their independently audited desired landmarks.
    desired = np.concatenate((
        desired_first, transition_actual, desired_second_aligned
    ), axis=0)
    tangent = np.concatenate((
        tangent_first, transition_tangent, tangent_second
    ), axis=0)
    qpos = np.concatenate((qpos_first, transition_qpos, qpos_second), axis=0)
    contacts_first = np.asarray(first["foot_contact"], dtype=np.bool_)
    contacts_second = np.asarray(second["foot_contact"], dtype=np.bool_)
    common = contacts_first[-1] & contacts_second[0]
    transition_contacts = np.tile(common, (transition_frames, 1))
    blend_first = np.asarray(first["contact_blend"], dtype=np.float64)
    blend_second = np.asarray(second["contact_blend"], dtype=np.float64)
    smooth_phases = phases * phases * (3.0 - 2.0 * phases)
    transition_blend = np.stack([
        common.astype(np.float64) * (
            blend_first[-1] * (1.0 - phase)
            + blend_second[0] * phase
        )
        for phase in smooth_phases
    ])
    blend_second_output = blend_second.copy()
    settle = min(contact_settle_frames, len(blend_second_output))
    if settle > 1:
        for side in range(blend_second_output.shape[1]):
            if (common[side] and blend_first[-1, side] < 0.999
                    and blend_second[0, side] >= 0.999):
                blend_second_output[:settle - 1, side] = np.minimum(
                    blend_second_output[:settle - 1, side], 0.998
                )
    contacts = np.concatenate((
        contacts_first, transition_contacts, contacts_second
    ), axis=0)
    blend = np.concatenate((
        blend_first,
        transition_blend,
        blend_second_output,
    ), axis=0)
    actual = []
    for row in qpos:
        data.qpos[:] = row
        mujoco.mj_forward(model, data)
        actual.append(np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in object_ids
        ]))
    actual = np.asarray(actual, dtype=np.float64)
    qvel = np.zeros((len(qpos), model.nv), dtype=np.float64)
    for frame in range(len(qpos)):
        before = max(0, frame - 1)
        after = min(len(qpos) - 1, frame + 1)
        interval = max(dt, (after - before) * dt)
        mujoco.mj_differentiatePos(
            model, qvel[frame], interval, qpos[before], qpos[after]
        )
    provenance = np.asarray(
        ["first"] * len(qpos_first)
        + ["transition"] * transition_frames
        + ["second"] * len(qpos_second)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        qpos=qpos, qvel=qvel, tangent=tangent,
        tangent_names=np.asarray(tangent_names),
        timestep=np.asarray([dt], dtype=np.float64),
        source_frames=np.arange(len(qpos), dtype=np.float64),
        foot_contact=contacts, contact_blend=blend,
        target_landmark_names=np.asarray(target_names),
        desired_positions=desired, actual_positions=actual,
        source_provenance=provenance,
    )
    transition_steps = np.abs(np.diff(tangent, axis=0))
    report = {
        "schema": 1,
        "model": str(args.model.resolve()),
        "first": str(args.first.resolve()),
        "second": str(args.second.resolve()),
        "output": str(args.output.resolve()),
        "transition_frames": transition_frames,
        "common_support": common.tolist(),
        "root_alignment_yaw_rad": yaw(alignment),
        "maximum_tangent_step_rad": float(np.max(transition_steps)),
        "maximum_transition_tangent_step_rad": float(np.max(
            transition_steps[len(qpos_first) - 1:
                             len(qpos_first) + transition_frames]
        )),
        "transition_limit_clamp_count": int(np.count_nonzero(
            tangent_clamp > 1.0e-12
        )),
        "maximum_transition_limit_clamp_rad": float(np.max(
            tangent_clamp
        )),
        "transition_contact_blend_start": transition_blend[0].tolist(),
        "transition_contact_blend_end": transition_blend[-1].tolist(),
        "contact_settle_frames": contact_settle_frames,
        "status": "composed_kinematic_transition_requires_contact_optimization",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
