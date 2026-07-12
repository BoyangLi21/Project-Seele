#!/usr/bin/env python3
"""Convert the Blender-exported Kantrophe rifle into a LOCAL-ONLY weapon mesh.

This is intentionally a separate staging pack.  The converter never writes to
``run/resourcepacks/eva_real_model`` unless an explicit ``--output`` points
there after the offline previews have been accepted.
"""

import argparse
import io
import json
import math
import zipfile
from pathlib import Path

from PIL import Image, ImageChops


REPO = Path(__file__).resolve().parent.parent
ARCHIVE = REPO / "external-assets/incoming/positron-rifle-neon-genesis-evangelion.zip"
DEFAULT_OBJ = REPO / "external-assets/work/positron_rifle_export/positron_rifle.obj"
DEFAULT_OUTPUT = REPO / "external-assets/work/kantrophe_positron_pack/assets/projectseele"
SOURCE_URL = ("https://sketchfab.com/3d-models/"
              "positron-rifle-neon-genesis-evangelion-523e4d5b344543aa97b21e885f9dc064")
SOURCE_LABEL = "Kantrophe Positron Rifle (CC Attribution), local evaluation only"
TEXTURE_TILE = 1024
ATLAS_SIZE = TEXTURE_TILE * 2


def obj_index(value, length):
    index = int(value)
    return index - 1 if index > 0 else length + index


def parse_obj(path):
    positions = []
    texcoords = []
    normals = []
    triangles = []
    material = "material_default"
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "v":
            positions.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "vt":
            texcoords.append(tuple(float(value) for value in fields[1:3]))
        elif fields[0] == "vn":
            normals.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "usemtl":
            material = fields[1]
        elif fields[0] == "f":
            refs = []
            for field in fields[1:]:
                values = field.split("/")
                refs.append((obj_index(values[0], len(positions)),
                             obj_index(values[1], len(texcoords))
                             if len(values) > 1 and values[1] else -1,
                             obj_index(values[2], len(normals))
                             if len(values) > 2 and values[2] else -1))
            for index in range(1, len(refs) - 1):
                triangles.append((refs[0], refs[index], refs[index + 1], material))
    return positions, texcoords, normals, triangles


def face_normal(points):
    ax, ay, az = (points[1][axis] - points[0][axis] for axis in range(3))
    bx, by, bz = (points[2][axis] - points[0][axis] for axis in range(3))
    nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


def choose_barrel_axis(positions, requested):
    if requested != "auto":
        return "xyz".index(requested)
    spans = [max(point[axis] for point in positions) - min(point[axis] for point in positions)
             for axis in range(3)]
    return max(range(3), key=spans.__getitem__)


def transform_position(position, bounds, barrel_axis, target_length, barrel_sign,
                       grip_from_rear, vertical_offset):
    source_min = bounds[0]
    source_max = bounds[1]
    barrel_span = source_max[barrel_axis] - source_min[barrel_axis]
    scale = target_length / barrel_span
    up_axis = 2 if barrel_axis != 2 else 1
    side_axis = next(axis for axis in range(3) if axis not in (barrel_axis, up_axis))
    barrel = ((position[barrel_axis] - source_min[barrel_axis]) / barrel_span)
    if barrel_sign < 0:
        barrel = 1.0 - barrel
    # Project SEELE's cannon attachment was authored down local -Y; the aim
    # animation rotates that axis into the EVA's forward direction. Keep the
    # imported barrel on the same contract instead of local -Z, which becomes
    # vertical after the hand aims.
    model_y = (grip_from_rear - barrel) * target_length
    # Gecko/Bedrock applies the JSON -92-degree combined arm bend as an
    # approximately +92-degree socket rotation. Local -Y becomes world -Z
    # (muzzle forward), while local -Z becomes world +Y (weapon top upward).
    model_z = (-(position[up_axis] - (source_min[up_axis] + source_max[up_axis]) * 0.5)
               * scale + vertical_offset)
    model_x = ((position[side_axis] - (source_min[side_axis] + source_max[side_axis]) * 0.5)
               * scale)
    return model_x, model_y, model_z, side_axis, up_axis


