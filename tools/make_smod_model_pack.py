#!/usr/bin/env python3
"""Generate a LOCAL-ONLY Unit-01/02 pack from SmOd's Bedrock addon.

The downloaded artwork is not part of Project SEELE. Do not redistribute the
generated pack; obtain SmOd's permission before any public use.
"""
import copy
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "evaaddon1-0.zip"
EUD_SOURCE = REPO / "eud-1.1.0-forge-1.20.1.jar"
OUT = REPO / "run/resourcepacks/eva_real_model"
SCALE = 6.0
CANVAS = 512

BONE_MAP = {
    "root": "bone7", "torso_lower": "Lowerbody", "torso_upper": "Upperbody",
    "arm_l": "Leftarm", "forearm_l": "Lowerarm2",
    "arm_r": "Rightarm", "forearm_r": "Lowerarm",
    "leg_l": "Leftleg", "shin_l": "bone6",
    "leg_r": "Rightleg", "shin_r": "bone16", "head": "Head",
}


def read_suffix(archive, suffix):
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {suffix}, found {len(matches)}")
    return archive.read(matches[0])


def scale_values(value, factor):
    if isinstance(value, list):
        return [item * factor if isinstance(item, (int, float)) else item for item in value]
    if isinstance(value, dict):
        return {key: scale_values(item, factor) for key, item in value.items()}
    return value


def convert_eud_lance(model, px, socket_y, pz):
    """Convert EUD's local Java item model into cubes on our hand socket."""
    cubes = []
    for element in model.get("elements", []):
        start = element["from"]
        end = element["to"]
        cube = {
            "origin": [px + (start[0] - 8.0) * SCALE,
                       socket_y - (end[1] + 16.0) * SCALE,
                       pz + (start[2] - 8.0) * SCALE],
            "size": [(end[0] - start[0]) * SCALE,
                     (end[1] - start[1]) * SCALE,
                     (end[2] - start[2]) * SCALE],
        }
        faces = {}
        for name, face in element.get("faces", {}).items():
            uv = face.get("uv")
            if isinstance(uv, list) and len(uv) == 4:
                faces[name] = {
                    "uv": [384 + uv[0] * 8, 384 + uv[1] * 8],
                    "uv_size": [(uv[2] - uv[0]) * 8, (uv[3] - uv[1]) * 8],
                }
        if faces:
            cube["uv"] = faces
        rotation = element.get("rotation", {})
        angle = rotation.get("angle", 0)
        if angle:
            axis = rotation.get("axis")
            java_pivot = rotation.get("origin", [8, -16, 8])
            converted = [0, 0, 0]
            if axis == "x":
                converted[0] = -angle
            elif axis == "y":
                converted[1] = angle
            elif axis == "z":
                converted[2] = -angle
            cube["rotation"] = converted
            cube["pivot"] = [px + (java_pivot[0] - 8.0) * SCALE,
                             socket_y - (java_pivot[1] + 16.0) * SCALE,
                             pz + (java_pivot[2] - 8.0) * SCALE]
        cubes.append(cube)
    return cubes


