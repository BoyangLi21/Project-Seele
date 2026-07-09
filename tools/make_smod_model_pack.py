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
            {"origin": [px - 2, py - 34, pz - 2], "size": [4, 30, 4], "uv": [400, 0]},
        ]},
        {"name": "cannon", "parent": "Lowerarm", "pivot": [px, py, pz], "cubes": [
            {"origin": [px - 4, py - 82, pz - 5], "size": [8, 80, 10], "uv": [400, 80]},
            {"origin": [px - 8, py - 42, pz - 2], "size": [4, 16, 4], "uv": [472, 80]},
        ]},
    ]


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
    return result


def build_animations(source, unit):
    built_in = json.loads((REPO / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json")
                          .read_text(encoding="utf-8"))["animations"]
    output = {name: remap_animation(animation) for name, animation in built_in.items()}
    source_animations = source["animations"]
    output["animation.eva_unit01.idle"] = scale_position_channels(
        source_animations[f"animation.entity_eva{unit}.idle_1"])
    output["animation.eva_unit01.walk"] = scale_position_channels(
        source_animations[f"animation.entity_eva{unit}.move"])
    return {"format_version": "1.8.0", "animations": output}


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
        "$g.FillRectangle($steel,400,0,42,72);$g.FillRectangle($metal,400,80,72,128);"
        "$g.FillRectangle($dark,472,80,32,40);$g.Dispose();"
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
