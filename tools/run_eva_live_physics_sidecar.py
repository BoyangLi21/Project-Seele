#!/usr/bin/env python3
"""Run a trained ProtoMotions policy in live MuJoCo and publish its state.

This is a calibration bridge for the isolated motion lab.  It never reads a
recorded state log: every published sample is produced by policy inference and
the immediately following MuJoCo integration step.
"""

from __future__ import annotations

import argparse
import mmap
from pathlib import Path
import signal
import struct
import sys
import time

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
import torch


COMMAND = struct.Struct("<QQII2ffff2f2fff3fI172x")
STATE = struct.Struct("<QQII3f4f3f3f41f41fQ8fff60x")
VISUAL = struct.Struct("<QQII3f4f60fQ2f204x")
COMMAND_OFFSET = 0
STATE_OFFSET = 256
VISUAL_OFFSET = 768
SHARED_BYTES = 1280

FLAG_RESET = 1 << 0
FLAG_IMPULSE = 1 << 1
FLAG_POLICY_LIVE = 1 << 8
FLAG_LEFT_CONTACT = 1 << 9
FLAG_RIGHT_CONTACT = 1 << 10
FLAG_FALLEN = 1 << 11

BONES = (
    "torso_lower", "torso_upper", "head",
    "arm_l", "forearm_l", "hand_l",
    "arm_r", "forearm_r", "hand_r",
    "leg_l", "shin_l", "foot_l",
    "leg_r", "shin_r", "foot_r",
)

# ProtoMotions common-body indices. Each value is (visual parent, child body).
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
# Bedrock: +X right, +Y up, +Z back. Determinant is +1.
SIM_TO_BEDROCK = np.asarray([
    [0.0, -1.0, 0.0],
    [0.0, 0.0, 1.0],
    [-1.0, 0.0, 0.0],
], dtype=np.float64)