def transform_normal(normal, side_axis, up_axis, barrel_axis, barrel_sign):
    barrel = normal[barrel_axis] * (-1 if barrel_sign > 0 else 1)
    return normal[side_axis], barrel, -normal[up_axis]


def build_mesh(positions, texcoords, normals, triangles, args):
    minimum = [min(point[axis] for point in positions) for axis in range(3)]
    maximum = [max(point[axis] for point in positions) for axis in range(3)]
    bounds = (minimum, maximum)
    barrel_axis = choose_barrel_axis(positions, args.barrel_axis)
    vertices = []
    material_counts = {}
    for triangle in triangles:
        points = [positions[ref[0]] for ref in triangle[:3]]
        fallback = face_normal(points)
        material = triangle[3]
        material_lower = material.lower()
        if "support" in material_lower or material_lower == "material.010":
            tile_x, tile_y = 1, 0
        elif ("visor" in material_lower or "eye" in material_lower
              or material_lower == "material.016"):
            tile_x, tile_y = 0, 1
        else:
            tile_x, tile_y = 0, 0
        if tile_x == 1 and tile_y == 0 and not args.include_supports:
            continue
        for ref in triangle[:3]:
            transformed = transform_position(positions[ref[0]], bounds, barrel_axis,
                                             args.target_length, args.barrel_sign,
                                             args.grip_from_rear, args.vertical_offset)
            model_x, model_y, model_z, side_axis, up_axis = transformed
            uv = texcoords[ref[1]] if ref[1] >= 0 else (0.0, 0.0)
            normal = normals[ref[2]] if ref[2] >= 0 else fallback
            nx, ny, nz = transform_normal(normal, side_axis, up_axis,
                                          barrel_axis, args.barrel_sign)
            # Decimation can move seam UVs a few thousandths outside the
            # authored tile. Clamp that numerical drift before atlas mapping.
            local_u = min(1.0, max(0.0, uv[0]))
            local_v = min(1.0, max(0.0, 1.0 - uv[1]))
            vertices.extend([
                round(model_x, 5), round(model_y, 5), round(model_z, 5),
                round(local_u * 0.5 + tile_x * 0.5, 6),
                round(local_v * 0.5 + tile_y * 0.5, 6),
                round(nx, 5), round(ny, 5), round(nz, 5),
            ])
        material_counts[material] = material_counts.get(material, 0) + 1
    return {
        "format_version": 1,
        "source": SOURCE_LABEL,
        "model_height": args.target_length,
        "stride": 8,
        "parts": {"cannon": {"pivot": list(args.socket_pivot), "vertices": vertices}},
    }, material_counts, barrel_axis


def archive_image(archive, suffix, mode="RGBA"):
    names = [name for name in archive.namelist() if name.lower().endswith(suffix.lower())]
    if len(names) != 1:
        raise RuntimeError(f"expected one *{suffix}, found {names}")
    return Image.open(io.BytesIO(archive.read(names[0]))).convert(mode)


def tile(image):
    return image.resize((TEXTURE_TILE, TEXTURE_TILE), Image.Resampling.LANCZOS)


def apply_alpha(colour, alpha):
    result = tile(colour)
    result.putalpha(tile(alpha.convert("L")))
    return result


def build_atlases():
    with zipfile.ZipFile(ARCHIVE) as archive:
        rifle = apply_alpha(archive_image(archive, "Rifle_BaseColor.png"),
                            archive_image(archive, "Rifle_Alpha.png"))
        supports = apply_alpha(archive_image(archive, "Supports_BaseColor.png"),
                               archive_image(archive, "Supports_Alpha.png"))
        emission = tile(archive_image(archive, "Rifle_Emission.png", "RGBA"))
        visor = tile(archive_image(archive, "VisorView.png", "RGBA"))
    colour = Image.new("RGBA", (ATLAS_SIZE, ATLAS_SIZE), (0, 0, 0, 0))
    colour.paste(rifle, (0, 0))
    colour.paste(supports, (TEXTURE_TILE, 0))
    emissive = Image.new("RGBA", colour.size, (0, 0, 0, 0))
    colour.paste(visor, (0, TEXTURE_TILE))
    emissive.paste(ImageChops.multiply(emission, rifle), (0, 0))
    emissive.paste(visor, (0, TEXTURE_TILE))
    return colour, emissive


