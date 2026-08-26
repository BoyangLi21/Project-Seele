"""Audit the visible EVA shin/foot seam on an evaluated Blender rig.

This deliberately measures the rendered mesh, not just foot contact markers.
The EVA preview mesh is assembled from rigid armour pieces, so a perfectly
continuous bone hierarchy can still expose a large gap at the ankle.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mesh", default="EVA_ANATOMICAL_RIGID_MESH")
    parser.add_argument("--rig", default="EVA_ANATOMICAL_ARMATURE")
    parser.add_argument("--sample-step", type=int, default=1)
    parser.add_argument("--boundary-count", type=int, default=48)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def group_indices(obj: bpy.types.Object, name: str) -> list[int]:
    group = obj.vertex_groups.get(name)
    if group is None:
        raise RuntimeError(f"missing vertex group: {name}")
    return [
        vertex.index
        for vertex in obj.data.vertices
        if any(link.group == group.index and link.weight > 0.5
               for link in vertex.groups)
    ]


def group_faces(obj: bpy.types.Object, selected: set[int]) -> list[tuple[int, ...]]:
    return [
        tuple(polygon.vertices)
        for polygon in obj.data.polygons
        if all(index in selected for index in polygon.vertices)
    ]


def percentile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    return float(np.percentile(np.asarray(values, dtype=float), q))


def vector_tuple(value: Vector) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


args = parse_args()
scene = bpy.context.scene
mesh = bpy.data.objects[args.mesh]
rig = bpy.data.objects[args.rig]
depsgraph = bpy.context.evaluated_depsgraph_get()

parts: dict[str, dict[str, object]] = {}
for side in ("l", "r"):
    for part in ("shin", "foot"):
        name = f"{part}_{side}"
        indices = group_indices(mesh, name)
        parts[name] = {
            "indices": indices,
            "selected": set(indices),
            "faces": group_faces(mesh, set(indices)),
        }


def evaluated_geometry() -> tuple[bpy.types.Object, bpy.types.Mesh, list[Vector]]:
    evaluated = mesh.evaluated_get(depsgraph)
    evaluated_mesh = evaluated.to_mesh()
    points = [
        evaluated.matrix_world @ vertex.co.copy()
        for vertex in evaluated_mesh.vertices
    ]
    return evaluated, evaluated_mesh, points


def bvh_for(part_name: str, points: list[Vector]) -> BVHTree:
    part = parts[part_name]
    ordered = part["indices"]
    remap = {old: new for new, old in enumerate(ordered)}
    local_points = [points[index] for index in ordered]
    faces = [
        tuple(remap[index] for index in face)
        for face in part["faces"]
    ]
    return BVHTree.FromPolygons(local_points, faces, all_triangles=False)


def visible_bvh_for(part_name: str, points: list[Vector], side: str) -> BVHTree:
    part = parts[part_name]
    ordered = part["indices"]
    remap = {old: new for new, old in enumerate(ordered)}
    local_points = [points[index] for index in ordered]
    faces = [
        tuple(remap[index] for index in face)
        for face in part["faces"]
    ]
    sleeve = bpy.data.objects.get(
        f"EVA_ANKLE_JOINT_SLEEVE_{side.upper()}"
    )
    if sleeve is not None:
        sleeve_eval = sleeve.evaluated_get(depsgraph)
        sleeve_mesh = sleeve_eval.to_mesh()
        offset = len(local_points)
        local_points.extend(
            sleeve_eval.matrix_world @ vertex.co.copy()
            for vertex in sleeve_mesh.vertices
        )
        faces.extend(
            tuple(offset + index for index in polygon.vertices)
            for polygon in sleeve_mesh.polygons
        )
        sleeve_eval.to_mesh_clear()
    return BVHTree.FromPolygons(local_points, faces, all_triangles=False)


def nearest_distance(tree: BVHTree, point: Vector) -> float:
    hit = tree.find_nearest(point)
    return float(hit[3]) if hit is not None else math.inf


# Choose a stable interface ring once, at the first frame.  Subsequent frames
# measure those exact armour vertices against the other evaluated surface.
scene.frame_set(scene.frame_start)
bpy.context.view_layer.update()
evaluated, evaluated_mesh, initial_points = evaluated_geometry()
all_points = np.asarray([tuple(point) for point in initial_points], dtype=float)
height = float(np.max(all_points[:, 2]) - np.min(all_points[:, 2]))
if height <= 1.0e-8:
    raise RuntimeError("invalid zero-height EVA mesh")

boundary: dict[str, list[int]] = {}
baseline: dict[str, dict[str, float]] = {}
for side in ("l", "r"):
    shin_name = f"shin_{side}"
    foot_name = f"foot_{side}"
    foot_tree = bvh_for(foot_name, initial_points)
    shin_tree = bvh_for(shin_name, initial_points)
    shin_ranked = sorted(
        ((nearest_distance(foot_tree, initial_points[index]), index)
         for index in parts[shin_name]["indices"]),
        key=lambda item: item[0],
    )
    foot_ranked = sorted(
        ((nearest_distance(shin_tree, initial_points[index]), index)
         for index in parts[foot_name]["indices"]),
        key=lambda item: item[0],
    )
    count_shin = min(args.boundary_count, len(shin_ranked))
    count_foot = min(args.boundary_count, len(foot_ranked))
    boundary[shin_name] = [index for _, index in shin_ranked[:count_shin]]
    boundary[foot_name] = [index for _, index in foot_ranked[:count_foot]]
    visible_foot_tree = visible_bvh_for(foot_name, initial_points, side)
    visible_shin_tree = visible_bvh_for(shin_name, initial_points, side)
    visible_shin_distances = [
        nearest_distance(visible_foot_tree, initial_points[index])
        for index in boundary[shin_name]
    ]
    visible_foot_distances = [
        nearest_distance(visible_shin_tree, initial_points[index])
        for index in boundary[foot_name]
    ]
    baseline[side] = {
        "shin_to_foot_min_H": shin_ranked[0][0] / height,
        "shin_to_foot_boundary_p95_H": percentile(
            [value for value, _ in shin_ranked[:count_shin]], 95.0
        ) / height,
        "foot_to_shin_min_H": foot_ranked[0][0] / height,
        "foot_to_shin_boundary_p95_H": percentile(
            [value for value, _ in foot_ranked[:count_foot]], 95.0
        ) / height,
        "visible_shin_to_foot_boundary_p95_H": percentile(
            visible_shin_distances, 95.0
        ) / height,
        "visible_foot_to_shin_boundary_p95_H": percentile(
            visible_foot_distances, 95.0
        ) / height,
    }
evaluated.to_mesh_clear()


def bone_point(name: str, endpoint: str) -> Vector:
    pose_bone = rig.pose.bones[name]
    point = pose_bone.head if endpoint == "head" else pose_bone.tail
    return rig.matrix_world @ point


def relative_bone_rotation_degrees(parent_name: str, child_name: str) -> float:
    parent = rig.pose.bones[parent_name].matrix.to_quaternion()
    child = rig.pose.bones[child_name].matrix.to_quaternion()
    relative = parent.inverted() @ child
    return quaternion_shortest_angle_degrees(relative)


def quaternion_shortest_angle_degrees(rotation) -> float:
    rotation = rotation.normalized()
    return math.degrees(2.0 * math.acos(min(1.0, abs(rotation.w))))


def relative_bone_rotation(parent_name: str, child_name: str):
    parent = rig.pose.bones[parent_name].matrix.to_quaternion()
    child = rig.pose.bones[child_name].matrix.to_quaternion()
    return parent.inverted() @ child


baseline_relative_rotations = {
    side: relative_bone_rotation(f"shin_{side}", f"foot_{side}")
    for side in ("l", "r")
}


frames = list(range(
    int(scene.frame_start), int(scene.frame_end) + 1,
    max(1, args.sample_step),
))
samples: dict[str, list[dict[str, object]]] = {"l": [], "r": []}
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    evaluated, evaluated_mesh, points = evaluated_geometry()
    for side in ("l", "r"):
        shin_name = f"shin_{side}"
        foot_name = f"foot_{side}"
        foot_tree = visible_bvh_for(foot_name, points, side)
        shin_tree = visible_bvh_for(shin_name, points, side)
        shin_distances = [
            nearest_distance(foot_tree, points[index])
            for index in boundary[shin_name]
        ]
        foot_distances = [
            nearest_distance(shin_tree, points[index])
            for index in boundary[foot_name]
        ]
        shin_tail = bone_point(shin_name, "tail")
        foot_head = bone_point(foot_name, "head")
        relative_rotation = relative_bone_rotation(shin_name, foot_name)
        relative_delta = (
            baseline_relative_rotations[side].inverted() @ relative_rotation
        )
        samples[side].append({
            "frame": frame,
            "shin_to_foot_min_H": min(shin_distances) / height,
            "shin_to_foot_median_H": percentile(shin_distances, 50.0) / height,
            "shin_to_foot_p95_H": percentile(shin_distances, 95.0) / height,
            "foot_to_shin_min_H": min(foot_distances) / height,
            "foot_to_shin_median_H": percentile(foot_distances, 50.0) / height,
            "foot_to_shin_p95_H": percentile(foot_distances, 95.0) / height,
            "bone_endpoint_gap_H": (shin_tail - foot_head).length / height,
            "shin_foot_relative_rotation_degrees":
                relative_bone_rotation_degrees(shin_name, foot_name),
            "shin_foot_rotation_delta_from_baseline_degrees":
                quaternion_shortest_angle_degrees(relative_delta),
            "shin_tail": vector_tuple(shin_tail),
            "foot_head": vector_tuple(foot_head),
        })
    evaluated.to_mesh_clear()

summary: dict[str, dict[str, object]] = {}
for side in ("l", "r"):
    side_samples = samples[side]
    metric_names = (
        "shin_to_foot_min_H",
        "shin_to_foot_median_H",
        "shin_to_foot_p95_H",
        "foot_to_shin_min_H",
        "foot_to_shin_median_H",
        "foot_to_shin_p95_H",
        "bone_endpoint_gap_H",
        "shin_foot_relative_rotation_degrees",
        "shin_foot_rotation_delta_from_baseline_degrees",
    )
    side_summary: dict[str, object] = {}
    for metric in metric_names:
        maximum = max(side_samples, key=lambda item: float(item[metric]))
        side_summary[metric] = {
            "max": float(maximum[metric]),
            "max_frame": int(maximum["frame"]),
            "median": percentile(
                [float(item[metric]) for item in side_samples], 50.0
            ),
        }
    summary[side] = side_summary

bone_continuity_limit = 1.0e-5
mesh_growth_limit = 0.005
issues: list[str] = []
for side in ("l", "r"):
    bone_max = float(summary[side]["bone_endpoint_gap_H"]["max"])
    seam_max = float(summary[side]["shin_to_foot_p95_H"]["max"])
    seam_base = float(
        baseline[side]["visible_shin_to_foot_boundary_p95_H"]
    )
    if bone_max > bone_continuity_limit:
        issues.append(
            f"{side}: shin/foot bone endpoints separate by {bone_max:.6f} H"
        )
    if seam_max - seam_base > mesh_growth_limit:
        issues.append(
            f"{side}: visible shin/foot seam grows by "
            f"{seam_max - seam_base:.6f} H"
        )

payload = {
    "schema": 1,
    "blend": bpy.data.filepath,
    "scene_frames": [int(scene.frame_start), int(scene.frame_end)],
    "sampled_frames": len(frames),
    "body_height": height,
    "boundary_vertex_count": args.boundary_count,
    "visual_sleeves": {
        side: bpy.data.objects.get(
            f"EVA_ANKLE_JOINT_SLEEVE_{side.upper()}"
        ) is not None
        for side in ("l", "r")
    },
    "baseline": baseline,
    "summary": summary,
    "issues": issues,
    "verdict": "FAIL" if issues else "PASS",
    "samples": samples,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(
    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "output": str(args.output),
    "verdict": payload["verdict"],
    "issues": issues,
    "summary": summary,
}, ensure_ascii=False))
