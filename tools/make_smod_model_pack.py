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


def weapon_bones(bones):
    forearm = next(bone for bone in bones if bone["name"] == "Lowerarm")
    px, py, pz = forearm["pivot"]
    return [
        {"name": "knife", "parent": "Lowerarm", "pivot": [px, py, pz], "cubes": [
            # SmOd's forearm points down its local -Y axis. Keeping the blade
            # on that axis makes it point forward after the arm aims, instead
            # of rotating into a vertical white slab.
            {"origin": [px - 3, py - 70, pz - 2], "size": [6, 26, 4], "uv": [400, 0]},
            {"origin": [px - 2.5, py - 86, pz - 1.5], "size": [5, 16, 3], "uv": [400, 0]},
            {"origin": [px - 1.5, py - 96, pz - 1], "size": [3, 10, 2], "uv": [400, 0]},
            {"origin": [px - 3.5, py - 86, pz + 1.5], "size": [1, 42, 1], "uv": [472, 80]},
            {"origin": [px - 5, py - 46, pz - 5], "size": [10, 12, 10], "uv": [472, 80]},
        ]},
        {"name": "cannon", "parent": "Lowerarm", "pivot": [px, py, pz], "cubes": [
            {"origin": [px - 8, py - 64, pz - 8], "size": [16, 54, 16], "uv": [400, 80]},
            {"origin": [px - 6, py - 102, pz - 6], "size": [12, 38, 12], "uv": [400, 80]},
            {"origin": [px - 4, py - 128, pz - 4], "size": [8, 26, 8], "uv": [400, 80]},
            {"origin": [px - 7, py - 134, pz - 7], "size": [14, 7, 14], "uv": [472, 80]},
            {"origin": [px - 12, py - 55, pz - 3], "size": [6, 24, 6], "uv": [472, 80]},
        ]},
        {"name": "lance", "parent": "Lowerarm", "pivot": [px, py, pz], "cubes": [
            {"origin": [px - 3, py - 75, pz - 3], "size": [6, 75, 6], "uv": [400, 220]},
            {"origin": [px - 3, py - 150, pz - 3], "size": [6, 75, 6], "uv": [400, 220]},
            {"origin": [px - 3, py - 225, pz - 3], "size": [6, 75, 6], "uv": [400, 220]},
            {"origin": [px - 12, py - 290, pz - 2.5], "size": [5, 68, 5], "uv": [424, 220],
             "rotation": [0, 0, -7], "pivot": [px, py - 222, pz]},
            {"origin": [px + 7, py - 290, pz - 2.5], "size": [5, 68, 5], "uv": [448, 220],
             "rotation": [0, 0, 7], "pivot": [px, py - 222, pz]},
            {"origin": [px - 9, py - 6, pz - 9], "size": [18, 18, 18], "uv": [472, 220]},
        ]},
    ]


def enlarge_head_details(bones):
    """Make SmOd's very small face readable at Project SEELE's camera scale."""
    head = next(bone for bone in bones if bone["name"] == "Head")
    px, py, pz = head["pivot"]
    sx, sy, sz = 1.28, 1.15, 1.28
    for cube in head.get("cubes", []):
        ox, oy, oz = cube["origin"]
        wx, wy, wz = cube["size"]
        cube["origin"] = [px + (ox - px) * sx, py + (oy - py) * sy, pz + (oz - pz) * sz]
        cube["size"] = [wx * sx, wy * sy, wz * sz]
        if "pivot" in cube:
            qx, qy, qz = cube["pivot"]
            cube["pivot"] = [px + (qx - px) * sx, py + (qy - py) * sy, pz + (qz - pz) * sz]
        if isinstance(cube.get("inflate"), (int, float)):
            cube["inflate"] *= 1.18


def scale_geometry(data):
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
    enlarge_head_details(geometry["bones"])
    geometry["bones"].extend(weapon_bones(geometry["bones"]))
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
            "Rightarm": {"rotation": {"0.0": [-52, -8, -4], "0.6": [-53.5, -8, -4], "1.2": [-52, -8, -4]}},
            "Lowerarm": {"rotation": {"0.0": [-40, 0, 0]}},
            "Leftarm": {"rotation": {"0.0": [-70, -18, 10], "0.6": [-71, -18, 10], "1.2": [-70, -18, 10]}},
            "Lowerarm2": {"rotation": {"0.0": [-22, -14, 0]}},
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


def render_texture(source_path, target_path):
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
        "$g.FillRectangle($steel,400,0,42,72);$g.FillRectangle($metal,400,80,72,128);"
        "$g.FillRectangle($dark,472,80,32,40);$g.FillRectangle($red,400,220,104,148);$g.Dispose();"
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

    with zipfile.ZipFile(SOURCE) as archive:
        for unit in (1, 2):
            geometry = json.loads(read_suffix(archive, f"models/entity/entity_eva{unit}.json"))
            animations = json.loads(read_suffix(archive, f"animations/entity_eva{unit}.animation.json"))
            texture = read_suffix(archive, f"textures/entity/pamobile/entity_eva{unit}.png")
            target = "01" if unit == 1 else "02"
            (geo_dir / f"eva_unit{target}.geo.json").write_text(
                json.dumps(scale_geometry(geometry), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (anim_dir / f"eva_unit{target}.animation.json").write_text(
                json.dumps(build_animations(animations, unit), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raw_texture = source_dir / f"eva{unit}.png"
            raw_texture.write_bytes(texture)
            render_texture(raw_texture, texture_dir / f"eva_unit{target}.png")
        shutil.rmtree(source_dir)

    (OUT / "pack.mcmeta").write_text(json.dumps({"pack": {
        "pack_format": 15, "description": "SmOd EVA-01/02 conversion - LOCAL TEST ONLY",
    }}, indent=2), encoding="utf-8")
    (OUT / "_SOURCE.txt").write_text(
        "EVANGELION: END ADDON V1.0 by SmOd774YT (Planet Minecraft).\n"
        "LOCAL TESTING ONLY. Do not commit or redistribute this generated pack.\n"
        "Obtain the author's explicit permission before public use.\n", encoding="utf-8")
    print(f"local pack written -> {OUT}")


if __name__ == "__main__":
    main()
