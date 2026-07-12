#!/usr/bin/env python3
"""Render any generated Tiger rigid-bone mesh without launching Minecraft."""

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image


STRESS_ROTATION = {
    "torso_lower": (0, 0, -3), "torso_upper": (0, 0, 6),
    "head": (0, 12, -3),
    "arm_l": (0, 0, -58), "forearm_l": (-20, 0, -18), "hand_l": (0, 0, 8),
    "arm_r": (0, 0, 58), "forearm_r": (-20, 0, 18), "hand_r": (0, 0, -8),
    "leg_l": (0, 0, -8), "shin_l": (8, 0, 4),
    "leg_r": (0, 0, 8), "shin_r": (8, 0, -4),
    "wing_l": (0, -9, -3), "wing_r": (0, 9, 3),
}

RITUAL_ROTATION = {
    "torso_upper": (3, 0, 0), "head": (15, 0, 0),
    "arm_l": (0, 0, 86), "forearm_l": (0, 0, 0),
    "arm_r": (0, 0, -86), "forearm_r": (0, 0, 0),
    "leg_l": (0, 0, -2), "leg_r": (0, 0, 2),
    "wing_l": (0, 0, -2), "wing_r": (0, 0, 2),
}

# Gecko's Bedrock animation conversion applies the EVA JSON -92-degree arm
# bend as approximately +92 degrees in rendered socket space.
AIM_SOCKET_ROTATION = {"cannon": (92, 0, 0)}


def identity():
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def multiply(left, right):
    return [[sum(left[row][index] * right[index][column] for index in range(4))
             for column in range(4)] for row in range(4)]


def translation(x, y, z):
    matrix = identity()
    matrix[0][3], matrix[1][3], matrix[2][3] = x, y, z
    return matrix


def rotation(values):
    x, y, z = (math.radians(value) for value in values)
    rx = [[1, 0, 0, 0], [0, math.cos(x), -math.sin(x), 0],
          [0, math.sin(x), math.cos(x), 0], [0, 0, 0, 1]]
    ry = [[math.cos(y), 0, math.sin(y), 0], [0, 1, 0, 0],
          [-math.sin(y), 0, math.cos(y), 0], [0, 0, 0, 1]]
    rz = [[math.cos(z), -math.sin(z), 0, 0], [math.sin(z), math.cos(z), 0, 0],
          [0, 0, 1, 0], [0, 0, 0, 1]]
    return multiply(rz, multiply(ry, rx))


def transform(matrix, point):
    vector = [point[0], point[1], point[2], 1.0]
    return [sum(matrix[row][index] * vector[index] for index in range(4))
            for row in range(3)]


def bone_matrix(bone, pivots, parents, cache, rotations):
    if bone in cache:
        return cache[bone]
    parent = parents.get(bone)
    if parent is None or parent == "root":
        parent_matrix = identity()
        parent_pivot = [0, 0, 0]
    else:
        parent_matrix = bone_matrix(parent, pivots, parents, cache, rotations)
        parent_pivot = pivots[parent]
    pivot = pivots[bone]
    offset = [pivot[index] - parent_pivot[index] for index in range(3)]
    cache[bone] = multiply(parent_matrix, multiply(
        translation(*offset), rotation(rotations.get(bone, (0, 0, 0)))))
    return cache[bone]


def project(point, view):
    x, y, z = point
    return {"front": (-x, y, -z), "left": (z, y, -x),
            "back": (x, y, z), "right": (-z, y, x)}[view]


def render(mesh, texture_path, parents, view, output, pose, label, show_origin):
    texture = Image.open(texture_path).convert("RGB")
    pixels = texture.load()
    width, height = texture.size
    pivots = {bone: part["pivot"] for bone, part in mesh["parts"].items()}
    cache = {}
    rotations = STRESS_ROTATION if pose == "stress" else (
        RITUAL_ROTATION if pose == "ritual" else (
            AIM_SOCKET_ROTATION if pose == "aim_socket" else {}))
    triangles = []
    for bone, part in mesh["parts"].items():
        matrix = bone_matrix(bone, pivots, parents, cache, rotations)
        values = part["vertices"]
        stride = mesh["stride"]
        for start in range(0, len(values), stride * 3):
            points = []
            uvs = []
            for vertex in range(3):
                index = start + vertex * stride
                points.append(transform(matrix, values[index:index + 3]))
                uvs.append(values[index + 3:index + 5])
            projected = [project(point, view) for point in points]
            u = sum(value[0] for value in uvs) / 3.0
            v = sum(value[1] for value in uvs) / 3.0
            colour = pixels[min(width - 1, max(0, int(u * width))),
                            min(height - 1, max(0, int(v * height)))]
            triangles.append((sum(point[2] for point in projected) / 3.0,
                              [point[:2] for point in projected],
                              tuple(channel / 255.0 for channel in colour) + (1.0,)))
    triangles.sort(key=lambda item: item[0])
    xs = [point[0] for _, polygon, _ in triangles for point in polygon]
    ys = [point[1] for _, polygon, _ in triangles for point in polygon]
    centre_x, centre_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.08
    figure, axis = plt.subplots(figsize=(8, 8), dpi=160)
    figure.patch.set_facecolor("#20232a")
    axis.set_facecolor("#20232a")
    axis.add_collection(PolyCollection([item[1] for item in triangles],
                                       facecolors=[item[2] for item in triangles],
                                       edgecolors=(0.04, 0.04, 0.06, 0.32), linewidths=0.16))
    axis.set_xlim(centre_x - span / 2, centre_x + span / 2)
    axis.set_ylim(centre_y - span / 2, centre_y + span / 2)
    axis.set_aspect("equal")
    axis.axis("off")
    if show_origin:
        axis.scatter([0], [0], marker="+", s=90, linewidths=1.4,
                     color="#ff9f00", zorder=20)
    axis.text(0.02, 0.98, f"{label.upper()} RIG {pose.upper()} / {view.upper()}",
              color="#f0a000", fontsize=12, ha="left", va="top",
              transform=axis.transAxes)
    figure.savefig(output, bbox_inches="tight", pad_inches=0.08,
                   facecolor=figure.get_facecolor())
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mesh", type=Path)
    parser.add_argument("texture", type=Path)
    parser.add_argument("geometry", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pose", choices=("identity", "stress", "ritual", "aim_socket"),
                        default="stress")
    parser.add_argument("--label")
    parser.add_argument("--show-origin", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    mesh = json.loads(args.mesh.read_text(encoding="utf-8"))
    geometry = json.loads(args.geometry.read_text(encoding="utf-8"))["minecraft:geometry"][0]
    parents = {bone["name"]: bone.get("parent") for bone in geometry["bones"]}
    label = args.label or args.mesh.stem.replace(".mesh", "")
    for view in ("front", "left", "back", "right"):
        render(mesh, args.texture, parents, view,
               args.output / f"{label}_rig_{args.pose}_{view}.png", args.pose, label,
               args.show_origin)
    print(f"rendered {label} {args.pose} rig preview -> {args.output}")


if __name__ == "__main__":
    main()
