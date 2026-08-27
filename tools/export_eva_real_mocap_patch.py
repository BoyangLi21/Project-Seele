#!/usr/bin/env python3
"""Export screened real-human motion databases into Gecko animation layers."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    "torso_lower", "leg_l", "shin_l", "ankle_l", "foot_l",
    "leg_r", "shin_r", "ankle_r", "foot_r",
}
POUNCE = FULL - {"foot_l", "foot_r"}


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
    Export("knife_strike", "knife", "knife_ready", frozenset(UPPER),
           loop=True, static=True),
    Export("knife_strike", "knife", "knife", frozenset(FULL)),
    Export("knife_strike", "knife", "crouch_knife", frozenset(UPPER)),
    Export("knife_strike", "knife", "prone_knife", frozenset(UPPER)),
    Export("knife_heavy", "knife_heavy", "knife_heavy", frozenset(FULL)),
    Export("knife_heavy", "knife_heavy", "crouch_knife_heavy",
           frozenset(UPPER)),
    Export("knife_heavy", "knife_heavy", "prone_knife_heavy",
           frozenset(UPPER)),
    Export("lance_thrust", "lance_thrust", "lance_ready",
           frozenset(UPPER), loop=True, static=True),
    Export("lance_thrust", "lance_thrust", "lance_carry",
           frozenset(UPPER), loop=True, static=True),
    Export("lance_thrust", "lance_thrust", "prone_lance_ready",
           frozenset(UPPER), loop=True, static=True),
    Export("lance_thrust", "lance_thrust", "lance_thrust",
           frozenset(FULL)),
    Export("lance_thrust", "lance_thrust", "crouch_lance_thrust",
           frozenset(UPPER)),
    Export("lance_thrust", "lance_thrust", "prone_lance_thrust",
           frozenset(UPPER)),
    Export("crouch_idle", "crouch", "crouch", frozenset(FULL), loop=True),
    Export("stand_to_crouch", "stand_to_crouch", "stand_to_crouch",
           frozenset(FULL)),
    Export("stand_to_crouch", "stand_to_crouch", "crouch_to_stand",
           frozenset(FULL), reverse=True),
    Export("crouch_walk", "crouch_walk", "crouch_walk",
           frozenset(FULL), loop=True),
    Export("prone_idle", "prone", "prone", frozenset(FULL), loop=True),
    Export("crouch_to_prone", "crouch_to_prone", "crouch_to_prone",
           frozenset(FULL)),
    Export("prone_to_crouch", "prone_to_crouch", "prone_to_crouch",
           frozenset(FULL)),
    Export("crawl", "crawl", "crawl", frozenset(FULL), loop=True),
    Export("berserk_roar", "berserk_roar", "berserk_roar",
           frozenset(FULL)),
    Export("berserk_run", "berserk_run", "berserk_run",
           frozenset(FULL), loop=True),
    Export("berserk_claw_r", "berserk_claw_r", "berserk_claw_r",
           frozenset(FULL)),
    Export("berserk_claw_l", "berserk_claw_l", "berserk_claw_l",
           frozenset(FULL)),
    Export("berserk_pounce", "berserk_pounce", "berserk_pounce",
           frozenset(POUNCE)),
)


def key(seconds: float) -> str:
    return f"{seconds:.5f}".rstrip("0").rstrip(".") or "0"


def clean(value: float) -> float:
    result = round(float(value), 5)
    return 0.0 if abs(result) < 0.000005 else result


def animation(document: dict, clip_name: str, selected: frozenset[str],
              loop: bool, static: bool, reverse: bool) -> dict:
    clip = document["clips"][clip_name]
    frames = clip["frames"]
    fps = float(document.get("sample_rate", 60.0))
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
        euler = rotations.as_euler(
            "xyz", degrees=False)
        euler = np.unwrap(euler, axis=0)
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
    duration = 1.2 if static else sample_times[-1]
    output = {
        "animation_length": clean(duration),
        "bones": bones,
    }
    if loop:
        output["loop"] = True
    return output


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
        euler = np.unwrap(Rotation.concatenate(corrected).as_euler(
            "xyz", degrees=False), axis=0)
        channel.clear()
        channel.update({
            item: [clean(value) for value in row]
            for item, row in zip(keys, np.degrees(euler))
        })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
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
    crouch = replacements["animation.eva_unit01.crouch"]
    prone = replacements["animation.eva_unit01.prone"]
    match_edge(replacements["animation.eva_unit01.stand_to_crouch"],
               crouch, "end")
    match_edge(replacements["animation.eva_unit01.crouch_to_stand"],
               crouch, "start")
    match_edge(replacements["animation.eva_unit01.crouch_to_prone"],
               crouch, "start")
    match_edge(replacements["animation.eva_unit01.crouch_to_prone"],
               prone, "end")
    match_edge(replacements["animation.eva_unit01.prone_to_crouch"],
               prone, "start")
    match_edge(replacements["animation.eva_unit01.prone_to_crouch"],
               crouch, "end")
    payload = {
        "schema": 1,
        "authority": "real_human_mocap_body_plus_target_weapon_constraints",
        "loop_closure": "distributed_local_geodesic_drift",
        "transition_edge_blend_seconds": 0.35,
        "sample_rate_hz": 30,
        "sources": sources,
        "replace_animations": replacements,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"EVA real mocap patch: animations={len(replacements)} "
        f"sources={len(sources)} output={args.output}"
    )


if __name__ == "__main__":
    main()
