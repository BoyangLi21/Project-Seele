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
ENTITY_TEXTURE_OFFSET = (448, 448)
ENTITY_SCALE = 6.0
BLOCK_TEXTURE_UV_SCALE = 4.0


def read_unique(archive, suffix):
    matches = [entry for entry in archive.namelist() if entry.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {suffix}, found {len(matches)}")
    return archive.read(matches[0])


def entity_cubes(model, pivot, scale=ENTITY_SCALE, texture_offset=ENTITY_TEXTURE_OFFSET,
                 texture_uv_scale=BLOCK_TEXTURE_UV_SCALE):
    px, py, pz = pivot
    texture_x, texture_y = texture_offset
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
                "uv": [texture_x + u1 * texture_uv_scale,
                       texture_y + v1 * texture_uv_scale],
                "uv_size": [(u2 - u1) * texture_uv_scale,
                            (v2 - v1) * texture_uv_scale],
            }
        cubes.append({"origin": origin, "size": size, "uv": faces})
    return cubes


def remap_mesh_u(mesh_path, old_width, new_width):
    mesh = json.loads(mesh_path.read_text(encoding="utf-8"))
    stride = mesh.get("stride")
    if stride != 8:
        raise RuntimeError(f"unsupported mesh stride in {mesh_path}")
    factor = old_width / new_width
    for part in mesh.get("parts", {}).values():
        values = part.get("vertices", [])
        for index in range(3, len(values), stride):
            values[index] = round(values[index] * factor, 8)
    mesh_path.write_text(json.dumps(mesh, separators=(",", ":")), encoding="utf-8")


def install_texture(atlas, source, mesh_path):
    """Place the used lance pixels without resizing or overwriting EVA art."""
    used = source.getchannel("A").getbbox()
    if used is None:
        raise RuntimeError("EUD lance texture is fully transparent")
    if used[0] != 0 or used[1] != 0:
        raise RuntimeError(f"unsupported non-zero EUD texture origin {used}")
    tile = source.crop(used)
    width, height = tile.size
    alpha = atlas.getchannel("A")
    # Search backwards so the attachment stays away from the source model's
    # conventional upper-left UV area. Eight-pixel alignment keeps authored
    # cube UVs integral while making the scan inexpensive and deterministic.
    for step in (8, 1):
        for y in range(atlas.height - height, -1, -step):
            for x in range(atlas.width - width, -1, -step):
                if alpha.crop((x, y, x + width, y + height)).getbbox() is None:
                    atlas.paste(tile, (x, y), tile)
                    return atlas, (x, y)
    # Some authored atlases are fully opaque. Add a narrow attachment column
    # and renormalise only the local triangle mesh U values; Gecko cube UVs
    # are pixel coordinates and remain valid when the declared width changes.
    old_width = atlas.width
    new_width = old_width + 64
    expanded = Image.new("RGBA", (new_width, atlas.height), (0, 0, 0, 0))
    expanded.paste(atlas, (0, 0))
    expanded.paste(tile, (old_width, 0), tile)
    remap_mesh_u(mesh_path, old_width, new_width)
    return expanded, (old_width, 0)


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
# source texture in a verified transparent region of each existing atlas.
source_texture = Image.open(io.BytesIO(texture)).convert("RGBA")
for unit in ("00", "01", "02"):
    geo_path = OUT / f"geo/eva_unit{unit}.geo.json"
    eva_texture_path = OUT / f"textures/entity/eva_unit{unit}.png"
    mesh_path = OUT / f"mesh/eva_unit{unit}.mesh.json"
    if not geo_path.exists() or not eva_texture_path.exists() or not mesh_path.exists():
        continue
    atlas = Image.open(eva_texture_path).convert("RGBA")
    atlas, texture_offset = install_texture(atlas, source_texture, mesh_path)
    geometry = json.loads(geo_path.read_text(encoding="utf-8"))
    description = geometry["minecraft:geometry"][0]["description"]
    description["texture_width"] = atlas.width
    description["texture_height"] = atlas.height
    bones = geometry["minecraft:geometry"][0]["bones"]
    lance = next((bone for bone in bones if bone["name"] == "lance"), None)
    if lance is None:
        continue
    lance["cubes"] = entity_cubes(model, lance["pivot"],
                                  texture_offset=texture_offset)
    geo_path.write_text(json.dumps(geometry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atlas.save(eva_texture_path)

# Mass-production EVAs carry a replica spear. Their unscaled SmOd rig is
# rendered at 10x, so a 1.2x EUD model reaches the correct world length.
mp_geo_path = OUT / "geo/mass_production_eva.geo.json"
mp_texture_path = OUT / "textures/entity/mass_production_eva.png"
mp_mesh_path = OUT / "mesh/mass_production_eva.mesh.json"
if mp_geo_path.exists() and mp_texture_path.exists() and mp_mesh_path.exists():
    geometry = json.loads(mp_geo_path.read_text(encoding="utf-8"))
    geo = geometry["minecraft:geometry"][0]
    atlas = Image.open(mp_texture_path).convert("RGBA")
    atlas, texture_offset = install_texture(atlas, source_texture, mp_mesh_path)
    geo["description"]["texture_width"] = atlas.width
    geo["description"]["texture_height"] = atlas.height
    geo["description"]["visible_bounds_width"] = 6.0
    geo["description"]["visible_bounds_height"] = 6.0
    bones = geo["bones"]
    bones[:] = [bone for bone in bones if bone["name"] != "replica_lance"]
    forearm = next((bone for bone in bones
                    if bone["name"] in ("forearm_r", "Lowerarm")), None)
    if forearm is None:
        raise RuntimeError("Mass Production EVA rig has no right forearm weapon socket")
    bones.append({
        "name": "replica_lance",
        "parent": forearm["name"],
        "pivot": forearm["pivot"],
        "cubes": entity_cubes(model, forearm["pivot"], scale=1.2,
                              texture_offset=texture_offset),
    })
    mp_geo_path.write_text(json.dumps(geometry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atlas.save(mp_texture_path)

note = REPO / "run/resourcepacks/eva_real_model/_SOURCE.txt"
text = note.read_text(encoding="utf-8") if note.exists() else ""
line = "EUD Longinus model: local testing only; CC BY-NC 4.0 attribution required."
if line not in text:
    note.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")
print("Installed local EUD Lance of Longinus item and EVA-bone models")
