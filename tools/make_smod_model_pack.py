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
    "foot_l": "bone5", "leg_r": "Rightleg", "shin_r": "bone16",
    "foot_r": "bone17", "head": "Head",
    "hand_l": "LeftHand", "hand_r": "RightHand",
    "knife": "knife", "lance": "lance",
    "entry_plug": "entry_plug",
    "plug_hatch_l": "plug_hatch_l", "plug_hatch_r": "plug_hatch_r",
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
    geometry["bones"].extend(weapon_bones(geometry["bones"], eud_lance))
    data["format_version"] = "1.12.0"
    return data


def remap_animation(animation):
    unknown = set(animation.get("bones", {})) - set(BONE_MAP)
    if unknown:
        raise RuntimeError(
            "canonical animation uses unmapped SmOd bones: "
            + ", ".join(sorted(unknown)))
    result = copy.deepcopy(animation)
    result["bones"] = {
        BONE_MAP[name]: channels for name, channels in animation.get("bones", {}).items()
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
    derived_visuals = {
        "visual_knife_windup": ("knife", 0.12),
        "visual_knife_contact": ("knife", 0.28),
        "visual_knife_recovery": ("knife", 0.50),
        "visual_lance_windup": ("lance_thrust", 0.20),
        "visual_lance_contact": ("lance_thrust", 0.42),
        "visual_lance_recovery": ("lance_thrust", 0.70),
        "visual_cannon": ("aim", 0.0),
    }
    for target, (source_name, sample_time) in derived_visuals.items():
        target_key = f"animation.eva_unit01.{target}"
        source_key = f"animation.eva_unit01.{source_name}"
        if target_key not in output:
            output[target_key] = static_pose(output[source_key], sample_time)
    return {"format_version": "1.8.0", "animations": output}


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
        "$g.FillRectangle($steel,400,0,42,72);$g.FillRectangle($metal,400,80,72,128);"
        "$g.FillRectangle($dark,472,80,32,40);$g.FillRectangle($red,400,220,104,148);"
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
    # The base generator replaces the entire pack. Reinstall every local-only
    # extension immediately so Unit-00, Mass Production EVA and Angels cannot
    # silently disappear after a Unit-01/02 rebuild.
    subprocess.run([sys.executable, str(REPO / "tools/make_smod_angel_pack.py"), str(SOURCE)], check=True)
    if EUD_SOURCE.exists():
        subprocess.run([sys.executable, str(REPO / "tools/make_eud_eva00_pack.py")], check=True)
    print(f"local pack written -> {OUT}")


if __name__ == "__main__":
    main()
