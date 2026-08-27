#!/usr/bin/env python3
"""Replace one tangent coordinate window by boundary interpolation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--tangent", required=True)
    parser.add_argument("--source-start", required=True, type=float)
    parser.add_argument("--source-end", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    source = np.load(args.state)
    tangent = np.asarray(source["tangent"], dtype=np.float64).copy()
    tangent_names = [str(value) for value in source["tangent_names"]]
    if args.tangent not in tangent_names:
        raise RuntimeError("requested tangent is absent")
    tangent_index = tangent_names.index(args.tangent)
    frames = np.asarray(source["source_frames"], dtype=np.float64)
    selected = np.flatnonzero(
        (frames >= args.source_start - 1.0e-6)
        & (frames <= args.source_end + 1.0e-6)
    )
    if not len(selected):
        raise RuntimeError("repair window contains no frames")
    first = int(selected[0])
    last = int(selected[-1])
    if first == 0 or last == len(frames) - 1:
        raise RuntimeError("repair window requires both boundary frames")
    before = first - 1
    after = last + 1
    original = tangent[:, tangent_index].copy()
    tangent[first:last + 1, tangent_index] = np.interp(
        frames[first:last + 1],
        [frames[before], frames[after]],
        [original[before], original[after]],
    )

    joint_groups = {}
    for index, name in enumerate(tangent_names):
        actuator_id = model.actuator(f"a_{name}").id
        joint_id = int(model.actuator_trnid[actuator_id, 0])
        joint_groups.setdefault(joint_id, []).append({
            "index": index,
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

    names = [str(value) for value in source["target_landmark_names"]]
    objects = []
    for name in names:
        object_type, object_name = TARGET_OBJECTS[name]
        object_id = mujoco.mj_name2id(
            model,
            (mujoco.mjtObj.mjOBJ_BODY if object_type == "body"
             else mujoco.mjtObj.mjOBJ_GEOM), object_name,
        )
        objects.append((object_type, object_id))
    root_qpos = np.asarray(source["qpos"], dtype=np.float64)
    qpos = []
    actual = []
    for frame in range(len(frames)):
        data.qpos[:] = root_qpos[frame]
        set_tangent(tangent[frame])
        mujoco.mj_forward(model, data)
        qpos.append(data.qpos.copy())
        actual.append(np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in objects
        ]))
    qpos = np.asarray(qpos, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    dt = float(source["timestep"][0])
    qvel = np.zeros((len(qpos), model.nv), dtype=np.float64)
    for frame in range(len(qpos)):
        previous = max(0, frame - 1)
        following = min(len(qpos) - 1, frame + 1)
        duration = max(dt, (following - previous) * dt)
        mujoco.mj_differentiatePos(
            model, qvel[frame], duration,
            qpos[previous], qpos[following],
        )
    fields = {key: source[key] for key in source.files}
    fields.update({
        "tangent": tangent, "qpos": qpos, "qvel": qvel,
        "actual_positions": actual,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **fields)
    report = {
        "schema": 1,
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "tangent": args.tangent,
        "source_window": [args.source_start, args.source_end],
        "frame_indices": [first, last],
        "boundary_indices": [before, after],
        "maximum_change_rad": float(np.max(np.abs(
            tangent[:, tangent_index] - original
        ))),
        "maximum_step_before_rad": float(np.max(np.abs(np.diff(original)))),
        "maximum_step_after_rad": float(np.max(np.abs(np.diff(
            tangent[:, tangent_index]
        )))),
        "status": "local_tangent_repair_requires_full_reaudit",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
