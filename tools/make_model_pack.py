#!/usr/bin/env python3
"""Build a LOCAL-ONLY resource pack that swaps our placeholder EVA-01 for the
Rei Chikita mod's detailed model.

Usage:  python tools/make_model_pack.py [path-to-chikita-jar]

Output: run/resourcepacks/eva_real_model/   (run/ is gitignored)

The source model is All Rights Reserved (author: DanielFernandez / Rei
Chikita Mod). This pack is for private testing on our own machines only and
must never be committed or redistributed. Get the author's permission before
any public use (ROADMAP section 9).

Transformations applied:
  * geometry rescaled so total height = 192 geo units (matches our renderer,
    30 blocks at scale 2.5)
  * animations renamed to the keys our code triggers
  * our positron-cannon and prog-knife bones grafted onto the right forearm
    (uv [0,0]; colors borrowed from their sheet, close enough for testing)
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
JAR = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "Rei_Chikita_Mod_1.1.7b__jv1.20.1.jar"
OUT = REPO / "run" / "resourcepacks" / "eva_real_model"
ASSET_BASE = "assets/rei_chikita_mod_updated_20_df"
GEO_PATH = f"{ASSET_BASE}/geo/eva_01_animated.geo.json"
ANIM_PATH = f"{ASSET_BASE}/animations/eva_01_animated.animation.json"
TEX_PATH = f"{ASSET_BASE}/textures/entities/eva_01_animated_danielfernandez.png"
TARGET_HEIGHT = 192.0
RIGHT_FOREARM = "brazoderechobajo"

ANIM_MAP = {
    "animation.eva_unit01.idle": "animation.eva_01_robot.idle",
    "animation.eva_unit01.walk": "animation.eva_01_robot.walking",
    "animation.eva_unit01.run": "animation.eva_01_robot.runing",
    "animation.eva_unit01.jump": "animation.eva_01_robot.jump",
    "animation.eva_unit01.melee": "animation.eva_01_robot.attack",
}


def scale_vec(vec, k):
    return [v * k for v in vec] if isinstance(vec, list) else vec


def main():
    if not JAR.exists():
        sys.exit(f"jar not found: {JAR}")
    with zipfile.ZipFile(JAR) as zf:
        geo = json.loads(zf.read(GEO_PATH))
        anim = json.loads(zf.read(ANIM_PATH))
        texture = zf.read(TEX_PATH)

    geometry = geo["minecraft:geometry"][0]
    bones = geometry["bones"]

    # --- measure and rescale ---
    top = 0.0
    for bone in bones:
        for cube in bone.get("cubes", []):
            top = max(top, cube["origin"][1] + cube["size"][1])
    k = TARGET_HEIGHT / top
    print(f"source height {top:.1f} geo units -> scale x{k:.3f}")

    cube_index = 0
    for bone in bones:
        if "pivot" in bone:
            bone["pivot"] = scale_vec(bone["pivot"], k)
        for cube in bone.get("cubes", []):
            cube["origin"] = scale_vec(cube["origin"], k)
            cube["size"] = scale_vec(cube["size"], k)
            if "pivot" in cube:
                cube["pivot"] = scale_vec(cube["pivot"], k)
            # Stagger inflate per cube: the rescale squeezes the author's
            # overlapping plates together and they z-fight (visible flicker);
            # a sub-visible inflate offset breaks the coplanarity.
            cube["inflate"] = cube.get("inflate", 0.0) * k + (cube_index % 7) * 0.02
            cube_index += 1

    # --- graft weapon bones onto the right forearm ---
    forearm = next((b for b in bones if b["name"] == RIGHT_FOREARM), None)
    if forearm is None:
        sys.exit(f"bone {RIGHT_FOREARM} not found; model layout changed?")
    # Weapon uv regions land in the texture's top-left corner, which we
    # repaint below (the source sheet is transparent there). Both weapons
    # are modelled ALONG THE ARM AXIS (pointing down at rest) so raising
    # the arm aims them forward instead of tilting them like a walking cane.
    px, py, pz = forearm["pivot"]
    bones.append({
        "name": "knife",
        "parent": RIGHT_FOREARM,
        "pivot": [px, py, pz],
        "cubes": [
            {"origin": [px - 2, py - 34, pz - 2], "size": [4, 28, 4], "uv": [0, 40]}
        ],
    })
    bones.append({
        "name": "cannon",
        "parent": RIGHT_FOREARM,
        "pivot": [px, py, pz],
        "cubes": [
            {"origin": [px - 4, py - 82, pz - 5], "size": [8, 80, 10], "uv": [0, 80]},
            {"origin": [px - 8, py - 40, pz - 2], "size": [4, 14, 4], "uv": [200, 80]},
        ],
    })

    # --- remap animations to the keys our controllers trigger ---
    src_anims = anim["animations"]
    out_anims = {}
    for ours, theirs in ANIM_MAP.items():
        if theirs in src_anims:
            out_anims[ours] = src_anims[theirs]
    # Static aiming pose (they have no aim animation): right arm level with
    # the shoulder so the along-arm cannon points dead ahead.
    out_anims["animation.eva_unit01.aim"] = {
        "loop": True,
        "animation_length": 0.5,
        "bones": {
            "brazoderecho": {"rotation": {"0.0": [-88, 0, 0]}},
            "brazoizquierda": {"rotation": {"0.0": [-60, 0, 30]}},
        },
    }
    out_anims["animation.eva_unit01.crouch"] = {
        "loop": True,
        "animation_length": 1.2,
        "bones": {
            "todo": {"position": {"0.0": [0, -33, 0]}},
            "CINTURA": {"rotation": {"0.0": [10, 0, 0]}},
            "PIERNAIZQUIERD": {"rotation": {"0.0": [-72, 0, -3]}},
            "PIERNADERECHA": {"rotation": {"0.0": [-14, 0, 5]}},
            "PIERNABAJAIZQUIERDA": {"rotation": {"0.0": [116, 0, 0]}},
            "PIERNABAJAIZQUIERDA2": {"rotation": {"0.0": [38, 0, 0]}},
        },
    }
    out_anims["animation.eva_unit01.crouch_walk"] = {
        "loop": True,
        "animation_length": 1.0,
        "bones": {
            "todo": {"position": {"0.0": [0, -30, 0]}},
            "CINTURA": {"rotation": {"0.0": [12, 5, 0], "0.5": [12, -5, 0], "1.0": [12, 5, 0]}},
            "PIERNAIZQUIERD": {"rotation": {"0.0": [-70, 0, -3], "0.5": [-16, 0, -3], "1.0": [-70, 0, -3]}},
            "PIERNADERECHA": {"rotation": {"0.0": [-16, 0, 3], "0.5": [-70, 0, 3], "1.0": [-16, 0, 3]}},
            "PIERNABAJAIZQUIERDA": {"rotation": {"0.0": [114, 0, 0], "0.5": [42, 0, 0], "1.0": [114, 0, 0]}},
            "PIERNABAJAIZQUIERDA2": {"rotation": {"0.0": [42, 0, 0], "0.5": [114, 0, 0], "1.0": [42, 0, 0]}},
        },
    }
    out_anims["animation.eva_unit01.prone"] = {
        "loop": True,
        "animation_length": 1.8,
        "bones": {
            "todo": {"rotation": {"0.0": [90, 0, 0]}, "position": {"0.0": [0, 8, -12]}},
            "brazoizquierda": {"rotation": {"0.0": [-142, 0, 12]}},
            "brazoderecho": {"rotation": {"0.0": [-142, 0, -12]}},
            "PIERNAIZQUIERD": {"rotation": {"0.0": [8, 0, -4]}},
            "PIERNADERECHA": {"rotation": {"0.0": [8, 0, 4]}},
        },
    }
    out_anims["animation.eva_unit01.crawl"] = {
        "loop": True,
        "animation_length": 1.2,
        "bones": {
            "todo": {"rotation": {"0.0": [90, 0, 0]}, "position": {"0.0": [0, 8, -12]}},
            "brazoizquierda": {"rotation": {"0.0": [-158, 0, 12], "0.6": [-118, 0, 12], "1.2": [-158, 0, 12]}},
            "brazoderecho": {"rotation": {"0.0": [-118, 0, -12], "0.6": [-158, 0, -12], "1.2": [-118, 0, -12]}},
            "PIERNAIZQUIERD": {"rotation": {"0.0": [-16, 0, -4], "0.6": [24, 0, -4], "1.2": [-16, 0, -4]}},
            "PIERNADERECHA": {"rotation": {"0.0": [24, 0, 4], "0.6": [-16, 0, 4], "1.2": [24, 0, 4]}},
        },
    }
    out_anims["animation.eva_unit01.fall"] = {
        "loop": True,
        "animation_length": 0.5,
        "bones": {
            "CINTURA": {"rotation": {"0.0": [6, 0, 0]}},
            "brazoizquierda": {"rotation": {"0.0": [18, 0, 30]}},
            "brazoderecho": {"rotation": {"0.0": [18, 0, -30]}},
            "PIERNAIZQUIERD": {"rotation": {"0.0": [12, 0, -7]}},
            "PIERNADERECHA": {"rotation": {"0.0": [12, 0, 7]}},
        },
    }
    # Distinct left jab and two-handed smash (their sheet only has one
    # attack animation; mapping all three to it made the buttons feel
    # identical).
    out_anims["animation.eva_unit01.melee_left"] = {
        "loop": False,
        "animation_length": 0.6,
        "bones": {
            "brazoizquierda": {"rotation": {
                "0.0": [0, 0, 0], "0.12": [38, 0, 14], "0.3": [-128, 8, -6],
                "0.45": [-96, 4, -2], "0.6": [0, 0, 0]}},
        },
    }
    out_anims["animation.eva_unit01.smash"] = {
        "loop": False,
        "animation_length": 0.8,
        "bones": {
            "brazoderecho": {"rotation": {
                "0.0": [0, 0, 0], "0.25": [-172, 0, -8], "0.45": [-38, 0, -4], "0.8": [0, 0, 0]}},
            "brazoizquierda": {"rotation": {
                "0.0": [0, 0, 0], "0.25": [-172, 0, 8], "0.45": [-38, 0, 4], "0.8": [0, 0, 0]}},
        },
    }
    out_anims["animation.eva_unit01.knife"] = {
        "loop": False,
        "animation_length": 0.7,
        "bones": {
            "pecho": {"rotation": {"0.0": [0, 0, 0], "0.16": [-5, 24, 0], "0.38": [7, -28, 0], "0.7": [0, 0, 0]}},
            "brazoderecho": {"rotation": {"0.0": [0, 0, 0], "0.16": [-122, -12, -18], "0.38": [-74, 10, 8], "0.7": [0, 0, 0]}},
        },
    }
    out_anims["animation.eva_unit01.knife_left"] = {
        "loop": False,
        "animation_length": 0.65,
        "bones": {
            "pecho": {"rotation": {"0.0": [0, 0, 0], "0.14": [-5, -28, 0], "0.32": [8, 26, 0], "0.65": [0, 0, 0]}},
            "brazoderecho": {"rotation": {"0.0": [0, 0, 0], "0.14": [-48, 34, -42], "0.32": [-116, -24, 22], "0.65": [0, 0, 0]}},
        },
    }
    out_anims["animation.eva_unit01.cannon_fire"] = {
        "loop": False,
        "animation_length": 0.55,
        "bones": {
            "pecho": {"rotation": {"0.0": [0, 0, 0], "0.06": [-8, 0, 0], "0.2": [5, 0, 0], "0.55": [0, 0, 0]}},
            "brazoderecho": {"rotation": {"0.0": [0, 0, 0], "0.06": [12, 0, 0], "0.55": [0, 0, 0]}},
            "brazoizquierda": {"rotation": {"0.0": [0, 0, 0], "0.06": [9, 0, 0], "0.55": [0, 0, 0]}},
        },
    }
    out_anims["animation.eva_unit01.land"] = {
        "loop": False,
        "animation_length": 0.46,
        "bones": {
            "todo": {"position": {"0.0": [0, 0, 0], "0.08": [0, -4, 0], "0.22": [0, 1, 0], "0.46": [0, 0, 0]}},
            "CINTURA": {"rotation": {"0.0": [0, 0, 0], "0.08": [13, 0, 0], "0.46": [0, 0, 0]}},
            "PIERNAIZQUIERD": {"rotation": {"0.0": [0, 0, 0], "0.08": [-24, 0, -3], "0.46": [0, 0, 0]}},
            "PIERNADERECHA": {"rotation": {"0.0": [0, 0, 0], "0.08": [-24, 0, 3], "0.46": [0, 0, 0]}},
        },
    }
    out_anims["animation.eva_unit01.stomp"] = {
        "loop": False,
        "animation_length": 0.72,
        "bones": {
            "todo": {"position": {"0.0": [0, 0, 0], "0.2": [0, 4, 0], "0.42": [0, -3, 0], "0.72": [0, 0, 0]}},
            "CINTURA": {"rotation": {"0.0": [0, 0, 0], "0.2": [-12, -5, 0], "0.42": [16, 4, 0], "0.72": [0, 0, 0]}},
            "PIERNADERECHA": {"rotation": {"0.0": [0, 0, 0], "0.2": [-68, 0, 4], "0.34": [-78, 0, 4], "0.42": [24, 0, 0], "0.72": [0, 0, 0]}},
            "PIERNABAJAIZQUIERDA2": {"rotation": {"0.0": [0, 0, 0], "0.2": [94, 0, 0], "0.34": [106, 0, 0], "0.42": [-12, 0, 0], "0.72": [0, 0, 0]}},
        },
    }

    # --- write the pack ---
    if OUT.exists():
        shutil.rmtree(OUT)
    geo_dir = OUT / "assets" / "projectseele" / "geo"
    anim_dir = OUT / "assets" / "projectseele" / "animations"
    tex_dir = OUT / "assets" / "projectseele" / "textures" / "entity"
    for d in (geo_dir, anim_dir, tex_dir):
        d.mkdir(parents=True, exist_ok=True)

    (OUT / "pack.mcmeta").write_text(json.dumps({
        "pack": {
            "pack_format": 15,
            "description": "EVA-01 real model (LOCAL TEST ONLY - Rei Chikita assets)",
        }
    }, indent=2), encoding="utf-8")
    (OUT / "_SOURCE.txt").write_text(
        "Model/texture/animations extracted from Rei_Chikita_Mod_1.1.7b (CurseForge),\n"
        "author DanielFernandez. License: All Rights Reserved.\n"
        "LOCAL TESTING ONLY - do not commit, do not redistribute.\n"
        "Contact the author for permission before any public use (ROADMAP section 9).\n",
        encoding="utf-8")
    (geo_dir / "eva_unit01.geo.json").write_text(json.dumps(geo), encoding="utf-8")
    (anim_dir / "eva_unit01.animation.json").write_text(
        json.dumps({"format_version": anim.get("format_version", "1.8.0"), "animations": out_anims}),
        encoding="utf-8")
    tex_path = tex_dir / "eva_unit01.png"
    tex_path.write_bytes(texture)
    repaint_weapon_regions(tex_path)
    print(f"pack written -> {OUT}")
    print("enable it in-game: Options > Resource Packs > eva_real_model")


def repaint_weapon_regions(png_path: Path):
    """Fill the grafted weapon uv regions with solid colors — the source
    sheet is transparent in its top-left corner, which made the weapons
    invisible. Uses System.Drawing through PowerShell (no PIL dependency)."""
    import subprocess
    script = (
        "Add-Type -AssemblyName System.Drawing;"
        f"$p='{png_path}';"
        "$src=[System.Drawing.Image]::FromFile($p);"
        "$bmp=New-Object System.Drawing.Bitmap($src);$src.Dispose();"
        "$g=[System.Drawing.Graphics]::FromImage($bmp);"
        "$steel=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,216,220,230));"
        "$metal=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,72,78,92));"
        "$dark=New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,40,44,54));"
        "$g.FillRectangle($steel,0,40,20,36);"          # knife box uv
        "$g.FillRectangle($metal,0,80,40,94);"          # cannon barrel box uv (along-arm)
        "$g.FillRectangle($dark,200,80,20,22);"         # scope box uv
        "$g.Dispose();"
        "$bmp.Save($p+'.tmp',[System.Drawing.Imaging.ImageFormat]::Png);$bmp.Dispose();"
        "Move-Item -Force ($p+'.tmp') $p;"
        "Write-Output 'weapon regions repainted'"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


if __name__ == "__main__":
    main()