def write_json(path, value, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False,
                      separators=(",", ":") if compact else None,
                      indent=None if compact else 2)
    path.write_text(text + ("" if compact else "\n"), encoding="utf-8")


def validate_mesh(mesh):
    stride = mesh["stride"]
    for bone, part in mesh["parts"].items():
        values = part["vertices"]
        if len(values) % (stride * 3) != 0:
            raise RuntimeError(f"incomplete triangle data in {bone}")
        for index in range(0, len(values), stride):
            if not all(math.isfinite(value) for value in values[index:index + stride]):
                raise RuntimeError(f"non-finite vertex data in {bone}")
            if not 0.0 <= values[index + 3] <= 1.0 or not 0.0 <= values[index + 4] <= 1.0:
                raise RuntimeError(f"UV outside atlas in {bone}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--obj", type=Path, default=DEFAULT_OBJ)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-length", type=float, default=128.0,
                        help="weapon length in Gecko model pixels")
    parser.add_argument("--barrel-axis", choices=("auto", "x", "y", "z"), default="auto")
    # The downloaded blend points its muzzle toward source -Y after world
    # transforms; -1 maps that muzzle down the cannon bone's local -Y axis.
    parser.add_argument("--barrel-sign", type=int, choices=(-1, 1), default=-1)
    parser.add_argument("--grip-from-rear", type=float, default=0.28)
    parser.add_argument("--vertical-offset", type=float, default=0.0)
    parser.add_argument("--socket-pivot", type=float, nargs=3,
                        default=(-24.25, 88.34, 0.875),
                        metavar=("X", "Y", "Z"),
                        help="absolute Gecko model pivot shared by the EVA cannon socket")
    parser.add_argument("--include-supports", action="store_true",
                        help="also attach the authored ground cradles/tripods")
    args = parser.parse_args()
    if not args.obj.exists():
        raise SystemExit(
            f"exported OBJ not found: {args.obj}\n"
            "Run tools/export_positron_rifle_blender.py with Blender first.")
    if not ARCHIVE.exists():
        raise SystemExit(f"source archive not found: {ARCHIVE}")
    positions, texcoords, normals, triangles = parse_obj(args.obj)
    mesh, material_counts, barrel_axis = build_mesh(
        positions, texcoords, normals, triangles, args)
    validate_mesh(mesh)
    output = args.output.resolve()
    write_json(output / "mesh/positron_cannon.mesh.json", mesh, compact=True)
    write_json(output / "geo/positron_cannon.geo.json", {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": "geometry.positron_cannon",
                "texture_width": ATLAS_SIZE,
                "texture_height": ATLAS_SIZE,
            },
            "bones": [{"name": "cannon", "pivot": [0, 0, 0]}],
        }],
    })
    colour, emissive = build_atlases()
    texture_dir = output / "textures/entity"
    texture_dir.mkdir(parents=True, exist_ok=True)
    colour.save(texture_dir / "positron_cannon.png")
    emissive.save(texture_dir / "positron_cannon_emissive.png")
    pack_root = output.parent.parent
    pack_root.mkdir(parents=True, exist_ok=True)
    pack_meta = pack_root / "pack.mcmeta"
    if not pack_meta.exists():
        write_json(pack_meta, {"pack": {
            "pack_format": 15,
            "description": "Project SEELE local external model evaluation - not for redistribution",
        }})
    source_note = pack_root / "_SOURCE.txt"
    existing = source_note.read_text(encoding="utf-8") if source_note.exists() else ""
    if SOURCE_URL not in existing:
        source_note.write_text(existing.rstrip() + "\n"
                               + f"{SOURCE_LABEL}\n{SOURCE_URL}\n"
                               + "Converted for LOCAL TESTING ONLY.\n",
                               encoding="utf-8")
    included_triangles = sum(material_counts.values())
    print(f"positron_cannon: {len(positions)} exported vertices / "
          f"{included_triangles} included triangles; "
          f"barrel axis={'xyz'[barrel_axis]}")
    print("materials: " + ", ".join(
        f"{name}={count}" for name, count in sorted(material_counts.items())))
    print(f"staged weapon pack -> {output}")


if __name__ == "__main__":
    main()
