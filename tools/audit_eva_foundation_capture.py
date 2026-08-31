#!/usr/bin/env python3
"""Audit a Phase-F game-frame capture before it can become a review pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.spatial import cKDTree


REPO = Path(__file__).resolve().parent.parent
EVA = REPO / "src/main/resources/assets/projectseele/eva"
BODY = EVA / "eva_unit01_manifold_inner.skinned.json"
MASKS = EVA / "eva_unit01_rigid_shell_masks.json"
RIG = EVA / "eva_rig_schema.json"
CONTRACT = EVA / "eva_foundation_review_contract.json"
TIGER = REPO / (
    "run/resourcepacks/eva_real_model/assets/projectseele/mesh/"
    "eva_unit01.mesh.json")
CAPTURE_ROOT = REPO / "run/screenshots/projectseele_foundation"
_TOPOLOGY_EXCLUSION_CACHE: dict[tuple[int, int, int], list[set[int]]] = {}


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def matrix(values: Iterable[float]) -> np.ndarray:
    result = np.asarray(list(values), dtype=np.float64)
    require(result.shape == (16,), "captured matrix is not float[16]")
    result = result.reshape((4, 4), order="F")
    require(np.all(np.isfinite(result)), "captured matrix is non-finite")
    require(abs(float(np.linalg.det(result))) > 1.0e-9,
            "captured matrix is singular")
    return result


def transform_points(points: np.ndarray, transform: np.ndarray) -> np.ndarray:
    homogeneous = np.column_stack((points, np.ones(len(points))))
    return (homogeneous @ transform.T)[:, :3]


def latest_batch() -> Path:
    candidates = sorted(path for path in CAPTURE_ROOT.glob("*")
                        if (path / "frame_audit.jsonl").is_file())
    require(bool(candidates), f"no foundation capture under {CAPTURE_ROOT}")
    return candidates[-1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(batch: Path) -> list[dict]:
    path = batch / "frame_audit.jsonl"
    require(path.is_file(), f"missing {path}")
    records = [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    require(bool(records), "empty foundation frame audit")
    return records


def mesh_arrays(body: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                           np.ndarray, np.ndarray]:
    stride = int(body["stride"])
    require(stride == 16, "foundation body stride differs")
    packed = np.asarray(body["vertices"], dtype=np.float64).reshape(-1, stride)
    positions = packed[:, :3]
    joints = np.rint(packed[:, 8:12]).astype(np.int32)
    weights = packed[:, 12:16]
    indices = np.asarray(body["indices"], dtype=np.int32).reshape(-1, 3)
    inverse_bind = np.asarray([matrix(values) for values in
                               body["inverseBindMatrices"]])
    return positions, joints, weights, indices, inverse_bind


def skin_positions(positions: np.ndarray, joints: np.ndarray,
                   weights: np.ndarray, inverse_bind: np.ndarray,
                   current: np.ndarray) -> np.ndarray:
    skin = current @ inverse_bind
    homogeneous = np.column_stack((positions, np.ones(len(positions))))
    result = np.zeros_like(positions)
    for influence in range(4):
        selected = skin[joints[:, influence]]
        transformed = np.einsum("nij,nj->ni", selected, homogeneous)[:, :3]
        result += transformed * weights[:, influence, None]
    return result


def skin_normals(normals: np.ndarray, joints: np.ndarray,
                 weights: np.ndarray, inverse_bind: np.ndarray,
                 current: np.ndarray) -> np.ndarray:
    skin = current @ inverse_bind
    normal_matrices = np.linalg.inv(skin[:, :3, :3]).transpose(0, 2, 1)
    result = np.zeros_like(normals)
    for influence in range(4):
        selected = normal_matrices[joints[:, influence]]
        result += np.einsum("nij,nj->ni", selected, normals) \
            * weights[:, influence, None]
    result /= np.linalg.norm(result, axis=1)[:, None]
    return result


def correct_orientations(vertices: np.ndarray, normals: np.ndarray,
                         indices: np.ndarray, sweeps: int = 48,
                         target: float = 1.0e-5,
                         maximum_delta: float = 0.10
                         ) -> tuple[np.ndarray, int, float]:
    result = vertices.copy()
    original = vertices.copy()
    completed = 0
    for sweep in range(sweeps):
        changed = 0
        for a, b, c in indices:
            desired = normals[[a, b, c]].sum(axis=0)
            length = float(np.linalg.norm(desired))
            if length <= 1.0e-10:
                continue
            desired /= length
            edge_a = result[b] - result[a]
            edge_b = result[c] - result[a]
            signed = float(np.dot(np.cross(edge_a, edge_b), desired))
            if signed >= target:
                continue
            gradient_b = np.cross(edge_b, desired)
            gradient_c = np.cross(desired, edge_a)
            gradient_a = -(gradient_b + gradient_c)
            denominator = float(
                np.dot(gradient_a, gradient_a)
                + np.dot(gradient_b, gradient_b)
                + np.dot(gradient_c, gradient_c))
            if denominator <= 1.0e-12:
                continue
            scale = (target - signed) / denominator
            result[a] += scale * gradient_a
            result[b] += scale * gradient_b
            result[c] += scale * gradient_c
            changed += 1
        completed = sweep + 1
        if changed == 0:
            break
    displacement = float(np.max(np.linalg.norm(result - original, axis=1)))
    require(displacement <= maximum_delta + 1.0e-7,
            f"orientation correction exceeded {displacement}")
    return result, completed, displacement


def bone_inverse_bind(rig: dict) -> dict[str, np.ndarray]:
    result = {}
    for bone in rig["bones"]:
        pivot = np.asarray(bone["pivot"], dtype=np.float64)
        position = np.asarray([-pivot[0], pivot[1], pivot[2]]) / 16.0
        inverse = np.eye(4)
        inverse[:3, 3] = -position
        result[bone["name"]] = inverse
    return result


def tiger_points(tiger: dict) -> dict[str, np.ndarray]:
    stride = int(tiger["stride"])
    require(stride == 8, "Tiger mesh stride differs")
    result = {}
    for name, part in tiger["parts"].items():
        packed = np.asarray(part["vertices"], dtype=np.float64).reshape(-1, stride)
        pivot = np.asarray(part["pivot"], dtype=np.float64)
        absolute = packed[:, :3] + pivot
        absolute[:, 0] *= -1.0
        absolute /= 16.0
        result[name] = np.unique(np.round(absolute, 7), axis=0)
    return result


def record_palette(record: dict, expected: list[str]) -> np.ndarray:
    names = [item["name"] for item in record["palette"]]
    require(names == expected,
            f"palette order differs at {record['pose']}/{record['view']}/"
            f"{record['frame']}")
    return np.asarray([matrix(item["modelMatrix"])
                       for item in record["palette"]])


def record_bones(record: dict) -> dict[str, np.ndarray]:
    result = {item["name"]: matrix(item["modelMatrix"])
              for item in record["bones"]}
    require(len(result) == len(record["bones"]),
            "duplicate names in captured complete bone palette")
    return result


SEAM_PAIRS = [
    ("torso_lower", "torso_upper"),
    ("torso_upper", "head"),
    ("torso_upper", "pylon_l"),
    ("torso_upper", "pylon_r"),
]
for _side in ("l", "r"):
    SEAM_PAIRS.extend([
        ("torso_upper", f"arm_{_side}"),
        (f"arm_{_side}", f"forearm_{_side}"),
        (f"forearm_{_side}", f"hand_{_side}"),
        ("torso_lower", f"leg_{_side}"),
        (f"leg_{_side}", f"shin_{_side}"),
        (f"shin_{_side}", f"foot_{_side}"),
        (f"hand_{_side}", f"finger_thumb_{_side}"),
    ])
    for _digit in ("index", "middle", "ring", "little"):
        SEAM_PAIRS.extend([
            (f"hand_{_side}", f"finger_{_digit}_{_side}"),
            (f"finger_{_digit}_{_side}",
             f"finger_{_digit}_distal_{_side}"),
            (f"finger_{_digit}_distal_{_side}",
             f"finger_{_digit}_tip_{_side}"),
        ])


def seam_correspondence(left: np.ndarray, right: np.ndarray,
                        count: int = 24) -> tuple[np.ndarray, np.ndarray,
                                                 np.ndarray]:
    right_tree = cKDTree(right)
    left_distance, left_index = right_tree.query(left, k=1)
    left_tree = cKDTree(left)
    right_distance, right_index = left_tree.query(right, k=1)
    candidates = [(float(distance), index, int(left_index[index]))
                  for index, distance in enumerate(left_distance)]
    candidates.extend((float(distance), int(right_index[index]), index)
                      for index, distance in enumerate(right_distance))
    candidates.sort()
    chosen = []
    used = set()
    for distance, left_id, right_id in candidates:
        key = (left_id, right_id)
        if key in used:
            continue
        used.add(key)
        chosen.append((left_id, right_id, distance))
        if len(chosen) >= count:
            break
    require(len(chosen) >= min(8, count), "insufficient seam samples")
    return (np.asarray([item[0] for item in chosen], dtype=np.int32),
            np.asarray([item[1] for item in chosen], dtype=np.int32),
            np.asarray([item[2] for item in chosen], dtype=np.float64))


@dataclass
class BvhNode:
    minimum: np.ndarray
    maximum: np.ndarray
    indices: np.ndarray | None = None
    left: "BvhNode | None" = None
    right: "BvhNode | None" = None


def build_bvh(minimum: np.ndarray, maximum: np.ndarray,
              centers: np.ndarray, indices: np.ndarray) -> BvhNode:
    node_minimum = np.min(minimum[indices], axis=0)
    node_maximum = np.max(maximum[indices], axis=0)
    if len(indices) <= 12:
        return BvhNode(node_minimum, node_maximum, indices=indices)
    axis = int(np.argmax(np.ptp(centers[indices], axis=0)))
    ordered = indices[np.argsort(centers[indices, axis], kind="stable")]
    middle = len(ordered) // 2
    return BvhNode(node_minimum, node_maximum,
                   left=build_bvh(minimum, maximum, centers,
                                  ordered[:middle]),
                   right=build_bvh(minimum, maximum, centers,
                                   ordered[middle:]))


def boxes_overlap(left: BvhNode, right: BvhNode,
                  epsilon: float = 1.0e-7) -> bool:
    return bool(np.all(left.maximum + epsilon >= right.minimum)
                and np.all(right.maximum + epsilon >= left.minimum))


def orient2d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float((b[0] - a[0]) * (c[1] - a[1])
                 - (b[1] - a[1]) * (c[0] - a[0]))


def point_in_triangle_2d(point: np.ndarray, triangle: np.ndarray,
                         epsilon: float) -> bool:
    values = [orient2d(triangle[index], triangle[(index + 1) % 3], point)
              for index in range(3)]
    return not (min(values) < -epsilon and max(values) > epsilon)


def segments_intersect_2d(a: np.ndarray, b: np.ndarray, c: np.ndarray,
                          d: np.ndarray, epsilon: float) -> bool:
    first = (orient2d(a, b, c), orient2d(a, b, d))
    second = (orient2d(c, d, a), orient2d(c, d, b))
    return (min(first) <= epsilon and max(first) >= -epsilon
            and min(second) <= epsilon and max(second) >= -epsilon)


def segment_triangle(start: np.ndarray, end: np.ndarray,
                     triangle: np.ndarray, epsilon: float) -> bool:
    direction = end - start
    edge_a = triangle[1] - triangle[0]
    edge_b = triangle[2] - triangle[0]
    cross = np.cross(direction, edge_b)
    determinant = float(np.dot(edge_a, cross))
    if abs(determinant) <= epsilon:
        return False
    inverse = 1.0 / determinant
    offset = start - triangle[0]
    u = float(np.dot(offset, cross)) * inverse
    if u < -epsilon or u > 1.0 + epsilon:
        return False
    q = np.cross(offset, edge_a)
    v = float(np.dot(direction, q)) * inverse
    if v < -epsilon or u + v > 1.0 + epsilon:
        return False
    distance = float(np.dot(edge_b, q)) * inverse
    return -epsilon <= distance <= 1.0 + epsilon


def triangles_intersect(left: np.ndarray, right: np.ndarray,
                        epsilon: float = 1.0e-7) -> bool:
    for index in range(3):
        if segment_triangle(left[index], left[(index + 1) % 3],
                            right, epsilon):
            return True
        if segment_triangle(right[index], right[(index + 1) % 3],
                            left, epsilon):
            return True
    normal_left = np.cross(left[1] - left[0], left[2] - left[0])
    normal_right = np.cross(right[1] - right[0], right[2] - right[0])
    length_left = float(np.linalg.norm(normal_left))
    length_right = float(np.linalg.norm(normal_right))
    if length_left <= epsilon or length_right <= epsilon:
        return False
    parallel = np.linalg.norm(np.cross(normal_left, normal_right))
    coplanar = (parallel <= epsilon * length_left * length_right
                and abs(float(np.dot(normal_left,
                                     right[0] - left[0])))
                <= epsilon * length_left)
    if not coplanar:
        return False
    axis = int(np.argmax(np.abs(normal_left)))
    axes = [value for value in range(3) if value != axis]
    left_2d = left[:, axes]
    right_2d = right[:, axes]
    for left_index in range(3):
        for right_index in range(3):
            if segments_intersect_2d(
                    left_2d[left_index], left_2d[(left_index + 1) % 3],
                    right_2d[right_index],
                    right_2d[(right_index + 1) % 3], epsilon):
                return True
    return (point_in_triangle_2d(left_2d[0], right_2d, epsilon)
            or point_in_triangle_2d(right_2d[0], left_2d, epsilon))


def first_self_intersection(vertices: np.ndarray,
                            indices: np.ndarray,
                            excluded_topology_hops: int = 4
                            ) -> tuple[int, int] | None:
    triangles = vertices[indices]
    minimum = np.min(triangles, axis=1)
    maximum = np.max(triangles, axis=1)
    centers = (minimum + maximum) * 0.5
    root = build_bvh(minimum, maximum, centers,
                     np.arange(len(indices), dtype=np.int32))
    cache_key = (int(indices.__array_interface__["data"][0]),
                 len(vertices), excluded_topology_hops)
    excluded = _TOPOLOGY_EXCLUSION_CACHE.get(cache_key)
    if excluded is None:
        adjacency = [set() for _ in vertices]
        for triangle in indices:
            for left, right in ((triangle[0], triangle[1]),
                                (triangle[1], triangle[2]),
                                (triangle[2], triangle[0])):
                adjacency[int(left)].add(int(right))
                adjacency[int(right)].add(int(left))
        excluded = []
        for vertex in range(len(vertices)):
            seen = {vertex}
            frontier = {vertex}
            for _ in range(excluded_topology_hops):
                frontier = {linked for current in frontier
                            for linked in adjacency[current]} - seen
                seen.update(frontier)
            excluded.append(seen)
        _TOPOLOGY_EXCLUSION_CACHE[cache_key] = excluded

    def leaf_test(left_ids: np.ndarray, right_ids: np.ndarray,
                  same: bool) -> tuple[int, int] | None:
        for left_offset, left_id in enumerate(left_ids):
            start = left_offset + 1 if same else 0
            for right_id in right_ids[start:]:
                left_id = int(left_id)
                right_id = int(right_id)
                if left_id == right_id:
                    continue
                if any(int(right_vertex) in excluded[int(left_vertex)]
                       for left_vertex in indices[left_id]
                       for right_vertex in indices[right_id]):
                    continue
                if (np.any(maximum[left_id] + 1.0e-7 < minimum[right_id])
                        or np.any(maximum[right_id] + 1.0e-7
                                  < minimum[left_id])):
                    continue
                if triangles_intersect(triangles[left_id],
                                       triangles[right_id]):
                    return tuple(sorted((left_id, right_id)))
        return None

    def visit(left: BvhNode, right: BvhNode,
              same: bool) -> tuple[int, int] | None:
        if not boxes_overlap(left, right):
            return None
        if left.indices is not None and right.indices is not None:
            return leaf_test(left.indices, right.indices, same)
        if same:
            for first, second, child_same in (
                    (left.left, left.left, True),
                    (left.left, left.right, False),
                    (left.right, left.right, True)):
                found = visit(first, second, child_same)
                if found is not None:
                    return found
            return None
        left_size = float(np.prod(left.maximum - left.minimum))
        right_size = float(np.prod(right.maximum - right.minimum))
        if right.indices is not None or (left.indices is None
                                         and left_size >= right_size):
            found = visit(left.left, right, False)
            return found if found is not None else visit(
                left.right, right, False)
        found = visit(left, right.left, False)
        return found if found is not None else visit(
            left, right.right, False)

    return visit(root, root, True)


def transformed_parts(points: dict[str, np.ndarray],
                      bones: dict[str, np.ndarray],
                      inverse: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {name: transform_points(values, bones[name] @ inverse[name])
            for name, values in points.items()}


def audit_capture(batch: Path, report_path: Path | None = None) -> dict:
    batch = batch.resolve()
    contract = load_json(CONTRACT)
    body = load_json(BODY)
    masks = load_json(MASKS)
    rig = load_json(RIG)
    tiger = load_json(TIGER)
    records = load_records(batch)
    actions = contract["actions"]
    views = contract["views"]
    gates = contract["automaticGates"]
    expected_groups = {(action["pose"], view): action["framesPerView"]
                       for action in actions for view in views}
    grouped: dict[tuple[str, str], list[dict]] = {}
    serials = []
    expected_palette = body["palette"]
    body_hash = raw_sha256(BODY)
    mask_hash = raw_sha256(MASKS)
    model_tags = set()
    required_bones = set(masks["parts"])
    for record in records:
        require(record.get("schema") == 1, "frame audit schema differs")
        key = (record["pose"], record["view"])
        require(key in expected_groups, f"unexpected capture group {key}")
        grouped.setdefault(key, []).append(record)
        serials.append(int(record["renderSerial"]))
        require(record["triangles"] == len(body["indices"]) // 3,
                f"runtime triangle count differs at {key}/{record['frame']}")
        require(record["invertedTriangles"]
                == gates["invertedTriangles"],
                f"inverted manifold triangle at {key}/{record['frame']}")
        require(record["collapsedTriangles"]
                == gates["collapsedTriangles"],
                f"collapsed manifold triangle at {key}/{record['frame']}")
        require(record["minimumDoubleArea"]
                >= gates["minimumDoubleArea"],
                f"manifold area gate failed at {key}/{record['frame']}")
        require(record["manifoldBodySha256"] == body_hash,
                "captured manifold body hash differs")
        require(record["rigidMaskSha256"] == mask_hash,
                "captured rigid mask hash differs")
        record_palette(record, expected_palette)
        names = {item["name"] for item in record["bones"]}
        require(required_bones <= names,
                f"capture omits rigid owners: {sorted(required_bones - names)}")
        model_tags.add(record["bodyModelTag"])
        require(record.get("powerTicks", 0) > 0,
                f"capture target is unpowered at {key}/{record['frame']}")
        require(record.get("visualPose") == 0,
                f"capture bypasses normal gameplay pose at {key}/"
                f"{record['frame']}")
        if record["pose"] in ("walk_contact", "run_contact"):
            require(not record.get("visuallyAirborne", False),
                    f"grounded locomotion became airborne at {key}/"
                    f"{record['frame']}")
    require(all(right > left for left, right in zip(serials, serials[1:])),
            "render serials are not strictly increasing")
    require(len(model_tags) == 1, "body fingerprint changed during capture")
    model_tag = next(iter(model_tags))
    require("triangle-mesh-6044-p43-" in model_tag,
            f"capture did not use the required Tiger mesh: {model_tag}")
    require(set(grouped) == set(expected_groups),
            f"capture groups differ: missing={set(expected_groups)-set(grouped)}")
    for key, expected_count in expected_groups.items():
        entries = sorted(grouped[key], key=lambda item: item["frame"])
        require([item["frame"] for item in entries]
                == list(range(1, expected_count + 1)),
                f"non-contiguous audit frames for {key}")
        images = sorted((batch / key[0] / key[1]).glob("frame_*.png"))
        require(len(images) == expected_count,
                f"PNG count differs for {key}: {len(images)} != {expected_count}")
        require([path.name for path in images]
                == [f"frame_{index:04d}.png"
                    for index in range(1, expected_count + 1)],
                f"non-contiguous PNG frames for {key}")

    require(canonical_sha256(tiger)
            == masks["sourceMeshSemanticSha256"],
            "installed Tiger mesh semantic hash differs from rigid mask")
    positions, joints, weights, indices, inverse_bind = mesh_arrays(body)
    packed_body = np.asarray(body["vertices"], dtype=np.float64).reshape(
        -1, int(body["stride"]))
    bind_normals = packed_body[:, 5:8]
    inverse_bones = bone_inverse_bind(rig)
    parts = tiger_points(tiger)
    require(set(parts) == required_bones,
            "Tiger parts differ from rigid mask owners")

    front_records = []
    for action in actions:
        front_records.extend(sorted(grouped[(action["pose"], "front_close")],
                                    key=lambda item: item["frame"]))
    skinned: dict[tuple[str, int], np.ndarray] = {}
    complete_bones: dict[tuple[str, int], dict[str, np.ndarray]] = {}
    maximum_bounds_delta = 0.0
    maximum_offline_correction = 0.0
    for record in front_records:
        key = (record["pose"], int(record["frame"]))
        palette = record_palette(record, expected_palette)
        vertices = skin_positions(positions, joints, weights,
                                  inverse_bind, palette)
        deformed_normals = skin_normals(
            bind_normals, joints, weights, inverse_bind, palette)
        vertices, _, correction = correct_orientations(
            vertices, deformed_normals, indices)
        maximum_offline_correction = max(
            maximum_offline_correction, correction)
        skinned[key] = vertices
        complete_bones[key] = record_bones(record)
        bounds = np.asarray(record["bounds"], dtype=np.float64)
        computed = np.concatenate((np.min(vertices, axis=0),
                                   np.max(vertices, axis=0)))
        maximum_bounds_delta = max(maximum_bounds_delta,
                                   float(np.max(np.abs(bounds - computed))))
    require(maximum_bounds_delta <= 5.0e-5,
            f"offline/runtime skin bounds differ: {maximum_bounds_delta}")

    motion_evidence = {}
    for action in actions:
        pose = action["pose"]
        action_records = sorted(grouped[(pose, "front_close")],
                                key=lambda item: item["frame"])
        reference = record_bones(action_records[0])
        maximum_delta = 0.0
        for record in action_records:
            current = record_bones(record)
            maximum_delta = max(maximum_delta, max(
                float(np.max(np.abs(current[name] - reference[name])))
                for name in reference))
        positions_runtime = np.asarray(
            [record["entityPosition"] for record in action_records],
            dtype=np.float64)
        horizontal = np.linalg.norm(
            positions_runtime[:, (0, 2)] - positions_runtime[0, (0, 2)],
            axis=1)
        vertical_range = float(np.ptp(positions_runtime[:, 1]))
        evidence = {
            "maximumBoneMatrixDelta": maximum_delta,
            "maximumHorizontalDisplacement": float(np.max(horizontal)),
            "verticalRange": vertical_range,
            "weapons": sorted({int(record["weapon"])
                               for record in action_records}),
            "sprintingObserved": any(bool(record["pilotSprinting"])
                                     for record in action_records),
            "airborneObserved": any(bool(record["visuallyAirborne"])
                                    for record in action_records),
        }
        motion_evidence[pose] = evidence
        if pose != "idle":
            require(maximum_delta
                    >= gates["minimumDynamicBoneMatrixDelta"],
                    f"dynamic action stayed static: {pose} {evidence}")
        expected_weapon = 1 if pose == "live_knife" else 0
        require(evidence["weapons"] == [expected_weapon],
                f"wrong foundation weapon for {pose}: {evidence}")
    require(motion_evidence["walk_contact"]
            ["maximumHorizontalDisplacement"]
            >= gates["minimumWalkHorizontalDisplacement"],
            f"walk input did not move the EVA: {motion_evidence['walk_contact']}")
    require(motion_evidence["run_contact"]
            ["maximumHorizontalDisplacement"]
            >= gates["minimumRunHorizontalDisplacement"],
            f"run input did not move the EVA: {motion_evidence['run_contact']}")
    require(motion_evidence["run_contact"]["sprintingObserved"],
            "run capture never entered server-authorized sprint")
    require(motion_evidence["live_jump"]["verticalRange"]
            >= gates["minimumJumpVerticalRange"]
            and motion_evidence["live_jump"]["airborneObserved"],
            f"jump input never became airborne: {motion_evidence['live_jump']}")

    reference_key = (actions[0]["pose"], 1)
    reference_parts = transformed_parts(parts,
                                        complete_bones[reference_key],
                                        inverse_bones)
    body_height = float(max(point[:, 1].max() for point in reference_parts.values())
                        - min(point[:, 1].min()
                              for point in reference_parts.values()))
    require(body_height > 1.0, f"invalid Tiger body height {body_height}")
    runtime_correction = max(float(record["maximumOrientationCorrection"])
                             for record in records)
    require(runtime_correction / body_height
            <= gates["maximumOrientationCorrectionHeightFraction"],
            f"runtime orientation correction is too large: "
            f"{runtime_correction / body_height}")
    require(abs(runtime_correction - maximum_offline_correction) <= 5.0e-5,
            "runtime/offline orientation correction differs")
    seam_samples = {}
    for left_name, right_name in SEAM_PAIRS:
        require(left_name in reference_parts and right_name in reference_parts,
                f"missing seam pair {left_name}/{right_name}")
        seam_samples[(left_name, right_name)] = seam_correspondence(
            reference_parts[left_name], reference_parts[right_name])

    seam_contact_worst = {"fraction": 0.0}
    seam_band_worst = {"fraction": 0.0}
    seam_opening_worst = {"fraction": 0.0}
    clearance_worst_drop = {"fraction": 0.0}
    clearance_worst_drift = {"fraction": 0.0}
    reference_armor = np.concatenate(list(reference_parts.values()), axis=0)
    sample_indices = np.arange(0, len(positions), 8, dtype=np.int32)
    reference_clearance = cKDTree(reference_armor).query(
        skinned[reference_key][sample_indices], k=1)[0]
    for record in front_records:
        key = (record["pose"], int(record["frame"]))
        runtime_parts = transformed_parts(parts, complete_bones[key],
                                          inverse_bones)
        for pair, (left_ids, right_ids, _) in seam_samples.items():
            reference_distance = np.concatenate((
                cKDTree(reference_parts[pair[1]]).query(
                    reference_parts[pair[0]][left_ids], k=1)[0],
                cKDTree(reference_parts[pair[0]]).query(
                    reference_parts[pair[1]][right_ids], k=1)[0]))
            runtime_distance = np.concatenate((
                cKDTree(runtime_parts[pair[1]]).query(
                    runtime_parts[pair[0]][left_ids], k=1)[0],
                cKDTree(runtime_parts[pair[0]]).query(
                    runtime_parts[pair[1]][right_ids], k=1)[0]))
            metrics = {
                "minimum": max(0.0, float(
                    np.percentile(runtime_distance, 0)
                    - np.percentile(reference_distance, 0))) / body_height,
                "contactBandP05": max(0.0, float(
                    np.percentile(runtime_distance, 5)
                    - np.percentile(reference_distance, 5))) / body_height,
                "openingP95": max(0.0, float(
                    np.percentile(runtime_distance, 95)
                    - np.percentile(reference_distance, 95))) / body_height,
            }
            for metric, target in (
                    ("minimum", seam_contact_worst),
                    ("contactBandP05", seam_band_worst),
                    ("openingP95", seam_opening_worst)):
                if metrics[metric] > target["fraction"]:
                    target.clear()
                    target.update({"fraction": metrics[metric],
                                   "pose": key[0], "frame": key[1],
                                   "pair": list(pair)})
        runtime_armor = np.concatenate(list(runtime_parts.values()), axis=0)
        clearance = cKDTree(runtime_armor).query(
            skinned[key][sample_indices], k=1)[0]
        drop_fraction = float(np.percentile(
            np.maximum(0.0, reference_clearance - clearance), 95)
                              / body_height)
        drift_fraction = float(np.percentile(
            np.abs(reference_clearance - clearance), 95) / body_height)
        if drop_fraction > clearance_worst_drop["fraction"]:
            clearance_worst_drop = {"fraction": drop_fraction,
                                    "pose": key[0], "frame": key[1]}
        if drift_fraction > clearance_worst_drift["fraction"]:
            clearance_worst_drift = {"fraction": drift_fraction,
                                     "pose": key[0], "frame": key[1]}
    require(seam_contact_worst["fraction"]
            <= gates["seamMinimumGrowthHeightFraction"],
            f"rigid seam contact failed: {seam_contact_worst}")
    require(seam_band_worst["fraction"]
            <= gates["seamContactBandP05GrowthHeightFraction"],
            f"rigid seam contact band failed: {seam_band_worst}")
    require(clearance_worst_drop["fraction"]
            <= gates["clearanceP95DropHeightFraction"],
            f"inner/armor clearance drop failed: {clearance_worst_drop}")
    require(clearance_worst_drift["fraction"]
            <= gates["clearanceP95DriftHeightFraction"],
            f"inner/armor clearance drift failed: {clearance_worst_drift}")

    self_samples = []
    step = int(gates["selfIntersectionSampleStep"])
    for action in actions:
        count = int(action["framesPerView"])
        frames = sorted(set(range(1, count + 1, step)) | {count})
        for frame in frames:
            key = (action["pose"], frame)
            intersection = first_self_intersection(
                skinned[key], indices,
                int(gates["selfIntersectionExcludedTopologyHops"]))
            self_samples.append({"pose": key[0], "frame": frame,
                                 "intersection": intersection})
            require(intersection is None,
                    f"manifold self-intersection at {key}: {intersection}")

    report = {
        "schema": 1,
        "phase": "F",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "batch": batch.name,
        "captureDirectory": str(batch),
        "actions": len(actions),
        "views": len(views),
        "frames": len(records),
        "frontGeometryFrames": len(front_records),
        "selfIntersectionSamples": len(self_samples),
        "selfIntersectionExcludedTopologyHops":
            int(gates["selfIntersectionExcludedTopologyHops"]),
        "runtimeInvertedTriangles": 0,
        "runtimeCollapsedTriangles": 0,
        "maximumRuntimeOfflineBoundsDelta": maximum_bounds_delta,
        "maximumOrientationCorrection": runtime_correction,
        "maximumOrientationCorrectionHeightFraction":
            runtime_correction / body_height,
        "motionEvidence": motion_evidence,
        "tigerBodyHeight": body_height,
        "worstSeamMinimumGrowth": seam_contact_worst,
        "worstSeamContactBandP05Growth": seam_band_worst,
        "worstSeamOpeningP95Diagnostic": seam_opening_worst,
        "worstClearanceP95Drop": clearance_worst_drop,
        "worstClearanceP95Drift": clearance_worst_drift,
        "bodyModelTag": model_tag,
        "manifoldBodySha256": body_hash,
        "rigidMaskSha256": mask_hash,
        "tigerSemanticSha256": canonical_sha256(tiger),
        "contractSha256": raw_sha256(CONTRACT),
        "manualReviewStillRequired": True,
    }
    if report_path is None:
        report_path = batch / "phase_f_gate_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)
                           + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    batch = args.batch if args.batch else latest_batch()
    report = audit_capture(batch, args.report)
    print("EVA Phase-F capture gates passed: "
          f"batch={report['batch']} actions={report['actions']} "
          f"views={report['views']} frames={report['frames']} "
          f"selfSamples={report['selfIntersectionSamples']} "
          f"seamContact="
          f"{report['worstSeamMinimumGrowth']['fraction']:.8f} "
          f"clearanceDropP95="
          f"{report['worstClearanceP95Drop']['fraction']:.8f} "
          "result=ELIGIBLE_FOR_HUMAN_REVIEW_ONLY")


if __name__ == "__main__":
    main()
