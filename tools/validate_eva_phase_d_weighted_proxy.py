#!/usr/bin/env python3
"""Validate the isolated Unit-01 weighted inner proxy and render hook."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
EVA = REPO / "src/main/resources/assets/projectseele/eva"
RIG = EVA / "eva_rig_schema.json"
CONTRACT = EVA / "eva_weighted_proxy_contract.json"
PROXY = EVA / "eva_unit01_inner_proxy.skinned.json"
STRIDE = 16
TOLERANCE = 1.0e-6


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("EVA Phase-D weighted proxy invalid: " + message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def multiply(left: list[float], right: list[float]) -> list[float]:
    result = [0.0] * 16
    for column in range(4):
        for row in range(4):
            result[column * 4 + row] = sum(
                left[k * 4 + row] * right[column * 4 + k]
                for k in range(4)
            )
    return result


def translation(position: list[float]) -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        position[0], position[1], position[2], 1.0,
    ]


def model_position(pivot: list[float]) -> list[float]:
    return [-pivot[0] / 16.0, pivot[1] / 16.0, pivot[2] / 16.0]


def main() -> None:
    rig = read_json(RIG)
    contract = read_json(CONTRACT)
    proxy = read_json(PROXY)
    bones = {bone["name"]: bone for bone in rig["bones"]}

    require(contract.get("schema") == 1 and contract.get("phase") == "D",
            "unexpected contract schema or phase")
    require(contract.get("status") == "AFTER_RECURSION_RESEARCH_PROXY",
            "contract is not research-only")
    require(contract.get("migrationBaselineCommit") ==
            "18b0efb310ef3407598dee20c46c5f96600bf86b",
            "Phase-D baseline commit differs")
    require(contract.get("proxyResource") ==
            "projectseele:eva/eva_unit01_inner_proxy.skinned.json"
            and contract.get("format") ==
            "projectseele:skinned_mesh_v1",
            "proxy resource or format differs")
    require(contract.get("previewProperty") ==
            "projectseele.skinnedProxyPreview"
            and contract.get("renderHook") ==
            "AFTER_ROOT_RECURSION_MODEL_PALETTE",
            "preview property or render hook differs")
    activation = contract.get("runtimeActivation", {})
    require(all(activation.get(key) is False for key in
                ("defaultEnabled", "replacesTigerBody", "writesPoseBones",
                 "productionReady"))
            and activation.get("humanReviewRequiredBeforePromotion") is True,
            "weighted proxy escaped isolation")

    require(proxy.get("schema") == 1
            and proxy.get("format") == "projectseele:skinned_mesh_v1"
            and proxy.get("coordinateSpace") == "GECKO_MODEL_SPACE_BLOCKS"
            and proxy.get("status") == "RESEARCH_PROXY_NOT_LIVE_BODY",
            "proxy header differs")
    require(proxy.get("stride") == STRIDE
            and proxy.get("maxInfluences") == 4,
            "proxy vertex layout differs")
    palette = proxy.get("palette", [])
    require(len(palette) == len(set(palette))
            and set(palette).issubset(bones),
            "proxy palette is duplicate or non-canonical")
    inverse_bind = proxy.get("inverseBindMatrices", [])
    require(len(inverse_bind) == len(palette),
            "proxy inverse-bind palette differs")
    identity = translation([0.0, 0.0, 0.0])
    for name, inverse in zip(palette, inverse_bind):
        require(len(inverse) == 16
                and all(math.isfinite(value) for value in inverse),
                f"invalid inverse bind for {name}")
        position = model_position(bones[name]["pivot"])
        round_trip = multiply(translation(position), inverse)
        require(max(abs(before - after)
                    for before, after in zip(identity, round_trip))
                <= TOLERANCE,
                f"bind round-trip differs for {name}")

    packed = proxy.get("vertices", [])
    indices = proxy.get("indices", [])
    require(packed and len(packed) % STRIDE == 0,
            "proxy vertex buffer is incomplete")
    vertex_count = len(packed) // STRIDE
    blended = 0
    positions = []
    for base in range(0, len(packed), STRIDE):
        row = packed[base:base + STRIDE]
        require(all(isinstance(value, (int, float))
                    and math.isfinite(value) for value in row),
                "proxy has a non-finite packed value")
        joints = row[8:12]
        weights = row[12:16]
        require(all(float(joint).is_integer()
                    and 0 <= int(joint) < len(palette) for joint in joints),
                "proxy palette index is invalid")
        require(all(0.0 <= weight <= 1.0 for weight in weights)
                and abs(sum(weights) - 1.0) <= TOLERANCE,
                "proxy weights are invalid")
        positive = sum(weight > TOLERANCE for weight in weights)
        require(positive in (1, 2),
                "proxy vertex does not use one or two influences")
        blended += positive == 2
        positions.append(row[0:3])
    bounds = [[min(point[axis] for point in positions),
               max(point[axis] for point in positions)]
              for axis in range(3)]
    require(bounds[0][0] >= -2.5 and bounds[0][1] <= 2.5
            and bounds[1][0] >= 0.0 and bounds[1][1] <= 11.0
            and bounds[2][0] >= -2.0 and bounds[2][1] <= 2.0,
            "proxy bounds escape the Unit-01 inner envelope")
    require(abs(bounds[0][0] + bounds[0][1]) <= TOLERANCE,
            "proxy left/right bounds are not mirrored")
    require(indices and len(indices) % 3 == 0
            and all(isinstance(index, int) and 0 <= index < vertex_count
                    for index in indices),
            "proxy triangle buffer is invalid")
    for offset in range(0, len(indices), 3):
        require(len(set(indices[offset:offset + 3])) == 3,
                "proxy has a repeated triangle index")

    segments = proxy.get("segments", [])
    interfaces = {(segment["parent"], segment["child"])
                  for segment in segments}
    required = {tuple(pair) for pair in contract["requiredInterfaces"]}
    require(interfaces == required,
            "proxy interfaces differ from contract")
    for segment in segments:
        start = segment["startVertex"]
        count = segment["vertexCount"]
        require(count == 26 and segment["triangleCount"] == 48,
                "proxy segment topology differs")
        rows = [packed[index:index + STRIDE]
                for index in range(start * STRIDE,
                                   (start + count - 2) * STRIDE, STRIDE)]
        middle = rows[8:16]
        require(all(abs(row[12] - 0.5) <= TOLERANCE
                    and abs(row[13] - 0.5) <= TOLERANCE
                    for row in middle),
                "proxy middle ring is not dual-weighted")

    expected = contract["expected"]
    require(expected == {
        "paletteBones": len(palette),
        "segments": len(segments),
        "vertices": vertex_count,
        "triangles": len(indices) // 3,
        "blendedVertices": blended,
    }, "proxy counts differ from contract")

    runtime = read(
        "src/main/java/com/projectseele/client/render/"
        "EvaWeightedInnerProxy.java")
    renderer = read(
        "src/main/java/com/projectseele/client/render/EvaUnit01Renderer.java")
    client = read("src/main/java/com/projectseele/client/ClientEvents.java")
    recorder = read(
        "src/main/java/com/projectseele/client/render/"
        "EvaPoseRuntimeRecorder.java")
    gradle = read("build.gradle")
    require("EvaWeightedInnerProxy.reload(resourceManager)" in client,
            "weighted proxy is not loaded on resource reload")
    require("EvaWeightedInnerProxy.prepare(model)" in renderer,
            "weighted proxy palette tracking is missing")
    require("EvaWeightedInnerProxy.renderAfterRoot(" in renderer
            and renderer.index("super.renderRecursively(") <
            renderer.index("EvaWeightedInnerProxy.renderAfterRoot("),
            "weighted proxy does not render after Gecko recursion")
    require("bone.getParent() == null" in renderer,
            "weighted proxy is not restricted to one root pass")
    require("projectseele.skinnedProxyPreview" in runtime
            and "replacesTiger=false" in runtime,
            "weighted proxy preview gate is missing")
    require(not any(token in runtime for token in
                    (".setRotX(", ".setRotY(", ".setRotZ(",
                     ".setPosX(", ".setPosY(", ".setPosZ(")),
            "weighted proxy writes pose bones")
    require("skinnedProxyPreview" in gradle,
            "weighted proxy userdev property is missing")
    require("weightedProxyReplacesTiger" in recorder
            and "weightedProxyResourceSha256" in recorder,
            "final-pose capture omits proxy isolation evidence")

    print("EVA Phase-D weighted proxy passed: "
          f"palette={len(palette)} segments={len(segments)} "
          f"vertices={vertex_count} triangles={len(indices) // 3} "
          f"blended={blended} defaultEnabled=false replacesTiger=false "
          f"contractSha256={sha256(CONTRACT)[:12]} "
          f"proxySha256={sha256(PROXY)[:12]}")


if __name__ == "__main__":
    main()
