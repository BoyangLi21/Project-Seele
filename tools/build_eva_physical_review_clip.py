#!/usr/bin/env python3
"""Export one audited EVA physical state as a lab-only visual review clip."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation


BONES = (
    "root", "torso_lower", "torso_upper", "head",
    "arm_l", "forearm_l", "hand_l", "arm_r", "forearm_r", "hand_r",
    "leg_l", "shin_l", "foot_l", "leg_r", "shin_r", "foot_r",
)
BODY_FOR_BONE = {
    "root": "pelvis", "torso_lower": "abdomen",
    "torso_upper": "thorax", "head": "head",
    "arm_l": "upper_arm_l", "forearm_l": "forearm_l",
    "hand_l": "hand_l", "arm_r": "upper_arm_r",
    "forearm_r": "forearm_r", "hand_r": "hand_r",
    "leg_l": "thigh_l", "shin_l": "shin_l", "foot_l": "foot_l",
    "leg_r": "thigh_r", "shin_r": "shin_r", "foot_r": "foot_r",
}
VISUAL_PARENT = {
    "root": None, "torso_lower": "root", "torso_upper": "torso_lower",
    "head": "torso_upper", "arm_l": "torso_upper",
    "forearm_l": "arm_l", "hand_l": "forearm_l",
    "arm_r": "torso_upper", "forearm_r": "arm_r",
    "hand_r": "forearm_r", "leg_l": "torso_lower",
    "shin_l": "leg_l", "foot_l": "shin_l",
    "leg_r": "torso_lower", "shin_r": "leg_r", "foot_r": "shin_r",
}

# Physical +X forward/+Y left/+Z up -> Tiger Gecko-authored +Z front/
# +X visual-left-before-mesh-reflection/+Y up. Determinant is +1.
SIM_TO_AUTHORED = np.asarray([
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.0, 0.0, 0.0],
], dtype=np.float64)
ROOT_METRE_SCALE = (192.0 / 4.0) / 112.0


def body_rotation(model, data, name):
    return data.xmat[model.body(name).id].reshape(3, 3).copy()


def body_world_matrices(model, data):
    return {
        bone: body_rotation(model, data, body)
        for bone, body in BODY_FOR_BONE.items()
    }


def wxyz(matrix):
    value = Rotation.from_matrix(matrix).as_quat()
    return [round(float(value[3]), 7), round(float(value[0]), 7),
            round(float(value[1]), 7), round(float(value[2]), 7)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    determinant = float(np.linalg.det(SIM_TO_AUTHORED))
    mapped_forward = SIM_TO_AUTHORED @ np.asarray((1.0, 0.0, 0.0))
    mapped_left = SIM_TO_AUTHORED @ np.asarray((0.0, 1.0, 0.0))
    if (abs(determinant - 1.0) > 1.0e-8
            or not np.allclose(mapped_forward, (0.0, 0.0, 1.0))
            or not np.allclose(mapped_left, (1.0, 0.0, 0.0))):
        raise RuntimeError("EVA physical-to-Tiger visual axis contract failed")

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    data.qpos[:] = model.qpos0
    mujoco.mj_forward(model, data)
    neutral_world = body_world_matrices(model, data)
    state = np.load(args.state)
    qpos = np.asarray(state["qpos"], dtype=np.float64)
    contacts = np.asarray(state["foot_contact"], dtype=np.bool_)
    if qpos.shape != (len(qpos), model.nq) or contacts.shape != (len(qpos), 2):
        raise RuntimeError("invalid physical review state")
    dt = float(state["timestep"][0])
    root_origin = qpos[0, :3].copy()
    frames = []
    maximum_angle_step = 0.0
    previous_rotations = None
    for frame_index, pose in enumerate(qpos):
        data.qpos[:] = pose
        data.qvel[:] = 0.0
        mujoco.mj_forward(model, data)
        current_world = body_world_matrices(model, data)
        authored_global = {}
        for bone in BONES:
            deformation = current_world[bone] @ neutral_world[bone].T
            authored_global[bone] = (
                SIM_TO_AUTHORED @ deformation @ SIM_TO_AUTHORED.T
            )
        rotations = []
        matrices = []
        for bone in BONES:
            parent = VISUAL_PARENT[bone]
            local = (authored_global[bone] if parent is None else
                     authored_global[parent].T @ authored_global[bone])
            matrices.append(local)
            rotations.append(wxyz(local))
        if previous_rotations is not None:
            for before, after in zip(previous_rotations, matrices):
                maximum_angle_step = max(maximum_angle_step, float(
                    (Rotation.from_matrix(before).inv()
                     * Rotation.from_matrix(after)).magnitude()
                ))
        previous_rotations = matrices
        root = SIM_TO_AUTHORED @ (pose[:3] - root_origin)
        root *= ROOT_METRE_SCALE
        frames.append({
            "root_m": [round(float(value), 7) for value in root],
            "rotation_wxyz": rotations,
            "foot_contact": [bool(contacts[frame_index, 0]),
                             bool(contacts[frame_index, 1])],
        })

    clip = {
        "duration_seconds": round((len(frames) - 1) * dt, 7),
        "loop": False,
        "closed_endpoint": False,
        "role": "strict_single_eva_physical_candidate_review_only",
        "source_id": args.source_id,
        "frames": frames,
    }
    document = {
        "schema": 2,
        "coordinate_system": (
            "gecko_authored_x_visual_left_y_up_z_front_pre_mesh_reflection"
        ),
        "quaternion_order": "wxyz",
        "sample_rate": 1.0 / dt,
        "preview_only": True,
        "authority": "offline_strict_physical_replay_not_gameplay_physics",
        "legacy_visual_chain_collapse": True,
        "sources": [{"name": args.source_name, "url": args.source_url,
                     "license": args.license}],
        "bones": list(BONES),
        "clips": {args.clip: clip},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        document, ensure_ascii=False, separators=(",", ":")
    ) + "\n", encoding="utf-8")
    report = {
        "schema": 1,
        "state": str(args.state.resolve()),
        "output": str(args.output.resolve()),
        "clip": args.clip,
        "frames": len(frames),
        "duration_seconds": clip["duration_seconds"],
        "basis_determinant": determinant,
        "forward_alignment": float(np.dot(
            mapped_forward, (0.0, 0.0, 1.0)
        )),
        "left_alignment": float(np.dot(mapped_left, (1.0, 0.0, 0.0))),
        "maximum_rotation_step_degrees": float(np.degrees(
            maximum_angle_step
        )),
        "rotation_mapping": (
            "physics_world_deformation_to_visual_global_then_parent_local"
        ),
        "status": "visual_review_only_not_runtime_integrated",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
