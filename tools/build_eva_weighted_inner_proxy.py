#!/usr/bin/env python3
"""Build a project-owned weighted Unit-01 inner-joint proxy."""

from __future__ import annotations

import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RIG = REPO / "src/main/resources/assets/projectseele/eva/eva_rig_schema.json"
OUTPUT = REPO / (
    "src/main/resources/assets/projectseele/eva/"
    "eva_unit01_inner_proxy.skinned.json")
SIDES = 8
RING_WEIGHTS = (0.0, 0.5, 1.0)
STRIDE = 16

SEGMENTS = (
    ("root", "torso_lower", 0.90, 1.00),
    ("torso_lower", "torso_upper", 1.10, 0.95),
    ("torso_upper", "neck", 0.70, 0.35),
    ("clavicle_l", "arm_l", 0.58, 0.55),
    ("arm_l", "forearm_l", 0.52, 0.42),
    ("forearm_l", "wrist_l", 0.42, 0.28),
    ("clavicle_r", "arm_r", 0.58, 0.55),
    ("arm_r", "forearm_r", 0.52, 0.42),
    ("forearm_r", "wrist_r", 0.42, 0.28),
    ("torso_lower", "leg_l", 0.82, 0.74),
    ("leg_l", "shin_l", 0.76, 0.56),
    ("shin_l", "ankle_l", 0.56, 0.34),
    ("torso_lower", "leg_r", 0.82, 0.74),
    ("leg_r", "shin_r", 0.76, 0.56),
    ("shin_r", "ankle_r", 0.56, 0.34),
)


def add(a: tuple[float, float, float],
        b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[index] + b[index] for index in range(3))


def subtract(a: tuple[float, float, float],
             b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[index] - b[index] for index in range(3))


def scale(value: tuple[float, float, float], amount: float
          ) -> tuple[float, float, float]:
    return tuple(component * amount for component in value)


def dot(a: tuple[float, float, float],
        b: tuple[float, float, float]) -> float:
    return sum(a[index] * b[index] for index in range(3))


def cross(a: tuple[float, float, float],
          b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def normalize(value: tuple[float, float, float]
              ) -> tuple[float, float, float]:
    length = math.sqrt(dot(value, value))
    if length <= 1.0e-9:
        raise RuntimeError("zero-length proxy segment")
    return scale(value, 1.0 / length)


def model_position(pivot: list[float]) -> tuple[float, float, float]:
    return (-float(pivot[0]) / 16.0,
            float(pivot[1]) / 16.0,
            float(pivot[2]) / 16.0)


def inverse_translation(position: tuple[float, float, float]) -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        -position[0], -position[1], -position[2], 1.0,
    ]


def vertex(values: list[float], position: tuple[float, float, float],
           uv: tuple[float, float], normal: tuple[float, float, float],
           parent: int, child: int, child_weight: float) -> int:
    index = len(values) // STRIDE
    values.extend([
        *position, *uv, *normal,
        parent, child, 0, 0,
        round(1.0 - child_weight, 6), round(child_weight, 6), 0.0, 0.0,
    ])
    return index


def add_tube(values: list[float], indices: list[int], parent: int,
             child: int, start: tuple[float, float, float],
             end: tuple[float, float, float], start_radius: float,
             end_radius: float) -> dict:
    axis = normalize(subtract(end, start))
    reference = (0.0, 0.0, 1.0)
    if abs(dot(axis, reference)) > 0.92:
        reference = (1.0, 0.0, 0.0)
    tangent = normalize(cross(axis, reference))
    bitangent = normalize(cross(axis, tangent))
    rings: list[list[int]] = []
    for ring_index, child_weight in enumerate(RING_WEIGHTS):
        centre = add(start, scale(subtract(end, start), child_weight))
        radius = start_radius + (end_radius - start_radius) * child_weight
        ring = []
        for side in range(SIDES):
            angle = 2.0 * math.pi * side / SIDES
            normal = add(scale(tangent, math.cos(angle)),
                         scale(bitangent, math.sin(angle)))
            ring.append(vertex(
                values, add(centre, scale(normal, radius)),
                (side / SIDES, ring_index / (len(RING_WEIGHTS) - 1)),
                normal, parent, child, child_weight))
        rings.append(ring)
    for ring_index in range(len(rings) - 1):
        before = rings[ring_index]
        after = rings[ring_index + 1]
        for side in range(SIDES):
            next_side = (side + 1) % SIDES
            indices.extend((before[side], after[side], before[next_side],
                            before[next_side], after[side], after[next_side]))
    start_centre = vertex(values, start, (0.5, 0.0), scale(axis, -1.0),
                          parent, child, 0.0)
    end_centre = vertex(values, end, (0.5, 1.0), axis,
                        parent, child, 1.0)
    for side in range(SIDES):
        next_side = (side + 1) % SIDES
        indices.extend((start_centre, rings[0][next_side], rings[0][side]))
        indices.extend((end_centre, rings[-1][side], rings[-1][next_side]))
    return {
        "startVertex": rings[0][0],
        "vertexCount": len(RING_WEIGHTS) * SIDES + 2,
        "triangleCount": (len(RING_WEIGHTS) - 1) * SIDES * 2
                         + SIDES * 2,
    }


def main() -> None:
    rig = json.loads(RIG.read_text(encoding="utf-8"))
    bones = {bone["name"]: bone for bone in rig["bones"]}
    palette = []
    for parent, child, _, _ in SEGMENTS:
        for name in (parent, child):
            if name not in palette:
                palette.append(name)
    palette_index = {name: index for index, name in enumerate(palette)}
    positions = {
        name: model_position(bones[name]["pivot"])
        for name in palette
    }
    values: list[float] = []
    indices: list[int] = []
    segment_manifest = []
    for parent, child, start_radius, end_radius in SEGMENTS:
        segment = add_tube(
            values, indices, palette_index[parent], palette_index[child],
            positions[parent], positions[child], start_radius, end_radius)
        segment_manifest.append({
            "parent": parent,
            "child": child,
            "startRadiusBlocks": start_radius,
            "endRadiusBlocks": end_radius,
            **segment,
        })
    payload = {
        "schema": 1,
        "format": "projectseele:skinned_mesh_v1",
        "coordinateSpace": "GECKO_MODEL_SPACE_BLOCKS",
        "source": "Project SEELE procedural Unit-01 inner-joint proxy",
        "status": "RESEARCH_PROXY_NOT_LIVE_BODY",
        "stride": STRIDE,
        "maxInfluences": 4,
        "palette": palette,
        "inverseBindMatrices": [
            inverse_translation(positions[name]) for name in palette
        ],
        "vertices": values,
        "indices": indices,
        "segments": segment_manifest,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(
        payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "paletteBones": len(palette),
        "segments": len(segment_manifest),
        "vertices": len(values) // STRIDE,
        "triangles": len(indices) // 3,
        "blendedVertices": sum(
            values[index + 13] > 0.0 and values[index + 12] > 0.0
            for index in range(0, len(values), STRIDE)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
