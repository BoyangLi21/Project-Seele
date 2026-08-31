#!/usr/bin/env python3
"""Validate the manifold inner body, rigid Tiger masks and runtime isolation."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
EVA = REPO / "src/main/resources/assets/projectseele/eva"
RIG = EVA / "eva_rig_schema.json"
BODY = EVA / "eva_unit01_manifold_inner.skinned.json"
MASKS = EVA / "eva_unit01_rigid_shell_masks.json"
CONTRACT = EVA / "eva_manifold_inner_contract.json"
TIGER = REPO / (
    "run/resourcepacks/eva_real_model/assets/projectseele/mesh/"
    "eva_unit01.mesh.json")
STRIDE = 16
TOLERANCE = 1.0e-6


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("EVA Phase-E manifold invalid: " + message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_position(pivot: list[float]) -> list[float]:
    return [-pivot[0] / 16.0, pivot[1] / 16.0, pivot[2] / 16.0]


def main() -> None:
    contract = read_json(CONTRACT)
    body = read_json(BODY)
    masks = read_json(MASKS)
    rig = read_json(RIG)
    tiger = read_json(TIGER)
    bones = {bone["name"]: bone for bone in rig["bones"]}

    require(contract.get("schema") == 1 and contract.get("phase") == "E",
            "unexpected contract schema or phase")
    require(contract.get("status") ==
            "MANIFOLD_INNER_AND_RIGID_MASK_RESEARCH",
            "contract is not research-only")
    require(contract.get("migrationBaselineCommit") ==
            "c9864e1a1a3862a128da897114ae82af48ac75b4",
            "Phase-E baseline commit differs")
    activation = contract.get("runtimeActivation", {})
    require(activation.get("defaultEnabled") is False
            and activation.get("replacesTigerBody") is False
            and activation.get("productionReady") is False
            and activation.get("humanReviewRequiredBeforePromotion") is True,
            "manifold body escaped isolation")

    require(body.get("schema") == 1
            and body.get("format") == "projectseele:skinned_mesh_v1"
            and body.get("coordinateSpace") == "GECKO_MODEL_SPACE_BLOCKS"
            and body.get("status") ==
            "RESEARCH_MANIFOLD_NOT_LIVE_BODY",
            "inner body header differs")
    require(body.get("stride") == STRIDE
            and body.get("maxInfluences") == 4,
            "inner body vertex layout differs")
    palette = body.get("palette", [])
    require(len(palette) == len(set(palette))
            and set(palette).issubset(bones),
            "inner body palette is invalid")
    inverse_bind = body.get("inverseBindMatrices", [])
    require(len(inverse_bind) == len(palette),
            "inner body inverse-bind count differs")
    for name, matrix in zip(palette, inverse_bind):
        position = model_position(bones[name]["pivot"])
        expected = [1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    -position[0], -position[1], -position[2], 1.0]
        require(len(matrix) == 16
                and max(abs(before - after)
                        for before, after in zip(expected, matrix))
                <= TOLERANCE,
                f"inverse bind differs for {name}")

    packed = body.get("vertices", [])
    indices = body.get("indices", [])
    require(packed and len(packed) % STRIDE == 0,
            "inner body vertex buffer is incomplete")
    vertex_count = len(packed) // STRIDE
    positions = []
    influence_histogram = Counter()
    for base in range(0, len(packed), STRIDE):
        row = packed[base:base + STRIDE]
        require(all(isinstance(value, (int, float))
                    and math.isfinite(value) for value in row),
                "inner body contains a non-finite value")
        joints = row[8:12]
        weights = row[12:16]
        require(all(float(joint).is_integer()
                    and 0 <= int(joint) < len(palette) for joint in joints),
                "inner body has an invalid palette index")
        require(all(0.0 <= weight <= 1.0 for weight in weights)
                and abs(sum(weights) - 1.0) <= TOLERANCE,
                "inner body weights are invalid")
        positive = sum(weight > TOLERANCE for weight in weights)
        require(1 <= positive <= 4,
                "inner body influence count is invalid")
        influence_histogram[positive] += 1
        normal_length = math.sqrt(sum(value * value for value in row[5:8]))
        require(abs(normal_length - 1.0) <= 2.0e-5,
                "inner body normal is not normalized")
        positions.append(row[0:3])
    require(indices and len(indices) % 3 == 0
            and all(isinstance(index, int) and 0 <= index < vertex_count
                    for index in indices),
            "inner body triangle buffer is invalid")

    edges = Counter()
    adjacency = defaultdict(set)
    for offset in range(0, len(indices), 3):
        triangle = indices[offset:offset + 3]
        require(len(set(triangle)) == 3,
                "inner body triangle repeats a vertex")
        a, b, c = triangle
        p0, p1, p2 = positions[a], positions[b], positions[c]
        edge_a = [p1[axis] - p0[axis] for axis in range(3)]
        edge_b = [p2[axis] - p0[axis] for axis in range(3)]
        cross = [edge_a[1] * edge_b[2] - edge_a[2] * edge_b[1],
                 edge_a[2] * edge_b[0] - edge_a[0] * edge_b[2],
                 edge_a[0] * edge_b[1] - edge_a[1] * edge_b[0]]
        require(sum(value * value for value in cross) > 1.0e-12,
                "inner body has a degenerate triangle")
        for left, right in ((a, b), (b, c), (c, a)):
            edge = tuple(sorted((left, right)))
            edges[edge] += 1
            adjacency[left].add(right)
            adjacency[right].add(left)
    non_manifold = sum(count != 2 for count in edges.values())
    visited = set()
    queue = deque([0])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(adjacency[current] - visited)
    components = 1 if len(visited) == vertex_count else 2
    euler = vertex_count - len(edges) + len(indices) // 3
    manifold = body.get("manifold", {})
    require(non_manifold == 0 and components == 1 and euler == 2,
            "inner body is not a closed sphere-topology manifold")
    require(manifold.get("nonManifoldEdges") == non_manifold
            and manifold.get("components") == components
            and manifold.get("eulerCharacteristic") == euler
            and manifold.get("signedVolume", 0) > 0,
            "inner body topology metadata differs")
    require(manifold.get("influenceHistogram") == {
        str(key): value for key, value in sorted(influence_histogram.items())
    }, "inner body influence histogram differs")

    require(masks.get("schema") == 1
            and masks.get("status") == "TIGER_SINGLE_OWNER_SHELL_MASK",
            "rigid mask header differs")
    require(masks.get("sourceMeshSemanticSha256") ==
            canonical_sha256(tiger), "rigid mask source hash differs")
    require(masks.get("sourcePartCount") == len(tiger["parts"]),
            "rigid mask part count differs")
    mask_triangles = 0
    for name, part in tiger["parts"].items():
        require(name in masks["parts"], f"rigid mask misses {name}")
        mask = masks["parts"][name]
        triangles = len(part["vertices"]) // (tiger["stride"] * 3)
        mask_triangles += triangles
        require(mask["ownerBone"] == name
                and mask["triangleCount"] == triangles
                and mask["maxInfluences"] == 1,
                f"rigid mask ownership differs for {name}")
    require(mask_triangles == masks.get("sourceTriangleCount") == 6044,
            "rigid mask triangle count differs")

    expected = contract["expected"]
    require(expected == {
        "paletteBones": len(palette),
        "primitives": len(body["primitives"]),
        "vertices": vertex_count,
        "triangles": len(indices) // 3,
        "components": components,
        "nonManifoldEdges": non_manifold,
        "eulerCharacteristic": euler,
        "rigidParts": len(masks["parts"]),
        "rigidTriangles": mask_triangles,
    }, "Phase-E expected metrics differ")

    runtime = read(
        "src/main/java/com/projectseele/client/render/"
        "EvaManifoldInnerBody.java")
    renderer = read(
        "src/main/java/com/projectseele/client/render/EvaUnit01Renderer.java")
    client = read("src/main/java/com/projectseele/client/ClientEvents.java")
    recorder = read(
        "src/main/java/com/projectseele/client/render/"
        "EvaPoseRuntimeRecorder.java")
    gradle = read("build.gradle")
    require("EvaManifoldInnerBody.reload(resourceManager)" in client,
            "manifold body is not loaded on resource reload")
    require("EvaManifoldInnerBody.prepare(model)" in renderer
            and "EvaManifoldInnerBody.renderAfterRoot(" in renderer,
            "manifold palette render hook is missing")
    require("projectseele.manifoldInnerPreview" in runtime
            and "replacesTiger=false" in runtime,
            "manifold preview isolation is missing")
    require(not any(token in runtime for token in
                    (".setRotX(", ".setRotY(", ".setRotZ(",
                     ".setPosX(", ".setPosY(", ".setPosZ(")),
            "manifold renderer writes pose bones")
    require("manifoldInnerPreview" in gradle,
            "manifold userdev property is missing")
    require("manifoldReplacesTiger" in recorder
            and "manifoldMaskSha256" in recorder,
            "final capture omits manifold isolation evidence")

    print("EVA Phase-E manifold passed: "
          f"palette={len(palette)} primitives={len(body['primitives'])} "
          f"vertices={vertex_count} triangles={len(indices) // 3} "
          f"components={components} nonManifoldEdges={non_manifold} "
          f"euler={euler} rigidParts={len(masks['parts'])} "
          f"rigidTriangles={mask_triangles} replacesTiger=false "
          f"bodySha256={raw_sha256(BODY)[:12]} "
          f"maskSha256={raw_sha256(MASKS)[:12]}")


if __name__ == "__main__":
    main()
