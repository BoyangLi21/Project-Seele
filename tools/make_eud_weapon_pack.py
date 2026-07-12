#!/usr/bin/env python3
"""Install EUD's Longinus item and graft it onto every local EVA model."""
import io
import json
import zipfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "eud-1.1.0-forge-1.20.1.jar"
OUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
ENTITY_TEXTURE_OFFSET = 448
ENTITY_SCALE = 6.0


def read_unique(archive, suffix):
    matches = [entry for entry in archive.namelist() if entry.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {suffix}, found {len(matches)}")
    return archive.read(matches[0])


def entity_cubes(model, pivot, scale=ENTITY_SCALE, texture_offset=ENTITY_TEXTURE_OFFSET):
    px, py, pz = pivot
    cubes = []
    for element in model["elements"]:
        start = element["from"]
        end = element["to"]
        # EUD's model runs from Y=-16 (grip) to Y=32 (fork tips).
        # Reverse it onto the EVA forearm's forward -Y axis.
        origin = [
            px + (start[0] - 8.0) * scale,
            py - (end[1] + 16.0) * scale,
            pz + (start[2] - 8.0) * scale,
        ]
        size = [
            (end[0] - start[0]) * scale,
            (end[1] - start[1]) * scale,
            (end[2] - start[2]) * scale,
        ]
        faces = {}
        for name, face in element.get("faces", {}).items():
            u1, v1, u2, v2 = face["uv"]
            faces[name] = {
                "uv": [texture_offset + u1, texture_offset + v1],
                "uv_size": [u2 - u1, v2 - v1],
            }
        cubes.append({"origin": origin, "size": size, "uv": faces})
    return cubes


with zipfile.ZipFile(SOURCE) as archive:
    model = json.loads(read_unique(archive, "assets/eud/models/custom/lanzadelonginusmodel.json"))
    model["textures"] = {
        "0": "projectseele:item/lance_of_longinus_local",
        "particle": "projectseele:item/lance_of_longinus_local",
    }
    texture = read_unique(archive, "assets/eud/textures/block/texturelanzadelonginus.png")

model_path = OUT / "models/item/lance_of_longinus.json"
texture_path = OUT / "textures/item/lance_of_longinus_local.png"
model_path.parent.mkdir(parents=True, exist_ok=True)
texture_path.parent.mkdir(parents=True, exist_ok=True)
model_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
texture_path.write_bytes(texture)

# The SmOd/EUD Unit models all expose the same grafted `lance` bone. Replace
# its placeholder red fork with EUD's actual 40-element model and place the
# source texture in the unused lower-right corner of each 512px atlas.
source_texture = Image.open(io.BytesIO(texture)).convert("RGBA")
for unit in ("00", "01", "02"):
    geo_path = OUT / f"geo/eva_unit{unit}.geo.json"
    eva_texture_path = OUT / f"textures/entity/eva_unit{unit}.png"
    if not geo_path.exists() or not eva_texture_path.exists():
        continue
    geometry = json.loads(geo_path.read_text(encoding="utf-8"))
    description = geometry["minecraft:geometry"][0]["description"]
    description["texture_width"] = 512
    description["texture_height"] = 512
    bones = geometry["minecraft:geometry"][0]["bones"]
    lance = next((bone for bone in bones if bone["name"] == "lance"), None)
    if lance is None:
        continue
    lance["cubes"] = entity_cubes(model, lance["pivot"])
    geo_path.write_text(json.dumps(geometry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atlas = Image.open(eva_texture_path).convert("RGBA")
    if atlas.width < 512 or atlas.height < 512:
        enlarged = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        enlarged.paste(atlas, (0, 0))
        atlas = enlarged
    atlas.paste(source_texture, (ENTITY_TEXTURE_OFFSET, ENTITY_TEXTURE_OFFSET), source_texture)
    atlas.save(eva_texture_path)

# Mass-production EVAs carry a replica spear. Their unscaled SmOd rig is
# rendered at 10x, so a 1.2x EUD model reaches the correct world length.
mp_geo_path = OUT / "geo/mass_production_eva.geo.json"
mp_texture_path = OUT / "textures/entity/mass_production_eva.png"
if mp_geo_path.exists() and mp_texture_path.exists():
    geometry = json.loads(mp_geo_path.read_text(encoding="utf-8"))
    geo = geometry["minecraft:geometry"][0]
    geo["description"]["texture_width"] = 512
    geo["description"]["texture_height"] = 512
    geo["description"]["visible_bounds_width"] = 6.0
    geo["description"]["visible_bounds_height"] = 6.0
    bones = geo["bones"]
    bones[:] = [bone for bone in bones if bone["name"] != "replica_lance"]
    forearm = next(bone for bone in bones if bone["name"] == "Lowerarm")
    bones.append({
        "name": "replica_lance",
        "parent": "Lowerarm",
        "pivot": forearm["pivot"],
        "cubes": entity_cubes(model, forearm["pivot"], scale=1.2),
    })
    mp_geo_path.write_text(json.dumps(geometry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atlas = Image.open(mp_texture_path).convert("RGBA")
    enlarged = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    enlarged.paste(atlas, (0, 0))
    enlarged.paste(source_texture, (ENTITY_TEXTURE_OFFSET, ENTITY_TEXTURE_OFFSET), source_texture)
    enlarged.save(mp_texture_path)

note = REPO / "run/resourcepacks/eva_real_model/_SOURCE.txt"
text = note.read_text(encoding="utf-8") if note.exists() else ""
line = "EUD Longinus model: local testing only; CC BY-NC 4.0 attribution required."
if line not in text:
    note.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")
print("Installed local EUD Lance of Longinus item and EVA-bone models")
