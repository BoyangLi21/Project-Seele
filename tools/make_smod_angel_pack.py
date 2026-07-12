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


def main():
    with zipfile.ZipFile(SOURCE) as archive:
        for target, source in ASSETS.items():
            geometry = json.loads(read_unique(archive, source["geo"]))
            geometry["minecraft:geometry"][0]["description"]["identifier"] = f"geometry.{target}"
            animation = json.loads(read_unique(archive, source["animation"]))
            if target == "mass_production_eva":
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