class SharedState:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as stream:
            stream.truncate(SHARED_BYTES)
        self.stream = path.open("r+b", buffering=0)
        self.mapping = mmap.mmap(self.stream.fileno(), SHARED_BYTES)
        self.sequence = 0
        self.command_sequence = -1

    def close(self):
        self.mapping.close()
        self.stream.close()

    def read_command(self):
        sequence = struct.unpack_from("<Q", self.mapping, COMMAND_OFFSET)[0]
        if sequence == self.command_sequence:
            return None
        values = COMMAND.unpack_from(self.mapping, COMMAND_OFFSET)
        self.command_sequence = sequence
        return {
            "sequence": sequence,
            "flags": int(values[2]),
            "desired_velocity": np.asarray(values[4:6], dtype=np.float32),
        }

    def _write_packet(self, offset: int, packet: bytes):
        odd = self.sequence + 1
        even = self.sequence + 2
        struct.pack_into("<Q", self.mapping, offset, odd)
        self.mapping[offset + 8:offset + len(packet)] = packet[8:]
        struct.pack_into("<Q", self.mapping, offset, even)
        self.sequence = even

    def publish(self, simulator, neutral_local, root_origin, unit_id=1):
        model = simulator.model
        data = simulator.data
        root_delta = SIM_TO_BEDROCK @ (data.qpos[:3] - root_origin)
        root_linear = SIM_TO_BEDROCK @ data.qvel[:3]
        root_angular = SIM_TO_BEDROCK @ data.qvel[3:6]

        world = Rotation.from_quat(
            data.xquat[1:1 + simulator._num_robot_bodies][:, [1, 2, 3, 0]])
        world_matrices = world.as_matrix()
        rotations_wxyz = []
        for bone in BONES:
            parent, child = LINKS[bone]
            child_world = world_matrices[child]
            local = child_world if parent is None else (
                world_matrices[parent].T @ child_world)
            delta = local @ neutral_local[bone].T
            bedrock = SIM_TO_BEDROCK @ delta @ SIM_TO_BEDROCK.T
            xyzw = Rotation.from_matrix(bedrock).as_quat()
            rotations_wxyz.extend((xyzw[3], xyzw[0], xyzw[1], xyzw[2]))

        contact = np.zeros(2, dtype=np.uint8)
        normal_force = np.zeros(2, dtype=np.float64)
        foot_ids = (
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY,
                              "left_ankle_roll_link"),
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY,
                              "right_ankle_roll_link"),
        )
        for index in range(data.ncon):
            item = data.contact[index]
            body1 = int(model.geom_bodyid[item.geom1])
            body2 = int(model.geom_bodyid[item.geom2])
            for side, foot in enumerate(foot_ids):
                if body1 != foot and body2 != foot:
                    continue
                other = body2 if body1 == foot else body1
                if other != 0:
                    continue
                force = np.zeros(6, dtype=np.float64)
                mujoco.mj_contactForce(model, data, index, force)
                normal_force[side] += max(0.0, float(force[0]))
                contact[side] = normal_force[side] > 1.0e-3

        flags = FLAG_POLICY_LIVE
        if contact[0]:
            flags |= FLAG_LEFT_CONTACT
        if contact[1]:
            flags |= FLAG_RIGHT_CONTACT
        if data.qpos[2] < 0.45:
            flags |= FLAG_FALLEN
        contact_mask = int(contact[0]) | (int(contact[1]) << 1)
        normalized_force = np.clip(normal_force / (29.0 * 9.81), 0.0, 4.0)

        joints = np.zeros(41, dtype=np.float32)
        joint_velocity = np.zeros(41, dtype=np.float32)
        count = min(41, model.nu)
        joints[:count] = data.qpos[7:7 + count]
        joint_velocity[:count] = data.qvel[6:6 + count]
        now = time.perf_counter_ns()

        root_matrix = SIM_TO_BEDROCK @ world_matrices[0] @ SIM_TO_BEDROCK.T
        root_xyzw = Rotation.from_matrix(root_matrix).as_quat()
        root_wxyz = (root_xyzw[3], root_xyzw[0], root_xyzw[1], root_xyzw[2])
        state_values = (
            self.sequence + 2, now, flags, unit_id,
            *root_delta.astype(np.float32), *root_wxyz,
            *root_linear.astype(np.float32), *root_angular.astype(np.float32),
            *joints, *joint_velocity, contact_mask,
            *normalized_force.astype(np.float32), *np.zeros(6, dtype=np.float32),
            0.0, 0.0,
        )
        state_packet = STATE.pack(*state_values)
        visual_packet = VISUAL.pack(
            self.sequence + 2, now, flags, unit_id,
            *root_delta.astype(np.float32), *root_wxyz,
            *np.asarray(rotations_wxyz, dtype=np.float32),
            contact_mask, *normalized_force.astype(np.float32))
        self._write_packet(STATE_OFFSET, state_packet)
        # Keep both pages on the same even sequence for a coherent snapshot.
        visual_packet = bytearray(visual_packet)
        struct.pack_into("<Q", visual_packet, 0, self.sequence + 2)
        self._write_packet(VISUAL_OFFSET, bytes(visual_packet))