def weapon_bones(bones, eud_lance=None):
    forearm = next(bone for bone in bones if bone["name"] == "Lowerarm")
    left_forearm = next(bone for bone in bones if bone["name"] == "Lowerarm2")
    px, py, pz = forearm["pivot"]
    lx, ly, lz = left_forearm["pivot"]
    hand_y = py - 42
    left_hand_y = ly - 42
    socket_y = hand_y - 14
    lance_cubes = convert_eud_lance(eud_lance, px, socket_y, pz) if eud_lance else None
    upperbody = next(bone for bone in bones if bone["name"] == "Upperbody")
    ux, uy, uz = upperbody["pivot"]
    return [
        {"name": "RightHand", "parent": "Lowerarm", "pivot": [px, hand_y, pz], "cubes": [
            {"origin": [px - 7, hand_y - 14, pz - 7], "size": [14, 14, 14], "uv": [120, 180]},
        ]},
        {"name": "LeftHand", "parent": "Lowerarm2", "pivot": [lx, left_hand_y, lz], "cubes": [
            {"origin": [lx - 7, left_hand_y - 14, lz - 7], "size": [14, 14, 14], "uv": [168, 180]},
        ]},
        {"name": "weapon_socket_r", "parent": "RightHand", "pivot": [px, socket_y, pz]},
        {"name": "camera_socket", "parent": "Head", "pivot": [0, 183, 14]},
        {"name": "knife", "parent": "weapon_socket_r", "pivot": [px, socket_y, pz], "cubes": [
            {"origin": [px - 3, socket_y - 30, pz - 2], "size": [6, 26, 4], "uv": [400, 0]},
            {"origin": [px - 2.5, socket_y - 46, pz - 1.5], "size": [5, 16, 3], "uv": [400, 0]},
            {"origin": [px - 1.5, socket_y - 56, pz - 1], "size": [3, 10, 2], "uv": [400, 0]},
            {"origin": [px - 3.5, socket_y - 46, pz + 1.5], "size": [1, 42, 1], "uv": [472, 80]},
            {"origin": [px - 5, socket_y - 4, pz - 5], "size": [10, 12, 10], "uv": [472, 80]},
        ]},
        {"name": "cannon", "parent": "weapon_socket_r", "pivot": [px, socket_y, pz], "cubes": [
            {"origin": [px - 8, socket_y - 54, pz - 8], "size": [16, 54, 16], "uv": [400, 80]},
            {"origin": [px - 6, socket_y - 92, pz - 6], "size": [12, 38, 12], "uv": [400, 80]},
            {"origin": [px - 4, socket_y - 118, pz - 4], "size": [8, 26, 8], "uv": [400, 80]},
            {"origin": [px - 7, socket_y - 124, pz - 7], "size": [14, 7, 14], "uv": [472, 80]},
            {"origin": [px - 12, socket_y - 45, pz - 3], "size": [6, 24, 6], "uv": [472, 80]},
        ]},
        {"name": "lance", "parent": "weapon_socket_r", "pivot": [px, socket_y, pz], "cubes": lance_cubes or [
            {"origin": [px - 3, socket_y - 75, pz - 3], "size": [6, 75, 6], "uv": [400, 220]},
            {"origin": [px - 3, socket_y - 150, pz - 3], "size": [6, 75, 6], "uv": [400, 220]},
            {"origin": [px - 3, socket_y - 225, pz - 3], "size": [6, 75, 6], "uv": [400, 220]},
            {"origin": [px - 12, socket_y - 290, pz - 2.5], "size": [5, 68, 5], "uv": [424, 220],
             "rotation": [0, 0, -7], "pivot": [px, socket_y - 222, pz]},
            {"origin": [px + 7, socket_y - 290, pz - 2.5], "size": [5, 68, 5], "uv": [448, 220],
             "rotation": [0, 0, 7], "pivot": [px, socket_y - 222, pz]},
            {"origin": [px - 9, socket_y - 6, pz - 9], "size": [18, 18, 18], "uv": [472, 220]},
        ]},
        {"name": "entry_plug", "parent": "Upperbody", "pivot": [ux, uy, uz + 12], "cubes": [
            {"origin": [ux - 6, uy - 28, uz + 10], "size": [12, 58, 12], "uv": [400, 80]},
            {"origin": [ux - 8, uy + 26, uz + 8], "size": [16, 10, 16], "uv": [472, 80]},
        ]},
        {"name": "plug_hatch_l", "parent": "Upperbody", "pivot": [ux, uy, uz + 10], "cubes": [
            {"origin": [ux, uy - 28, uz + 8], "size": [16, 58, 5], "uv": [472, 80]},
        ]},
        {"name": "plug_hatch_r", "parent": "Upperbody", "pivot": [ux, uy, uz + 10], "cubes": [
            {"origin": [ux - 16, uy - 28, uz + 8], "size": [16, 58, 5], "uv": [472, 80]},
        ]},
    ]


def solid_uv(x, y):
    return {name: {"uv": [x, y], "uv_size": [2, 2]}
            for name in ("north", "east", "south", "west", "up", "down")}


