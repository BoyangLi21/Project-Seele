#!/usr/bin/env python3
"""Export screened real-human motion databases into Gecko animation layers."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


UPPER = {
    "torso_upper", "neck", "head", "clavicle_l", "arm_l",
    "forearm_l", "wrist_l", "hand_l", "clavicle_r", "arm_r",
    "forearm_r", "wrist_r", "hand_r",
}
FULL = UPPER | {
    "root", "torso_lower", "leg_l", "shin_l", "ankle_l", "foot_l",
    "leg_r", "shin_r", "ankle_r", "foot_r",
}
POUNCE = FULL - {"foot_l", "foot_r"}
KNIFE_UPPER = UPPER | {"knife"}
KNIFE_FULL = FULL | {"knife"}
LANCE_UPPER = UPPER | {"lance"}
LANCE_FULL = FULL | {"lance"}


@dataclass(frozen=True)
class Export:
    source: str
    clip: str
    target: str
    bones: frozenset[str]
    loop: bool = False
    static: bool = False
    reverse: bool = False


EXPORTS = (
    Export("knife_light", "knife_light", "knife_ready",
           frozenset(KNIFE_UPPER),
           loop=True, static=True),
    Export("knife_light", "knife_light", "knife", frozenset(KNIFE_FULL)),
    Export("knife_light", "knife_light", "crouch_knife",
           frozenset(KNIFE_UPPER)),
    Export("knife_heavy", "knife_heavy", "knife_heavy",
           frozenset(KNIFE_FULL)),
    Export("knife_heavy", "knife_heavy", "crouch_knife_heavy",
           frozenset(KNIFE_UPPER)),
    Export("lance_thrust", "lance_thrust", "lance_ready",
           frozenset(LANCE_UPPER), loop=True, static=True),
    Export("lance_thrust", "lance_thrust", "lance_carry",
           frozenset(LANCE_UPPER), loop=True, static=True),
    Export("lance_thrust_v03", "lance_thrust", "lance_thrust",
           frozenset(LANCE_FULL)),
    Export("lance_thrust_v03", "lance_thrust", "crouch_lance_thrust",
           frozenset(LANCE_UPPER)),
    Export("crouch_idle_v03", "crouch_idle", "crouch", frozenset(FULL),
           loop=True),
    Export("stand_to_crouch", "stand_to_crouch", "stand_to_crouch",
           frozenset(FULL)),
    Export("stand_to_crouch", "stand_to_crouch", "crouch_to_stand",
           frozenset(FULL), reverse=True),
    Export("crouch_walk_v03", "crouch_walk", "crouch_walk",
           frozenset(FULL), loop=True),
    Export("utd_prone_idle", "prone_idle", "prone",
           frozenset(FULL), loop=True),
    Export("utd_crawl", "crawl", "crawl", frozenset(FULL), loop=True),
    Export("utd_crouch_to_prone", "crouch_to_prone",
           "crouch_to_prone", frozenset(FULL)),
    Export("utd_prone_to_crouch", "prone_to_crouch",
           "prone_to_crouch", frozenset(FULL)),
    Export("utd_stand_to_prone", "stand_to_prone", "stand_to_prone",
           frozenset(FULL)),
    Export("utd_prone_to_stand", "prone_to_stand", "prone_to_stand",
           frozenset(FULL)),
)


def key(seconds: float) -> str:
    return f"{seconds:.5f}".rstrip("0").rstrip(".") or "0"


def clean(value: float) -> float:
    result = round(float(value), 5)
    return 0.0 if abs(result) < 0.000005 else result


def continuous_euler_xyz(rotations: Rotation) -> np.ndarray:
    """Choose the nearest equivalent XYZ Euler branch frame by frame."""
    raw = rotations.as_euler("xyz", degrees=False)
    if len(raw) <= 1:
        return raw
    result = [raw[0]]
    two_pi = math.tau
    for row in raw[1:]:
        branches = (
            row,
            np.asarray((row[0] + math.pi,
                        math.pi - row[1],
                        row[2] + math.pi), dtype=np.float64),
            np.asarray((row[0] - math.pi,
                        math.pi - row[1],
                        row[2] - math.pi), dtype=np.float64),
        )
        previous = result[-1]
        candidates = []
        for branch in branches:
            adjusted = branch + two_pi * np.round(
                (previous - branch) / two_pi)
            candidates.append(adjusted)
        result.append(min(
            candidates,
            key=lambda candidate: float(np.linalg.norm(
                candidate - previous)),
        ))
    return np.asarray(result, dtype=np.float64)


def animation(document: dict, clip_name: str, selected: frozenset[str],
              loop: bool, static: bool, reverse: bool) -> dict:
    clip = document["clips"][clip_name]
    frames = clip["frames"]
    fps = float(document.get("sample_rate", 60.0))
    selected = frozenset(selected) | frozenset(
        name for name in document["bones"] if name.startswith("finger_"))
    indices = [0] if static else list(range(0, len(frames), 2))
    if indices[-1] != len(frames) - 1:
        indices.append(len(frames) - 1)
    if reverse:
        indices.reverse()
    sample_times = [0.0]
    for before, after in zip(indices, indices[1:]):
        sample_times.append(sample_times[-1] + abs(after - before) / fps)
    bones = {}
    for bone_index, bone_name in enumerate(document["bones"]):
        if bone_name not in selected:
            continue
        quaternion = np.asarray([
            frames[index]["rotation_wxyz"][bone_index]
            for index in indices
        ], dtype=np.float64)
        rotations = Rotation.from_quat(quaternion[:, [1, 2, 3, 0]])
        if loop and not static and len(rotations) > 1:
            closure = rotations[-1].inv() * rotations[0]
            correction = closure.as_rotvec()
            rotations = rotations * Rotation.from_rotvec(np.asarray([
                correction * (index / (len(rotations) - 1))
                for index in range(len(rotations))
            ]))
        euler = continuous_euler_xyz(rotations)
        degrees = np.degrees(euler)
        if static:
            values = [clean(value) for value in degrees[0]]
            rotation = {"0.0": values, "1.2": values}
        else:
            rotation = {
                key(seconds): [clean(value) for value in row]
                for seconds, row in zip(sample_times, degrees)
            }
        bones[bone_name] = {"rotation": rotation}
        if bone_name == "root":
            positions = np.asarray([
                frames[index]["root_m"] for index in indices
            ], dtype=np.float64)
            if loop and not static and len(positions) > 1:
                drift = positions[-1] - positions[0]
                positions -= np.asarray([
                    drift * (index / (len(positions) - 1))
                    for index in range(len(positions))
                ])
            authored_positions = positions * 112.0
            if static:
                values = [clean(value) for value in authored_positions[0]]
                position = {"0.0": values, "1.2": values}
            else:
                position = {
                    key(seconds): [clean(value) for value in row]
                    for seconds, row in zip(sample_times,
                                            authored_positions)
                }
            bones[bone_name]["position"] = position
        elif bone_name in {"knife", "cannon", "lance"}:
            attachment_positions = [
                frames[index].get("bone_position_xyz", {}).get(bone_name)
                for index in indices
            ]
            if all(value is not None for value in attachment_positions):
                if static:
                    values = [clean(value)
                              for value in attachment_positions[0]]
                    position = {"0.0": values, "1.2": values}
                else:
                    position = {
                        key(seconds): [clean(value) for value in row]
                        for seconds, row in zip(
                            sample_times, attachment_positions)
                    }
                bones[bone_name]["position"] = position
    duration = 1.2 if static else sample_times[-1]
    output = {
        "animation_length": clean(duration),
        "bones": bones,
    }
    if loop:
        output["loop"] = True
    return output


def solved_weapon_overlay(base_document: dict, solved: dict,
                          clip_name: str = "prone_rifle_review") -> dict:
    """Preserve the reviewed grip while installing exact-mesh IK channels."""
    source = base_document["animations"][
        "animation.eva_unit01.prone_rifle_aim"]
    output = copy.deepcopy(source)
    frames = solved["clips"][clip_name]["frames"]
    fps = float(solved.get("sample_rate", 30.0))
    bone_indices = {name: index for index, name in enumerate(solved["bones"])}
    times = [index / fps for index in range(len(frames))]
    for bone_name in ("arm_l", "forearm_l", "cannon"):
        quaternion = np.asarray([
            frame["rotation_wxyz"][bone_indices[bone_name]]
            for frame in frames
        ], dtype=np.float64)
        rotations = Rotation.from_quat(quaternion[:, [1, 2, 3, 0]])
        degrees = np.degrees(continuous_euler_xyz(rotations))
        output.setdefault("bones", {}).setdefault(bone_name, {})[
            "rotation"] = {
                key(seconds): [clean(value) for value in row]
                for seconds, row in zip(times, degrees)
            }
    output["bones"]["cannon"]["position"] = {
        key(seconds): [clean(value) for value in
                       frame["bone_position_xyz"]["cannon"]]
        for seconds, frame in zip(times, frames)
    }
    output["animation_length"] = clean(times[-1])
    output["loop"] = True
    return output


def install_solved_channels(animation: dict, solved: dict, clip_name: str,
                            bone_names: tuple[str, ...],
                            static: bool = False) -> dict:
    """Replace selected Gecko channels from a final composed exact scene."""
    output = copy.deepcopy(animation)
    frames = solved["clips"][clip_name]["frames"]
    fps = float(solved.get("sample_rate", 30.0))
    bone_indices = {name: index for index, name in enumerate(solved["bones"])}
    indices = [0] if static else list(range(len(frames)))
    duration = 1.2 if static else (len(frames) - 1) / fps
    times = [0.0] if static else [index / fps for index in indices]
    for bone_name in bone_names:
        quaternion = np.asarray([
            frames[index]["rotation_wxyz"][bone_indices[bone_name]]
            for index in indices
        ], dtype=np.float64)
        rotations = Rotation.from_quat(quaternion[:, [1, 2, 3, 0]])
        degrees = np.degrees(continuous_euler_xyz(rotations))
        if static:
            value = [clean(component) for component in degrees[0]]
            rotation = {"0": list(value), "1.2": list(value)}
        else:
            rotation = {
                key(seconds): [clean(component) for component in row]
                for seconds, row in zip(times, degrees)
            }
        output.setdefault("bones", {}).setdefault(bone_name, {})[
            "rotation"] = rotation
        positions = [
            frames[index].get("bone_position_xyz", {}).get(bone_name)
            for index in indices
        ]
        if all(value is not None for value in positions):
            if static:
                value = [clean(component) for component in positions[0]]
                position = {"0": list(value), "1.2": list(value)}
            else:
                position = {
                    key(seconds): [clean(component) for component in row]
                    for seconds, row in zip(times, positions)
                }
            output["bones"][bone_name]["position"] = position
    output["animation_length"] = clean(duration)
    return output


def first_channel_value(channel) -> list[float]:
    if isinstance(channel, list):
        return [clean(value) for value in channel]
    first = min(channel, key=float)
    return [clean(value) for value in channel[first]]


def static_rotation(value: list[float], duration: float) -> dict:
    cleaned = [clean(component) for component in value]
    return {"0": list(cleaned), key(duration): list(cleaned)}


def repair_low_stance_semantics(replacements: dict,
                                _base_document: dict) -> dict:
    """Keep captured weight transfer but replace rejected arm/hand semantics."""
    arm_bones = (
        "clavicle_l", "arm_l", "forearm_l", "wrist_l", "hand_l",
        "clavicle_r", "arm_r", "forearm_r", "wrist_r", "hand_r",
    )
    guard_pose = {
        "clavicle_l": [0.0, 0.0, 0.0],
        "arm_l": [18.85362, -2.12002, -2.22401],
        "forearm_l": [22.47230, -1.73582, 5.75859],
        "wrist_l": [0.0, 0.0, 0.0],
        "hand_l": [0.0, 0.0, 0.0],
        "clavicle_r": [0.0, 0.0, 0.0],
        "arm_r": [1.64755, 2.19587, -33.32164],
        "forearm_r": [22.74297, 8.48156, -39.89046],
        "wrist_r": [0.0, 0.0, 0.0],
        "hand_r": [0.0, 0.0, 0.0],
    }

    crouch_targets = (
        "animation.eva_unit01.crouch",
        "animation.eva_unit01.crouch_walk",
        "animation.eva_unit01.stand_to_crouch",
        "animation.eva_unit01.crouch_to_stand",
    )
    for animation_name in crouch_targets:
        animation = replacements[animation_name]
        duration = float(animation["animation_length"])
        bones = animation.setdefault("bones", {})
        for bone_name, value in guard_pose.items():
            bones.setdefault(bone_name, {})["rotation"] = static_rotation(
                value, duration)

    return {
        "crouch_upper_body": "target_ik_forward_low_guard",
        "low_stance_fingers": "runtime_compact_curl_in_make_tiger_unit01_pack",
        "arm_bones": list(arm_bones),
        "finger_bones": [],
    }


def match_edge(animation: dict, target: dict, edge: str,
               fade_seconds: float = 0.35) -> None:
    """Close a captured transition onto the adjacent runtime stance."""
    for bone_name in animation["bones"].keys() & target["bones"].keys():
        channel = animation["bones"][bone_name].get("rotation")
        target_channel = target["bones"][bone_name].get("rotation")
        if not isinstance(channel, dict) or not isinstance(target_channel, dict):
            continue
        keys = sorted(channel, key=float)
        target_keys = sorted(target_channel, key=float)
        edge_index = 0 if edge == "start" else -1
        rotations = Rotation.from_euler(
            "xyz", [channel[item] for item in keys], degrees=True)
        desired = Rotation.from_euler(
            "xyz", target_channel[target_keys[edge_index]], degrees=True)
        correction = (rotations[edge_index].inv() * desired).as_rotvec()
        first_time = float(keys[0])
        last_time = float(keys[-1])
        corrected = []
        for item, rotation in zip(keys, rotations):
            seconds = float(item)
            if edge == "start":
                weight = max(0.0, 1.0 - (seconds - first_time)
                             / fade_seconds)
            else:
                weight = max(0.0, 1.0 - (last_time - seconds)
                             / fade_seconds)
            corrected.append(
                rotation * Rotation.from_rotvec(correction * weight))
        euler = continuous_euler_xyz(Rotation.concatenate(corrected))
        channel.clear()
        channel.update({
            item: [clean(value) for value in row]
            for item, row in zip(keys, np.degrees(euler))
        })
        position = animation["bones"][bone_name].get("position")
        target_position = target["bones"][bone_name].get("position")
        if not isinstance(position, dict) or not isinstance(target_position, dict):
            continue
        position_keys = sorted(position, key=float)
        target_position_keys = sorted(target_position, key=float)
        current_edge = np.asarray(
            position[position_keys[edge_index]], dtype=np.float64)
        desired_position = np.asarray(
            target_position[target_position_keys[edge_index]], dtype=np.float64)
        correction_position = desired_position - current_edge
        first_position_time = float(position_keys[0])
        last_position_time = float(position_keys[-1])
        for item in position_keys:
            seconds = float(item)
            if edge == "start":
                weight = max(0.0, 1.0 - (seconds - first_position_time)
                             / fade_seconds)
            else:
                weight = max(0.0, 1.0 - (last_position_time - seconds)
                             / fade_seconds)
            value = np.asarray(position[item], dtype=np.float64)
            position[item] = [
                clean(component)
                for component in value + correction_position * weight
            ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-animation", type=Path)
    parser.add_argument("--prone-rifle-solved-db", type=Path)
    parser.add_argument("--lance-runtime-solved-db", type=Path)
    parser.add_argument("--crouch-runtime-solved-db", type=Path)
    args = parser.parse_args()
    if bool(args.base_animation) != bool(args.prone_rifle_solved_db):
        parser.error(
            "--base-animation and --prone-rifle-solved-db are required together")
    documents = {}
    sources = {}
    replacements = {}
    for item in EXPORTS:
        if item.source not in documents:
            path = args.input_dir / f"{item.source}.json"
            documents[item.source] = json.loads(path.read_text(
                encoding="utf-8"))
            sources[item.source] = {
                "path": str(path.resolve()),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        replacements[f"animation.eva_unit01.{item.target}"] = animation(
            documents[item.source], item.clip, item.bones,
            item.loop, item.static, item.reverse)
    base_animation = (None if args.base_animation is None else json.loads(
        args.base_animation.read_text(encoding="utf-8")))
    low_stance_repair = (None if base_animation is None else
                         repair_low_stance_semantics(
                             replacements, base_animation))
    if args.crouch_runtime_solved_db:
        solved_crouch = json.loads(
            args.crouch_runtime_solved_db.read_text(encoding="utf-8"))
        leg_bones = ("leg_l", "shin_l", "leg_r", "shin_r")
        for animation_suffix, clip_name in (
                ("crouch", "crouch_review"),
                ("crouch_walk", "crouch_walk_review")):
            animation_name = f"animation.eva_unit01.{animation_suffix}"
            replacements[animation_name] = install_solved_channels(
                replacements[animation_name], solved_crouch,
                clip_name, leg_bones)
        sources["crouch_runtime_exact_solve"] = {
            "path": str(args.crouch_runtime_solved_db.resolve()),
            "sha256": hashlib.sha256(
                args.crouch_runtime_solved_db.read_bytes()).hexdigest(),
        }
    crouch = replacements["animation.eva_unit01.crouch"]
    prone = replacements["animation.eva_unit01.prone"]
    match_edge(replacements["animation.eva_unit01.stand_to_crouch"],
               crouch, "end")
    match_edge(replacements["animation.eva_unit01.crouch_to_stand"],
               crouch, "start")
    match_edge(replacements["animation.eva_unit01.crouch_to_prone"],
               crouch, "start", fade_seconds=0.80)
    match_edge(replacements["animation.eva_unit01.crouch_to_prone"],
               prone, "end", fade_seconds=0.35)
    match_edge(replacements["animation.eva_unit01.prone_to_crouch"],
               prone, "start", fade_seconds=0.35)
    match_edge(replacements["animation.eva_unit01.prone_to_crouch"],
               crouch, "end", fade_seconds=0.80)
    match_edge(replacements["animation.eva_unit01.stand_to_prone"],
               prone, "end", fade_seconds=0.35)
    match_edge(replacements["animation.eva_unit01.prone_to_stand"],
               prone, "start", fade_seconds=0.35)
    if base_animation is not None:
        idle = base_animation["animations"]["animation.eva_unit01.idle"]
        match_edge(replacements["animation.eva_unit01.stand_to_prone"],
                   idle, "start", fade_seconds=0.60)
        match_edge(replacements["animation.eva_unit01.prone_to_stand"],
                   idle, "end", fade_seconds=0.60)
    if args.prone_rifle_solved_db:
        solved = json.loads(args.prone_rifle_solved_db.read_text(
            encoding="utf-8"))
        replacements["animation.eva_unit01.prone_rifle_aim"] = \
            solved_weapon_overlay(base_animation, solved)
        sources["prone_rifle_exact_solve"] = {
            "path": str(args.prone_rifle_solved_db.resolve()),
            "sha256": hashlib.sha256(
                args.prone_rifle_solved_db.read_bytes()).hexdigest(),
        }
    if args.lance_runtime_solved_db:
        solved_lance = json.loads(args.lance_runtime_solved_db.read_text(
            encoding="utf-8"))
        lance_bones = (
            "clavicle_l", "arm_l", "forearm_l", "wrist_l", "hand_l",
            "clavicle_r", "arm_r", "forearm_r", "wrist_r", "hand_r",
            "lance",
        )
        ready_name = "animation.eva_unit01.lance_ready"
        replacements[ready_name] = install_solved_channels(
            replacements[ready_name], solved_lance,
            "lance_ready_review", lance_bones, static=True)
        replacements["animation.eva_unit01.lance_carry"] = copy.deepcopy(
            replacements[ready_name])
        thrust_name = "animation.eva_unit01.lance_thrust"
        solved_thrust = install_solved_channels(
            replacements[thrust_name], solved_lance,
            "lance_thrust_review", lance_bones)
        replacements[thrust_name] = solved_thrust
        crouch_thrust = replacements[
            "animation.eva_unit01.crouch_lance_thrust"]
        for bone_name in lance_bones:
            if bone_name in solved_thrust.get("bones", {}):
                crouch_thrust.setdefault("bones", {})[bone_name] = \
                    copy.deepcopy(solved_thrust["bones"][bone_name])
        sources["lance_runtime_exact_solve"] = {
            "path": str(args.lance_runtime_solved_db.resolve()),
            "sha256": hashlib.sha256(
                args.lance_runtime_solved_db.read_bytes()).hexdigest(),
        }
    payload = {
        "schema": 1,
        "authority": "real_human_mocap_body_plus_target_weapon_constraints",
        "loop_closure": "distributed_local_geodesic_drift",
        "transition_edge_blend_seconds": 0.35,
        "sample_rate_hz": 30,
        "sources": sources,
        "replace_animations": replacements,
    }
    if low_stance_repair is not None:
        payload["low_stance_semantic_repair"] = low_stance_repair
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"EVA real mocap patch: animations={len(replacements)} "
        f"sources={len(sources)} output={args.output}"
    )


if __name__ == "__main__":
    main()
