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
ARM_DIRECTION_SEGMENTS = (
    ("arm_l", "forearm_l", "upper_arm_l", "forearm_l"),
    ("forearm_l", "wrist_l", "forearm_l", "wrist_link_l"),
    ("arm_r", "forearm_r", "upper_arm_r", "forearm_r"),
    ("forearm_r", "wrist_r", "forearm_r", "wrist_link_r"),
)

# Physical +X forward/+Y left/+Z up -> Tiger runtime -Z front/-X left/+Y up.
# Positions use that proper anatomical basis.  The legacy Tiger deformation
# bridge uses an improper orientation basis because the source mesh has already
# been reflected at import and again on authored X at emission.  Replacing that
# bridge globally disconnects the rigid visual hierarchy.  Limb directions are
# therefore constrained explicitly from physical joint positions below.
SIM_TO_RUNTIME_POSITION = np.asarray([
    [0.0, -1.0, 0.0],
    [0.0, 0.0, 1.0],
    [-1.0, 0.0, 0.0],
], dtype=np.float64)
SIM_TO_RUNTIME_DEFORMATION = np.asarray([
    [0.0, -1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.0, 0.0, 0.0],
], dtype=np.float64)
AUTHORED_TO_RUNTIME_POSITION = np.diag((-1.0, 1.0, 1.0))
SIM_TO_AUTHORED_POSITION = (
    AUTHORED_TO_RUNTIME_POSITION @ SIM_TO_RUNTIME_POSITION
)
ROOT_METRE_SCALE = (192.0 / 4.0) / 112.0


def body_rotation(model, data, name):
    return data.xmat[model.body(name).id].reshape(3, 3).copy()


def body_world_matrices(model, data):
    return {
        bone: body_rotation(model, data, body)
        for bone, body in BODY_FOR_BONE.items()
    }


def body_position(model, data, name):
    return data.xpos[model.body(name).id].copy()


def load_visual_runtime_pivots(path):
    document = json.loads(path.read_text(encoding="utf-8"))
    geometries = document.get("minecraft:geometry", [])
    if not geometries:
        raise RuntimeError(f"visual geometry has no minecraft:geometry: {path}")
    pivots = {}
    for bone in geometries[0].get("bones", []):
        if bone["name"] not in BONES:
            continue
        raw = np.asarray(bone.get("pivot", (0.0, 0.0, 0.0)),
                         dtype=np.float64)
        pivots[bone["name"]] = np.asarray((-raw[0], raw[1], raw[2]))
    missing = set(BONES) - set(pivots)
    if missing:
        raise RuntimeError(
            "visual geometry is missing physical bridge bones: "
            + ", ".join(sorted(missing))
        )
    return pivots


def direction_frame(direction):
    forward = np.asarray(direction, dtype=np.float64)
    forward /= np.linalg.norm(forward)
    up_hint = np.asarray((0.0, 1.0, 0.0))
    right = np.cross(up_hint, forward)
    if np.linalg.norm(right) < 1.0e-8:
        up_hint = np.asarray((1.0, 0.0, 0.0))
        right = np.cross(up_hint, forward)
    right /= np.linalg.norm(right)
    up = np.cross(forward, right)
    up /= np.linalg.norm(up)
    return np.column_stack((right, up, forward))


def constrain_limb_directions(runtime_global, model, data, visual_pivots):
    base = {bone: matrix.copy() for bone, matrix in runtime_global.items()}
    minimum_dot = 1.0
    for side in ("l", "r"):
        segments = [segment for segment in ARM_DIRECTION_SEGMENTS
                    if segment[0].endswith(f"_{side}")]
        for bone, child, physical_start, physical_end in segments:
            bind = visual_pivots[child] - visual_pivots[bone]
            desired_physical = (
                body_position(model, data, physical_end)
                - body_position(model, data, physical_start)
            )
            desired = SIM_TO_RUNTIME_POSITION @ desired_physical
            predicted = runtime_global[bone] @ bind
            correction = (
                direction_frame(desired) @ direction_frame(predicted).T
            )
            runtime_global[bone] = correction @ runtime_global[bone]
            corrected = runtime_global[bone] @ bind
            alignment = float(np.dot(
                corrected / np.linalg.norm(corrected),
                desired / np.linalg.norm(desired),
            ))
            minimum_dot = min(minimum_dot, alignment)

        # Wrist and hand have no non-zero child-pivot segment in the Tiger
        # geometry. Preserve their original local articulation after the two
        # direction-constrained segments instead of inventing another target.
        forearm = f"forearm_{side}"
        wrist = f"wrist_{side}"
        hand = f"hand_{side}"
        runtime_global[wrist] = (
            runtime_global[forearm]
            @ base[forearm].T @ base[wrist]
        )
        runtime_global[hand] = (
            runtime_global[wrist]
            @ base[wrist].T @ base[hand]
        )
    return minimum_dot


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
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    position_determinant = float(np.linalg.det(SIM_TO_RUNTIME_POSITION))
    deformation_determinant = float(np.linalg.det(
        SIM_TO_RUNTIME_DEFORMATION
    ))
    authored_position_determinant = float(np.linalg.det(
        SIM_TO_AUTHORED_POSITION
    ))
    mapped_forward = SIM_TO_RUNTIME_POSITION @ np.asarray((1.0, 0.0, 0.0))
    mapped_left = SIM_TO_RUNTIME_POSITION @ np.asarray((0.0, 1.0, 0.0))
    mapped_up = SIM_TO_RUNTIME_POSITION @ np.asarray((0.0, 0.0, 1.0))
    if (abs(position_determinant - 1.0) > 1.0e-8
            or abs(deformation_determinant + 1.0) > 1.0e-8
            or abs(authored_position_determinant + 1.0) > 1.0e-8
            or not np.allclose(mapped_forward, (0.0, 0.0, -1.0))
            or not np.allclose(mapped_left, (-1.0, 0.0, 0.0))
            or not np.allclose(mapped_up, (0.0, 1.0, 0.0))):
        raise RuntimeError("EVA physical-to-Tiger visual axis contract failed")

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    visual_pivots = load_visual_runtime_pivots(args.geo)
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
    minimum_limb_direction_dot = 1.0
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
                SIM_TO_RUNTIME_DEFORMATION @ deformation
                @ SIM_TO_RUNTIME_DEFORMATION.T
            )
        minimum_limb_direction_dot = min(
            minimum_limb_direction_dot,
            constrain_limb_directions(
                runtime_global, model, data, visual_pivots
            ),
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
        root = SIM_TO_AUTHORED_POSITION @ (pose[:3] - root_origin)
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
    if minimum_limb_direction_dot < 0.999:
        raise RuntimeError(
            "physical-to-visual limb direction alignment failed: "
            f"minimum_dot={minimum_limb_direction_dot}"
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
            "gecko_authored_y_up_negative_z_front_x_reflected_at_runtime"
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
        "position_basis_determinant": position_determinant,
        "deformation_basis_determinant": deformation_determinant,
        "authored_position_basis_determinant": (
            authored_position_determinant
        ),
        "forward_alignment": float(np.dot(
            mapped_forward, (0.0, 0.0, -1.0)
        )),
        "left_alignment": float(np.dot(mapped_left, (-1.0, 0.0, 0.0))),
        "up_alignment": float(np.dot(mapped_up, (0.0, 1.0, 0.0))),
        "minimum_limb_direction_dot": minimum_limb_direction_dot,
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
            "legacy_tiger_deformation_basis_plus_true_front_physical_limb_"
            "direction_constraints_then_inverse_gecko_authored_euler"
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