def add_unit01_face(bones):
    """Overlay an original Unit-01 mask on SmOd's overly square base head."""
    bones.append({
        "name": "Unit01FaceMask",
        "parent": "Head",
        "pivot": [0, 174, -15],
        "cubes": [
            {"origin": [-5, 175, -18], "size": [10, 9, 5], "uv": solid_uv(480, 130)},
            {"origin": [-8, 169, -19], "size": [16, 6, 4], "uv": solid_uv(480, 178)},
            {"origin": [-7, 171.5, -20], "size": [5, 1.8, 1.5], "uv": solid_uv(480, 162),
             "rotation": [0, 0, -7], "pivot": [-2, 172, -20]},
            {"origin": [2, 171.5, -20], "size": [5, 1.8, 1.5], "uv": solid_uv(480, 162),
             "rotation": [0, 0, 7], "pivot": [2, 172, -20]},
            {"origin": [-9, 162, -18.5], "size": [6, 8, 4], "uv": solid_uv(480, 130),
             "rotation": [0, 0, -10], "pivot": [-3, 169, -17]},
            {"origin": [3, 162, -18.5], "size": [6, 8, 4], "uv": solid_uv(480, 130),
             "rotation": [0, 0, 10], "pivot": [3, 169, -17]},
            {"origin": [-8, 164, -19.5], "size": [2, 5, 1.5], "uv": solid_uv(480, 146)},
            {"origin": [6, 164, -19.5], "size": [2, 5, 1.5], "uv": solid_uv(480, 146)},
            {"origin": [-5, 157, -18], "size": [10, 7, 5], "uv": solid_uv(480, 130)},
            {"origin": [-3.5, 151, -17.5], "size": [7, 7, 4.5], "uv": solid_uv(480, 130)},
            {"origin": [-3, 149, -17], "size": [6, 3, 4], "uv": solid_uv(480, 178)},
            {"origin": [-1.5, 158, -19.2], "size": [3, 3, 1.5], "uv": solid_uv(480, 146)},
        ],
    })


def scale_geometry(data, eud_lance=None, unit=1):
    geometry = data["minecraft:geometry"][0]
    description = geometry["description"]
    description["texture_width"] = CANVAS
    description["texture_height"] = CANVAS
    for bone in geometry["bones"]:
        if "pivot" in bone:
            bone["pivot"] = scale_values(bone["pivot"], SCALE)
        for cube in bone.get("cubes", []):
            cube["origin"] = scale_values(cube["origin"], SCALE)
            cube["size"] = scale_values(cube["size"], SCALE)
            if isinstance(cube.get("inflate"), (int, float)):
                cube["inflate"] *= SCALE
            if "pivot" in cube:
                cube["pivot"] = scale_values(cube["pivot"], SCALE)
            if isinstance(cube.get("uv"), list):
                cube["uv"] = scale_values(cube["uv"], SCALE)
            elif isinstance(cube.get("uv"), dict):
                for face in cube["uv"].values():
                    if "uv" in face:
                        face["uv"] = scale_values(face["uv"], SCALE)
                    if "uv_size" in face:
                        face["uv_size"] = scale_values(face["uv_size"], SCALE)
    if unit == 1:
        add_unit01_face(geometry["bones"])
    geometry["bones"].extend(weapon_bones(geometry["bones"], eud_lance))
    data["format_version"] = "1.12.0"
    return data


def remap_animation(animation):
    result = copy.deepcopy(animation)
    result["bones"] = {
        BONE_MAP[name]: channels for name, channels in animation.get("bones", {}).items()
        if name in BONE_MAP
    }
    return result


def scale_position_channels(animation):
    result = copy.deepcopy(animation)
    for channels in result.get("bones", {}).values():
        if "position" in channels:
            channels["position"] = scale_values(channels["position"], SCALE)
        # SmOd's idle bakes a 4x root scale to enlarge its native ~2-block
        # model. Our pipeline already sizes via geo SCALE + renderer scale,
        # so this channel makes the Unit gigantic while idle. Drop it.
        channels.pop("scale", None)
    return result


