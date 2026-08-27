#!/usr/bin/env python3
"""Lock one EVA arm to an explicit torso-relative guard during an attack."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


ARM_NAMES = {
    side: [
        f"clavicle_{side}_protract", f"clavicle_{side}_elevate",
        f"shoulder_{side}_abduct", f"shoulder_{side}_flex",
        f"shoulder_{side}_twist", f"elbow_{side}",
        f"forearm_twist_{side}", f"wrist_{side}_deviation",
        f"wrist_{side}_flex",
    ]
    for side in ("l", "r")
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


def tangent_names(model_path: Path) -> list[str]:
    root = ET.parse(model_path).getroot()
    custom = root.find("custom")
    return next(
        item.attrib["data"].split() for item in custom.findall("text")
        if item.attrib["name"] == "tangent_joint_names"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--side", choices=("left", "right"), required=True)
    parser.add_argument("--guard-frame", type=int, default=0)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    source = np.load(args.state)
    contract = tangent_names(args.model)
    state_names = [str(value) for value in source["tangent_names"]]
    if contract != state_names:
        raise RuntimeError("tangent contract mismatch")
    side = "l" if args.side == "left" else "r"
    qpos_source = np.asarray(source["qpos"], dtype=np.float64)
    tangent_source = np.asarray(source["tangent"], dtype=np.float64)
    frame_count = len(qpos_source)
    guard_frame = min(frame_count - 1, max(0, args.guard_frame))
    indices = [state_names.index(name) for name in ARM_NAMES[side]]
    tangent = tangent_source.copy()
    tangent[:, indices] = tangent_source[guard_frame, indices]

    joint_groups = {}
    for tangent_index, name in enumerate(state_names):
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

    landmark_names = [str(value) for value in source["target_landmark_names"]]
    object_ids = []
    for name in landmark_names:
        object_type, object_name = TARGET_OBJECTS[name]
        enum = (mujoco.mjtObj.mjOBJ_BODY if object_type == "body"
                else mujoco.mjtObj.mjOBJ_GEOM)
        object_ids.append((object_type,
                           mujoco.mj_name2id(model, enum, object_name)))

    def evaluate(frame: int):
        data.qpos[:] = qpos_source[frame]
        set_tangent(tangent[frame])
        mujoco.mj_forward(model, data)
        actual = np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in object_ids
        ])
        return data.qpos.copy(), actual

    guard_qpos, guard_actual = evaluate(guard_frame)
    data.qpos[:] = guard_qpos
    mujoco.mj_forward(model, data)
    thorax_id = model.body("thorax").id
    guard_thorax_position = data.xpos[thorax_id].copy()
    guard_thorax_rotation = data.xmat[thorax_id].reshape(3, 3).copy()
    guard_targets = {}
    for joint in ("shoulder", "elbow", "wrist", "hand"):
        name = f"{joint}_{side}"
        guard_targets[name] = guard_thorax_rotation.T @ (
            guard_actual[landmark_names.index(name)] - guard_thorax_position
        )

    desired = np.asarray(source["desired_positions"], dtype=np.float64).copy()
    qpos = []
    actual = []
    for frame in range(frame_count):
        qpos_row, actual_row = evaluate(frame)
        qpos.append(qpos_row)
        actual.append(actual_row)
        thorax_position = data.xpos[thorax_id].copy()
        thorax_rotation = data.xmat[thorax_id].reshape(3, 3).copy()
        for name, local in guard_targets.items():
            desired[frame, landmark_names.index(name)] = (
                thorax_position + thorax_rotation @ local
            )
    qpos = np.asarray(qpos, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    dt = float(source["timestep"][0])
    qvel = np.zeros((frame_count, model.nv), dtype=np.float64)
    for frame in range(frame_count):
        before = max(0, frame - 1)
        after = min(frame_count - 1, frame + 1)
        mujoco.mj_differentiatePos(
            model, qvel[frame], max(dt, (after - before) * dt),
            qpos[before], qpos[after],
        )
    fields = {key: source[key] for key in source.files}
    fields.update({
        "qpos": qpos, "qvel": qvel, "tangent": tangent,
        "desired_positions": desired, "actual_positions": actual,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **fields)
    report = {
        "schema": 1,
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "guard_side": args.side,
        "guard_frame": guard_frame,
        "locked_tangent_names": ARM_NAMES[side],
        "target_authority": "single_guard_pose_in_torso_frame_not_per_frame_fk",
        "root_or_lower_body_changed": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