def neutral_local_matrices(simulator):
    world = Rotation.from_quat(
        simulator.data.xquat[1:1 + simulator._num_robot_bodies][:, [1, 2, 3, 0]])
    matrices = world.as_matrix()
    output = {}
    for bone in BONES:
        parent, child = LINKS[bone]
        child_world = matrices[child]
        output[bone] = child_world if parent is None else (
            matrices[parent].T @ child_world)
    return output


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--live-shared", required=True, type=Path)
    parser.add_argument("--live-motion-id", type=int, default=1)
    parser.add_argument("--live-max-seconds", type=float, default=0.0)
    parser.add_argument("--live-auto-impulse-seconds", type=float, default=-1.0)
    parser.add_argument("--live-auto-impulse-dv", type=float, default=-0.5)
    local, remaining = parser.parse_known_args()

    project_root = Path(__file__).resolve().parents[1]
    physics_root = project_root / "artifacts" / "motion_research" / "physics_v1"
    bundle_root = physics_root / "p1_isaaclab_bundle"
    for path in (bundle_root, physics_root):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)

    if not np.isclose(np.linalg.det(SIM_TO_BEDROCK), 1.0):
        raise RuntimeError("simulation-to-Bedrock basis is mirrored")

    from protomotions.agents.evaluators.mimic_evaluator import MimicEvaluator
    from protomotions import inference_agent

    shared = SharedState(local.live_shared.resolve())
    stop = False

    def stop_handler(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    @torch.no_grad()
    def live_evaluate(self):
        nonlocal stop
        self.agent.eval()
        simulator = self.env.simulator
        if not hasattr(simulator, "data"):
            raise RuntimeError("live bridge requires the MuJoCo backend")
        env_ids = torch.tensor([0], dtype=torch.long, device=self.device)
        motion_id = torch.tensor(
            [local.live_motion_id], dtype=torch.long, device=self.device)
        global_start = None
        last_command_sequence = -1
        reset_requested = False

        while not stop:
            self.motion_manager.motion_ids[env_ids] = motion_id
            self.motion_manager.motion_times[env_ids] = 0.0
            obs, _ = self.env.reset(
                env_ids, sample_flat=True, disable_motion_resample=True)
            self.agent.pre_collect_step(0)
            obs = self.agent.add_agent_info_to_obs(obs)
            obs_td = self.agent.obs_dict_to_tensordict(obs)
            neutral = neutral_local_matrices(simulator)
            origin = simulator.data.qpos[:3].copy()
            previous_actions = None
            episode_start = time.perf_counter()
            next_step = episode_start
            impulse_sent = False
            reset_requested = False

            for step_index in range(1000000):
                if stop:
                    break
                if (local.live_max_seconds > 0.0
                        and global_start is not None
                        and time.perf_counter() - global_start
                        >= local.live_max_seconds):
                    stop = True
                    break
                command = shared.read_command()
                if command is not None:
                    last_command_sequence = command["sequence"]
                    if command["flags"] & FLAG_RESET:
                        reset_requested = True
                    if command["flags"] & FLAG_IMPULSE:
                        velocity = command["desired_velocity"]
                        impulse = torch.tensor(
                            [[float(velocity[0]), float(velocity[1]), 0.0]],
                            dtype=torch.float32, device=self.device)
                        simulator._apply_root_velocity_impulse(
                            impulse, torch.zeros_like(impulse), env_ids)
                elapsed = time.perf_counter() - episode_start
                if (not impulse_sent
                        and local.live_auto_impulse_seconds >= 0.0
                        and elapsed >= local.live_auto_impulse_seconds):
                    impulse = torch.tensor(
                        [[0.0, local.live_auto_impulse_dv, 0.0]],
                        dtype=torch.float32, device=self.device)
                    simulator._apply_root_velocity_impulse(
                        impulse, torch.zeros_like(impulse), env_ids)
                    impulse_sent = True

                actions = self._policy_action(obs_td)
                alpha = self.config.eval_action_ema_alpha
                if alpha is not None:
                    if previous_actions is None:
                        previous_actions = actions.clone()
                    actions = alpha * actions + (1.0 - alpha) * previous_actions
                    previous_actions = actions.clone()
                obs, _reward, dones, _terminated, _extras = self.env.step(actions)
                self.agent.pre_collect_step(step_index + 1)
                obs = self.agent.add_agent_info_to_obs(obs)
                obs_td = self.agent.obs_dict_to_tensordict(obs)
                shared.publish(simulator, neutral, origin)
                if global_start is None:
                    # Exclude lazy PyTorch materialization from the requested
                    # live-duration window; it is a one-time startup cost.
                    global_start = time.perf_counter()

                if reset_requested or bool(dones[0].item()):
                    break
                next_step += self.env.dt
                remaining_time = next_step - time.perf_counter()
                if remaining_time > 0.0:
                    time.sleep(remaining_time)

        print("LIVE_POLICY_BRIDGE_STOPPED", flush=True)
        return {}, None, 1

    MimicEvaluator.evaluate = live_evaluate
    sys.argv = [sys.argv[0], *remaining]
    try:
        inference_agent.main()
    finally:
        shared.close()


if __name__ == "__main__":
    main()