def retime_animation(animation, factor):
    """Shorten a Bedrock animation without changing its authored poses."""
    result = copy.deepcopy(animation)
    if isinstance(result.get("animation_length"), (int, float)):
        result["animation_length"] *= factor
    for channels in result.get("bones", {}).values():
        for name, values in list(channels.items()):
            if not isinstance(values, dict):
                continue
            timed = {}
            for key, value in values.items():
                try:
                    timed[f"{float(key) * factor:.4f}".rstrip("0").rstrip(".")] = value
                except (TypeError, ValueError):
                    timed[key] = value
            channels[name] = timed
    return result


def sample_channel(channel, time):
    if not isinstance(channel, dict):
        return copy.deepcopy(channel)
    keyed = []
    for key, value in channel.items():
        try:
            keyed.append((float(key), value))
        except (TypeError, ValueError):
            pass
    if not keyed:
        return copy.deepcopy(channel)
    keyed.sort(key=lambda item: item[0])
    before = max((item for item in keyed if item[0] <= time), default=keyed[0], key=lambda item: item[0])
    after = min((item for item in keyed if item[0] >= time), default=keyed[-1], key=lambda item: item[0])
    left = before[1].get("post", before[1].get("pre")) if isinstance(before[1], dict) else before[1]
    right = after[1].get("pre", after[1].get("post")) if isinstance(after[1], dict) else after[1]
    if before[0] == after[0] or not isinstance(left, list) or not isinstance(right, list):
        return copy.deepcopy(left)
    factor = (time - before[0]) / (after[0] - before[0])
    return [a + (b - a) * factor if isinstance(a, (int, float)) and isinstance(b, (int, float)) else a
            for a, b in zip(left, right)]


def static_pose(animation, time):
    bones = {}
    for bone, channels in animation.get("bones", {}).items():
        sampled = {}
        for name, channel in channels.items():
            sampled[name] = {"0.0": sample_channel(channel, time)}
        if sampled:
            bones[bone] = sampled
    return {"loop": True, "animation_length": 1.0, "bones": bones}


