#!/usr/bin/env python3
"""Export audited MuJoCo state logs as an isolated Minecraft pose preview.

This is deliberately an offline replay asset. It lets the motion-lab renderer
show the exact physical trajectory while the real-time native sidecar is still
under construction; it is never used as gameplay authority.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation, Slerp


SAMPLE_RATE = 30.0
BONES = (
    "torso_lower", "torso_upper", "head",
    "arm_l", "forearm_l", "hand_l",
    "arm_r", "forearm_r", "hand_r",
    "leg_l", "shin_l", "foot_l",
    "leg_r", "shin_r", "foot_r",
)

# ProtoMotions common-body indices. Each tuple is (visual parent, child body).
LINKS = {
    "torso_lower": (None, 0),
    "torso_upper": (0, 16),
    "head": (16, 1),
    "arm_l": (16, 19),
    "forearm_l": (19, 20),
    "hand_l": (20, 24),
    "arm_r": (16, 27),
    "forearm_r": (27, 28),
    "hand_r": (28, 32),
    "leg_l": (0, 4),
    "shin_l": (4, 5),
    "foot_l": (5, 7),
    "leg_r": (0, 10),
    "shin_r": (10, 11),
    "foot_r": (11, 13),
}

# G1 simulation: +X forward, +Y left, +Z up.
# Bedrock: +X right, +Y up, +Z back. This basis has determinant +1.
SIM_TO_BEDROCK = np.asarray([
    [0.0, -1.0, 0.0],
    [0.0, 0.0, 1.0],
    [-1.0, 0.0, 0.0],
])


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--walk-state", required=True, type=Path)
    parser.add_argument("--walk-episode", type=int, default=0)
    parser.add_argument("--recovery-state", required=True, type=Path)
    parser.add_argument("--recovery-episode", type=int, default=1)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def episode(state, index):
    start = int(state["episode_starts"][index])
    count = int(state["episode_lengths"][index])
    return slice(start, start + count), count


def local_delta_matrices(body_wxyz):
    body_xyzw = body_wxyz[..., [1, 2, 3, 0]]
    world = Rotation.from_quat(body_xyzw.reshape(-1, 4)).as_matrix()
    world = world.reshape(*body_xyzw.shape[:-1], 3, 3)
    output = {}
    for bone in BONES:
        parent, child = LINKS[bone]
        child_world = world[:, child]
        local = child_world if parent is None else (
            np.swapaxes(world[:, parent], -1, -2) @ child_world)
        neutral = local[0]
        delta = local @ neutral.T
        output[bone] = SIM_TO_BEDROCK @ delta @ SIM_TO_BEDROCK.T
    return output


def sample_rotation(matrices, source_time, target_time):
    rotations = Rotation.from_matrix(matrices)
    sampled = Slerp(source_time, rotations)(target_time).as_quat()
    # scipy xyzw -> database wxyz
    return sampled[:, [3, 0, 1, 2]]


def make_clip(path, episode_index, name):
    state = np.load(path)
    item, count = episode(state, episode_index)
    dt = float(state["control_dt_seconds"][0])
    source_time = np.arange(count, dtype=np.float64) * dt
    duration = float(source_time[-1])
    frame_count = int(round(duration * SAMPLE_RATE)) + 1
    target_time = np.linspace(0.0, duration, frame_count)
    matrices = local_delta_matrices(state["body_quaternion_wxyz"][item])
    sampled_rotations = {
        bone: sample_rotation(value, source_time, target_time)
        for bone, value in matrices.items()
    }
    root_height = state["root_qpos"][item, 2]
    root_height = np.interp(target_time, source_time, root_height)
    root_height -= root_height[0]
    contact = state["foot_contact"][item].astype(bool)
    contact_indices = np.clip(
        np.rint(target_time / dt).astype(np.int64), 0, count - 1)

    frames = []
    for frame in range(frame_count):
        frames.append({
            "root_m": [0.0, round(float(root_height[frame]), 7), 0.0],
            "rotation_wxyz": [
                [round(float(value), 7) for value in sampled_rotations[bone][frame]]
                for bone in BONES
            ],
            "foot_contact": [
                bool(contact[contact_indices[frame], 0]),
                bool(contact[contact_indices[frame], 1]),
            ],
        })
    return {
        "duration_seconds": duration,
        "loop": True,
        "role": "offline_physics_preview_non_authoritative",
        "source_state": str(path.resolve()),
        "source_episode": episode_index,
        "frames": frames,
    }, {
        "name": name,
        "source": str(path.resolve()),
        "episode": episode_index,
        "source_frames": count,
        "output_frames": frame_count,
        "duration_seconds": duration,
        "root_write_authority": False,
    }


def main():
    args = parse_args()
    if not np.isclose(np.linalg.det(SIM_TO_BEDROCK), 1.0):
        raise RuntimeError("simulation-to-Bedrock basis is mirrored")
    walk, walk_report = make_clip(
        args.walk_state.resolve(), args.walk_episode, "physics_walk")
    recovery, recovery_report = make_clip(
        args.recovery_state.resolve(), args.recovery_episode,
        "physics_recovery")
    document = {
        "schema": 2,
        "coordinate_system": "bedrock_x_right_y_up_z_back",
        "quaternion_order": "wxyz",
        "sample_rate": SAMPLE_RATE,
        "preview_only": True,
        "authority": "offline_mujoco_replay_not_gameplay_physics",
        "sources": [{
            "name": "Project SEELE MuJoCo P1 state logs",
            "license": "private local research artifact",
        }],
        "bones": list(BONES),
        "clips": {
            "physics_walk": walk,
            "physics_recovery": recovery,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    report = {
        "schema": 1,
        "output": str(args.output.resolve()),
        "basis_determinant": float(np.linalg.det(SIM_TO_BEDROCK)),
        "preview_only": True,
        "clips": [walk_report, recovery_report],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
