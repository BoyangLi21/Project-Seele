#!/usr/bin/env python3
"""Build a single-component manifold EVA inner body and rigid-shell masks."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, deque
from pathlib import Path

import numpy as np
from scipy import ndimage, sparse

from build_eva_weighted_inner_proxy import SEGMENTS, model_position


REPO = Path(__file__).resolve().parent.parent
EVA = REPO / "src/main/resources/assets/projectseele/eva"
RIG = EVA / "eva_rig_schema.json"
TIGER = REPO / (
    "run/resourcepacks/eva_real_model/assets/projectseele/mesh/"
    "eva_unit01.mesh.json")
BODY = EVA / "eva_unit01_manifold_inner.skinned.json"
MASKS = EVA / "eva_unit01_rigid_shell_masks.json"
CONTRACT = EVA / "eva_manifold_inner_contract.json"
VOXEL = 0.12
PADDING = 0.42
SMOOTH_ITERATIONS = 3
SMOOTH_FACTOR = 0.24
STRIDE = 16
SHOULDER_RADIUS_SCALE = 0.45
UPPER_ARM_RADIUS_SCALE = 0.30
FOREARM_RADIUS_SCALE = 0.25
LEG_RADIUS_SCALE = 0.30
WEIGHT_TRANSITION_START = 0.88
WEIGHT_SMOOTH_ITERATIONS = 160
WEIGHT_SMOOTH_ALPHA = 0.55
ORIENTATION_CORRECTION_SWEEPS = 48
ORIENTATION_TARGET_DOT = 1.0e-5
ORIENTATION_MAX_VERTEX_DELTA = 0.10


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize(value: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(value))
    if length <= 1.0e-9:
        raise RuntimeError("zero-length manifold primitive")
    return value / length


def capsule(name: str, parent: str, child: str, start: np.ndarray,
            end: np.ndarray, radius_start: float,
            radius_end: float) -> dict:
    return {
        "name": name,
        "parent": parent,
        "child": child,
        "start": start,
        "end": end,
        "radiusStart": radius_start,
        "radiusEnd": radius_end,
    }


def terminal_capsules(positions: dict[str, np.ndarray]) -> list[dict]:
    result = []
    neck = positions["neck"]
    result.append(capsule(
        "head_terminal", "neck", "head", neck,
        neck + np.array([0.0, 0.72, 0.0]), 0.38, 0.72))
    for side in ("l", "r"):
        wrist = positions[f"wrist_{side}"]
        forearm = positions[f"forearm_{side}"]
        hand_axis = normalize(wrist - forearm)
        result.append(capsule(
            f"hand_terminal_{side}", f"wrist_{side}", f"hand_{side}",
            wrist, wrist + hand_axis * 0.68, 0.10, 0.14))
        ankle = positions[f"ankle_{side}"]
        foot_end = ankle + np.array([0.0, -0.14, -0.90])
        result.append(capsule(
            f"foot_terminal_{side}", f"ankle_{side}", f"foot_{side}",
            ankle, foot_end, 0.22, 0.30))
    return result


def occupancy(primitives: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    minimum = np.min(np.asarray([
        primitive[endpoint] - max(
            primitive["radiusStart"], primitive["radiusEnd"]) - PADDING
        for primitive in primitives for endpoint in ("start", "end")
    ]), axis=0)
    maximum = np.max(np.asarray([
        primitive[endpoint] + max(
            primitive["radiusStart"], primitive["radiusEnd"]) + PADDING
        for primitive in primitives for endpoint in ("start", "end")
    ]), axis=0)
    shape = np.ceil((maximum - minimum) / VOXEL).astype(int)
    origin = minimum
    axes = [origin[axis] + (np.arange(shape[axis]) + 0.5) * VOXEL
            for axis in range(3)]
    x, y, z = np.meshgrid(*axes, indexing="ij")
    points = np.stack((x, y, z), axis=-1)
    inside = np.zeros(tuple(shape), dtype=bool)
    for primitive in primitives:
        start = primitive["start"]
        delta = primitive["end"] - start
        length_squared = float(np.dot(delta, delta))
        t = np.clip(np.sum((points - start) * delta, axis=-1)
                    / length_squared, 0.0, 1.0)
        closest = start + t[..., None] * delta
        radius = primitive["radiusStart"] + t * (
            primitive["radiusEnd"] - primitive["radiusStart"])
        inside |= np.sum((points - closest) ** 2, axis=-1) <= radius ** 2
    # Remove diagonal one-voxel saddles before extracting a cubical boundary;
    # they are one connected volume but create four-face non-manifold edges.
    inside = ndimage.binary_closing(
        inside, structure=ndimage.generate_binary_structure(3, 1),
        iterations=1)
    inside = repair_diagonal_saddles(inside)
    labels, components = ndimage.label(
        inside, structure=ndimage.generate_binary_structure(3, 1))
    if components != 1:
        sizes = ndimage.sum(inside, labels, range(1, components + 1))
        raise RuntimeError(
            f"manifold voxel union has {components} components: {sizes}")
    return inside, origin


def repair_diagonal_saddles(source: np.ndarray) -> np.ndarray:
    """Fill the locally best voxel when two solids touch along one edge."""
    inside = source.copy()
    structure = ndimage.generate_binary_structure(3, 1).astype(np.int8)
    structure[1, 1, 1] = 0
    for _ in range(256):
        neighbours = ndimage.convolve(
            inside.astype(np.int8), structure, mode="constant", cval=0)
        candidates: list[tuple[int, int, int]] = []

        def collect(a: np.ndarray, b: np.ndarray, c: np.ndarray,
                    d: np.ndarray, coordinates) -> None:
            diagonal_ad = a & d & ~b & ~c
            diagonal_bc = ~a & ~d & b & c
            for index in np.argwhere(diagonal_ad):
                candidates.extend(coordinates(tuple(index), True))
            for index in np.argwhere(diagonal_bc):
                candidates.extend(coordinates(tuple(index), False))

        collect(inside[:, :-1, :-1], inside[:, 1:, :-1],
                inside[:, :-1, 1:], inside[:, 1:, 1:],
                lambda value, ad: [
                    (value[0], value[1] + 1, value[2]) if ad
                    else (value[0], value[1], value[2]),
                    (value[0], value[1], value[2] + 1) if ad
                    else (value[0], value[1] + 1, value[2] + 1)])
        collect(inside[:-1, :, :-1], inside[1:, :, :-1],
                inside[:-1, :, 1:], inside[1:, :, 1:],
                lambda value, ad: [
                    (value[0] + 1, value[1], value[2]) if ad
                    else (value[0], value[1], value[2]),
                    (value[0], value[1], value[2] + 1) if ad
                    else (value[0] + 1, value[1], value[2] + 1)])
        collect(inside[:-1, :-1, :], inside[1:, :-1, :],
                inside[:-1, 1:, :], inside[1:, 1:, :],
                lambda value, ad: [
                    (value[0] + 1, value[1], value[2]) if ad
                    else (value[0], value[1], value[2]),
                    (value[0], value[1] + 1, value[2]) if ad
                    else (value[0] + 1, value[1] + 1, value[2])])
        candidates = sorted(set(candidate for candidate in candidates
                                if not inside[candidate]),
                            key=lambda candidate: (
                                -int(neighbours[candidate]), candidate))
        if not candidates:
            return inside
        inside[candidates[0]] = True
    raise RuntimeError("diagonal saddle repair did not converge")


FACE_CORNERS = (
    ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
    ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
    ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
    ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
    ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
)


def extract_surface(inside: np.ndarray, origin: np.ndarray
                    ) -> tuple[np.ndarray, np.ndarray]:
    vertex_map: dict[tuple[int, int, int], int] = {}
    grid_vertices: list[tuple[int, int, int]] = []
    triangles: list[tuple[int, int, int]] = []
    shape = inside.shape

    def vertex_index(corner: tuple[int, int, int]) -> int:
        if corner not in vertex_map:
            vertex_map[corner] = len(grid_vertices)
            grid_vertices.append(corner)
        return vertex_map[corner]

    for cell_array in np.argwhere(inside):
        cell = tuple(int(value) for value in cell_array)
        for direction, corners in FACE_CORNERS:
            neighbour = tuple(cell[axis] + direction[axis]
                              for axis in range(3))
            exposed = any(neighbour[axis] < 0
                          or neighbour[axis] >= shape[axis]
                          for axis in range(3))
            if not exposed:
                exposed = not bool(inside[neighbour])
            if not exposed:
                continue
            quad = [vertex_index(tuple(cell[axis] + corner[axis]
                                       for axis in range(3)))
                    for corner in corners]
            triangles.extend(((quad[0], quad[1], quad[2]),
                              (quad[0], quad[2], quad[3])))
    vertices = origin + np.asarray(grid_vertices, dtype=float) * VOXEL
    return vertices, np.asarray(triangles, dtype=np.int32)


def topology(vertices: np.ndarray, triangles: np.ndarray) -> dict:
    edges = Counter()
    adjacency = defaultdict(set)
    for triangle in triangles:
        a, b, c = (int(value) for value in triangle)
        if len({a, b, c}) != 3:
            raise RuntimeError("manifold surface has degenerate indices")
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
    euler = len(vertices) - len(edges) + len(triangles)
    return {
        "edges": len(edges),
        "nonManifoldEdges": non_manifold,
        "connectedVertexCount": len(visited),
        "components": 1 if len(visited) == len(vertices) else 2,
        "eulerCharacteristic": euler,
    }


def smooth(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    neighbours = [set() for _ in vertices]
    for a, b, c in triangles:
        neighbours[a].update((int(b), int(c)))
        neighbours[b].update((int(a), int(c)))
        neighbours[c].update((int(a), int(b)))
    result = vertices.copy()
    for _ in range(SMOOTH_ITERATIONS):
        updated = result.copy()
        for index, linked in enumerate(neighbours):
            mean = np.mean(result[list(linked)], axis=0)
            updated[index] = result[index] + SMOOTH_FACTOR * (
                mean - result[index])
        result = updated
    return result


def normals(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    result = np.zeros_like(vertices)
    for a, b, c in triangles:
        value = np.cross(vertices[b] - vertices[a],
                         vertices[c] - vertices[a])
        area = float(np.linalg.norm(value))
        if area <= 1.0e-10:
            raise RuntimeError("smoothed manifold has a degenerate triangle")
        result[a] += value
        result[b] += value
        result[c] += value
    lengths = np.linalg.norm(result, axis=1)
    if np.any(lengths <= 1.0e-10):
        raise RuntimeError("smoothed manifold has a collapsed normal")
    return result / lengths[:, None]


def signed_volume(vertices: np.ndarray, triangles: np.ndarray) -> float:
    return float(sum(np.dot(vertices[a], np.cross(vertices[b], vertices[c]))
                     for a, b, c in triangles) / 6.0)


def smooth_skin_weights(vertices: np.ndarray, triangles: np.ndarray,
                        primitives: list[dict], palette: list[str]
                        ) -> tuple[np.ndarray, np.ndarray]:
    palette_index = {name: index for index, name in enumerate(palette)}
    dense = np.zeros((len(vertices), len(palette)), dtype=np.float64)
    for vertex_index, point in enumerate(vertices):
        candidates = []
        for primitive in primitives:
            start = primitive["start"]
            delta = primitive["end"] - start
            t = float(np.clip(np.dot(point - start, delta)
                              / np.dot(delta, delta), 0.0, 1.0))
            closest = start + t * delta
            radius = primitive["radiusStart"] + t * (
                primitive["radiusEnd"] - primitive["radiusStart"])
            surface_error = abs(
                float(np.linalg.norm(point - closest)) - radius)
            candidates.append((surface_error / max(radius, 1.0e-9),
                               primitive["name"], primitive, t))
        _, _, source, t = min(candidates,
                              key=lambda item: (item[0], item[1]))
        transition = float(np.clip(
            (t - WEIGHT_TRANSITION_START)
            / (1.0 - WEIGHT_TRANSITION_START), 0.0, 1.0))
        child = transition * transition * (3.0 - 2.0 * transition)
        dense[vertex_index, palette_index[source["parent"]]] = 1.0 - child
        dense[vertex_index, palette_index[source["child"]]] = child

    rows = np.concatenate((triangles[:, 0], triangles[:, 1],
                           triangles[:, 1], triangles[:, 2],
                           triangles[:, 2], triangles[:, 0]))
    columns = np.concatenate((triangles[:, 1], triangles[:, 0],
                              triangles[:, 2], triangles[:, 1],
                              triangles[:, 0], triangles[:, 2]))
    adjacency = sparse.coo_matrix(
        (np.ones(len(rows)), (rows, columns)),
        shape=(len(vertices), len(vertices))).tocsr()
    adjacency.data[:] = 1.0
    degree = np.asarray(adjacency.sum(axis=1)).reshape(-1)
    average = sparse.diags(1.0 / degree) @ adjacency
    for _ in range(WEIGHT_SMOOTH_ITERATIONS):
        dense = ((1.0 - WEIGHT_SMOOTH_ALPHA) * dense
                 + WEIGHT_SMOOTH_ALPHA * (average @ dense))

    order = np.argsort(-dense, axis=1, kind="stable")[:, :4]
    selected = np.take_along_axis(dense, order, axis=1)
    selected /= selected.sum(axis=1)[:, None]
    return order.astype(np.int32), selected


def inverse_translation(position: np.ndarray) -> list[float]:
    return [1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            -float(position[0]), -float(position[1]),
            -float(position[2]), 1.0]


def build_masks(mesh: dict) -> dict:
    stride = int(mesh["stride"])
    parts = {}
    total = 0
    for name, part in sorted(mesh["parts"].items()):
        triangles = len(part["vertices"]) // (stride * 3)
        total += triangles
        parts[name] = {
            "ownerBone": name,
            "triangleCount": triangles,
            "maxInfluences": 1,
            "role": ("RIGID_DIGIT_SHELL" if name.startswith("finger_")
                     else "RIGID_ARMOR_SHELL"),
        }
    return {
        "schema": 1,
        "status": "TIGER_SINGLE_OWNER_SHELL_MASK",
        "sourceMeshSemanticSha256": canonical_sha256(mesh),
        "sourceTriangleCount": total,
        "sourcePartCount": len(parts),
        "parts": parts,
    }


def main() -> None:
    rig = json.loads(RIG.read_text(encoding="utf-8"))
    bones = {bone["name"]: bone for bone in rig["bones"]}
    base_names = {name for segment in SEGMENTS for name in segment[:2]}
    base_names.update({"head", "hand_l", "hand_r", "foot_l", "foot_r"})
    palette = sorted(base_names, key=lambda name: [
        bone["name"] for bone in rig["bones"]].index(name))
    positions = {name: np.asarray(model_position(bones[name]["pivot"]),
                                  dtype=float) for name in palette}
    primitives = []
    for parent, child, radius_start, radius_end in SEGMENTS:
        if parent == "root":
            # The Gecko root is a transform origin near the feet, not an
            # anatomical body segment. A visible root-to-pelvis capsule ran
            # through both legs and created two non-physical topology handles.
            continue
        if parent == "torso_lower" and child == "torso_upper":
            radius_start, radius_end = 0.62, 0.72
        scale = (SHOULDER_RADIUS_SCALE if parent.startswith("clavicle_")
                 else UPPER_ARM_RADIUS_SCALE if parent.startswith("arm_")
                 else FOREARM_RADIUS_SCALE if parent.startswith("forearm_")
                 else LEG_RADIUS_SCALE if any(
                     token in parent or token in child
                     for token in ("leg_", "shin_", "ankle_"))
                 else 1.0)
        primitives.append(capsule(
            f"{parent}_to_{child}", parent, child,
            positions[parent], positions[child],
            radius_start * scale, radius_end * scale))
    primitives.extend(terminal_capsules(positions))
    inside, origin = occupancy(primitives)
    vertices, triangles = extract_surface(inside, origin)
    initial_topology = topology(vertices, triangles)
    if (initial_topology["nonManifoldEdges"] != 0
            or initial_topology["components"] != 1):
        raise RuntimeError(f"invalid extracted topology: {initial_topology}")
    vertices = smooth(vertices, triangles)
    vertex_normals = normals(vertices, triangles)
    volume = signed_volume(vertices, triangles)
    if volume <= 0.0:
        raise RuntimeError(f"manifold orientation/volume invalid: {volume}")
    audited_topology = topology(vertices, triangles)
    joint_field, weight_field = smooth_skin_weights(
        vertices, triangles, primitives, palette)
    packed = []
    influence_histogram = Counter()
    for vertex_index, (point, normal) in enumerate(
            zip(vertices, vertex_normals)):
        joints = joint_field[vertex_index].tolist()
        skin_weights = weight_field[vertex_index].tolist()
        rounded_weights = [round(float(value), 7)
                           for value in skin_weights]
        rounded_weights[-1] = round(1.0 - sum(rounded_weights[:-1]), 7)
        influence_histogram[sum(value > 1.0e-6
                                for value in rounded_weights)] += 1
        u = (math.atan2(float(point[2]), float(point[0]))
             / (2.0 * math.pi)) % 1.0
        v = (float(point[1]) - float(vertices[:, 1].min())) / max(
            1.0e-9, float(np.ptp(vertices[:, 1])))
        packed.extend([
            *[round(float(value), 6) for value in point],
            round(u, 6), round(v, 6),
            *[round(float(value), 6) for value in normal],
            *joints,
            *rounded_weights,
        ])
    body = {
        "schema": 1,
        "format": "projectseele:skinned_mesh_v1",
        "coordinateSpace": "GECKO_MODEL_SPACE_BLOCKS",
        "source": "Project SEELE procedural voxel-union manifold inner body",
        "status": "RESEARCH_MANIFOLD_NOT_LIVE_BODY",
        "stride": STRIDE,
        "maxInfluences": 4,
        "palette": palette,
        "inverseBindMatrices": [inverse_translation(positions[name])
                                for name in palette],
        "vertices": packed,
        "indices": triangles.reshape(-1).astype(int).tolist(),
        "manifold": {
            "voxelSize": VOXEL,
            "gridShape": list(inside.shape),
            "occupiedCells": int(np.count_nonzero(inside)),
            "smoothingIterations": SMOOTH_ITERATIONS,
            "smoothingFactor": SMOOTH_FACTOR,
            "weightTransitionStart": WEIGHT_TRANSITION_START,
            "weightSmoothingIterations": WEIGHT_SMOOTH_ITERATIONS,
            "weightSmoothingAlpha": WEIGHT_SMOOTH_ALPHA,
            "orientationCorrectionSweeps": ORIENTATION_CORRECTION_SWEEPS,
            "orientationTargetDot": ORIENTATION_TARGET_DOT,
            "orientationMaximumVertexDelta":
                ORIENTATION_MAX_VERTEX_DELTA,
            "primitiveCount": len(primitives),
            "signedVolume": volume,
            **audited_topology,
            "influenceHistogram": {
                str(key): value for key, value
                in sorted(influence_histogram.items())
            },
            "bounds": [[float(vertices[:, axis].min()),
                        float(vertices[:, axis].max())]
                       for axis in range(3)],
        },
        "primitives": [{
            "name": primitive["name"],
            "parent": primitive["parent"],
            "child": primitive["child"],
            "radiusStart": primitive["radiusStart"],
            "radiusEnd": primitive["radiusEnd"],
        } for primitive in primitives],
    }
    tiger = json.loads(TIGER.read_text(encoding="utf-8"))
    masks = build_masks(tiger)
    contract = {
        "schema": 1,
        "phase": "E",
        "status": "MANIFOLD_INNER_AND_RIGID_MASK_RESEARCH",
        "migrationBaselineCommit":
            "c9864e1a1a3862a128da897114ae82af48ac75b4",
        "innerBodyResource":
            "projectseele:eva/eva_unit01_manifold_inner.skinned.json",
        "rigidMaskResource":
            "projectseele:eva/eva_unit01_rigid_shell_masks.json",
        "previewProperty": "projectseele.manifoldInnerPreview",
        "expected": {
            "paletteBones": len(palette),
            "primitives": len(primitives),
            "vertices": len(vertices),
            "triangles": len(triangles),
            "components": audited_topology["components"],
            "nonManifoldEdges": audited_topology["nonManifoldEdges"],
            "eulerCharacteristic": audited_topology["eulerCharacteristic"],
            "rigidParts": masks["sourcePartCount"],
            "rigidTriangles": masks["sourceTriangleCount"],
        },
        "runtimeActivation": {
            "defaultEnabled": False,
            "replacesTigerBody": False,
            "productionReady": False,
            "humanReviewRequiredBeforePromotion": True,
        },
    }
    BODY.write_text(json.dumps(body, ensure_ascii=False,
                               separators=(",", ":")) + "\n",
                    encoding="utf-8")
    MASKS.write_text(json.dumps(masks, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    CONTRACT.write_text(json.dumps(contract, ensure_ascii=False, indent=2)
                        + "\n", encoding="utf-8")
    print(json.dumps({
        "body": str(BODY),
        "masks": str(MASKS),
        "contract": str(CONTRACT),
        **contract["expected"],
        "influenceHistogram": body["manifold"]["influenceHistogram"],
        "volume": volume,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
