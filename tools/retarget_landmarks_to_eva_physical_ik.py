#!/usr/bin/env python3
"""Retarget normalized BVH landmarks to the 41-DOF EVA model by IK."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


TARGETS = [
    ("abdomen", "body", "abdomen", 0.45),
    ("thorax", "body", "thorax", 0.65),
    ("neck", "body", "neck", 0.65),
    ("head", "body", "head", 1.30),
    ("shoulder_l", "body", "upper_arm_l", 0.25),
    ("elbow_l", "body", "elbow_link_l", 1.30),
    ("wrist_l", "body", "wrist_link_l", 1.70),
    ("hand_l", "geom", "knuckle_l", 1.45),
    ("shoulder_r", "body", "upper_arm_r", 0.25),
    ("elbow_r", "body", "elbow_link_r", 1.30),
    ("wrist_r", "body", "wrist_link_r", 1.70),
    ("hand_r", "geom", "knuckle_r", 1.45),
    ("hip_l", "body", "thigh_l", 0.45),
    ("knee_l", "body", "shin_l", 1.25),
    ("ankle_l", "body", "ankle_link_l", 1.85),
    ("toe_l", "body", "toe_l", 1.45),
    ("hip_r", "body", "thigh_r", 0.45),
    ("knee_r", "body", "shin_r", 1.25),
    ("ankle_r", "body", "ankle_link_r", 1.85),
    ("toe_r", "body", "toe_r", 1.45),
]

PARENTS = {
    "abdomen": "pelvis", "thorax": "abdomen", "neck": "thorax",
    "head": "neck", "shoulder_l": "thorax", "elbow_l": "shoulder_l",
    "wrist_l": "elbow_l", "hand_l": "wrist_l",
    "shoulder_r": "thorax", "elbow_r": "shoulder_r",
    "wrist_r": "elbow_r", "hand_r": "wrist_r",
    "hip_l": "pelvis", "knee_l": "hip_l", "ankle_l": "knee_l",
    "toe_l": "ankle_l", "hip_r": "pelvis", "knee_r": "hip_r",
    "ankle_r": "knee_r", "toe_r": "ankle_r",
}

ABSOLUTE_ANCHOR_WEIGHTS = {
    "head": 0.35,
    "hand_l": 0.75,
    "hand_r": 0.75,
    "ankle_l": 1.00,
    "toe_l": 1.00,
    "ankle_r": 1.00,
    "toe_r": 1.00,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--landmarks", required=True, type=Path)
    parser.add_argument("--reference-landmarks", type=Path)
    parser.add_argument(
        "--initial-tangent-state", type=Path,
        help="Optional prior solved trajectory used only to seed frame zero.",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--max-nfev", type=int, default=70)
    parser.add_argument("--temporal-weight", type=float, default=0.055)
    parser.add_argument("--acceleration-weight", type=float, default=0.018)
    parser.add_argument("--neutral-weight", type=float, default=0.004)
    parser.add_argument("--shoulder-offset-mode",
                        choices=("body", "yaw", "world"),
                        default="body")
    parser.add_argument("--thorax-orientation-weight", type=float,
                        default=0.55)
    parser.add_argument("--objective-mode", choices=("absolute", "segment"),
                        default="segment")
    parser.add_argument("--root-orientation-mode", choices=("yaw", "full"),
                        default="yaw")
    parser.add_argument(
        "--root-tilt-scale", type=float, default=0.0,
        help=("Blend source pelvis roll/pitch into a yaw-authority root. "
              "0 keeps yaw only; 1 reproduces the full source basis."),
    )
    parser.add_argument(
        "--root-position-mode", choices=("relative", "shared"),
        default="relative",
        help=("Use the actor's first pelvis as origin, or preserve a shared "
              "source-space origin for synchronized multi-actor motion."),
    )
    parser.add_argument(
        "--root-yaw-mode", choices=("relative", "shared"),
        default="relative",
        help=("Remove the actor's initial yaw, or preserve yaw in a shared "
              "multi-actor frame."),
    )
    parser.add_argument("--target-construction",
                        choices=("chain", "bind_delta"), default="chain")
    parser.add_argument("--flex-weight", type=float, default=0.16)
    parser.add_argument("--limit-barrier-weight", type=float, default=0.10)
    parser.add_argument("--contact-weight", type=float, default=4.0)
    parser.add_argument("--contact-ground-weight", type=float, default=24.0)
    parser.add_argument("--contact-orientation-weight", type=float, default=4.0)
    parser.add_argument("--ground-penetration-weight", type=float, default=80.0)
    parser.add_argument("--force-contact",
                        choices=("none", "left", "right", "both"),
                        default="none")
    parser.add_argument("--contact-blend-frames", type=int, default=4)
    parser.add_argument("--initial-multistart", type=int, default=6)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    source = np.load(args.landmarks)
    names = [str(value) for value in source["landmark_names"]]
    source_index = {name: index for index, name in enumerate(names)}
    positions_h = np.asarray(source["positions_H"], dtype=np.float64)
    source_frames = np.asarray(source["frames"], dtype=np.float64)
    fps = float(source["fps"][0])
    source_yaw = np.asarray(source["root_yaw_rad"], dtype=np.float64)
    contacts = np.asarray(source["foot_contact"], dtype=np.bool_)
    if args.force_contact in {"left", "both"}:
        contacts[:, 0] = True
    if args.force_contact in {"right", "both"}:
        contacts[:, 1] = True
    if model.nv != 47 or model.nu != 41:
        raise RuntimeError(
            f"expected 41-DOF EVA model, got nq={model.nq} "
            f"nv={model.nv} nu={model.nu}"
        )
    reference_pose = None
    if args.reference_landmarks is not None:
        reference = np.load(args.reference_landmarks)
        reference_names = [str(value) for value in reference["landmark_names"]]
        if reference_names != names:
            raise RuntimeError("reference landmark order does not match source")
        reference_pose = np.median(
            np.asarray(reference["positions_H"], dtype=np.float64), axis=0
        )
    if args.target_construction == "bind_delta" and reference_pose is None:
        raise RuntimeError("bind_delta requires --reference-landmarks")

    mujoco.mj_forward(model, data)
    default_qpos = data.qpos.copy()
    head_id = model.body("head").id
    foot_l_id = model.body("foot_l").id
    foot_r_id = model.body("foot_r").id
    target_height = float(
        data.xpos[head_id, 2]
        - min(data.xpos[foot_l_id, 2], data.xpos[foot_r_id, 2])
    )
    base_translation = default_qpos[:3].copy()

    tangent_names, lower, upper = tangent_metadata(args.model)
    if len(tangent_names) != 41:
        raise RuntimeError(
            f"expected 41 tangent coordinates, got {len(tangent_names)}"
        )
    joint_vector_index = {
        name: index for index, name in enumerate(tangent_names)
    }
    joint_groups = {}
    for index, name in enumerate(tangent_names):
        actuator_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"a_{name}")
        if actuator_id < 0:
            raise RuntimeError(f"missing actuator a_{name}")
        joint_id = int(model.actuator_trnid[actuator_id, 0])
        spec = {
            "index": index,
            "axis": np.asarray(
                model.actuator_gear[actuator_id, :3], dtype=np.float64
            ).copy(),
        }
        joint_groups.setdefault(joint_id, []).append(spec)

    def set_tangent_qpos(value: np.ndarray) -> None:
        for joint_id, specs in joint_groups.items():
            joint_type = int(model.jnt_type[joint_id])
            address = int(model.jnt_qposadr[joint_id])
            if joint_type == mujoco.mjtJoint.mjJNT_BALL:
                rotation_vector = sum(
                    (spec["axis"] * value[spec["index"]]
                     for spec in specs),
                    np.zeros(3, dtype=np.float64),
                )
                angle = float(np.linalg.norm(rotation_vector))
                if angle < 1.0e-10:
                    data.qpos[address:address + 4] = (
                        1.0, 0.0, 0.0, 0.0
                    )
                else:
                    axis = rotation_vector / angle
                    data.qpos[address:address + 4] = np.concatenate((
                        [math.cos(angle * 0.5)],
                        axis * math.sin(angle * 0.5),
                    ))
            elif joint_type == mujoco.mjtJoint.mjJNT_HINGE:
                if len(specs) != 1:
                    raise RuntimeError(
                        "hinge has multiple tangent coordinates"
                    )
                data.qpos[address] = value[specs[0]["index"]]
            else:
                raise RuntimeError(f"unsupported joint type {joint_type}")

    target_ids = []
    for source_name, object_type, target_name, weight in TARGETS:
        if source_name not in source_index:
            raise RuntimeError(f"missing source landmark {source_name}")
        if object_type == "body":
            object_id = mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_BODY, target_name)
        else:
            object_id = mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_GEOM, target_name)
        if object_id < 0:
            raise RuntimeError(f"missing target {object_type} {target_name}")
        target_ids.append((source_name, object_type, object_id, weight))

    def target_position(object_type: str, object_id: int) -> np.ndarray:
        return (data.xpos[object_id] if object_type == "body"
                else data.geom_xpos[object_id])

    neutral_positions = {
        name: data.xpos[model.body(body_name).id].copy()
        for name, body_name in {
            "pelvis": "pelvis", "abdomen": "abdomen",
            "thorax": "thorax", "neck": "neck", "head": "head",
            "shoulder_l": "upper_arm_l", "elbow_l": "elbow_link_l",
            "wrist_l": "wrist_link_l", "hip_l": "thigh_l",
            "knee_l": "shin_l", "ankle_l": "ankle_link_l",
            "toe_l": "toe_l", "shoulder_r": "upper_arm_r",
            "elbow_r": "elbow_link_r", "wrist_r": "wrist_link_r",
            "hip_r": "thigh_r", "knee_r": "shin_r",
            "ankle_r": "ankle_link_r", "toe_r": "toe_r",
        }.items()
    }
    neutral_positions["hand_l"] = data.geom_xpos[
        model.geom("knuckle_l").id].copy()
    neutral_positions["hand_r"] = data.geom_xpos[
        model.geom("knuckle_r").id].copy()

    def geom_bottom(geom_name: str) -> float:
        geom_id = model.geom(geom_name).id
        rotation = data.geom_xmat[geom_id].reshape(3, 3)
        size = np.asarray(model.geom_size[geom_id], dtype=np.float64)
        geom_type = int(model.geom_type[geom_id])
        if geom_type == mujoco.mjtGeom.mjGEOM_BOX:
            vertical_extent = float(np.sum(np.abs(rotation[2]) * size))
        elif geom_type == mujoco.mjtGeom.mjGEOM_ELLIPSOID:
            vertical_extent = float(np.sqrt(np.sum(
                (rotation[2] * size) ** 2
            )))
        else:
            raise RuntimeError(
                f"unsupported sole geometry type for {geom_name}"
            )
        return float(data.geom_xpos[geom_id, 2] - vertical_extent)

    ground_id = model.geom("ground").id
    ground_z = float(data.geom_xpos[ground_id, 2])
    contact_landmark_clearance = {}
    for side in ("l", "r"):
        sole_bottom = min(
            geom_bottom(f"heel_{side}"),
            geom_bottom(f"forefoot_{side}"),
            geom_bottom(f"toe_{side}_collision"),
        )
        contact_landmark_clearance[side] = {
            "ankle": (
                neutral_positions[f"ankle_{side}"][2] - sole_bottom
            ),
            "toe": neutral_positions[f"toe_{side}"][2] - sole_bottom,
        }

    def neutral_length(first: str, second: str) -> float:
        return float(np.linalg.norm(
            neutral_positions[second] - neutral_positions[first]
        ))

    segment_lengths = {
        ("pelvis", "abdomen"): neutral_length("pelvis", "abdomen"),
        ("abdomen", "thorax"): neutral_length("abdomen", "thorax"),
        ("thorax", "neck"): neutral_length("thorax", "neck"),
        ("neck", "head"): neutral_length("neck", "head"),
    }
    for side in ("l", "r"):
        segment_lengths[("thorax", f"shoulder_{side}")] = neutral_length(
            "thorax", f"shoulder_{side}")
        segment_lengths[(f"shoulder_{side}", f"elbow_{side}")] = neutral_length(
            f"shoulder_{side}", f"elbow_{side}")
        segment_lengths[(f"elbow_{side}", f"wrist_{side}")] = neutral_length(
            f"elbow_{side}", f"wrist_{side}")
        segment_lengths[(f"wrist_{side}", f"hand_{side}")] = neutral_length(
            f"wrist_{side}", f"hand_{side}")
        segment_lengths[("pelvis", f"hip_{side}")] = neutral_length(
            "pelvis", f"hip_{side}")
        segment_lengths[(f"hip_{side}", f"knee_{side}")] = neutral_length(
            f"hip_{side}", f"knee_{side}")
        segment_lengths[(f"knee_{side}", f"ankle_{side}")] = neutral_length(
            f"knee_{side}", f"ankle_{side}")
        segment_lengths[(f"ankle_{side}", f"toe_{side}")] = neutral_length(
            f"ankle_{side}", f"toe_{side}")

    def normalized_direction(source_row, first: str, second: str,
                             fallback: np.ndarray) -> np.ndarray:
        value = (source_row[source_index[second]]
                 - source_row[source_index[first]])
        length = float(np.linalg.norm(value))
        if length < 1.0e-8:
            return fallback
        return value / length

    def build_desired(source_row: np.ndarray,
                      pelvis_position: np.ndarray):
        def body_basis(left_name: str, right_name: str,
                       lower_name: str, upper_name: str) -> np.ndarray:
            up = (source_row[source_index[upper_name]]
                  - source_row[source_index[lower_name]])
            if np.linalg.norm(up) < 1.0e-8:
                up = np.asarray((0.0, 0.0, 1.0), dtype=np.float64)
            else:
                up /= np.linalg.norm(up)
            left_axis = (source_row[source_index[left_name]]
                         - source_row[source_index[right_name]])
            left_axis -= up * np.dot(left_axis, up)
            if np.linalg.norm(left_axis) < 1.0e-8:
                left_axis = np.asarray((0.0, 1.0, 0.0), dtype=np.float64)
                left_axis -= up * np.dot(left_axis, up)
            left_axis /= max(np.linalg.norm(left_axis), 1.0e-8)
            forward_axis = np.cross(left_axis, up)
            if np.linalg.norm(forward_axis) < 1.0e-8:
                forward_axis = np.asarray((1.0, 0.0, 0.0),
                                          dtype=np.float64)
            else:
                forward_axis /= np.linalg.norm(forward_axis)
            left_axis = np.cross(up, forward_axis)
            left_axis /= max(np.linalg.norm(left_axis), 1.0e-8)
            return np.column_stack((forward_axis, left_axis, up))

        if args.target_construction == "bind_delta":
            desired = {"pelvis": pelvis_position.copy()}
            reference_pelvis = reference_pose[source_index["pelvis"]]
            source_pelvis = source_row[source_index["pelvis"]]
            for name, neutral in neutral_positions.items():
                if name == "pelvis":
                    continue
                source_relative = (
                    source_row[source_index[name]] - source_pelvis
                )
                reference_relative = (
                    reference_pose[source_index[name]] - reference_pelvis
                )
                desired[name] = (
                    pelvis_position
                    + neutral - neutral_positions["pelvis"]
                    + (source_relative - reference_relative) * target_height
                )
            thorax_basis = body_basis(
                "shoulder_l", "shoulder_r", "thorax", "neck"
            )
            pelvis_basis = body_basis(
                "hip_l", "hip_r", "pelvis", "abdomen"
            )
            return desired, {"pelvis": pelvis_basis,
                             "thorax": thorax_basis}

        desired = {"pelvis": pelvis_position.copy()}
        for first, second in (("pelvis", "abdomen"),
                              ("abdomen", "thorax"),
                              ("thorax", "neck"),
                              ("neck", "head")):
            fallback = (
                neutral_positions[second] - neutral_positions[first]
            ) / max(segment_lengths[(first, second)], 1.0e-8)
            desired[second] = (
                desired[first]
                + normalized_direction(source_row, first, second, fallback)
                * segment_lengths[(first, second)]
            )
        thorax_basis = body_basis(
            "shoulder_l", "shoulder_r", "thorax", "neck"
        )
        pelvis_basis = body_basis(
            "hip_l", "hip_r", "pelvis", "abdomen"
        )
        thorax_yaw = math.atan2(thorax_basis[1, 0], thorax_basis[0, 0])
        thorax_yaw_basis = np.asarray((
            (math.cos(thorax_yaw), -math.sin(thorax_yaw), 0.0),
            (math.sin(thorax_yaw), math.cos(thorax_yaw), 0.0),
            (0.0, 0.0, 1.0),
        ))
        for side in ("l", "r"):
            shoulder = f"shoulder_{side}"
            desired[shoulder] = (
                desired["thorax"]
                + ((thorax_basis @ (
                    neutral_positions[shoulder]
                    - neutral_positions["thorax"]
                )) if args.shoulder_offset_mode == "body" else (
                    thorax_yaw_basis @ (
                        neutral_positions[shoulder]
                        - neutral_positions["thorax"]
                    ) if args.shoulder_offset_mode == "yaw" else
                    neutral_positions[shoulder]
                    - neutral_positions["thorax"]
                ))
            )
            for first, second in ((shoulder, f"elbow_{side}"),
                                  (f"elbow_{side}", f"wrist_{side}"),
                                  (f"wrist_{side}", f"hand_{side}")):
                fallback = (
                    neutral_positions[second] - neutral_positions[first]
                ) / max(segment_lengths[(first, second)], 1.0e-8)
                desired[second] = (
                    desired[first]
                    + normalized_direction(source_row, first, second, fallback)
                    * segment_lengths[(first, second)]
                )
            hip = f"hip_{side}"
            desired[hip] = (
                desired["pelvis"]
                + pelvis_basis @ (
                    neutral_positions[hip]
                    - neutral_positions["pelvis"]
                )
            )
            for first, second in ((hip, f"knee_{side}"),
                                  (f"knee_{side}", f"ankle_{side}"),
                                  (f"ankle_{side}", f"toe_{side}")):
                fallback = (
                    neutral_positions[second] - neutral_positions[first]
                ) / max(segment_lengths[(first, second)], 1.0e-8)
                desired[second] = (
                    desired[first]
                    + normalized_direction(source_row, first, second, fallback)
                    * segment_lengths[(first, second)]
                )
        return desired, {"pelvis": pelvis_basis, "thorax": thorax_basis}

    initial_source_pelvis = positions_h[0, source_index["pelvis"]].copy()
    if args.root_position_mode == "relative":
        initial_source_pelvis -= positions_h[0, source_index["pelvis"]]
    initial_pelvis_position = (
        base_translation + initial_source_pelvis * target_height
    )
    initial_desired, _ = build_desired(
        positions_h[0], initial_pelvis_position
    )
    initial_ground_candidates = []
    for side_index, side in enumerate(("l", "r")):
        if bool(contacts[0, side_index]):
            initial_ground_candidates.extend((
                initial_desired[f"ankle_{side}"][2]
                - contact_landmark_clearance[side]["ankle"],
                initial_desired[f"toe_{side}"][2]
                - contact_landmark_clearance[side]["toe"],
            ))
    if not initial_ground_candidates:
        for side in ("l", "r"):
            initial_ground_candidates.extend((
                initial_desired[f"ankle_{side}"][2]
                - contact_landmark_clearance[side]["ankle"],
                initial_desired[f"toe_{side}"][2]
                - contact_landmark_clearance[side]["toe"],
            ))
    root_ground_offset = (
        ground_z - float(np.min(initial_ground_candidates))
    )

    qpos_rows = []
    tangent_rows = []
    desired_rows = []
    actual_rows = []
    contact_blend_rows = []
    errors = []
    frame_reports = []
    def source_flex(frame_index: int, first: str,
                    pivot: str, last: str) -> float:
        row = positions_h[frame_index]
        first_vector = (row[source_index[first]]
                        - row[source_index[pivot]])
        second_vector = (row[source_index[last]]
                         - row[source_index[pivot]])
        first_vector /= max(np.linalg.norm(first_vector), 1.0e-8)
        second_vector /= max(np.linalg.norm(second_vector), 1.0e-8)
        joint_angle = math.acos(float(np.clip(
            np.dot(first_vector, second_vector), -1.0, 1.0
        )))
        return math.pi - joint_angle

    previous = np.zeros(41, dtype=np.float64)
    if args.initial_tangent_state is not None:
        seed_state = np.load(args.initial_tangent_state)
        seed_names = [str(value) for value in seed_state["tangent_names"]]
        if seed_names != tangent_names:
            raise RuntimeError("initial tangent state order does not match")
        seed_frames = np.asarray(seed_state["source_frames"], dtype=np.float64)
        seed_index = int(np.argmin(np.abs(seed_frames - source_frames[0])))
        previous[:] = np.asarray(
            seed_state["tangent"], dtype=np.float64
        )[seed_index]
    else:
        for side in ("l", "r"):
            previous[joint_vector_index[f"elbow_{side}"]] = source_flex(
                0, f"shoulder_{side}", f"elbow_{side}", f"wrist_{side}"
            )
            previous[joint_vector_index[f"knee_{side}"]] = source_flex(
                0, f"hip_{side}", f"knee_{side}", f"ankle_{side}"
            )
    previous = np.clip(previous, lower + 1.0e-6, upper - 1.0e-6)
    before_previous = previous.copy()
    contact_anchors = {"l": None, "r": None}
    contact_phase = {"l": 0.0, "r": 0.0}
    for frame_index in range(len(source_frames)):
        source_row = positions_h[frame_index]
        source_pelvis = source_row[source_index["pelvis"]]
        if args.root_position_mode == "relative":
            source_pelvis = (
                source_pelvis
                - positions_h[0, source_index["pelvis"]]
            )
        pelvis_position = base_translation + source_pelvis * target_height
        pelvis_position[2] += root_ground_offset
        desired, desired_bases = build_desired(source_row, pelvis_position)
        contact_blend = {"l": 0.0, "r": 0.0}
        for side_index, side in enumerate(("l", "r")):
            planted = bool(contacts[frame_index, side_index])
            if planted:
                if contact_anchors[side] is None:
                    if actual_rows:
                        previous_actual = {
                            name: actual_rows[-1][index]
                            for index, name in enumerate(
                                source_name for source_name, _, _, _
                                in target_ids
                            )
                        }
                        ankle_anchor = previous_actual[f"ankle_{side}"].copy()
                        toe_anchor = previous_actual[f"toe_{side}"].copy()
                    else:
                        ankle_anchor = desired[f"ankle_{side}"].copy()
                        toe_anchor = desired[f"toe_{side}"].copy()
                    ankle_anchor[2] = (
                        ground_z
                        + contact_landmark_clearance[side]["ankle"]
                    )
                    toe_anchor[2] = (
                        ground_z
                        + contact_landmark_clearance[side]["toe"]
                    )
                    contact_anchors[side] = {
                        "ankle": ankle_anchor,
                        "toe": toe_anchor,
                    }
                    if frame_index == 0:
                        contact_phase[side] = 1.0
                contact_phase[side] = min(
                    1.0, contact_phase[side]
                    + 1.0 / max(1, args.contact_blend_frames)
                )
            else:
                contact_phase[side] = max(
                    0.0, contact_phase[side]
                    - 1.0 / max(1, args.contact_blend_frames)
                )
            phase = contact_phase[side]
            weight = phase * phase * (3.0 - 2.0 * phase)
            if contact_anchors[side] is not None and weight > 0.0:
                contact_blend[side] = weight
                desired[f"ankle_{side}"] = (
                    desired[f"ankle_{side}"] * (1.0 - weight)
                    + contact_anchors[side]["ankle"] * weight
                )
                desired[f"toe_{side}"] = (
                    desired[f"toe_{side}"] * (1.0 - weight)
                    + contact_anchors[side]["toe"] * weight
                )
                hip_name = f"hip_{side}"
                knee_name = f"knee_{side}"
                ankle_name = f"ankle_{side}"
                hip = desired[hip_name]
                ankle = desired[ankle_name]
                original_knee = desired[knee_name]
                axis = ankle - hip
                distance = float(np.linalg.norm(axis))
                upper_leg = segment_lengths[(hip_name, knee_name)]
                lower_leg = segment_lengths[(knee_name, ankle_name)]
                distance = min(
                    max(distance, abs(upper_leg - lower_leg) + 1.0e-6),
                    upper_leg + lower_leg - 1.0e-6,
                )
                axis /= max(np.linalg.norm(axis), 1.0e-8)
                along = (
                    upper_leg * upper_leg - lower_leg * lower_leg
                    + distance * distance
                ) / (2.0 * distance)
                bend_radius = math.sqrt(max(
                    0.0, upper_leg * upper_leg - along * along
                ))
                projection = hip + axis * np.dot(original_knee - hip, axis)
                bend = original_knee - projection
                bend -= axis * np.dot(bend, axis)
                if np.linalg.norm(bend) < 1.0e-8:
                    bend = np.cross(
                        axis, np.asarray((0.0, 1.0, 0.0))
                    )
                bend /= max(np.linalg.norm(bend), 1.0e-8)
                desired[knee_name] = (
                    hip + axis * along + bend * bend_radius
                )
            elif not planted:
                contact_anchors[side] = None
        yaw = float(source_yaw[frame_index])
        if args.root_yaw_mode == "relative":
            yaw -= float(source_yaw[0])
        yaw_matrix = Rotation.from_euler("z", yaw).as_matrix()
        tilt_scale = (1.0 if args.root_orientation_mode == "full"
                      else float(args.root_tilt_scale))
        if not 0.0 <= tilt_scale <= 1.0:
            raise RuntimeError("root_tilt_scale must be in [0, 1]")
        if tilt_scale > 0.0:
            pelvis_delta = Rotation.from_matrix(
                yaw_matrix.T @ desired_bases["pelvis"]
            ).as_rotvec()
            root_matrix = (
                yaw_matrix
                @ Rotation.from_rotvec(pelvis_delta * tilt_scale).as_matrix()
            )
            root_xyzw = Rotation.from_matrix(root_matrix).as_quat()
            root_quaternion = np.asarray(
                (root_xyzw[3], root_xyzw[0], root_xyzw[1], root_xyzw[2]),
                dtype=np.float64,
            )
        else:
            root_quaternion = np.asarray(
                (math.cos(yaw * 0.5), 0.0, 0.0, math.sin(yaw * 0.5)),
                dtype=np.float64,
            )

        def apply(value: np.ndarray) -> None:
            data.qpos[:] = default_qpos
            data.qpos[:3] = pelvis_position
            data.qpos[3:7] = root_quaternion
            set_tangent_qpos(value)
            mujoco.mj_forward(model, data)

        def residual(value: np.ndarray) -> np.ndarray:
            apply(value)
            rows = []
            actual = {
                source_name: target_position(object_type, object_id)
                for source_name, object_type, object_id, _ in target_ids
            }
            actual["pelvis"] = data.xpos[model.body("pelvis").id]
            for source_name, object_type, object_id, weight in target_ids:
                if args.objective_mode == "absolute":
                    error = actual[source_name] - desired[source_name]
                else:
                    parent = PARENTS[source_name]
                    error = (
                        (actual[source_name] - actual[parent])
                        - (desired[source_name] - desired[parent])
                    )
                rows.extend(weight * error / target_height)
                anchor_weight = ABSOLUTE_ANCHOR_WEIGHTS.get(source_name, 0.0)
                if args.objective_mode == "segment" and anchor_weight > 0.0:
                    rows.extend(
                        anchor_weight
                        * (actual[source_name] - desired[source_name])
                        / target_height
                    )
            if args.thorax_orientation_weight > 0.0:
                thorax_rotation = data.xmat[
                    model.body("thorax").id
                ].reshape(3, 3)
                thorax_error = Rotation.from_matrix(
                    desired_bases["thorax"].T @ thorax_rotation
                ).as_rotvec()
                rows.extend(args.thorax_orientation_weight * thorax_error)
            if args.contact_weight > 0.0:
                for side in ("l", "r"):
                    anchor = contact_anchors[side]
                    if anchor is None:
                        continue
                    rows.extend(args.contact_weight * contact_blend[side] * (
                        actual[f"ankle_{side}"] - anchor["ankle"]
                    ) / target_height)
                    rows.extend(args.contact_weight * contact_blend[side] * (
                        actual[f"toe_{side}"] - anchor["toe"]
                    ) / target_height)
                    if args.contact_ground_weight > 0.0:
                        sole_bottom = min(
                            geom_bottom(f"heel_{side}"),
                            geom_bottom(f"forefoot_{side}"),
                            geom_bottom(f"toe_{side}_collision"),
                        )
                        rows.append(
                            args.contact_ground_weight
                            * contact_blend[side]
                            * (sole_bottom - ground_z)
                            / target_height
                        )
                    if args.contact_orientation_weight > 0.0:
                        rows.extend(
                            args.contact_orientation_weight
                            * contact_blend[side]
                            * np.asarray((
                                value[joint_vector_index[
                                    f"ankle_{side}_roll"
                                ]],
                                value[joint_vector_index[
                                    f"ankle_{side}_pitch"
                                ]],
                                value[joint_vector_index[
                                    f"toe_{side}_pitch"
                                ]],
                            ), dtype=np.float64)
                        )
            if args.ground_penetration_weight > 0.0:
                for side in ("l", "r"):
                    sole_bottom = min(
                        geom_bottom(f"heel_{side}"),
                        geom_bottom(f"forefoot_{side}"),
                        geom_bottom(f"toe_{side}_collision"),
                    )
                    penetration = min(0.0, sole_bottom - ground_z)
                    rows.append(
                        args.ground_penetration_weight
                        * penetration / target_height
                    )
            if frame_index > 0:
                rows.extend(args.temporal_weight * (value - previous))
            if args.flex_weight > 0.0:
                for side in ("l", "r"):
                    rows.append(args.flex_weight * (
                        value[joint_vector_index[f"elbow_{side}"]]
                        - source_flex(frame_index, f"shoulder_{side}",
                                      f"elbow_{side}", f"wrist_{side}")
                    ))
                    rows.append(args.flex_weight * (
                        value[joint_vector_index[f"knee_{side}"]]
                        - source_flex(frame_index, f"hip_{side}",
                                      f"knee_{side}", f"ankle_{side}")
                    ))
            if frame_index > 1:
                rows.extend(args.acceleration_weight * (
                    value - 2.0 * previous + before_previous
                ))
            if args.limit_barrier_weight > 0.0:
                barrier = np.zeros_like(value)
                for joint_index in range(len(value)):
                    if lower[joint_index] >= -1.0e-8:
                        upper_start = upper[joint_index] * 0.88
                        if value[joint_index] > upper_start:
                            barrier[joint_index] = (
                                (value[joint_index] - upper_start)
                                / max(upper[joint_index] - upper_start,
                                      1.0e-8)
                            )
                    else:
                        center = 0.5 * (lower[joint_index]
                                        + upper[joint_index])
                        half = 0.5 * (upper[joint_index]
                                      - lower[joint_index])
                        normalized_value = (
                            (value[joint_index] - center) / max(half, 1.0e-8)
                        )
                        if abs(normalized_value) > 0.88:
                            barrier[joint_index] = math.copysign(
                                (abs(normalized_value) - 0.88) / 0.12,
                                normalized_value,
                            )
                rows.extend(args.limit_barrier_weight * barrier)
            rows.extend(args.neutral_weight * value)
            return np.asarray(rows, dtype=np.float64)

        seeds = [previous]
        if frame_index == 0 and args.initial_multistart > 1:
            rng = np.random.default_rng(20260827)
            for _ in range(args.initial_multistart - 1):
                seed = previous + rng.normal(0.0, 0.42, len(previous))
                for side in ("l", "r"):
                    seed[joint_vector_index[f"elbow_{side}"]] = (
                        source_flex(
                            0, f"shoulder_{side}", f"elbow_{side}",
                            f"wrist_{side}"
                        ) + rng.normal(0.0, 0.18)
                    )
                    seed[joint_vector_index[f"knee_{side}"]] = (
                        source_flex(
                            0, f"hip_{side}", f"knee_{side}",
                            f"ankle_{side}"
                        ) + rng.normal(0.0, 0.18)
                    )
                seeds.append(np.clip(
                    seed, lower + 1.0e-6, upper - 1.0e-6
                ))
        candidates = [
            least_squares(
                residual, seed, bounds=(lower, upper),
                max_nfev=args.max_nfev, method="trf",
                ftol=2.0e-6, xtol=2.0e-6, gtol=2.0e-6,
            )
            for seed in seeds
        ]
        result = min(candidates, key=lambda candidate: candidate.cost)
        solved = result.x
        apply(solved)
        frame_errors = []
        for source_name, object_type, object_id, weight in target_ids:
            amount = float(np.linalg.norm(
                target_position(object_type, object_id)
                - desired[source_name]
            ) / target_height)
            frame_errors.append(amount)
            errors.append({
                "frame": float(source_frames[frame_index]),
                "landmark": source_name,
                "error_H": amount,
            })
        qpos_rows.append(data.qpos.copy())
        tangent_rows.append(solved.copy())
        contact_blend_rows.append(
            [contact_blend["l"], contact_blend["r"]]
        )
        desired_rows.append(np.stack([
            desired[source_name] for source_name, _, _, _ in target_ids
        ]))
        actual_rows.append(np.stack([
            target_position(object_type, object_id).copy()
            for _, object_type, object_id, _ in target_ids
        ]))
        frame_reports.append({
            "frame": float(source_frames[frame_index]),
            "cost": float(result.cost),
            "nfev": int(result.nfev),
            "mean_error_H": float(np.mean(frame_errors)),
            "maximum_error_H": float(np.max(frame_errors)),
            "optimality": float(result.optimality),
        })
        before_previous = previous.copy()
        previous = solved.copy()
        if frame_index % 10 == 0 or frame_index == len(source_frames) - 1:
            print(
                f"frame {frame_index + 1}/{len(source_frames)} "
                f"mean={np.mean(frame_errors):.5f}H "
                f"max={np.max(frame_errors):.5f}H nfev={result.nfev}"
            )

    qpos = np.asarray(qpos_rows, dtype=np.float64)
    timestep = 1.0 / fps
    qvel = np.zeros((len(qpos), model.nv), dtype=np.float64)
    for index in range(1, len(qpos)):
        mujoco.mj_differentiatePos(
            model, qvel[index], timestep, qpos[index - 1], qpos[index]
        )
    if len(qpos) > 1:
        qvel[0] = qvel[1]

    per_landmark = {}
    for source_name, _, _, _ in target_ids:
        values = [row["error_H"] for row in errors
                  if row["landmark"] == source_name]
        per_landmark[source_name] = {
            "mean_H": float(np.mean(values)),
            "p95_H": float(np.percentile(values, 95.0)),
            "maximum_H": float(np.max(values)),
        }
    all_errors = np.asarray([row["error_H"] for row in errors])
    tangent = np.asarray(tangent_rows, dtype=np.float64)
    minimum_margin = float(np.min(np.minimum(
        tangent - lower,
        upper - tangent,
    )))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        qpos=qpos,
        qvel=qvel,
        timestep=np.asarray([timestep], dtype=np.float64),
        source_frames=source_frames,
        foot_contact=contacts,
        contact_blend=np.asarray(contact_blend_rows, dtype=np.float64),
        tangent=tangent,
        tangent_names=np.asarray(tangent_names),
        target_landmark_names=np.asarray([
            source_name for source_name, _, _, _ in target_ids
        ]),
        desired_positions=np.asarray(desired_rows, dtype=np.float64),
        actual_positions=np.asarray(actual_rows, dtype=np.float64),
    )
    metrics = {
        "schema": 1,
        "model": str(args.model.resolve()),
        "landmarks": str(args.landmarks.resolve()),
        "frames": [float(source_frames[0]), float(source_frames[-1])],
        "fps": fps,
        "target_skeleton_height_units": target_height,
        "mean_marker_error_H": float(np.mean(all_errors)),
        "p95_marker_error_H": float(np.percentile(all_errors, 95.0)),
        "maximum_marker_error_H": float(np.max(all_errors)),
        "minimum_joint_limit_margin_radians": minimum_margin,
        "shoulder_offset_mode": args.shoulder_offset_mode,
        "thorax_orientation_weight": args.thorax_orientation_weight,
        "objective_mode": args.objective_mode,
        "root_orientation_mode": args.root_orientation_mode,
        "root_tilt_scale": (
            1.0 if args.root_orientation_mode == "full"
            else args.root_tilt_scale
        ),
        "root_position_mode": args.root_position_mode,
        "root_yaw_mode": args.root_yaw_mode,
        "root_ground_offset_m": root_ground_offset,
        "target_construction": args.target_construction,
        "reference_landmarks": (
            None if args.reference_landmarks is None
            else str(args.reference_landmarks.resolve())
        ),
        "initial_tangent_state": (
            None if args.initial_tangent_state is None
            else str(args.initial_tangent_state.resolve())
        ),
        "flex_weight": args.flex_weight,
        "limit_barrier_weight": args.limit_barrier_weight,
        "contact_weight": args.contact_weight,
        "contact_ground_weight": args.contact_ground_weight,
        "contact_orientation_weight": args.contact_orientation_weight,
        "ground_penetration_weight": args.ground_penetration_weight,
        "force_contact": args.force_contact,
        "contact_blend_frames": args.contact_blend_frames,
        "initial_multistart": args.initial_multistart,
        "per_landmark": per_landmark,
        "frame_reports": frame_reports,
        "root_runtime_authority": (
            "offline reference trajectory only; not a runtime root write"
        ),
        "status": "kinematic_IK_candidate_not_physical_tracking",
    }
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "mean_H": metrics["mean_marker_error_H"],
        "p95_H": metrics["p95_marker_error_H"],
        "max_H": metrics["maximum_marker_error_H"],
        "min_limit_margin": minimum_margin,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
