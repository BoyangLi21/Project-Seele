#!/usr/bin/env python3
"""Convert the ignored TV-style Pallet Rifle OBJ into the local EVA pack.

The source art is deliberately never copied into Git.  This converter accepts
only the exact locally reviewed 167-vertex / 292-triangle OBJ and BMP pair and
writes their runtime derivative under the ignored resource-pack directory.
Publication remains blocked until the source author/licensor approves it.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image


REPO = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO / "external-assets/work/pallet-rifle-oni/palett"
OBJ = SOURCE_ROOT / "palett.obj"
BITMAP = SOURCE_ROOT / "palett.bmp"
ASSET_ROOT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
GEO = ASSET_ROOT / "geo/eva_unit01.geo.json"
MESH = ASSET_ROOT / "mesh/eva_pallet_smg.mesh.json"
TEXTURE = ASSET_ROOT / "textures/entity/eva_pallet_smg.png"

OBJ_SHA256 = "e82f47eaaa1528208b165b50a1979b153b01cb8c8b92114abd9f371cc2d4dd6f"
BITMAP_SHA256 = "3a4c72ad452e0851767c1d764725b6b764da519454f64e83a7f3546ccd24cb58"
SOURCE_URL = "https://wiki.oni2.net/AE_talk%3ANew_weapons"
SOURCE_LABEL = (
    "TV-style Pallet Rifle local evaluation derivative; source downloaded "
    "from the Oni Anniversary Edition community; redistribution prohibited "
    "pending explicit permission"
)

# Source contract: X is side, Y is up, -Z is muzzle-forward.  Runtime weapon
# attachments point down local -Y before the Tiger aim pose rotates them into
# model-forward -Z.  The trigger/grip origin was measured from the OBJ.
SOURCE_ORIGIN = (0.0, 36.0, 18.0)
SIDE_SCALE = 0.90
BARREL_SCALE = 0.32
UP_SCALE = 0.24


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_sources() -> None:
    for path in (OBJ, BITMAP, GEO):
        if not path.is_file():
            raise FileNotFoundError(path)
    actual = (digest(OBJ), digest(BITMAP))
    expected = (OBJ_SHA256, BITMAP_SHA256)
    if actual != expected:
        raise RuntimeError(
            "Pallet Rifle source fingerprint mismatch; refusing to convert "
            f"{actual!r}"
        )


def obj_index(value: str, length: int) -> int:
    index = int(value)
    return index - 1 if index > 0 else length + index


def parse_obj() -> tuple[list, list, list, list]:
    positions: list[tuple[float, float, float]] = []
    texcoords: list[tuple[float, float]] = []
    normals: list[tuple[float, float, float]] = []
    triangles: list[tuple] = []
    for raw in OBJ.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "v":
            positions.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "vt":
            texcoords.append(tuple(float(value) for value in fields[1:3]))
        elif fields[0] == "vn":
            normals.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "f":
            refs = []
            for field in fields[1:]:
                values = field.split("/")
                refs.append((
                    obj_index(values[0], len(positions)),
                    obj_index(values[1], len(texcoords))
                    if len(values) > 1 and values[1] else -1,
                    obj_index(values[2], len(normals))
                    if len(values) > 2 and values[2] else -1,
                ))
            for index in range(1, len(refs) - 1):
                triangles.append((refs[0], refs[index], refs[index + 1]))
    if (len(positions), len(texcoords), len(normals), len(triangles)) != (
            167, 136, 167, 292):
        raise RuntimeError(
            "unexpected Pallet Rifle topology "
            f"{len(positions)}v/{len(texcoords)}vt/"
            f"{len(normals)}vn/{len(triangles)}t"
        )
    return positions, texcoords, normals, triangles


def socket_pivot() -> list[float]:
    geometry = json.loads(GEO.read_text(encoding="utf-8"))["minecraft:geometry"][0]
    socket = next((bone for bone in geometry["bones"]
                   if bone["name"] == "cannon"), None)
    if socket is None:
        raise RuntimeError("active EVA rig has no semantic cannon socket")
    return [float(value) for value in socket["pivot"]]


def face_normal(points: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    ax, ay, az = (points[1][axis] - points[0][axis] for axis in range(3))
    bx, by, bz = (points[2][axis] - points[0][axis] for axis in range(3))
    normal = (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
    length = math.sqrt(sum(value * value for value in normal)) or 1.0
    return tuple(value / length for value in normal)


def transform_position(point: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        (x - SOURCE_ORIGIN[0]) * SIDE_SCALE,
        (z - SOURCE_ORIGIN[2]) * BARREL_SCALE,
        -(y - SOURCE_ORIGIN[1]) * UP_SCALE,
    )


def transform_normal(normal: tuple[float, float, float]) -> tuple[float, float, float]:
    # Inverse-transpose for the non-uniform axis permutation above.
    nx, ny, nz = normal
    transformed = (nx / SIDE_SCALE, nz / BARREL_SCALE, -ny / UP_SCALE)
    length = math.sqrt(sum(value * value for value in transformed)) or 1.0
    return tuple(value / length for value in transformed)


def main() -> None:
    checked_sources()
    positions, texcoords, normals, triangles = parse_obj()
    values: list[float] = []
    transformed_positions = [transform_position(point) for point in positions]
    for triangle in triangles:
        fallback = face_normal([positions[ref[0]] for ref in triangle])
        for position_index, uv_index, normal_index in triangle:
            x, y, z = transformed_positions[position_index]
            u, source_v = texcoords[uv_index] if uv_index >= 0 else (0.0, 0.0)
            nx, ny, nz = transform_normal(
                normals[normal_index] if normal_index >= 0 else fallback)
            values.extend((
                round(x, 5), round(y, 5), round(z, 5),
                round(min(1.0, max(0.0, u)), 6),
                round(min(1.0, max(0.0, 1.0 - source_v)), 6),
                round(nx, 5), round(ny, 5), round(nz, 5),
            ))

    bounds = [
        [min(point[axis] for point in transformed_positions) for axis in range(3)],
        [max(point[axis] for point in transformed_positions) for axis in range(3)],
    ]
    mesh = {
        "format_version": 1,
        "source": SOURCE_LABEL,
        "source_url": SOURCE_URL,
        "source_sha256": {"obj": OBJ_SHA256, "texture": BITMAP_SHA256},
        "local_only": True,
        "release_approved": False,
        "model_height": bounds[1][1] - bounds[0][1],
        "stride": 8,
        "parts": {
            "cannon": {
                "pivot": socket_pivot(),
                "vertices": values,
            },
        },
        "triangle_count": len(triangles),
    }
    MESH.parent.mkdir(parents=True, exist_ok=True)
    MESH.write_text(json.dumps(mesh, separators=(",", ":")), encoding="utf-8")
    TEXTURE.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(BITMAP) as image:
        image.convert("RGBA").save(TEXTURE)
    print(
        "Generated local TV Pallet Rifle: "
        f"{len(triangles)} triangles / bounds "
        f"{[[round(value, 2) for value in row] for row in bounds]} / "
        "muzzle local -Y"
    )


if __name__ == "__main__":
    main()
