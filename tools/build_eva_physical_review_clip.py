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
    "root", "torso_lower", "torso_upper", "neck", "head",
    "clavicle_l", "arm_l", "forearm_l", "wrist_l", "hand_l",
    "clavicle_r", "arm_r", "forearm_r", "wrist_r", "hand_r",
    "leg_l", "shin_l", "ankle_l", "foot_l",
    "leg_r", "shin_r", "ankle_r", "foot_r",
)
BODY_FOR_BONE = {
    "root": "pelvis", "torso_lower": "abdomen",
    "torso_upper": "thorax", "neck": "neck", "head": "head",
    "clavicle_l": "clavicle_l", "arm_l": "upper_arm_l",
    "forearm_l": "forearm_l", "wrist_l": "wrist_link_l",
    "hand_l": "hand_l", "clavicle_r": "clavicle_r",
    "arm_r": "upper_arm_r", "forearm_r": "forearm_r",
    "wrist_r": "wrist_link_r", "hand_r": "hand_r",
    "leg_l": "thigh_l", "shin_l": "shin_l",
    "ankle_l": "ankle_link_l", "foot_l": "foot_l",
    "leg_r": "thigh_r", "shin_r": "shin_r",
    "ankle_r": "ankle_link_r", "foot_r": "foot_r",
}
VISUAL_PARENT = {
    "root": None, "torso_lower": "root", "torso_upper": "torso_lower",
    "neck": "torso_upper", "head": "neck",
    "clavicle_l": "torso_upper", "arm_l": "clavicle_l",
    "forearm_l": "arm_l", "wrist_l": "forearm_l", "hand_l": "wrist_l",
    "clavicle_r": "torso_upper", "arm_r": "clavicle_r",
    "forearm_r": "arm_r", "wrist_r": "forearm_r", "hand_r": "wrist_r",
    "leg_l": "torso_lower", "shin_l": "leg_l",
    "ankle_l": "shin_l", "foot_l": "ankle_l",
    "leg_r": "torso_lower", "shin_r": "leg_r",
    "ankle_r": "shin_r", "foot_r": "ankle_r",
}

# Physical +X forward/+Y left/+Z up -> Tiger Gecko-authored +Z front/
# +X visual-left-before-mesh-reflection/+Y up. Determinant is +1.
SIM_TO_AUTHORED = np.asarray([
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.0, 0.0, 0.0],
], dtype=np.float64)
AUTHORED_TO_RUNTIME_POSITION = np.diag((-1.0, 1.0, 1.0))
SIM_TO_RUNTIME = AUTHORED_TO_RUNTIME_POSITION @ SIM_TO_AUTHORED
ROOT_METRE_SCALE = (192.0 / 4.0) / 112.0


def body_rotation(model, data, name):
    return data.xmat[model.body(name).id].reshape(3, 3).copy()


def body_world_matrices(model, data):
    return {
        bone: body_rotation(model, data, body)
        for bone, body in BODY_FOR_BONE.items()
    }


def authored_wxyz_for_runtime_matrix(matrix):
    # Gecko's Bedrock factory applies authored Euler rotations as
    # (-X,-Y,+Z).  Encode the inverse operation here; writing the runtime
    # matrix directly as an authored quaternion applies that conversion a
    # second time and reverses upper/forearm segment directions.
    runtime_euler = Rotation.from_matrix(matrix).as_euler("xyz")
    authored_euler = np.asarray((
        -runtime_euler[0], -runtime_euler[1], runtime_euler[2]
    ))
    value = Rotation.from_euler("xyz", authored_euler).as_quat()
    return [round(float(value[3]), 7), round(float(value[0]), 7),
            round(float(value[1]), 7), round(float(value[2]), 7)]


def runtime_matrix_from_authored_wxyz(value):
    authored = Rotation.from_quat((value[1], value[2], value[3], value[0]))
    authored_euler = authored.as_euler("xyz")
    runtime_euler = np.asarray((
        -authored_euler[0], -authored_euler[1], authored_euler[2]
    ))
    return Rotation.from_euler("xyz", runtime_euler).as_matrix()


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
    maximum_runtime_round_trip_error = 0.0
    maximum_runtime_round_trip_location = None
    previous_rotations = None
    for frame_index, pose in enumerate(qpos):
        data.qpos[:] = pose
        data.qvel[:] = 0.0
        mujoco.mj_forward(model, data)
        current_world = body_world_matrices(model, data)
        runtime_global = {}
        for bone in BONES:
            deformation = current_world[bone] @ neutral_world[bone].T
            runtime_global[bone] = (
                SIM_TO_RUNTIME @ deformation @ SIM_TO_RUNTIME.T
            )
        rotations = []
        matrices = []
        for bone in BONES:
            parent = VISUAL_PARENT[bone]
            local = (runtime_global[bone] if parent is None else
                     runtime_global[parent].T @ runtime_global[bone])
            matrices.append(local)
            authored = authored_wxyz_for_runtime_matrix(local)
            rotations.append(authored)
            decoded = runtime_matrix_from_authored_wxyz(authored)
            round_trip_error = float((
                Rotation.from_matrix(local).inv()
                * Rotation.from_matrix(decoded)
            ).magnitude())
            if round_trip_error > maximum_runtime_round_trip_error:
                maximum_runtime_round_trip_error = round_trip_error
                maximum_runtime_round_trip_location = {
                    "frame": frame_index,
                    "bone": bone,
                }
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

    if maximum_runtime_round_trip_error > 1.0e-5:
        raise RuntimeError(
            "authored-to-Gecko runtime rotation round trip failed: "
            f"error={maximum_runtime_round_trip_error} "
            f"location={maximum_runtime_round_trip_location}"
        )

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
        "legacy_visual_chain_collapse": False,
        "visual_bridge_bones": [
            "neck", "clavicle_l", "clavicle_r",
            "wrist_l", "wrist_r", "ankle_l", "ankle_r",
        ],
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
        "maximum_runtime_round_trip_error_degrees": float(np.degrees(
            maximum_runtime_round_trip_error
        )),
        "maximum_runtime_round_trip_error_location": (
            maximum_runtime_round_trip_location
        ),
        "rotation_mapping": (
            "physics_world_deformation_to_runtime_global_then_inverse_gecko_"
            "authored_euler"
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
