#!/usr/bin/env python3
"""Install SmOd Angel/MP geometry into the LOCAL-ONLY development pack.

Nothing produced by this script belongs in the public jar. Obtain SmOd774YT's
permission before distributing the generated resource pack.
"""
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "evaaddon1-0.zip"
OUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"

ASSETS = {
    "mass_production_eva": {
        "geo": "models/entity/entity_mp.json",
        "animation": "animations/entity_mp.animation.json",
        "texture": "textures/entity/pamobile/entity_mp.png",
    },
    "sachiel": {
        "geo": "models/entity/entity_sachiel.json",
        "animation": "animations/entity_sachiel.animation.json",
        "texture": "textures/entity/pamobile/entity_sachiel.png",
    },
    "israfel": {
        "geo": "models/entity/entity_israfel.json",
        "animation": "animations/entity_israfel.animation.json",
        "texture": "textures/entity/pamobile/entity_israfel.png",
    },
}


def read_unique(archive, suffix):
    matches = [entry for entry in archive.namelist() if entry.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {suffix}, found {len(matches)}")
    return archive.read(matches[0])


def add_mass_production_wings(geometry):
    bones = geometry["minecraft:geometry"][0]["bones"]
    bones[:] = [bone for bone in bones if not bone["name"].startswith("wing_")]
    bones.extend([
        {"name": "wing_l_upper", "parent": "Upperbody", "pivot": [2.5, 26.0, 2.0], "cubes": [
            {"origin": [2.5, 25.3, 1.0], "size": [18.0, 1.4, 3.0], "uv": [0, 0]},
            {"origin": [3.5, 23.8, 1.8], "size": [15.5, 1.1, 2.2], "uv": [0, 0]},
            {"origin": [4.5, 22.5, 2.5], "size": [12.5, 0.9, 1.8], "uv": [0, 0]},
        ]},
        {"name": "wing_r_upper", "parent": "Upperbody", "pivot": [-2.5, 26.0, 2.0], "cubes": [
            {"origin": [-20.5, 25.3, 1.0], "size": [18.0, 1.4, 3.0], "uv": [0, 0]},
            {"origin": [-19.0, 23.8, 1.8], "size": [15.5, 1.1, 2.2], "uv": [0, 0]},
            {"origin": [-17.0, 22.5, 2.5], "size": [12.5, 0.9, 1.8], "uv": [0, 0]},
        ]},
        {"name": "wing_l_lower", "parent": "Upperbody", "pivot": [2.5, 23.0, 2.5], "cubes": [
            {"origin": [2.5, 21.8, 1.5], "size": [16.0, 1.3, 2.8], "uv": [0, 0]},
            {"origin": [3.5, 20.2, 2.2], "size": [13.0, 1.0, 2.0], "uv": [0, 0]},
        ]},
        {"name": "wing_r_lower", "parent": "Upperbody", "pivot": [-2.5, 23.0, 2.5], "cubes": [
            {"origin": [-18.5, 21.8, 1.5], "size": [16.0, 1.3, 2.8], "uv": [0, 0]},
            {"origin": [-16.5, 20.2, 2.2], "size": [13.0, 1.0, 2.0], "uv": [0, 0]},
        ]},
    ])


def wing_pose(animation, values):
    bones = animation.setdefault("bones", {})
    for name, rotation in values.items():
        bones[name] = {"rotation": rotation}


def main():
    with zipfile.ZipFile(SOURCE) as archive:
        for target, source in ASSETS.items():
            geometry = json.loads(read_unique(archive, source["geo"]))
            geometry["minecraft:geometry"][0]["description"]["identifier"] = f"geometry.{target}"
            animation = json.loads(read_unique(archive, source["animation"]))
            if target == "mass_production_eva":
                add_mass_production_wings(geometry)
                wing_pose(animation["animations"]["animation.entity_mp.idle_1"], {
                    "wing_l_upper": {"0.0": [0, 5, -18], "1.0": [0, 7, -23], "2.0": [0, 5, -18]},
                    "wing_r_upper": {"0.0": [0, -5, 18], "1.0": [0, -7, 23], "2.0": [0, -5, 18]},
                    "wing_l_lower": {"0.0": [0, 10, 34], "1.0": [0, 12, 29], "2.0": [0, 10, 34]},
                    "wing_r_lower": {"0.0": [0, -10, -34], "1.0": [0, -12, -29], "2.0": [0, -10, -34]},
                })
                wing_pose(animation["animations"]["animation.entity_mp.move"], {
                    "wing_l_upper": {"0.0": [0, 8, -10], "0.45": [0, 3, -35], "0.9": [0, 8, -10]},
                    "wing_r_upper": {"0.0": [0, -8, 10], "0.45": [0, -3, 35], "0.9": [0, -8, 10]},
                    "wing_l_lower": {"0.0": [0, 8, 26], "0.45": [0, 16, 42], "0.9": [0, 8, 26]},
                    "wing_r_lower": {"0.0": [0, -8, -26], "0.45": [0, -16, -42], "0.9": [0, -8, -26]},
                })
                animation["animations"]["animation.entity_mp.ritual"] = {
                    "loop": True,
                    "animation_length": 2.4,
                    "bones": {
                        "Upperbody": {"rotation": {"0.0": [3, 0, 0]}},
                        "Head": {"rotation": {"0.0": [15, 0, 0], "1.2": [18, 0, 0], "2.4": [15, 0, 0]}},
                        "Rightarm": {"rotation": {"0.0": [0, 0, -88]}},
                        "Lowerarm": {"rotation": {"0.0": [0, 0, 0]}},
                        "Leftarm": {"rotation": {"0.0": [0, 0, 88]}},
                        "Lowerarm2": {"rotation": {"0.0": [0, 0, 0]}},
                        "Rightleg": {"rotation": {"0.0": [2, 0, 2]}},
                        "Leftleg": {"rotation": {"0.0": [-2, 0, -2]}},
                        "wing_l_upper": {"rotation": {"0.0": [0, 2, -8]}},
                        "wing_r_upper": {"rotation": {"0.0": [0, -2, 8]}},
                        "wing_l_lower": {"rotation": {"0.0": [0, 5, 16]}},
                        "wing_r_lower": {"rotation": {"0.0": [0, -5, -16]}},
                    },
                }
                animation["animations"]["animation.entity_mp.attack"] = {
                    "animation_length": 0.62,
                    "bones": {
                        "Rightarm": {"rotation": {"0.0": [18, 0, -14], "0.14": [-108, -8, 5],
                                                    "0.38": [-92, -4, 3], "0.62": [0, 0, 0]}},
                        "Lowerarm": {"rotation": {"0.0": [26, 0, 0], "0.14": [-8, 0, 0],
                                                   "0.62": [0, 0, 0]}},
                        "Leftarm": {"rotation": {"0.0": [-34, 0, 18], "0.14": [-62, 0, 24],
                                                  "0.62": [0, 0, 0]}},
                        "Upperbody": {"rotation": {"0.0": [0, -10, 0], "0.14": [0, 8, 0],
                                                    "0.62": [0, 0, 0]}},
                        "wing_l_upper": {"rotation": {"0.0": [0, 8, -28], "0.14": [0, 2, -10],
                                                       "0.62": [0, 8, -28]}},
                        "wing_r_upper": {"rotation": {"0.0": [0, -8, 28], "0.14": [0, -2, 10],
                                                       "0.62": [0, -8, 28]}},
                    },
                }
            texture = read_unique(archive, source["texture"])

            geo_path = OUT / "geo" / f"{target}.geo.json"
            animation_path = OUT / "animations" / f"{target}.animation.json"
            texture_path = OUT / "textures/entity" / f"{target}.png"
            for path in (geo_path, animation_path, texture_path):
                path.parent.mkdir(parents=True, exist_ok=True)
            geo_path.write_text(json.dumps(geometry, indent=2), encoding="utf-8")
            animation_path.write_text(json.dumps(animation, indent=2), encoding="utf-8")
            texture_path.write_bytes(texture)

    source_note = REPO / "run/resourcepacks/eva_real_model/_SOURCE.txt"
    existing = source_note.read_text(encoding="utf-8") if source_note.exists() else ""
    notice = ("\nMass-Production EVA and Sachiel model/texture/animations also extracted "
              "from the same SmOd774YT addon. LOCAL TESTING ONLY.\n")
    if notice.strip() not in existing:
        source_note.write_text(existing.rstrip() + "\n" + notice, encoding="utf-8")
    print("Installed local SmOd models: " + ", ".join(ASSETS))


if __name__ == "__main__":
    main()
