#!/usr/bin/env python3
"""Compose an upper-body action over an independently audited lower body."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation


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


def tangent_metadata(model_path: Path):
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
    return (names, numeric["tangent_joint_lower_rad"],
            numeric["tangent_joint_upper_rad"])


def root_rotation(qpos: np.ndarray) -> Rotation:
    q = qpos[3:7]
    return Rotation.from_quat((q[1], q[2], q[3], q[0]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--upper", required=True, type=Path)
    parser.add_argument("--lower", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--transfer-root-rotation-fraction", type=float, default=0.0,
        help=("Move this fraction of the upper source's root orientation "
              "difference into lumbar/thoracic articulation."),
    )
    parser.add_argument(
        "--root-orientation-authority", choices=("lower", "upper"),
        default="lower",
    )
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    upper = np.load(args.upper)
    lower = np.load(args.lower)
    if len(upper["qpos"]) != len(lower["qpos"]):
        raise RuntimeError("upper and lower states need matching frame counts")
    upper_dt = float(upper["timestep"][0])
    lower_dt = float(lower["timestep"][0])
    if not np.isclose(upper_dt, lower_dt):
        raise RuntimeError("upper and lower states need matching timestep")
    names = [str(value) for value in upper["tangent_names"]]
    if names != [str(value) for value in lower["tangent_names"]]:
        raise RuntimeError("tangent contracts differ")
    contract_names, tangent_lower, tangent_upper = tangent_metadata(args.model)
    if names != contract_names:
        raise RuntimeError("state tangent order differs from model")
    if not 0.0 <= args.transfer_root_rotation_fraction <= 1.0:
        raise RuntimeError("root rotation transfer fraction must be in [0,1]")
    landmark_names = [str(value) for value in upper["target_landmark_names"]]
    if landmark_names != [str(value) for value
                          in lower["target_landmark_names"]]:
        raise RuntimeError("landmark contracts differ")
    first_lower = names.index("hip_l_abduct")

    upper_tangent = np.asarray(upper["tangent"], dtype=np.float64)
    lower_tangent = np.asarray(lower["tangent"], dtype=np.float64)
    tangent = lower_tangent.copy()
    tangent[:, :first_lower] = upper_tangent[:, :first_lower]

    joint_groups = {}
    for index, name in enumerate(names):
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
    for name in landmark_names:
        object_type, object_name = TARGET_OBJECTS[name]
        enum = (mujoco.mjtObj.mjOBJ_BODY if object_type == "body"
                else mujoco.mjtObj.mjOBJ_GEOM)
        object_ids.append((object_type,
                           mujoco.mj_name2id(model, enum, object_name)))

    upper_qpos = np.asarray(upper["qpos"], dtype=np.float64)
    lower_qpos = np.asarray(lower["qpos"], dtype=np.float64)
    upper_desired = np.asarray(upper["desired_positions"], dtype=np.float64)
    lower_desired = np.asarray(lower["desired_positions"], dtype=np.float64)
    upper_landmarks = set((
        "abdomen", "thorax", "neck", "head",
        "shoulder_l", "elbow_l", "wrist_l", "hand_l",
        "shoulder_r", "elbow_r", "wrist_r", "hand_r",
    ))
    desired = lower_desired.copy()
    qpos_rows = []
    actual_rows = []
    root_rotation_delta = []
    transferred_rotation = []
    for frame in range(len(tangent)):
        upper_rotation = root_rotation(upper_qpos[frame])
        lower_rotation = root_rotation(lower_qpos[frame])
        relative_rotation = lower_rotation.inv() * upper_rotation
        transfer = Rotation.from_rotvec(
            relative_rotation.as_rotvec()
            * args.transfer_root_rotation_fraction
        )
        transfer_euler = transfer.as_euler("xyz")
        for axis, suffix in enumerate(("roll", "pitch", "yaw")):
            for segment in ("lumbar", "thoracic"):
                index = names.index(f"{segment}_{suffix}")
                tangent[frame, index] += 0.5 * transfer_euler[axis]
        tangent[frame] = np.clip(
            tangent[frame], tangent_lower, tangent_upper
        )
        data.qpos[:] = lower_qpos[frame]
        if args.root_orientation_authority == "upper":
            data.qpos[3:7] = upper_qpos[frame, 3:7]
        set_tangent(tangent[frame])
        mujoco.mj_forward(model, data)
        qpos_rows.append(data.qpos.copy())
        actual_rows.append(np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in object_ids
        ]))

        upper_root = upper_qpos[frame, :3]
        lower_root = lower_qpos[frame, :3]
        root_rotation_delta.append((
            lower_rotation.inv() * upper_rotation
        ).magnitude())
        transferred_rotation.append(transfer.magnitude())
        for index, name in enumerate(landmark_names):
            if name in upper_landmarks:
                local = upper_rotation.inv().apply(
                    upper_desired[frame, index] - upper_root
                )
                target_rotation = (upper_rotation
                                   if args.root_orientation_authority == "upper"
                                   else lower_rotation * transfer)
                desired[frame, index] = (
                    lower_root + target_rotation.apply(local)
                )
            elif args.root_orientation_authority == "upper":
                local = lower_rotation.inv().apply(
                    lower_desired[frame, index] - lower_root
                )
                desired[frame, index] = (
                    lower_root + upper_rotation.apply(local)
                )

    qpos = np.asarray(qpos_rows, dtype=np.float64)
    actual = np.asarray(actual_rows, dtype=np.float64)
    qvel = np.zeros((len(qpos), model.nv), dtype=np.float64)
    for frame in range(1, len(qpos)):
        mujoco.mj_differentiatePos(
            model, qvel[frame], upper_dt, qpos[frame - 1], qpos[frame]
        )
    if len(qpos) > 1:
        qvel[0] = qvel[1]

    output = dict(
        qpos=qpos,
        qvel=qvel,
        timestep=np.asarray([upper_dt], dtype=np.float64),
        source_frames=np.asarray(upper["source_frames"], dtype=np.float64),
        foot_contact=np.asarray(lower["foot_contact"], dtype=np.bool_),
        tangent=tangent,
        tangent_names=np.asarray(names),
        target_landmark_names=np.asarray(landmark_names),
        desired_positions=desired,
        actual_positions=actual,
    )
    if "contact_blend" in lower.files:
        output["contact_blend"] = np.asarray(
            lower["contact_blend"], dtype=np.float64
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **output)
    report = {
        "schema": 1,
        "model": str(args.model.resolve()),
        "upper_state": str(args.upper.resolve()),
        "lower_state": str(args.lower.resolve()),
        "output_state": str(args.output.resolve()),
        "frames": len(qpos),
        "fps": 1.0 / upper_dt,
        "upper_tangent_count": first_lower,
        "lower_tangent_count": len(names) - first_lower,
        "maximum_source_root_rotation_difference_degrees": math.degrees(
            max(root_rotation_delta, default=0.0)
        ),
        "root_rotation_transfer_fraction":
            args.transfer_root_rotation_fraction,
        "maximum_transferred_rotation_degrees": math.degrees(
            max(transferred_rotation, default=0.0)
        ),
        "root_position_authority": "audited lower-body state",
        "root_orientation_authority": args.root_orientation_authority,
        "upper_goal_authority": "upper targets transformed into lower root frame",
        "status": "project_authored_layered_kinematic_candidate",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
