#!/usr/bin/env python3
"""Author one readable EVA straight strike on the measured Tiger hierarchy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


PARENTS = {
    "root": None,
    "torso_lower": "root",
    "torso_upper": "torso_lower",
    "neck": "torso_upper",
    "head": "neck",
    "clavicle_l": "torso_upper",
    "arm_l": "clavicle_l",
    "forearm_l": "arm_l",
    "wrist_l": "forearm_l",
    "hand_l": "wrist_l",
    "clavicle_r": "torso_upper",
    "arm_r": "clavicle_r",
    "forearm_r": "arm_r",
    "wrist_r": "forearm_r",
    "hand_r": "wrist_r",
    "leg_l": "torso_lower",
    "shin_l": "leg_l",
    "ankle_l": "shin_l",
    "foot_l": "ankle_l",
    "leg_r": "torso_lower",
    "shin_r": "leg_r",
    "ankle_r": "shin_r",
    "foot_r": "ankle_r",
}


KEYS = (
    # frame, lower yaw, upper yaw, upper pitch, right elbow, right wrist
    (0, 0.0, 0.0, -2.0, (12, -8, -2), (-6, 8, -5)),
    (6, 0.0, 0.0, -2.0, (12, -8, -2), (-6, 8, -5)),
    (12, -6.0, -16.0, -8.0, (22, -18, 4), (10, -5, -12)),
    (18, 6.0, 13.0, -14.0, (12, -10, -28), (0, -5, -54)),
    (22, 10.0, 24.0, -18.0, (6, -7, -31), (-8, -4, -59)),
    (26, 12.0, 28.0, -20.0, (0, -9, -31), (-14, -8, -55)),
    (35, 4.0, 8.0, -8.0, (9, -11, -18), (-4, 0, -35)),
    (47, 0.0, 0.0, -2.0, (12, -8, -2), (-6, 8, -5)),
)


def runtime_matrix(value):
    authored = Rotation.from_quat((value[1], value[2], value[3], value[0]))
    euler = authored.as_euler("xyz")
    return Rotation.from_euler("xyz", (-euler[0], -euler[1], euler[2])).as_matrix()


def authored_wxyz(matrix):
    euler = Rotation.from_matrix(matrix).as_euler("xyz")
    value = Rotation.from_euler("xyz", (-euler[0], -euler[1], euler[2])).as_quat()
    return [round(float(value[3]), 7), round(float(value[0]), 7),
            round(float(value[1]), 7), round(float(value[2]), 7)]


def direction_frame(direction):
    forward = np.asarray(direction, dtype=np.float64)
    forward /= np.linalg.norm(forward)
    up_hint = np.asarray((0.0, 1.0, 0.0))
    right = np.cross(up_hint, forward)
    if np.linalg.norm(right) < 1.0e-8:
        right = np.cross((1.0, 0.0, 0.0), forward)
    right /= np.linalg.norm(right)
    up = np.cross(forward, right)
    up /= np.linalg.norm(up)
    return np.column_stack((right, up, forward))


def interpolate(frame):
    for left, right in zip(KEYS, KEYS[1:]):
        if frame <= right[0]:
            amount = (frame - left[0]) / max(1, right[0] - left[0])
            amount = amount * amount * (3.0 - 2.0 * amount)
            scalar = [
                left[index] + (right[index] - left[index]) * amount
                for index in range(1, 4)
            ]
            elbow = np.asarray(left[4], dtype=np.float64) * (1.0 - amount)
            elbow += np.asarray(right[4], dtype=np.float64) * amount
            wrist = np.asarray(left[5], dtype=np.float64) * (1.0 - amount)
            wrist += np.asarray(right[5], dtype=np.float64) * amount
            return (*scalar, elbow, wrist)
    return (*KEYS[-1][1:4], np.asarray(KEYS[-1][4]),
            np.asarray(KEYS[-1][5]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--finger-source", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    base = json.loads(args.base.read_text(encoding="utf-8"))
    finger_source = json.loads(args.finger_source.read_text(encoding="utf-8"))
    base_bones = list(base["bones"])
    base_frame = next(iter(base["clips"].values()))["frames"][0]
    base_rotations = {
        bone: runtime_matrix(base_frame["rotation_wxyz"][index])
        for index, bone in enumerate(base_bones)
    }
    finger_bones = [
        bone for bone in finger_source["bones"]
        if bone.startswith("finger_")
    ]
    finger_clip = finger_source["clips"]["punch_cross"]
    finger_frame = finger_clip["frames"][len(finger_clip["frames"]) // 2]
    finger_index = {bone: index for index, bone in enumerate(
        finger_source["bones"])}
    finger_rotations = {
        bone: finger_frame["rotation_wxyz"][finger_index[bone]]
        for bone in finger_bones
    }

    geometry = json.loads(args.geo.read_text(
        encoding="utf-8"))["minecraft:geometry"][0]["bones"]
    pivots = {}
    for row in geometry:
        raw = np.asarray(row.get("pivot", (0.0, 0.0, 0.0)),
                         dtype=np.float64)
        pivots[row["name"]] = np.asarray((-raw[0], raw[1], raw[2]))

    output_bones = base_bones + [bone for bone in finger_bones
                                if bone not in base_bones]
    frames = []
    maximum_step = 0.0
    previous = None
    for frame_index in range(KEYS[-1][0] + 1):
        lower_yaw, upper_yaw, upper_pitch, elbow_r, wrist_r = interpolate(
            frame_index)
        local = {bone: matrix.copy() for bone, matrix in base_rotations.items()}
        local["torso_lower"] = (
            Rotation.from_euler(
                "xy", np.radians((0.35 * upper_pitch, lower_yaw))
            ).as_matrix()
            @ base_rotations["torso_lower"]
        )
        local["torso_upper"] = (
            Rotation.from_euler(
                "xy", np.radians((upper_pitch, upper_yaw))
            ).as_matrix() @ base_rotations["torso_upper"]
        )
        local["neck"] = (
            Rotation.from_euler("y", np.radians(-0.60 * upper_yaw)).as_matrix()
            @ base_rotations["neck"]
        )

        global_rotation = {}
        for bone in base_bones:
            if bone in {"arm_l", "forearm_l", "wrist_l", "hand_l",
                        "arm_r", "forearm_r", "wrist_r", "hand_r"}:
                continue
            parent = PARENTS.get(bone)
            global_rotation[bone] = (
                local[bone] if parent is None
                else global_rotation[parent] @ local[bone]
            )

        targets = {
            "l": (np.asarray((-12, -8, -2), dtype=np.float64),
                  np.asarray((6, 8, -5), dtype=np.float64)),
            "r": (elbow_r, wrist_r),
        }
        for side, (elbow, wrist) in targets.items():
            arm = f"arm_{side}"
            forearm = f"forearm_{side}"
            wrist_bone = f"wrist_{side}"
            hand = f"hand_{side}"
            bind_arm = pivots[forearm] - pivots[arm]
            bind_forearm = pivots[wrist_bone] - pivots[forearm]
            arm_global = direction_frame(elbow) @ direction_frame(bind_arm).T
            forearm_global = (
                direction_frame(wrist - elbow)
                @ direction_frame(bind_forearm).T
            )
            parent = PARENTS[arm]
            local[arm] = global_rotation[parent].T @ arm_global
            global_rotation[arm] = arm_global
            local[forearm] = arm_global.T @ forearm_global
            global_rotation[forearm] = forearm_global
            local[wrist_bone] = np.identity(3)
            global_rotation[wrist_bone] = forearm_global
            local[hand] = np.identity(3)
            global_rotation[hand] = forearm_global

        authored = [authored_wxyz(local[bone]) for bone in base_bones]
        authored.extend(finger_rotations[bone] for bone in output_bones
                        if bone in finger_rotations)
        if previous is not None:
            for before, after in zip(previous, local.values()):
                maximum_step = max(maximum_step, float((
                    Rotation.from_matrix(before).inv()
                    * Rotation.from_matrix(after)
                ).magnitude()))
        previous = [local[bone].copy() for bone in base_bones]
        frames.append({
            "root_m": [0.0, 0.0, 0.0],
            "rotation_wxyz": authored,
            "foot_contact": [True, True],
        })

    output = {
        "schema": 2,
        "coordinate_system": "gecko_authored_y_up_negative_z_front",
        "quaternion_order": "wxyz",
        "sample_rate": 60.0,
        "preview_only": True,
        "authority": "project_authored_readable_attack_review_only",
        "sources": [{
            "name": "Quaternius punch timing reference plus Project SEELE rig",
            "url": "https://quaternius.com/packs/universalanimationlibrary.html",
            "license": "CC0-1.0 plus project-authored transformation",
        }],
        "bones": output_bones,
        "clips": {
            "ordinary_attack_right": {
                "duration_seconds": round((len(frames) - 1) / 60.0, 7),
                "loop": False,
                "role": "isolated_ordinary_attack_human_review_only",
                "frames": frames,
            }
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        output, ensure_ascii=False, separators=(",", ":")
    ) + "\n", encoding="utf-8")
    report = {
        "schema": 1,
        "frames": len(frames),
        "duration_seconds": output["clips"]["ordinary_attack_right"][
            "duration_seconds"],
        "bones": len(output_bones),
        "maximum_local_rotation_step_degrees": float(np.degrees(
            maximum_step)),
        "strike": "right palm thrust with planted stance and guarded left hand",
        "status": "human_review_required",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        report, ensure_ascii=False, indent=2
    ) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
