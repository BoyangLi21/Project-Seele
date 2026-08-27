#!/usr/bin/env python3
"""Jointly optimize an EVA trajectory's legs and root height over time."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

from audit_eva_physical_retarget import geom_bottom


LEG_NAMES = [
    "hip_l_abduct", "hip_l_flex", "hip_l_twist", "knee_l",
    "ankle_l_roll", "ankle_l_pitch", "toe_l_pitch",
    "hip_r_abduct", "hip_r_flex", "hip_r_twist", "knee_r",
    "ankle_r_roll", "ankle_r_pitch", "toe_r_pitch",
]

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


def runs(values: np.ndarray):
    result = []
    start = None
    for index, value in enumerate(values):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(values) - 1):
            end = index if value and index == len(values) - 1 else index - 1
            if end - start + 1 >= 3:
                result.append((start, end))
            start = None
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--max-nfev", type=int, default=24)
    parser.add_argument("--pose-weight", type=float, default=0.55)
    parser.add_argument("--leg-marker-weight", type=float, default=1.5)
    parser.add_argument("--contact-xy-weight", type=float, default=16.0)
    parser.add_argument("--contact-patch-weight", type=float, default=12.0)
    parser.add_argument("--contact-patch-velocity-weight", type=float,
                        default=0.0)
    parser.add_argument("--contact-ground-weight", type=float, default=28.0)
    parser.add_argument("--contact-depth-m", type=float, default=0.0)
    parser.add_argument("--contact-tangent-velocity-weight", type=float,
                        default=0.0)
    parser.add_argument("--penetration-weight", type=float, default=70.0)
    parser.add_argument("--allowed-penetration-m", type=float, default=0.0)
    parser.add_argument("--delta-velocity-weight", type=float, default=2.2)
    parser.add_argument("--delta-acceleration-weight", type=float, default=3.8)
    parser.add_argument("--absolute-velocity-weight", type=float, default=0.0)
    parser.add_argument("--absolute-acceleration-weight", type=float, default=0.0)
    parser.add_argument("--root-weight", type=float, default=0.8)
    parser.add_argument("--force-contact", choices=("none", "left", "right", "both"),
                        default="none")
    parser.add_argument("--diff-step", type=float, default=1.0e-5)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    source = np.load(args.state)
    qpos_source = np.asarray(source["qpos"], dtype=np.float64)
    tangent_source = np.asarray(source["tangent"], dtype=np.float64)
    tangent_names = [str(value) for value in source["tangent_names"]]
    contract_names, lower, upper = tangent_metadata(args.model)
    if tangent_names != contract_names:
        raise RuntimeError("state tangent order does not match model")
    leg_indices = [tangent_names.index(name) for name in LEG_NAMES]
    contacts = np.asarray(source["foot_contact"], dtype=np.bool_)
    blend = (
        np.asarray(source["contact_blend"], dtype=np.float64)
        if "contact_blend" in source.files
        else np.ones_like(contacts, dtype=np.float64)
    )
    if args.force_contact in {"left", "both"}:
        contacts[:, 0] = True
        blend[:, 0] = 1.0
    if args.force_contact in {"right", "both"}:
        contacts[:, 1] = True
        blend[:, 1] = 1.0
    stable = contacts & (blend >= 0.999)
    names = [str(value) for value in source["target_landmark_names"]]
    desired_source = np.asarray(source["desired_positions"], dtype=np.float64)
    frame_count = len(qpos_source)
    root_width = 3
    variable_width = len(leg_indices) + root_width
    height = 3.466729315

    joint_groups = {}
    for tangent_index, name in enumerate(tangent_names):
        actuator_id = model.actuator(f"a_{name}").id
        joint_id = int(model.actuator_trnid[actuator_id, 0])
        joint_groups.setdefault(joint_id, []).append({
            "index": tangent_index,
            "axis": np.asarray(model.actuator_gear[actuator_id, :3],
                               dtype=np.float64).copy(),
        })

    def set_tangent(value: np.ndarray) -> None:
        for joint_id, specs in joint_groups.items():
            address = int(model.jnt_qposadr[joint_id])
            joint_type = int(model.jnt_type[joint_id])
            if joint_type == mujoco.mjtJoint.mjJNT_BALL:
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

    object_ids = []
    for name in names:
        object_type, object_name = TARGET_OBJECTS[name]
        object_id = mujoco.mj_name2id(
            model,
            (mujoco.mjtObj.mjOBJ_BODY if object_type == "body"
             else mujoco.mjtObj.mjOBJ_GEOM),
            object_name,
        )
        object_ids.append((object_type, object_id))

    def apply(frame: int, leg_value: np.ndarray, root_delta: np.ndarray):
        full = tangent_source[frame].copy()
        full[leg_indices] = leg_value
        data.qpos[:] = qpos_source[frame]
        data.qpos[:3] += root_delta
        set_tangent(full)
        mujoco.mj_forward(model, data)
        actual = np.stack([
            (data.xpos[object_id] if object_type == "body"
             else data.geom_xpos[object_id]).copy()
            for object_type, object_id in object_ids
        ])
        return full, data.qpos.copy(), actual

    # Contact anchors come from the current candidate's first stable frame in
    # each segment; the optimizer may change leg pose but not world-space grip.
    anchors = {"l": {}, "r": {}}
    for side_index, side in enumerate(("l", "r")):
        for first, last in runs(stable[:, side_index]):
            _, _, actual = apply(
                first, tangent_source[first, leg_indices],
                np.zeros(3, dtype=np.float64)
            )
            anchors[side][first] = {
                "last": last,
                "ankle": actual[names.index(f"ankle_{side}")].copy(),
                "toe": actual[names.index(f"toe_{side}")].copy(),
                "patches": {
                    patch: data.geom_xpos[model.geom(
                        f"toe_{side}_collision" if patch == "toe"
                        else f"{patch}_{side}"
                    ).id, :2].copy()
                    for patch in ("heel", "forefoot", "toe")
                },
            }

    segment_for_frame = {"l": {}, "r": {}}
    for side in ("l", "r"):
        for first, anchor in anchors[side].items():
            for frame in range(first, anchor["last"] + 1):
                segment_for_frame[side][frame] = anchor

    initial = np.zeros((frame_count, variable_width), dtype=np.float64)
    initial[:, :-root_width] = tangent_source[:, leg_indices]
    initial[:, -root_width:] = qpos_source[:, :3]
    x0 = initial.ravel()
    lower_rows = []
    upper_rows = []
    for frame in range(frame_count):
        lower_rows.append(np.concatenate((
            lower[leg_indices],
            qpos_source[frame, :3] + np.asarray((-0.25, -0.25, -0.20)),
        )))
        upper_rows.append(np.concatenate((
            upper[leg_indices],
            qpos_source[frame, :3] + np.asarray((0.25, 0.25, 0.20)),
        )))
    bounds = (
        np.asarray(lower_rows, dtype=np.float64).ravel(),
        np.asarray(upper_rows, dtype=np.float64).ravel(),
    )

    dependencies = []

    def residual(flat: np.ndarray, record: bool = False) -> np.ndarray:
        values = flat.reshape(frame_count, variable_width)
        rows = []
        patch_xy = np.zeros((frame_count, 2, 3, 2), dtype=np.float64)
        evaluated_qpos = np.zeros_like(qpos_source)

        def add(array, frames):
            flattened = np.asarray(array, dtype=np.float64).ravel()
            rows.extend(flattened)
            if record:
                dependencies.extend([tuple(frames)] * len(flattened))

        for frame in range(frame_count):
            leg_value = values[frame, :-root_width]
            root_delta = (
                values[frame, -root_width:] - qpos_source[frame, :3]
            )
            _, qpos_row, actual = apply(frame, leg_value, root_delta)
            evaluated_qpos[frame] = qpos_row
            for side_index, side in enumerate(("l", "r")):
                for patch_index, patch in enumerate(
                        ("heel", "forefoot", "toe")):
                    geom_name = (f"toe_{side}_collision"
                                 if patch == "toe"
                                 else f"{patch}_{side}")
                    patch_xy[frame, side_index, patch_index] = (
                        data.geom_xpos[model.geom(geom_name).id, :2]
                    )
            desired = desired_source[frame].copy()
            desired += root_delta[None, :]
            # A stable contact is a world-space constraint.  Hermite or
            # retarget marker trajectories may still move beneath that flag;
            # letting those markers remain authoritative asks the optimizer
            # to slide and stay planted at the same time.  The segment's
            # pre-optimization first stable pose is the independent anchor.
            for side in ("l", "r"):
                anchor = segment_for_frame[side].get(frame)
                if anchor is None:
                    continue
                desired[names.index(f"ankle_{side}")] = anchor["ankle"]
                desired[names.index(f"toe_{side}")] = anchor["toe"]
            add(args.pose_weight * (
                leg_value - tangent_source[frame, leg_indices]
            ), (frame,))
            add(args.root_weight * root_delta / height, (frame,))
            for landmark in ("knee_l", "ankle_l", "toe_l",
                             "knee_r", "ankle_r", "toe_r"):
                index = names.index(landmark)
                add(args.leg_marker_weight * (
                    actual[index] - desired[index]
                ) / height, (frame,))
            for side in ("l", "r"):
                anchor = segment_for_frame[side].get(frame)
                if anchor is not None:
                    for landmark in (f"ankle_{side}", f"toe_{side}"):
                        index = names.index(landmark)
                        add(args.contact_xy_weight * (
                            actual[index, :2] - anchor[
                                "ankle" if landmark.startswith("ankle")
                                else "toe"
                            ][:2]
                        ) / height, (frame,))
                    for patch in ("heel", "forefoot", "toe"):
                        geom_name = (f"toe_{side}_collision"
                                     if patch == "toe"
                                     else f"{patch}_{side}")
                        geom_id = model.geom(geom_name).id
                        add(args.contact_patch_weight * (
                            data.geom_xpos[geom_id, :2]
                            - anchor["patches"][patch]
                        ) / height, (frame,))
                    bottom = min(
                        geom_bottom(model, data, f"heel_{side}"),
                        geom_bottom(model, data, f"forefoot_{side}"),
                        geom_bottom(model, data, f"toe_{side}_collision"),
                    )
                    add(args.contact_ground_weight * (
                        bottom - args.contact_depth_m
                    ) / height,
                        (frame,))
                bottom = min(
                    geom_bottom(model, data, f"heel_{side}"),
                    geom_bottom(model, data, f"forefoot_{side}"),
                    geom_bottom(model, data, f"toe_{side}_collision"),
                )
                add(args.penetration_weight * min(
                    0.0, bottom + args.allowed_penetration_m
                ) / height,
                    (frame,))
            if frame > 0:
                delta = (
                    values[frame] - initial[frame]
                    - values[frame - 1] + initial[frame - 1]
                )
                add(args.delta_velocity_weight * delta, (frame - 1, frame))
                if args.absolute_velocity_weight > 0.0:
                    add(args.absolute_velocity_weight * (
                        values[frame, :-root_width]
                        - values[frame - 1, :-root_width]
                    ), (frame - 1, frame))
            if frame > 1:
                delta_acceleration = (
                    values[frame] - initial[frame]
                    - 2.0 * (values[frame - 1] - initial[frame - 1])
                    + values[frame - 2] - initial[frame - 2]
                )
                add(args.delta_acceleration_weight * delta_acceleration,
                    (frame - 2, frame - 1, frame))
                if args.absolute_acceleration_weight > 0.0:
                    add(args.absolute_acceleration_weight * (
                        values[frame, :-root_width]
                        - 2.0 * values[frame - 1, :-root_width]
                        + values[frame - 2, :-root_width]
                    ), (frame - 2, frame - 1, frame))
        if args.contact_patch_velocity_weight > 0.0:
            for frame in range(1, frame_count):
                for side_index in range(2):
                    if not (stable[frame - 1, side_index]
                            and stable[frame, side_index]):
                        continue
                    for patch_index in range(3):
                        add(args.contact_patch_velocity_weight * (
                            patch_xy[frame, side_index, patch_index]
                            - patch_xy[frame - 1, side_index, patch_index]
                        ) / height, (frame - 1, frame))
        if args.contact_tangent_velocity_weight > 0.0:
            ground_id = model.geom("ground").id
            for frame in range(frame_count):
                before = max(0, frame - 1)
                after = min(frame_count - 1, frame + 1)
                duration = max(
                    float(source["timestep"][0]),
                    (after - before) * float(source["timestep"][0]),
                )
                velocity = np.zeros(model.nv, dtype=np.float64)
                mujoco.mj_differentiatePos(
                    model, velocity, duration,
                    evaluated_qpos[before], evaluated_qpos[after],
                )
                data.qpos[:] = evaluated_qpos[frame]
                data.qvel[:] = velocity
                mujoco.mj_forward(model, data)
                dependencies_for_velocity = tuple(sorted({
                    before, frame, after,
                }))
                for side_index in range(2):
                    if not stable[frame, side_index]:
                        continue
                    side = ("l", "r")[side_index]
                    for patch in ("heel", "forefoot", "toe"):
                        target_geom = model.geom(
                            f"toe_{side}_collision" if patch == "toe"
                            else f"{patch}_{side}"
                        ).id
                        tangential_rows = []
                        for contact_index in range(data.ncon):
                            contact = data.contact[contact_index]
                            geom1 = int(contact.geom1)
                            geom2 = int(contact.geom2)
                            if geom1 != ground_id and geom2 != ground_id:
                                continue
                            foot_geom = (
                                geom2 if geom1 == ground_id else geom1
                            )
                            if foot_geom != target_geom:
                                continue
                            jacobian = np.zeros(
                                (3, model.nv), dtype=np.float64
                            )
                            mujoco.mj_jac(
                                model, data, jacobian, None,
                                np.asarray(contact.pos, dtype=np.float64),
                                int(model.geom_bodyid[foot_geom]),
                            )
                            point_velocity = jacobian @ velocity
                            normal = np.asarray(
                                contact.frame[:3], dtype=np.float64
                            )
                            tangential_rows.append(
                                point_velocity
                                - normal * np.dot(point_velocity, normal)
                            )
                        tangential = (
                            np.mean(tangential_rows, axis=0)
                            if tangential_rows
                            else np.zeros(3, dtype=np.float64)
                        )
                        add(args.contact_tangent_velocity_weight
                            * tangential / height,
                            dependencies_for_velocity)
        return np.asarray(rows, dtype=np.float64)

    residual(x0, record=True)
    sparsity = lil_matrix((len(dependencies), len(x0)), dtype=np.int8)
    for row, frame_dependencies in enumerate(dependencies):
        for frame in frame_dependencies:
            first = frame * variable_width
            sparsity[row, first:first + variable_width] = 1
    result = least_squares(
        residual, x0, bounds=bounds, jac_sparsity=sparsity.tocsr(),
        method="trf", max_nfev=args.max_nfev, verbose=1,
        diff_step=args.diff_step,
        ftol=1.0e-5, xtol=1.0e-5, gtol=1.0e-5,
    )
    solved = result.x.reshape(frame_count, variable_width)
    tangent = tangent_source.copy()
    tangent[:, leg_indices] = solved[:, :-root_width]
    qpos = []
    actual = []
    desired = desired_source.copy()
    root_delta = solved[:, -root_width:] - qpos_source[:, :3]
    desired += root_delta[:, None, :]
    for frame in range(frame_count):
        for side in ("l", "r"):
            anchor = segment_for_frame[side].get(frame)
            if anchor is None:
                continue
            desired[frame, names.index(f"ankle_{side}")] = anchor["ankle"]
            desired[frame, names.index(f"toe_{side}")] = anchor["toe"]
    for frame in range(frame_count):
        _, qpos_row, actual_row = apply(
            frame, solved[frame, :-root_width],
            root_delta[frame]
        )
        qpos.append(qpos_row)
        actual.append(actual_row)
    qpos = np.asarray(qpos, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    dt = float(source["timestep"][0])
    qvel = np.zeros((frame_count, model.nv), dtype=np.float64)
    for frame in range(1, frame_count):
        mujoco.mj_differentiatePos(
            model, qvel[frame], dt, qpos[frame - 1], qpos[frame]
        )
    if frame_count > 1:
        qvel[0] = qvel[1]
    output_fields = {key: source[key] for key in source.files}
    output_fields.update({
        "qpos": qpos, "qvel": qvel, "tangent": tangent,
        "desired_positions": desired, "actual_positions": actual,
        "window_root_delta_m": root_delta,
        "foot_contact": contacts,
        "contact_blend": blend,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **output_fields)
    report = {
        "schema": 1,
        "model": str(args.model.resolve()),
        "source_state": str(args.state.resolve()),
        "output_state": str(args.output.resolve()),
        "frames": frame_count,
        "variables": len(x0),
        "residuals": len(result.fun),
        "success": bool(result.success),
        "message": result.message,
        "nfev": int(result.nfev),
        "cost_before": float(0.5 * np.dot(residual(x0), residual(x0))),
        "cost_after": float(result.cost),
        "maximum_leg_tangent_change_rad": float(np.max(np.abs(
            tangent[:, leg_indices] - tangent_source[:, leg_indices]
        ))),
        "maximum_root_translation_change_m": float(np.max(np.linalg.norm(
            root_delta, axis=1
        ))),
        "status": "whole_window_kinematic_contact_candidate_not_physical_tracking",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
