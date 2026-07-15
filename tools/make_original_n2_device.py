#!/usr/bin/env python3
"""Build Project SEELE's original hand-carried N2 self-destruction device."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw


REPO = Path(__file__).resolve().parent.parent
ASSET_ROOT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
GEO = ASSET_ROOT / "geo/eva_unit01.geo.json"
MESH = ASSET_ROOT / "mesh/eva_n2_device.mesh.json"
TEXTURE = ASSET_ROOT / "textures/entity/eva_n2_device.png"

COLOURS = (
    (43, 49, 55, 255),       # graphite shell, readable against EVA armour
    (51, 59, 66, 255),       # gunmetal
    (105, 115, 119, 255),    # machined edge
    (206, 55, 35, 255),      # armed red
    (239, 166, 26, 255),     # NERV orange
    (241, 211, 64, 255),     # hazard yellow
    (27, 34, 39, 255),       # recess
    (55, 220, 190, 255),     # status cyan
    (225, 232, 224, 255),    # stencil
)


def socket_pivot() -> list[float]:
    geometry = json.loads(GEO.read_text(encoding="utf-8"))["minecraft:geometry"][0]
    bone = next((item for item in geometry["bones"] if item["name"] == "n2"), None)
    if bone is None:
        raise RuntimeError("active EVA rig has no semantic n2 socket")
    return [float(value) for value in bone["pivot"]]


def add_vertex(values, point, normal, material):
    u = (material + 0.5) / len(COLOURS)
    values.extend((
        round(point[0], 4), round(point[1], 4), round(point[2], 4),
        round(u, 6), 0.5,
        round(normal[0], 4), round(normal[1], 4), round(normal[2], 4),
    ))


def add_triangle(values, a, b, c, normal, material):
    for point in (a, b, c):
        add_vertex(values, point, normal, material)


def add_quad(values, a, b, c, d, normal, material):
    add_triangle(values, a, b, c, normal, material)
    add_triangle(values, a, c, d, normal, material)


def add_box(values, bounds, material):
    x0, x1, y0, y1, z0, z1 = bounds
    add_quad(values, (x0, y0, z0), (x0, y1, z0), (x0, y1, z1),
             (x0, y0, z1), (-1, 0, 0), material)
    add_quad(values, (x1, y0, z1), (x1, y1, z1), (x1, y1, z0),
             (x1, y0, z0), (1, 0, 0), material)
    add_quad(values, (x0, y0, z1), (x1, y0, z1), (x1, y0, z0),
             (x0, y0, z0), (0, -1, 0), material)
    add_quad(values, (x0, y1, z0), (x1, y1, z0), (x1, y1, z1),
             (x0, y1, z1), (0, 1, 0), material)
    add_quad(values, (x0, y0, z0), (x1, y0, z0), (x1, y1, z0),
             (x0, y1, z0), (0, 0, -1), material)
    add_quad(values, (x0, y0, z1), (x0, y1, z1), (x1, y1, z1),
             (x1, y0, z1), (0, 0, 1), material)


def add_prism_y(values, y0, y1, radius_x, radius_z, material, segments=10):
    ring0 = []
    ring1 = []
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        point = (math.cos(angle) * radius_x, math.sin(angle) * radius_z)
        ring0.append((point[0], y0, point[1]))
        ring1.append((point[0], y1, point[1]))
    for index in range(segments):
        nxt = (index + 1) % segments
        angle = 2.0 * math.pi * (index + 0.5) / segments
        normal = (math.cos(angle), 0.0, math.sin(angle))
        add_quad(values, ring0[index], ring1[index], ring1[nxt], ring0[nxt],
                 normal, material)
        add_triangle(values, (0, y0, 0), ring0[nxt], ring0[index],
                     (0, -1, 0), material)
        add_triangle(values, (0, y1, 0), ring1[index], ring1[nxt],
                     (0, 1, 0), material)


def main() -> None:
    pivot = socket_pivot()
    values: list[float] = []

    # Armoured N2 charge body and raised end caps.
    add_prism_y(values, -15.0, 5.0, 5.3, 4.6, 0)
    add_prism_y(values, -16.3, -14.4, 4.7, 4.0, 2)
    add_prism_y(values, 4.4, 6.2, 4.7, 4.0, 2)
    # Two hazard locking bands read clearly even at EVA viewing distance.
    add_prism_y(values, -10.8, -8.7, 5.55, 4.85, 5)
    add_prism_y(values, -1.7, 0.4, 5.55, 4.85, 4)

    # Protected carry handle and mechanical hinge blocks.
    add_box(values, (-4.3, -2.5, 5.3, 11.6, -1.8, 1.8), 1)
    add_box(values, (2.5, 4.3, 5.3, 11.6, -1.8, 1.8), 1)
    add_box(values, (-4.3, 4.3, 10.1, 12.3, -1.8, 1.8), 2)
    add_box(values, (-5.0, -2.0, 4.2, 7.1, -2.4, 2.4), 6)
    add_box(values, (2.0, 5.0, 4.2, 7.1, -2.4, 2.4), 6)

    # Front arming panel, guarded red commit switch and status lamp.
    add_box(values, (-3.7, 3.7, -7.2, 3.4, -5.7, -4.45), 1)
    add_box(values, (-2.8, 2.8, -5.9, -1.2, -6.2, -5.65), 3)
    add_box(values, (-1.6, 1.6, 0.0, 2.0, -6.3, -5.6), 7)
    add_box(values, (-4.4, -3.5, -6.1, 2.5, -6.0, -5.45), 5)
    add_box(values, (3.5, 4.4, -6.1, 2.5, -6.0, -5.45), 5)
    # Rear stabiliser spine and twin cable housings.
    add_box(values, (-1.2, 1.2, -13.4, 3.8, 4.3, 5.45), 2)
    add_box(values, (-4.5, -2.8, -13.0, -3.0, 3.8, 5.1), 6)
    add_box(values, (2.8, 4.5, -13.0, -3.0, 3.8, 5.1), 6)

    # The first prototype was technically present but disappeared between
    # Unit-01's articulated palms at gameplay distance. Scale around the
    # semantic hand socket: it remains a carried charge, while its hazard
    # bands and arming panel now read from both first and third person.
    device_scale = 1.80
    for index in range(0, len(values), 8):
        values[index] = round(values[index] * device_scale, 4)
        values[index + 1] = round(values[index + 1] * device_scale, 4)
        values[index + 2] = round(values[index + 2] * device_scale, 4)

    mesh = {
        "format_version": 1,
        "source": "Project SEELE original EVA-carried N2 self-destruction device",
        "model_height": 190.0,
        "stride": 8,
        "parts": {"n2": {"pivot": pivot, "vertices": values}},
        "triangle_count": len(values) // 24,
    }
    MESH.parent.mkdir(parents=True, exist_ok=True)
    MESH.write_text(json.dumps(mesh, separators=(",", ":")), encoding="utf-8")

    texture = Image.new("RGBA", (32 * len(COLOURS), 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(texture)
    for index, colour in enumerate(COLOURS):
        draw.rectangle((index * 32, 0, index * 32 + 31, 31), fill=colour)
    # The label is documentary rather than a copied franchise texture.
    draw.text((8 * 32 + 6, 9), "N2", fill=(25, 25, 25, 255))
    TEXTURE.parent.mkdir(parents=True, exist_ok=True)
    texture.save(TEXTURE)
    print(f"Generated EVA-carried N2 device: {mesh['triangle_count']} triangles / pivot {pivot}")


if __name__ == "__main__":
    main()
