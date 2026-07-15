#!/usr/bin/env python3
"""Build Project SEELE's original low-poly EVA pallet SMG attachment.

The model is intentionally generated from simple mechanical volumes and does
not reproduce a downloaded or official mesh. It lives in the local high-detail
pack because it must share the converted EVA's final cannon socket pivot.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


REPO = Path(__file__).resolve().parent.parent
ASSET_ROOT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
GEO = ASSET_ROOT / "geo/eva_unit01.geo.json"
MESH = ASSET_ROOT / "mesh/eva_pallet_smg.mesh.json"
TEXTURE = ASSET_ROOT / "textures/entity/eva_pallet_smg.png"

COLOURS = (
    (20, 24, 29, 255),       # graphite
    (52, 61, 68, 255),       # gunmetal
    (104, 116, 119, 255),    # machined edge
    (214, 78, 24, 255),      # NERV orange
    (238, 172, 30, 255),     # warning stripe
    (49, 184, 176, 255),     # optical cyan
    (49, 70, 47, 255),       # military green
    (7, 8, 10, 255),         # recess
)


def socket_pivot() -> list[float]:
    if not GEO.exists():
        raise FileNotFoundError(f"generate the Tiger EVA pack first: {GEO}")
    geometry = json.loads(GEO.read_text(encoding="utf-8"))["minecraft:geometry"][0]
    cannon = next((bone for bone in geometry["bones"] if bone["name"] == "cannon"), None)
    if cannon is None:
        raise RuntimeError("active EVA rig has no semantic cannon socket")
    return [float(value) for value in cannon["pivot"]]


def add_vertex(values: list[float], point: tuple[float, float, float],
               normal: tuple[float, float, float], material: int) -> None:
    u = (material + 0.5) / len(COLOURS)
    values.extend((round(point[0], 4), round(point[1], 4), round(point[2], 4),
                   round(u, 6), 0.5, normal[0], normal[1], normal[2]))


def add_quad(values: list[float], a, b, c, d, normal, material: int) -> None:
    for point in (a, b, c, a, c, d):
        add_vertex(values, point, normal, material)


def add_box(values: list[float], bounds, material: int) -> None:
    x0, x1, y0, y1, z0, z1 = bounds
    add_quad(values, (x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1),
             (-1.0, 0.0, 0.0), material)
    add_quad(values, (x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (x1, y0, z0),
             (1.0, 0.0, 0.0), material)
    add_quad(values, (x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0),
             (0.0, -1.0, 0.0), material)
    add_quad(values, (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1),
             (0.0, 1.0, 0.0), material)
    add_quad(values, (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (0.0, 0.0, -1.0), material)
    add_quad(values, (x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1),
             (0.0, 0.0, 1.0), material)


def main() -> None:
    pivot = socket_pivot()
    values: list[float] = []
    volumes = (
        ((-6.2, 6.2, -31.0, 6.0, -5.2, 5.2), 1),
        ((-7.1, 7.1, -34.0, -9.0, -4.3, 4.3), 0),
        ((-2.1, 2.1, -69.0, -30.0, -2.1, 2.1), 2),
        ((-3.5, 3.5, -49.0, -32.0, -3.2, 3.2), 0),
        ((-4.0, 4.0, -76.0, -68.0, -4.0, 4.0), 7),
        ((-6.4, -3.8, -75.0, -65.0, -2.0, 2.0), 2),
        ((3.8, 6.4, -75.0, -65.0, -2.0, 2.0), 2),
        ((-5.0, 5.0, 5.5, 22.0, -4.0, 4.0), 6),
        ((-7.0, 7.0, 18.0, 25.0, -6.0, 6.0), 0),
        ((-3.0, 3.0, -1.0, 10.0, 4.5, 15.0), 7),
        ((-4.1, 4.1, -17.0, 1.0, 5.0, 18.0), 1),
        ((-7.5, -5.4, -34.0, -9.0, -5.0, 5.0), 6),
        ((5.4, 7.5, -34.0, -9.0, -5.0, 5.0), 6),
        ((-3.0, 3.0, -18.0, -3.0, -10.5, -5.4), 7),
        ((-2.3, 2.3, -15.5, -5.0, -14.0, -10.0), 5),
        ((-1.0, 1.0, -58.0, -53.0, -7.5, -2.2), 4),
        ((-6.5, 6.5, -28.0, -25.0, -5.5, 5.5), 3),
        ((-5.7, 5.7, -8.0, -5.0, -5.7, 5.7), 4),
        ((-2.7, 2.7, -42.0, -15.0, 3.2, 6.2), 1),
        ((-1.4, 1.4, -64.0, -48.0, -3.6, -2.2), 3),
    )
    for bounds, material in volumes:
        add_box(values, bounds, material)

    triangles = len(values) // (8 * 3)
    mesh = {
        "format_version": 1,
        "source": "Project SEELE original procedural EVA pallet SMG (MIT project asset)",
        "model_height": 190.0,
        "stride": 8,
        "parts": {"cannon": {"pivot": pivot, "vertices": values}},
        "triangle_count": triangles,
    }
    MESH.parent.mkdir(parents=True, exist_ok=True)
    MESH.write_text(json.dumps(mesh, separators=(",", ":")), encoding="utf-8")

    TEXTURE.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (16 * len(COLOURS), 16), (0, 0, 0, 0))
    for index, colour in enumerate(COLOURS):
        tile = Image.new("RGBA", (16, 16), colour)
        image.paste(tile, (index * 16, 0))
    image.save(TEXTURE)
    print(f"Generated original EVA pallet SMG: {triangles} triangles / pivot {pivot}")


if __name__ == "__main__":
    main()
