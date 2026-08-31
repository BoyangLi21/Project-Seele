#!/usr/bin/env python3
"""Fail closed on the isolated Phase-C weighted-mesh runtime contract."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RESOURCE = REPO / "src/main/resources/assets/projectseele/eva"
CONTRACT = RESOURCE / "eva_skinned_mesh_contract.json"
PROBE = RESOURCE / "skinning_probe_v1.json"
FORMAT = "projectseele:skinned_mesh_v1"
SPACE = "GECKO_MODEL_SPACE_BLOCKS"
STRIDE = 16
MAX_INFLUENCES = 4
TOLERANCE = 1.0e-5


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("EVA Phase-C skinning invalid: " + message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matrix_multiply(left: list[float], right: list[float]) -> list[float]:
    result = [0.0] * 16
    for column in range(4):
        for row in range(4):
            result[column * 4 + row] = sum(
                left[k * 4 + row] * right[column * 4 + k]
                for k in range(4)
            )
    return result


def transform_position(matrix: list[float], point: list[float]) -> list[float]:
    x, y, z = point
    return [
        matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
        matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
        matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
    ]


def transform_direction(matrix: list[float], value: list[float]) -> list[float]:
    x, y, z = value
    return [
        matrix[0] * x + matrix[4] * y + matrix[8] * z,
        matrix[1] * x + matrix[5] * y + matrix[9] * z,
        matrix[2] * x + matrix[6] * y + matrix[10] * z,
    ]


def main() -> None:
    contract = read_json(CONTRACT)
    probe = read_json(PROBE)
    require(contract.get("schema") == 1 and contract.get("phase") == "C",
            "unexpected contract schema or phase")
    require(contract.get("status") == "FORMAT_AND_RUNTIME_PROBE_ONLY",
            "contract is not isolated research infrastructure")
    require(contract.get("format") == FORMAT
            and contract.get("coordinateSpace") == SPACE,
            "contract format or coordinate space differs")
    require(contract.get("stride") == STRIDE
            and contract.get("maxInfluences") == MAX_INFLUENCES,
            "contract vertex layout differs")
    require(abs(contract.get("weightSumTolerance", -1) - TOLERANCE)
            <= 1.0e-12
            and contract.get("probeResource") ==
            "projectseele:eva/skinning_probe_v1.json",
            "contract tolerance or probe resource differs")
    activation = contract.get("runtimeActivation", {})
    require(activation.get("currentLiveBody") ==
            "projectseele:local_triangle_mesh_v1"
            and activation.get("skinnedBodyEnabled") is False
            and activation.get("productionAssetPresent") is False
            and activation.get("humanReviewRequiredBeforeActivation") is True,
            "weighted probe escaped live-body isolation")

    require(probe.get("schema") == 1 and probe.get("format") == FORMAT
            and probe.get("coordinateSpace") == SPACE,
            "probe header differs from contract")
    require(probe.get("stride") == STRIDE
            and probe.get("maxInfluences") == MAX_INFLUENCES,
            "probe layout differs from contract")
    palette = probe.get("palette", [])
    require(palette and len(palette) == len(set(palette)),
            "probe palette is empty or duplicated")
    inverse_bind = probe.get("inverseBindMatrices", [])
    pose = probe.get("probePoseMatrices", [])
    require(len(inverse_bind) == len(palette) == len(pose),
            "probe matrix palette size differs")
    for matrix in inverse_bind + pose:
        require(len(matrix) == 16
                and all(math.isfinite(value) for value in matrix),
                "probe contains an invalid matrix")

    packed = probe.get("vertices", [])
    require(packed and len(packed) % STRIDE == 0,
            "probe vertex buffer is incomplete")
    vertex_count = len(packed) // STRIDE
    blended = 0
    vertices = []
    for base in range(0, len(packed), STRIDE):
        row = packed[base:base + STRIDE]
        require(all(isinstance(value, (int, float))
                    and math.isfinite(value) for value in row),
                "probe has a non-finite packed value")
        joints = row[8:12]
        weights = row[12:16]
        require(all(float(joint).is_integer()
                    and 0 <= int(joint) < len(palette) for joint in joints),
                "probe has an invalid palette index")
        require(all(0.0 <= weight <= 1.0 for weight in weights)
                and abs(sum(weights) - 1.0) <= TOLERANCE,
                "probe weights are invalid")
        positive = sum(weight > TOLERANCE for weight in weights)
        require(positive > 0, "probe vertex has no influence")
        blended += positive > 1
        vertices.append((row[0:3], row[5:8],
                         [int(value) for value in joints], weights))
    require(blended > 0, "probe has no genuinely blended vertex")
    indices = probe.get("indices", [])
    require(indices and len(indices) % 3 == 0
            and all(isinstance(index, int) and 0 <= index < vertex_count
                    for index in indices),
            "probe triangle buffer is invalid")
    for offset in range(0, len(indices), 3):
        a, b, c = indices[offset:offset + 3]
        require(len({a, b, c}) == 3,
                "probe triangle repeats a vertex")
        p0, p1, p2 = (vertices[index][0] for index in (a, b, c))
        edge_a = [p1[axis] - p0[axis] for axis in range(3)]
        edge_b = [p2[axis] - p0[axis] for axis in range(3)]
        cross = [
            edge_a[1] * edge_b[2] - edge_a[2] * edge_b[1],
            edge_a[2] * edge_b[0] - edge_a[0] * edge_b[2],
            edge_a[0] * edge_b[1] - edge_a[1] * edge_b[0],
        ]
        require(sum(value * value for value in cross) > 1.0e-12,
                "probe contains a degenerate triangle")

    skin_matrices = [
        matrix_multiply(current, inverse)
        for current, inverse in zip(pose, inverse_bind)
    ]
    actual = []
    actual_normals = []
    for position, normal, joints, weights in vertices:
        output = [0.0, 0.0, 0.0]
        output_normal = [0.0, 0.0, 0.0]
        for joint, weight in zip(joints, weights):
            if weight <= 0.0:
                continue
            transformed = transform_position(skin_matrices[joint], position)
            for axis in range(3):
                output[axis] += weight * transformed[axis]
            transformed_normal = transform_direction(
                skin_matrices[joint], normal)
            for axis in range(3):
                output_normal[axis] += weight * transformed_normal[axis]
        actual.extend(output)
        length = math.sqrt(sum(value * value for value in output_normal))
        require(length > 1.0e-10, "probe normal collapsed")
        actual_normals.extend(value / length for value in output_normal)
    expected = probe.get("expectedProbePositions", [])
    require(len(expected) == len(actual),
            "probe expected-position count differs")
    maximum_error = max(abs(before - after)
                        for before, after in zip(expected, actual))
    require(maximum_error <= TOLERANCE,
            f"probe position error {maximum_error} exceeds {TOLERANCE}")
    expected_normals = probe.get("expectedProbeNormals", [])
    require(len(expected_normals) == len(actual_normals),
            "probe expected-normal count differs")
    maximum_normal_error = max(
        abs(before - after)
        for before, after in zip(expected_normals, actual_normals)
    )
    require(maximum_normal_error <= TOLERANCE,
            f"probe normal error {maximum_normal_error} exceeds {TOLERANCE}")

    runtime = read(
        "src/main/java/com/projectseele/client/render/"
        "EvaSkinnedMeshRuntime.java")
    client = read("src/main/java/com/projectseele/client/ClientEvents.java")
    renderer = read(
        "src/main/java/com/projectseele/client/render/EvaUnit01Renderer.java")
    rigid_layer = read(
        "src/main/java/com/projectseele/client/render/"
        "LocalTriangleMeshLayer.java")
    recorder = read(
        "src/main/java/com/projectseele/client/render/"
        "EvaPoseRuntimeRecorder.java")
    for token in ("inverseBindMatrices", "skinPositions", "skinNormals",
                  "mesh.inverseBind[index]", "MAX_INFLUENCES = 4",
                  "public static MeshData load", "public record MeshData",
                  "liveBody=false"):
        require(token in runtime, "runtime evaluator missing " + token)
    require("EvaSkinnedMeshRuntime.reload(resourceManager)" in client,
            "skinning probe is not part of resource reload")
    require("EvaSkinnedMeshRuntime" not in renderer,
            "skinned probe was connected to the live EVA renderer")
    require("stride != 8" in rigid_layer,
            "legacy rigid layer no longer rejects weighted layouts")
    require("skinnedLiveBodyEnabled" in recorder
            and "skinnedMeshContractSha256" in recorder,
            "final-pose capture omits Phase-C isolation evidence")

    print("EVA Phase-C skinning contract passed: "
          f"format={FORMAT} palette={len(palette)} vertices={vertex_count} "
          f"triangles={len(indices) // 3} blended={blended} "
          f"positionError={maximum_error:.9g} "
          f"normalError={maximum_normal_error:.9g} liveBody=false "
          f"contractSha256={raw_sha256(CONTRACT)[:12]} "
          f"probeSha256={raw_sha256(PROBE)[:12]}")


if __name__ == "__main__":
    main()
