#!/usr/bin/env python3
"""Export strict single-EVA physical candidates for motion-lab review.

The source NPZ files contain the 41-DOF MuJoCo pose.  Minecraft's current
legacy visual mesh exposes only 15 articulated body bones, so this exporter
collapses neck/clavicle/wrist/ankle/toe chains by measuring the endpoint body
rotation relative to the nearest visual parent.  It never changes the source
trajectory and it is explicitly a non-authoritative review asset.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation


BONES = (
    "root", "torso_lower", "torso_upper", "head",
    "arm_l", "forearm_l", "hand_l",
    "arm_r", "forearm_r", "hand_r",
    "leg_l", "shin_l", "foot_l",
    "leg_r", "shin_r", "foot_r",
)

# (nearest visual-parent physics body, endpoint physics body).  Intermediate
# physical joints remain represented because endpoint orientation is measured
# against the nearest parent retained by the legacy visual rig.
LINKS = {
    "root": (None, "pelvis"),
    "torso_lower": ("pelvis", "abdomen"),
    "torso_upper": ("abdomen", "thorax"),
    "head": ("thorax", "head"),
    "arm_l": ("thorax", "upper_arm_l"),
    "forearm_l": ("upper_arm_l", "forearm_l"),
    "hand_l": ("forearm_l", "hand_l"),
    "arm_r": ("thorax", "upper_arm_r"),
    "forearm_r": ("upper_arm_r", "forearm_r"),
    "hand_r": ("forearm_r", "hand_r"),
    "leg_l": ("pelvis", "thigh_l"),
    "shin_l": ("thigh_l", "shin_l"),
    "foot_l": ("shin_l", "foot_l"),
    "leg_r": ("pelvis", "thigh_r"),
    "shin_r": ("thigh_r", "shin_r"),
    "foot_r": ("shin_r", "foot_r"),
}

# MuJoCo: +X forward, +Y left, +Z up.
# The reviewed Tiger mesh is authored with +Z at the chest/face. Its renderer
# reflects mesh X, so physical left maps to authored +X. This is still a
# proper rotation (determinant +1), not a mirrored skeleton.
SIM_TO_AUTHORED = np.asarray([
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.0, 0.0, 0.0],
], dtype=np.float64)
PHYSICAL_FORWARD_SIM = np.asarray((1.0, 0.0, 0.0), dtype=np.float64)
PHYSICAL_LEFT_SIM = np.asarray((0.0, 1.0, 0.0), dtype=np.float64)
VISUAL_FORWARD_AUTHORED = np.asarray((0.0, 0.0, 1.0), dtype=np.float64)
VISUAL_LEFT_AUTHORED = np.asarray((1.0, 0.0, 0.0), dtype=np.float64)

# The runtime's historical 112 model-units/metre constant was calibrated to
# a roughly 1.714 m source human.  The canonical EVA physics proxy is 4 m, so
# its root translation must be reduced to the same 192-unit visual height.
PHYSICAL_TO_RUNTIME_METRES = (192.0 / 4.0) / 112.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--ward-left", required=True, type=Path)
    parser.add_argument("--ward-right", required=True, type=Path)
    parser.add_argument("--push-kick-right", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def body_rotation(model: mujoco.MjModel, data: mujoco.MjData,
                  name: str) -> np.ndarray:
    body_id = model.body(name).id
    return data.xmat[body_id].reshape(3, 3).copy()


def local_matrices(model: mujoco.MjModel,
                   data: mujoco.MjData) -> dict[str, np.ndarray]:
    output = {}
    for bone, (parent, child) in LINKS.items():
        child_world = body_rotation(model, data, child)
        output[bone] = (child_world if parent is None else
                        body_rotation(model, data, parent).T @ child_world)
    return output


def quaternion_wxyz(matrix: np.ndarray) -> list[float]:
    xyzw = Rotation.from_matrix(matrix).as_quat()
    return [round(float(xyzw[3]), 7), round(float(xyzw[0]), 7),
            round(float(xyzw[1]), 7), round(float(xyzw[2]), 7)]


def make_clip(model: mujoco.MjModel, neutral: dict[str, np.ndarray],
              path: Path, clip_name: str, source_id: str) -> tuple[dict, dict]:
    state = np.load(path)
    qpos = np.asarray(state["qpos"], dtype=np.float64)
    if qpos.ndim != 2 or qpos.shape[1] != model.nq or len(qpos) < 2:
        raise RuntimeError(f"invalid physical qpos in {path}")
    contact = np.asarray(state["foot_contact"], dtype=np.bool_)
    if contact.shape != (len(qpos), 2):
        raise RuntimeError(f"invalid foot_contact in {path}")
    dt = float(np.asarray(state["timestep"]).reshape(-1)[0])
    if not math.isfinite(dt) or dt <= 0.0:
        raise RuntimeError(f"invalid timestep in {path}")

    data = mujoco.MjData(model)
    root_origin = qpos[0, :3].copy()
    frames = []
    interframe_degrees = []
    previous = None
    root_steps = []
    previous_root = None
    for frame_index, pose in enumerate(qpos):
        data.qpos[:] = pose
        data.qvel[:] = 0.0
        mujoco.mj_forward(model, data)
        current = local_matrices(model, data)
        rotations = []
        for bone in BONES:
            delta = current[bone] @ neutral[bone].T
            authored = SIM_TO_AUTHORED @ delta @ SIM_TO_AUTHORED.T
            rotations.append(quaternion_wxyz(authored))
        if previous is not None:
            for before, after in zip(previous, rotations):
                q0 = Rotation.from_quat(before[1:] + before[:1])
                q1 = Rotation.from_quat(after[1:] + after[:1])
                interframe_degrees.append(math.degrees(
                    (q0.inv() * q1).magnitude()
                ))
        previous = rotations

        root_delta = SIM_TO_AUTHORED @ (pose[:3] - root_origin)
        root_delta *= PHYSICAL_TO_RUNTIME_METRES
        if previous_root is not None:
            root_steps.append(float(np.linalg.norm(
                root_delta - previous_root
            )))
        previous_root = root_delta.copy()
        frames.append({
            "root_m": [round(float(value), 7) for value in root_delta],
            "rotation_wxyz": rotations,
            "foot_contact": [bool(contact[frame_index, 0]),
                             bool(contact[frame_index, 1])],
        })

    norms = [
        abs(float(np.linalg.norm(rotation)) - 1.0)
        for frame in frames for rotation in frame["rotation_wxyz"]
    ]
    clip = {
        "duration_seconds": round((len(frames) - 1) * dt, 7),
        "loop": False,
        "closed_endpoint": False,
        "role": "strict_single_eva_physical_candidate_review_only",
        "source_id": source_id,
        "frames": frames,
    }
    report = {
        "clip": clip_name,
        "source_id": source_id,
        "source_state": str(path.resolve()),
        "frames": len(frames),
        "duration_seconds": clip["duration_seconds"],
        "quaternion_norm_error_maximum": max(norms, default=0.0),
        "interframe_rotation_degrees_p95": float(np.percentile(
            interframe_degrees, 95.0
        )),
        "interframe_rotation_degrees_maximum": max(
            interframe_degrees, default=0.0
        ),
        "runtime_root_step_maximum_m": max(root_steps, default=0.0),
        "root_write_authority": False,
    }
    return clip, report


def main() -> None:
    args = parse_args()
    if not np.isclose(np.linalg.det(SIM_TO_AUTHORED), 1.0):
        raise RuntimeError("simulation-to-authored basis is mirrored")
    mapped_forward = SIM_TO_AUTHORED @ PHYSICAL_FORWARD_SIM
    mapped_left = SIM_TO_AUTHORED @ PHYSICAL_LEFT_SIM
    forward_alignment = float(np.dot(
        mapped_forward, VISUAL_FORWARD_AUTHORED
    ))
    left_alignment = float(np.dot(mapped_left, VISUAL_LEFT_AUTHORED))
    if forward_alignment < 0.999999 or left_alignment < 0.999999:
        raise RuntimeError(
            "physical axes do not match the reviewed visual rig"
        )
    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    neutral_data = mujoco.MjData(model)
    neutral_data.qpos[:] = model.qpos0
    mujoco.mj_forward(model, neutral_data)
    neutral = local_matrices(model, neutral_data)

    specifications = (
        ("combat_ward_left", args.ward_left,
         "ACCAD_Male2_E11_frames_10_26_R12"),
        ("combat_ward_right", args.ward_right,
         "ACCAD_Male2_E13_frames_8_23_R04"),
        ("combat_push_kick_right", args.push_kick_right,
         "ACCAD_Male2_G18_frames_23_48_R18"),
    )
    clips = {}
    reports = []
    for name, path, source_id in specifications:
        clip, report = make_clip(model, neutral, path, name, source_id)
        clips[name] = clip
        reports.append(report)

    output = {
        "schema": 2,
        "coordinate_system": (
            "gecko_authored_x_visual_left_y_up_z_front_pre_mesh_reflection"
        ),
        "quaternion_order": "wxyz",
        "sample_rate": 60.0,
        "preview_only": True,
        "authority": "offline_strict_physical_replay_not_gameplay_physics",
        "legacy_visual_chain_collapse": True,
        "sources": [{
            "name": "ACCAD Open Motion Project martial-arts captures",
            "license": "CC BY 3.0",
            "url": "https://accad.osu.edu/research/motion-lab/mocap-system-and-data",
        }],
        "bones": list(BONES),
        "clips": clips,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        output, ensure_ascii=False, separators=(",", ":")
    ) + "\n", encoding="utf-8")
    audit = {
        "schema": 1,
        "output": str(args.output.resolve()),
        "basis_determinant": float(np.linalg.det(SIM_TO_AUTHORED)),
        "physical_forward_sim": PHYSICAL_FORWARD_SIM.tolist(),
        "mapped_forward_authored": mapped_forward.tolist(),
        "visual_forward_authored": VISUAL_FORWARD_AUTHORED.tolist(),
        "forward_alignment": forward_alignment,
        "physical_left_sim": PHYSICAL_LEFT_SIM.tolist(),
        "mapped_left_authored": mapped_left.tolist(),
        "visual_left_authored": VISUAL_LEFT_AUTHORED.tolist(),
        "left_alignment": left_alignment,
        "physical_to_runtime_metres": PHYSICAL_TO_RUNTIME_METRES,
        "preview_only": True,
        "legacy_visual_chain_collapse": {
            "head": "neck+head",
            "arms": "clavicle+shoulder and elbow+forearm and wrist+hand",
            "feet": "ankle+foot+toe endpoint represented by legacy foot",
        },
        "clips": reports,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        audit, ensure_ascii=False, indent=2
    ) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