def build_animations(source, unit):
    built_in = json.loads((REPO / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json")
                          .read_text(encoding="utf-8"))["animations"]
    output = {name: remap_animation(animation) for name, animation in built_in.items()}
    install_smod_pose_overrides(output)
    source_animations = source["animations"]
    output["animation.eva_unit01.idle"] = scale_position_channels(
        source_animations[f"animation.entity_eva{unit}.idle_1"])
    output["animation.eva_unit01.walk"] = scale_position_channels(
        source_animations[f"animation.entity_eva{unit}.move"])
    output["animation.eva_unit01.run"] = retime_animation(scale_position_channels(
        source_animations[f"animation.entity_eva{unit}.move"]), 0.58)
    output["animation.eva_unit01.visual_idle"] = static_pose(output["animation.eva_unit01.idle"], 0.0)
    # SmOd's stride extrema/contact is at loop start. Sampling 0.5 seconds
    # catches the passing pose where both legs overlap in profile.
    output["animation.eva_unit01.visual_walk_contact"] = static_pose(output["animation.eva_unit01.walk"], 0.0)
    output["animation.eva_unit01.visual_knife_windup"] = static_pose(output["animation.eva_unit01.knife"], 0.12)
    output["animation.eva_unit01.visual_knife_contact"] = static_pose(output["animation.eva_unit01.knife"], 0.28)
    output["animation.eva_unit01.visual_knife_recovery"] = static_pose(output["animation.eva_unit01.knife"], 0.50)
    output["animation.eva_unit01.visual_lance_windup"] = static_pose(output["animation.eva_unit01.lance_thrust"], 0.20)
    output["animation.eva_unit01.visual_lance_contact"] = static_pose(output["animation.eva_unit01.lance_thrust"], 0.42)
    output["animation.eva_unit01.visual_lance_recovery"] = static_pose(output["animation.eva_unit01.lance_thrust"], 0.70)
    output["animation.eva_unit01.visual_cannon"] = static_pose(output["animation.eva_unit01.aim"], 0.0)
    return {"format_version": "1.8.0", "animations": output}


def install_smod_pose_overrides(output):
    # The built-in prone pose was authored for Project SEELE's placeholder
    # bones. On SmOd's taller rig it reads like belly-swimming. These overrides
    # keep the Unit supported by hands and knees: a low, animal-like crawl.
    output["animation.eva_unit01.crouch"] = {
        "loop": True,
        "animation_length": 1.6,
        "bones": {
            "bone7": {"position": {"0.0": [0, -28, 2], "0.8": [0, -27, 2], "1.6": [0, -28, 2]}},
            "Body": {"rotation": {"0.0": [12, 0, 0]}},
            "Lowerbody": {"rotation": {"0.0": [10, -3, 0]}},
            "Upperbody": {"rotation": {"0.0": [-8, 4, 0]}},
            "Head": {"rotation": {"0.0": [-18, -3, 0]}},
            "Rightleg": {"rotation": {"0.0": [-78, 0, 7]}},
            "bone16": {"rotation": {"0.0": [125, 0, 0]}},
            "bone17": {"rotation": {"0.0": [-48, 0, 0]}},
            "Leftleg": {"rotation": {"0.0": [20, 0, -4]}},
            "bone6": {"rotation": {"0.0": [48, 0, 0]}},
            "bone5": {"rotation": {"0.0": [-20, 0, 0]}},
            "Rightarm": {"rotation": {"0.0": [-28, 0, -7]}},
            "Lowerarm": {"rotation": {"0.0": [-12, 0, 0]}},
            "Leftarm": {"rotation": {"0.0": [-24, 0, 7]}},
            "Lowerarm2": {"rotation": {"0.0": [-10, 0, 0]}},
        },
    }
    output["animation.eva_unit01.crouch_walk"] = {
        "loop": True,
        "animation_length": 1.2,
        "bones": {
            "bone7": {"position": {"0.0": [0, -20, 1], "0.3": [0, -18, 1], "0.6": [0, -20, 1], "0.9": [0, -18, 1], "1.2": [0, -20, 1]}},
            "Body": {"rotation": {"0.0": [14, 0, 0]}},
            "Lowerbody": {"rotation": {"0.0": [8, 4, 0], "0.6": [8, -4, 0], "1.2": [8, 4, 0]}},
            "Upperbody": {"rotation": {"0.0": [-6, -4, 0], "0.6": [-6, 4, 0], "1.2": [-6, -4, 0]}},
            "Head": {"rotation": {"0.0": [-16, 3, 0], "0.6": [-16, -3, 0], "1.2": [-16, 3, 0]}},
            "Rightleg": {"rotation": {"0.0": [-38, 0, 4], "0.6": [8, 0, 4], "1.2": [-38, 0, 4]}},
            "bone16": {"rotation": {"0.0": [78, 0, 0], "0.6": [46, 0, 0], "1.2": [78, 0, 0]}},
            "Leftleg": {"rotation": {"0.0": [8, 0, -4], "0.6": [-38, 0, -4], "1.2": [8, 0, -4]}},
            "bone6": {"rotation": {"0.0": [46, 0, 0], "0.6": [78, 0, 0], "1.2": [46, 0, 0]}},
            "Rightarm": {"rotation": {"0.0": [12, 0, -6], "0.6": [-30, 0, -6], "1.2": [12, 0, -6]}},
            "Leftarm": {"rotation": {"0.0": [-30, 0, 6], "0.6": [12, 0, 6], "1.2": [-30, 0, 6]}},
        },
    }
    # Kneeling low brace ("prone"): knees folded under, torso only slightly
    # leaned so the Unit can still aim and fire. Advancing rocks the knees.
    output["animation.eva_unit01.prone"] = {
        "loop": True,
        "animation_length": 2.4,
        "bones": {
            "bone7": {"position": {"0.0": [0, -58, 0]}},
            "Lowerbody": {"rotation": {"0.0": [16, 0, 0]}},
            "Upperbody": {"rotation": {"0.0": [12, 0, 0], "1.2": [14, 0, 0], "2.4": [12, 0, 0]}},
            "Head": {"rotation": {"0.0": [-20, 0, 0]}},
            "Rightarm": {"rotation": {"0.0": [-52, 0, -8]}},
            "Lowerarm": {"rotation": {"0.0": [-26, 0, 0]}},
            "Leftarm": {"rotation": {"0.0": [-52, 0, 8]}},
            "Lowerarm2": {"rotation": {"0.0": [-26, 0, 0]}},
            "Rightleg": {"rotation": {"0.0": [-28, 0, 6]}},
            "bone16": {"rotation": {"0.0": [122, 0, 0]}},
            "Leftleg": {"rotation": {"0.0": [-12, 0, -6]}},
            "bone6": {"rotation": {"0.0": [114, 0, 0]}},
        },
    }
    output["animation.eva_unit01.crawl"] = {
        "loop": True,
        "animation_length": 1.4,
        "bones": {
            "bone7": {"position": {"0.0": [0, -58, 0], "0.35": [0, -54, 2], "0.7": [0, -58, 0], "1.05": [0, -54, 2], "1.4": [0, -58, 0]}},
            "Lowerbody": {"rotation": {"0.0": [18, 0, 0]}},
            "Upperbody": {"rotation": {"0.0": [12, 5, 0], "0.7": [12, -5, 0], "1.4": [12, 5, 0]}},
            "Head": {"rotation": {"0.0": [-18, 0, 0]}},
            "Rightarm": {"rotation": {"0.0": [-36, 0, -8], "0.7": [-62, 0, -8], "1.4": [-36, 0, -8]}},
            "Leftarm": {"rotation": {"0.0": [-62, 0, 8], "0.7": [-36, 0, 8], "1.4": [-62, 0, 8]}},
            "Rightleg": {"rotation": {"0.0": [-36, 0, 6], "0.7": [-4, 0, 6], "1.4": [-36, 0, 6]}},
            "bone16": {"rotation": {"0.0": [126, 0, 0], "0.7": [108, 0, 0], "1.4": [126, 0, 0]}},
            "Leftleg": {"rotation": {"0.0": [-4, 0, -6], "0.7": [-36, 0, -6], "1.4": [-4, 0, -6]}},
            "bone6": {"rotation": {"0.0": [108, 0, 0], "0.7": [126, 0, 0], "1.4": [108, 0, 0]}},
        },
    }
    # Shouldered-rifle stance on SmOd's own skeleton: torso quartered away,
    # right forearm level (the along-arm cannon points at the reticle), left
    # arm crossed to the forestock, cheek to the scope.
    output["animation.eva_unit01.aim"] = {
        "loop": True,
        "animation_length": 1.2,
        "bones": {
            "Rightarm": {"rotation": {"0.0": [-52, -3, -4], "0.6": [-53.5, -3, -4], "1.2": [-52, -3, -4]}},
            "Lowerarm": {"rotation": {"0.0": [-38, 0, 0]}},
            "Leftarm": {"rotation": {"0.0": [-54, 18, 8], "0.6": [-55, 18, 8], "1.2": [-54, 18, 8]}},
            "Lowerarm2": {"rotation": {"0.0": [-36, 14, 0]}},
        },
    }
    # Two-handed Longinus thrust. Both hands stay on the same shaft line:
    # compact pull-back, full-body forward contact, then controlled recovery.
    output["animation.eva_unit01.lance_thrust"] = {
        "animation_length": 0.72,
        "bones": {
            "Upperbody": {"rotation": {
                "0.0": [0, 0, 0], "0.20": [-2, 14, 0],
                "0.42": [4, -10, 0], "0.72": [0, 0, 0]}},
            "Rightarm": {"rotation": {
                "0.0": [-34, -4, -6], "0.20": [-28, -10, -12],
                "0.42": [-66, -2, -5], "0.72": [-10, 0, -5]}},
            "Lowerarm": {"rotation": {
                "0.0": [-48, 0, 0], "0.20": [-62, 0, 0],
                "0.42": [-26, 0, 0], "0.72": [-6, 0, 0]}},
            "Leftarm": {"rotation": {
                "0.0": [-42, 18, 8], "0.20": [-38, 24, 10],
                "0.42": [-61, 18, 8], "0.72": [-10, 0, 5]}},
            "Lowerarm2": {"rotation": {
                "0.0": [-46, 14, 0], "0.20": [-56, 16, 0],
                "0.42": [-31, 14, 0], "0.72": [-5, 0, 0]}},
            "Lowerbody": {"rotation": {
                "0.0": [0, 0, 0], "0.20": [0, -6, 0],
                "0.42": [5, 5, 0], "0.72": [0, 0, 0]}},
        },
    }
    # Progressive-knife strike. Keep the torso readable and let the arm
    # chain create the attack arc; the previous pose twisted the whole body
    # while both arms crossed over the face.
    output["animation.eva_unit01.knife"] = {
        "animation_length": 0.52,
        "bones": {
            "Upperbody": {"rotation": {
                "0.0": [0, 0, 0], "0.12": [-3, 15, 0],
                "0.28": [4, -12, 0], "0.52": [0, 0, 0]}},
            "Rightarm": {"rotation": {
                "0.0": [-8, 0, -4], "0.12": [-90, -10, -28],
                "0.28": [-58, 0, -6], "0.52": [-8, 0, -4]}},
            "Lowerarm": {"rotation": {
                "0.0": [0, 0, 0], "0.12": [-20, 0, 0],
                "0.28": [-34, 0, 0], "0.52": [0, 0, 0]}},
            "Leftarm": {"rotation": {
                "0.0": [-10, 0, 4], "0.12": [-12, 0, 4],
                "0.28": [-36, 0, 12], "0.52": [-10, 0, 4]}},
            "Lowerarm2": {"rotation": {
                "0.0": [0, 0, 0], "0.12": [0, 0, 0],
                "0.28": [-30, 0, 0], "0.52": [0, 0, 0]}},
        },
    }
    output["animation.eva_unit01.activation"] = {
        "animation_length": 6.0,
        "bones": {
            "entry_plug": {"position": {"0.0": [0, 42, 0], "1.1": [0, 18, 0],
                                         "2.0": [0, 0, 0], "6.0": [0, 0, 0]}},
            "plug_hatch_l": {"rotation": {"0.0": [0, -62, 0], "1.5": [0, -62, 0],
                                             "2.3": [0, 0, 0]}},
            "plug_hatch_r": {"rotation": {"0.0": [0, 62, 0], "1.5": [0, 62, 0],
                                             "2.3": [0, 0, 0]}},
            "Head": {"rotation": {"0.0": [10, 0, 0], "3.4": [10, 0, 0], "5.2": [0, 0, 0]}},
            "Leftarm": {"rotation": {"0.0": [-8, 0, 5]}},
            "Rightarm": {"rotation": {"0.0": [-8, 0, -5]}},
        },
    }
    # Nailed to the Tree: arms straight out, head bowed, gentle sway.
    output["animation.eva_unit01.crucified"] = {
        "loop": True,
        "animation_length": 3.0,
        "bones": {
            "Leftarm": {"rotation": {"0.0": [0, 0, 86], "1.5": [0, 0, 84.5], "3.0": [0, 0, 86]}},
            "Rightarm": {"rotation": {"0.0": [0, 0, -86], "1.5": [0, 0, -84.5], "3.0": [0, 0, -86]}},
            "Lowerarm": {"rotation": {"0.0": [0, 0, 0]}},
            "Lowerarm2": {"rotation": {"0.0": [0, 0, 0]}},
            "Head": {"rotation": {"0.0": [14, 0, 0], "1.5": [16, 0, 0], "3.0": [14, 0, 0]}},
            "Leftleg": {"rotation": {"0.0": [0, 0, -2]}},
            "Rightleg": {"rotation": {"0.0": [0, 0, 2]}},
            "Upperbody": {"rotation": {"0.0": [3, 0, 0]}},
        },
    }


def render_texture(source_path, target_path, lance_path=None):
    lance_draw = ""
    if lance_path is not None:
        lance_draw = (f"$lance=[System.Drawing.Image]::FromFile('{lance_path}');"
                      "$g.DrawImage($lance,384,384,128,128);$lance.Dispose();")
    script = (
        "Add-Type -AssemblyName System.Drawing;"
        f"$src=[System.Drawing.Image]::FromFile('{source_path}');"
        f"$bmp=New-Object System.Drawing.Bitmap({CANVAS},{CANVAS});"
        "$g=[System.Drawing.Graphics]::FromImage($bmp);"
        "$g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor;"
        "$g.PixelOffsetMode=[System.Drawing.Drawing2D.PixelOffsetMode]::Half;"
        f"$g.DrawImage($src,0,0,{int(64 * SCALE)},{int(64 * SCALE)});$src.Dispose();"
        "$steel=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,215,220,230));"
        "$metal=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,66,72,86));"
        "$dark=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,30,34,43));"
        "$red=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,196,14,28));"
        "$purple=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,88,26,148));"
        "$green=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,75,220,38));"
        "$gold=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,225,171,31));"
        "$g.FillRectangle($steel,400,0,42,72);$g.FillRectangle($metal,400,80,72,128);"
        "$g.FillRectangle($dark,472,80,32,40);$g.FillRectangle($red,400,220,104,148);"
        "$g.FillRectangle($purple,480,130,16,16);$g.FillRectangle($green,480,146,16,16);"
        "$g.FillRectangle($gold,480,162,16,16);$g.FillRectangle($dark,480,178,16,16);"
        f"{lance_draw}$g.Dispose();"
        f"$bmp.Save('{target_path}',[System.Drawing.Imaging.ImageFormat]::Png);$bmp.Dispose();"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


def main():
    if not SOURCE.exists():
        sys.exit(f"addon not found: {SOURCE}")
    if OUT.exists():
        shutil.rmtree(OUT)
    geo_dir = OUT / "assets/projectseele/geo"
    anim_dir = OUT / "assets/projectseele/animations"
    texture_dir = OUT / "assets/projectseele/textures/entity"
    source_dir = OUT / ".source"
    for directory in (geo_dir, anim_dir, texture_dir, source_dir):
        directory.mkdir(parents=True, exist_ok=True)

    eud_lance = None
    lance_texture = None
    if EUD_SOURCE.exists():
        with zipfile.ZipFile(EUD_SOURCE) as eud:
            eud_lance = json.loads(eud.read(
                "assets/eud/models/custom/lanzadelonginusmodel.json"))
            lance_texture = source_dir / "longinus.png"
            lance_texture.write_bytes(eud.read(
                "assets/eud/textures/block/texturelanzadelonginus.png"))

    with zipfile.ZipFile(SOURCE) as archive:
        for unit in (1, 2):
            geometry = json.loads(read_suffix(archive, f"models/entity/entity_eva{unit}.json"))
            animations = json.loads(read_suffix(archive, f"animations/entity_eva{unit}.animation.json"))
            texture = read_suffix(archive, f"textures/entity/pamobile/entity_eva{unit}.png")
            target = "01" if unit == 1 else "02"
            (geo_dir / f"eva_unit{target}.geo.json").write_text(
                json.dumps(scale_geometry(geometry, eud_lance, unit), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (anim_dir / f"eva_unit{target}.animation.json").write_text(
                json.dumps(build_animations(animations, unit), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raw_texture = source_dir / f"eva{unit}.png"
            raw_texture.write_bytes(texture)
            render_texture(raw_texture, texture_dir / f"eva_unit{target}.png", lance_texture)
        shutil.rmtree(source_dir)

    (OUT / "pack.mcmeta").write_text(json.dumps({"pack": {
        "pack_format": 15, "description": "SmOd EVA-01/02 conversion - LOCAL TEST ONLY",
    }}, indent=2), encoding="utf-8")
    (OUT / "_SOURCE.txt").write_text(
        "EVANGELION: END ADDON V1.0 by SmOd774YT (Planet Minecraft).\n"
        "Lance of Longinus geometry/texture from EUD 1.1.0 (CC BY-NC 4.0).\n"
        "LOCAL TESTING ONLY. Do not commit or redistribute this generated pack.\n"
        "Obtain the authors' explicit permission before public use.\n", encoding="utf-8")
    print(f"local pack written -> {OUT}")


if __name__ == "__main__":
    main()
