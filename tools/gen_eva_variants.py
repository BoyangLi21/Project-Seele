#!/usr/bin/env python3
"""Generate original Unit-00 and Unit-02 geometry from our MIT Unit-01 rig.

The variants keep identical animation bone names, but use distinct heads,
shoulder pylons and layered armour. No third-party geometry is copied.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEO_DIR = ROOT / "src/main/resources/assets/projectseele/geo"
SOURCE = GEO_DIR / "eva_unit01.geo.json"
ANIM_DIR = ROOT / "src/main/resources/assets/projectseele/animations"
ANIM_SOURCE = ANIM_DIR / "eva_unit01.animation.json"


def bone_map(geometry):
    return {bone["name"]: bone for bone in geometry["bones"]}


def armour_up(bones, heavy=False):
    inflate = 0.55 if heavy else 0.35
    for name in ("arm_l", "arm_r", "leg_l", "leg_r", "shin_l", "shin_r"):
        for cube in bones[name].get("cubes", []):
            cube["inflate"] = inflate


def unit00(source):
    data = copy.deepcopy(source)
    geometry = data["minecraft:geometry"][0]
    geometry["description"]["identifier"] = "geometry.eva_unit00"
    bones = bone_map(geometry)
    armour_up(bones, False)
    bones["head"]["cubes"] = [
        {"origin": [-6, 148, -5], "size": [12, 13, 10], "uv": [196, 0]},
        {"origin": [-4, 159, -4], "size": [8, 5, 8], "uv": [128, 0]},
        {"origin": [-3, 152, -7.5], "size": [6, 4, 3], "uv": [160, 140]},
        {"origin": [-4, 148, -7], "size": [8, 3, 3], "uv": [96, 152]},
    ]
    bones["horn"]["cubes"] = []
    bones["pylon_l"]["cubes"] = [
        {"origin": [11, 138, -6], "size": [7, 11, 12], "uv": [0, 140]}
    ]
    bones["pylon_r"]["cubes"] = [
        {"origin": [-18, 138, -6], "size": [7, 11, 12], "uv": [48, 140]}
    ]
    geometry["bones"].append({
        "name": "shield",
        "parent": "forearm_l",
        "pivot": [14.5, 100, -5],
        "cubes": [
            {"origin": [3.5, 58, -12], "size": [22, 56, 5], "uv": [0, 140]},
            {"origin": [7.5, 64, -14], "size": [14, 44, 3], "uv": [128, 0]},
        ],
    })
    return data


def unit02(source):
    data = copy.deepcopy(source)
    geometry = data["minecraft:geometry"][0]
    geometry["description"]["identifier"] = "geometry.eva_unit02"
    bones = bone_map(geometry)
    armour_up(bones, True)
    bones["head"]["cubes"] = [
        {"origin": [-6, 148, -6], "size": [12, 15, 12], "uv": [196, 0]},
        {"origin": [-5, 149, -9], "size": [10, 9, 4], "uv": [76, 0]},
        {"origin": [-4.5, 156, -9.6], "size": [3, 2, 1], "uv": [160, 140]},
        {"origin": [1.5, 156, -9.6], "size": [3, 2, 1], "uv": [170, 140]},
        {"origin": [-4.5, 152, -9.6], "size": [3, 2, 1], "uv": [160, 140]},
        {"origin": [1.5, 152, -9.6], "size": [3, 2, 1], "uv": [170, 140]},
        {"origin": [-4, 147, -8], "size": [8, 4, 3], "uv": [96, 152]},
    ]
    bones["horn"]["rotation"] = [-12, 0, 0]
    bones["horn"]["cubes"] = [
        {"origin": [-5, 158, -5], "size": [2, 20, 2], "uv": [180, 140]},
        {"origin": [3, 158, -5], "size": [2, 20, 2], "uv": [180, 140]},
    ]
    bones["pylon_l"]["cubes"] = [
        {"origin": [10, 135, -8], "size": [11, 20, 16], "uv": [0, 140]},
        {"origin": [18, 139, -5], "size": [4, 12, 10], "uv": [128, 0]},
    ]
    bones["pylon_r"]["cubes"] = [
        {"origin": [-21, 135, -8], "size": [11, 20, 16], "uv": [48, 140]},
        {"origin": [-22, 139, -5], "size": [4, 12, 10], "uv": [128, 0]},
    ]
    return data


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    outputs = {
        "eva_unit00.geo.json": unit00(source),
        "eva_unit02.geo.json": unit02(source),
    }
    for name, data in outputs.items():
        path = GEO_DIR / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    animation = json.loads(ANIM_SOURCE.read_text(encoding="utf-8"))

    # Unit-00's shield is functional, not decoration. In the kneeling stance
    # the left arm presents it toward Ramiel while the right arm reinforces it.
    unit00_animation = copy.deepcopy(animation)
    crouch = unit00_animation["animations"]["animation.eva_unit01.crouch"]["bones"]
    crouch["torso_upper"]["rotation"] = {"0.0": [-10, 8, 0], "0.8": [-8, 8, 0], "1.6": [-10, 8, 0]}
    crouch["arm_l"]["rotation"] = {"0.0": [-94, -12, 28]}
    crouch["forearm_l"] = {"rotation": {"0.0": [-42, 0, 0]}}
    crouch["arm_r"]["rotation"] = {"0.0": [-68, 18, -18]}
    crouch["forearm_r"] = {"rotation": {"0.0": [-56, 0, 0]}}

    crouch_walk = unit00_animation["animations"]["animation.eva_unit01.crouch_walk"]["bones"]
    crouch_walk["torso_upper"]["rotation"] = {"0.0": [-10, 8, 0]}
    crouch_walk["arm_l"] = {"rotation": {"0.0": [-94, -12, 28]}}
    crouch_walk["forearm_l"] = {"rotation": {"0.0": [-42, 0, 0]}}
    crouch_walk["arm_r"] = {"rotation": {"0.0": [-68, 18, -18]}}
    crouch_walk["forearm_r"] = {"rotation": {"0.0": [-56, 0, 0]}}

    animations = {
        "eva_unit00.animation.json": unit00_animation,
        "eva_unit02.animation.json": animation,
    }
    for name, data in animations.items():
        path = ANIM_DIR / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
