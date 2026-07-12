#!/usr/bin/env python3
"""Render deterministic textured OBJ turntable previews without a game client."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image


def load_obj(path):
    vertices = []
    texcoords = []
    faces = []
    face_uvs = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "v":
            vertices.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "vt":
            texcoords.append(tuple(float(value) for value in fields[1:3]))
        elif fields[0] == "f":
            refs = [field.split("/") for field in fields[1:]]
            indices = [int(ref[0]) - 1 for ref in refs]
            uv_indices = [int(ref[1]) - 1 if len(ref) > 1 and ref[1] else -1 for ref in refs]
            # Fan triangulation keeps this utility useful for quad OBJ files.
            for index in range(1, len(indices) - 1):
                faces.append((indices[0], indices[index], indices[index + 1]))
                face_uvs.append((uv_indices[0], uv_indices[index], uv_indices[index + 1]))
    return vertices, texcoords, faces, face_uvs


def sample_colours(texture, texcoords, face_uvs):
    image = Image.open(texture).convert("RGB")
    pixels = image.load()
    width, height = image.size
    colours = []
    for refs in face_uvs:
        valid = [texcoords[index] for index in refs if index >= 0]
        if not valid:
            colours.append((0.55, 0.55, 0.58, 1.0))
            continue
        u = sum(value[0] for value in valid) / len(valid)
        v = sum(value[1] for value in valid) / len(valid)
        red, green, blue = pixels[min(width - 1, max(0, int(u * width))),
                                  min(height - 1, max(0, int((1.0 - v) * height)))]
        colours.append((red / 255.0, green / 255.0, blue / 255.0, 1.0))
    return colours


def project(vertex, view):
    x, y, z = vertex
    if view == "front":
        return x, y, z
    if view == "back":
        return -x, y, -z
    if view == "left":
        return z, y, -x
    if view == "right":
        return -z, y, x
    raise ValueError(view)


def render(vertices, faces, colours, view, target):
    projected = [project(vertex, view) for vertex in vertices]
    ordered = sorted(range(len(faces)),
                     key=lambda index: sum(projected[v][2] for v in faces[index]) / 3.0)
    polygons = [[projected[vertex][:2] for vertex in faces[index]] for index in ordered]
    face_colours = [colours[index] for index in ordered]
    xs = [value[0] for value in projected]
    ys = [value[1] for value in projected]
    centre_x = (min(xs) + max(xs)) / 2.0
    centre_y = (min(ys) + max(ys)) / 2.0
    span = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.08

    figure, axis = plt.subplots(figsize=(8, 8), dpi=160)
    figure.patch.set_facecolor("#20232a")
    axis.set_facecolor("#20232a")
    axis.add_collection(PolyCollection(polygons, facecolors=face_colours,
                                       edgecolors=(0.04, 0.04, 0.06, 0.30), linewidths=0.16))
    axis.set_xlim(centre_x - span / 2.0, centre_x + span / 2.0)
    axis.set_ylim(centre_y - span / 2.0, centre_y + span / 2.0)
    axis.set_aspect("equal")
    axis.axis("off")
    axis.text(0.02, 0.98, f"UNIT-01 SOURCE / {view.upper()}", color="#f0a000",
              fontsize=12, ha="left", va="top", transform=axis.transAxes)
    figure.savefig(target, bbox_inches="tight", pad_inches=0.08, facecolor=figure.get_facecolor())
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("obj", type=Path)
    parser.add_argument("texture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    vertices, texcoords, faces, face_uvs = load_obj(args.obj)
    colours = sample_colours(args.texture, texcoords, face_uvs)
    for view in ("front", "left", "back", "right"):
        render(vertices, faces, colours, view, args.output / f"unit01_source_{view}.png")
    print(f"rendered {len(faces)} triangles -> {args.output}")


if __name__ == "__main__":
    main()
