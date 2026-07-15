#!/usr/bin/env python3
"""Render a local EVA rigid mesh with its real GeckoLib animation pose.

This is an intentionally small, offline visual-feedback loop.  It reads the
same generated triangle mesh, texture, Bedrock geometry skeleton and animation
JSON used by the game, samples one animation at a requested time, applies the
bone transforms through the parent hierarchy, then writes orthographic views.

``--first-person-stance`` switches the output to a perspective diagnostic that
uses Unit-01's real rider eye/forward sockets and Visual Lab pitch angles.  It
renders the same world-body mesh (with the enclosing head hidden, as it is in
game) instead of inventing a detached arm viewmodel.

The older ``--pose identity|stress`` mode is retained for converter smoke tests.
For animation work prefer ``--animation-json`` and ``--animation``.
"""

import argparse
import json
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from PIL import Image


DEFAULT_PARENT = {
    "torso_lower": "root", "torso_upper": "torso_lower", "head": "torso_upper",
    "pylon_l": "torso_upper", "pylon_r": "torso_upper",
    "arm_l": "torso_upper", "forearm_l": "arm_l", "hand_l": "forearm_l",
    "arm_r": "torso_upper", "forearm_r": "arm_r", "hand_r": "forearm_r",
    "leg_l": "torso_lower", "shin_l": "leg_l",
    "leg_r": "torso_lower", "shin_r": "leg_r",
}

STRESS_ROTATION = {
    "torso_lower": (0, 0, -3), "torso_upper": (0, 0, 6), "head": (0, 12, -3),
    "arm_l": (0, 0, -58), "forearm_l": (-20, 0, -18), "hand_l": (0, 0, 8),
    "arm_r": (0, 0, 58), "forearm_r": (-20, 0, 18), "hand_r": (0, 0, -8),
    "leg_l": (0, 0, -8), "shin_l": (8, 0, 4),
    "leg_r": (0, 0, 8), "shin_r": (8, 0, -4),
}

VIEW_AXES = {
    # Tiger's OBJ was reflected on Z during conversion and the game reflects X
    # at emission.  These labels match the established in-game capture rig.
    "front": lambda point: (-point[0], point[1], -point[2]),
    "left": lambda point: (point[2], point[1], -point[0]),
    "side": lambda point: (point[2], point[1], -point[0]),
    "back": lambda point: (point[0], point[1], point[2]),
    "right": lambda point: (-point[2], point[1], point[0]),
}

# Keep these values in lockstep with EvaUnit01Entity.positionRider() and
# VisualCaptureManager.maintainFirstPerson().  Gecko's renderer emits one
# model pixel as 1/16 block and EvaUnit01Renderer applies scale 2.5.
MODEL_PIXELS_PER_BLOCK = 16.0 / 2.5
FIRST_PERSON_SOCKETS = {
    "standing": {"eye_height": 24.63, "forward": 1.00},
    "crouch": {"eye_height": 19.70, "forward": 0.80},
    "prone": {"eye_height": 7.00, "forward": 12.00},
}
FIRST_PERSON_PITCH = {
    "forward": 12.0,
    "pitch_down": 70.0,
}
FIRST_PERSON_HIDDEN_ROOTS = {
    "head", "Head", "horn", "Horn", "neck", "Neck",
}
FIRST_PERSON_CAMERA_COVER_PARTS = {
    "standing": {"torso_lower", "torso_upper", "pylon_l", "pylon_r"},
    "crouch": {"torso_lower", "torso_upper", "pylon_l", "pylon_r"},
    "prone": {"torso_lower", "torso_upper", "pylon_l", "pylon_r"},
}


def model_identity(mesh_path):
    """Return a collision-safe output slug and readable Unit label."""
    name = mesh_path.name
    stem = name[:-len(".mesh.json")] if name.endswith(".mesh.json") else mesh_path.stem
    match = re.search(r"(?:eva_)?unit(\d+)", stem, re.IGNORECASE)
    if match:
        number = match.group(1)
        return f"unit{number}", f"UNIT-{number}"
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", stem).strip("_").lower() or "model"
    return safe, safe.replace("_", " ").upper()


def identity():
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def multiply(left, right):
    return [[sum(left[row][index] * right[index][column] for index in range(4))
             for column in range(4)] for row in range(4)]


def translation(values):
    matrix = identity()
    matrix[0][3], matrix[1][3], matrix[2][3] = values
    return matrix


def rotation(values):
    """Bedrock/Blockbench XYZ Euler values, in degrees.

    GeckoLib applies X, then Y, then Z to a column vector, represented here as
    Rz * Ry * Rx.  The model-space X reflection happens later in the game mesh
    emitter and is instead handled by the view convention above.
    """
    x, y, z = (math.radians(float(value)) for value in values)
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


def vector(value, label):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must be a three-number vector, got {value!r}")
    try:
        return tuple(float(component) for component in value)
    except (TypeError, ValueError) as exception:
        raise ValueError(f"Molang expressions are not supported in {label}: {value!r}") from exception


def sample_channel(channel, time, label):
    """Linearly sample the keyframe subset used by Project SEELE animations."""
    if isinstance(channel, list):
        return vector(channel, label)
    if not isinstance(channel, dict) or not channel:
        raise ValueError(f"{label} is not a supported Gecko channel")

    keyframes = sorted((float(key), vector(value, f"{label}@{key}"))
                       for key, value in channel.items())
    if time <= keyframes[0][0]:
        return keyframes[0][1]
    if time >= keyframes[-1][0]:
        return keyframes[-1][1]
    for (left_time, left), (right_time, right) in zip(keyframes, keyframes[1:]):
        if left_time <= time <= right_time:
            alpha = (time - left_time) / (right_time - left_time)
            return tuple(left[index] + (right[index] - left[index]) * alpha
                         for index in range(3))
    raise AssertionError("unreachable animation sample")


def select_animation(path, requested, time):
    data = json.loads(path.read_text(encoding="utf-8"))
    animations = data.get("animations", {})
    candidates = [requested]
    if not requested.startswith("animation."):
        candidates.extend((f"animation.eva_unit01.{requested}",
                           f"animation.{requested}"))
    name = next((candidate for candidate in candidates if candidate in animations), None)
    if name is None:
        available = ", ".join(sorted(animations))
        raise ValueError(f"animation {requested!r} not found; available: {available}")
    animation = animations[name]
    length = float(animation.get("animation_length", 0.0))
    sample_time = float(time)
    if animation.get("loop") is True and length > 0:
        sample_time %= length
    elif length > 0:
        sample_time = min(max(sample_time, 0.0), length)

    rotations = {}
    positions = {}
    for bone, channels in animation.get("bones", {}).items():
        if "rotation" in channels:
            rotations[bone] = sample_channel(
                channels["rotation"], sample_time, f"{name}/{bone}/rotation")
        if "position" in channels:
            positions[bone] = sample_channel(
                channels["position"], sample_time, f"{name}/{bone}/position")
    return name, sample_time, rotations, positions


def discover_geo(mesh_path, explicit):
    if explicit:
        return explicit
    mesh_name = mesh_path.name
    model_name = (mesh_name[:-len(".mesh.json")]
                  if mesh_name.endswith(".mesh.json") else mesh_path.stem)
    candidate = mesh_path.parent.parent / "geo" / f"{model_name}.geo.json"
    return candidate if candidate.exists() else None


def load_skeleton(mesh, geo_path):
    # BakedModelFactory reflects Bedrock's bone pivot on X before Gecko's
    # renderer ever sees it.  The local triangle layer likewise reflects each
    # emitted vertex on X.  Applying only the latter made rotated parts orbit
    # around the opposite shoulder: an idle pose looked plausible while every
    # weapon pose exploded sideways in the real client.
    pivots = {
        bone: (-float(part["pivot"][0]), float(part["pivot"][1]),
               float(part["pivot"][2]))
        for bone, part in mesh["parts"].items()
    }
    parents = dict(DEFAULT_PARENT)
    base_rotations = {}
    if geo_path:
        data = json.loads(geo_path.read_text(encoding="utf-8"))
        geometry = data["minecraft:geometry"][0]
        for bone in geometry["bones"]:
            name = bone["name"]
            if "pivot" in bone:
                raw_pivot = vector(bone["pivot"], f"geo/{name}/pivot")
                pivots[name] = (-raw_pivot[0], raw_pivot[1], raw_pivot[2])
            if "parent" in bone:
                parents[name] = bone["parent"]
            if "rotation" in bone:
                base_rotations[name] = vector(bone["rotation"], f"geo/{name}/rotation")
    pivots.setdefault("root", (0.0, 0.0, 0.0))
    return pivots, parents, base_rotations


def load_geo_cube_mesh(geo_path, requested_bones):
    """Convert selected Bedrock cubes into preview triangles.

    Formal EVA bodies come from rigid triangle meshes; weapons, shield and
    entry-plug hardware intentionally remain Gecko cubes.  Older previews
    ignored those cubes entirely and could therefore approve an invisible or
    ground-penetrating attachment.  This small converter keeps cube origins in
    the same absolute Bedrock coordinate space and samples their atlas region.
    """
    if not geo_path:
        raise ValueError("--geo-cube-bone requires --geo")
    data = json.loads(geo_path.read_text(encoding="utf-8"))
    geometry = data["minecraft:geometry"][0]
    description = geometry.get("description", {})
    texture_width = float(description.get("texture_width", 16))
    texture_height = float(description.get("texture_height", 16))
    by_name = {bone.get("name"): bone for bone in geometry.get("bones", [])}
    missing = sorted(set(requested_bones) - set(by_name))
    if missing:
        raise ValueError(f"geo cube bones not found: {', '.join(missing)}")

    face_indices = {
        "north": ((1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)),
        "south": ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
        "east": ((1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1)),
        "west": ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
        "up": ((0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)),
        "down": ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
    }
    normals = {
        "north": (0, 0, -1), "south": (0, 0, 1),
        "east": (1, 0, 0), "west": (-1, 0, 0),
        "up": (0, 1, 0), "down": (0, -1, 0),
    }
    parts = {}
    for name in requested_bones:
        bone = by_name[name]
        pivot = [float(value) for value in bone.get("pivot", (0, 0, 0))]
        values = []
        for cube in bone.get("cubes", []):
            origin = [float(value) for value in cube["origin"]]
            size = [float(value) for value in cube["size"]]
            uv = cube.get("uv", (0, 0))
            cube_rotation = cube.get("rotation", (0, 0, 0))
            cube_pivot = [float(value) for value in cube.get("pivot", pivot)]
            rotate = rotation(cube_rotation)
            cube_matrix = multiply(translation(cube_pivot), multiply(
                rotate, translation(tuple(-value for value in cube_pivot))))
            for face, corners in face_indices.items():
                if isinstance(uv, dict):
                    face_uv = uv.get(face, {}).get("uv", (0, 0))
                else:
                    face_uv = uv
                u = (float(face_uv[0]) + 0.5) / texture_width
                v = (float(face_uv[1]) + 0.5) / texture_height
                normal = transform(rotate, normals[face])
                points = []
                for corner in corners:
                    absolute = [origin[axis] + size[axis] * corner[axis]
                                for axis in range(3)]
                    absolute = transform(cube_matrix, absolute)
                    points.append([absolute[axis] - pivot[axis] for axis in range(3)])
                for index in (0, 1, 2, 0, 2, 3):
                    values.extend((*points[index], u, v, *normal))
        if values:
            parts[name] = {"pivot": pivot, "vertices": values}
    if not parts:
        raise ValueError("selected geo cube bones contain no cubes")
    return {"stride": 8, "parts": parts}


def bone_matrix(bone, pivots, parents, rotations, positions, base_rotations, cache, active=None):
    """Return GeckoLib's exact per-bone PoseStack deformation matrix.

    ``BakedModelFactory`` negates bone-pivot X and Bedrock rotation X/Y;
    ``RenderUtils.translateMatrixToBone`` also negates animated X position.
    The local triangle layer then reflects emitted vertex X, matching Gecko's
    baked cubes.  All four conversions are required for the preview to agree
    with the real client once a limb leaves its bind pose.
    """
    if bone in cache:
        return cache[bone]
    if active is None:
        active = set()
    if bone in active:
        raise ValueError(f"cyclic bone hierarchy at {bone}")
    active.add(bone)
    parent = parents.get(bone)
    parent_matrix = (identity() if parent is None else
                     bone_matrix(parent, pivots, parents, rotations, positions,
                                 base_rotations, cache, active))
    pivot = pivots.get(bone, (0.0, 0.0, 0.0))
    position = positions.get(bone, (0.0, 0.0, 0.0))
    animated_rotation = rotations.get(bone, (0.0, 0.0, 0.0))
    bind_rotation = base_rotations.get(bone, (0.0, 0.0, 0.0))
    raw_rotation = tuple(bind_rotation[index] + animated_rotation[index]
                         for index in range(3))
    combined_rotation = (-raw_rotation[0], -raw_rotation[1], raw_rotation[2])
    runtime_position = (-position[0], position[1], position[2])
    local = multiply(translation(runtime_position),
                     multiply(translation(pivot),
                              multiply(rotation(combined_rotation),
                                       translation(tuple(-value for value in pivot)))))
    cache[bone] = multiply(parent_matrix, local)
    active.remove(bone)
    return cache[bone]


def project(point, view):
    return VIEW_AXES[view](point)


def collect_scene(mesh, texture_path, view, matrices, pivots, parents,
                  attachments=(), isolated_bones=()):
    triangles = []
    transformed_by_bone = {}
    isolated = set(isolated_bones)
    for source_mesh, source_texture in ((mesh, texture_path), *attachments):
        texture = Image.open(source_texture).convert("RGB")
        pixels = texture.load()
        width, height = texture.size
        stride = int(source_mesh["stride"])
        if stride != 8:
            raise ValueError(f"expected stride 8, got {stride}")
        for bone, part in source_mesh["parts"].items():
            if isolated and bone not in isolated:
                continue
            matrix = matrices[bone]
            pivot = part["pivot"]
            values = part["vertices"]
            transformed_by_bone[bone] = transform(matrix, pivots[bone])
            for start in range(0, len(values), stride * 3):
                points = []
                uvs = []
                for vertex in range(3):
                    index = start + vertex * stride
                    absolute = [values[index + axis] + pivot[axis] for axis in range(3)]
                    emitted = [-absolute[0], absolute[1], absolute[2]]
                    points.append(project(transform(matrix, emitted), view))
                    uvs.append(values[index + 3:index + 5])
                u = sum(value[0] for value in uvs) / 3.0
                v = sum(value[1] for value in uvs) / 3.0
                colour = pixels[min(width - 1, max(0, int(u * width))),
                                min(height - 1, max(0, int(v * height)))]
                triangles.append((sum(point[2] for point in points) / 3.0,
                                  [point[:2] for point in points],
                                  tuple(channel / 255.0 for channel in colour) + (1.0,), bone))
    triangles.sort(key=lambda item: item[0])

    joints = {bone: project(point, view) for bone, point in transformed_by_bone.items()}
    segments = []
    for bone, parent in parents.items():
        if bone in joints and parent in joints:
            segments.append((joints[parent][:2], joints[bone][:2]))
    return triangles, joints, segments


def hidden_bones(parents, roots):
    """Return renderer-style hidden roots plus every descendant."""
    hidden = set(roots)
    changed = True
    while changed:
        changed = False
        for bone, parent in parents.items():
            if parent in hidden and bone not in hidden:
                hidden.add(bone)
                changed = True
    return hidden


def first_person_camera(stance, view, eye_height=None, forward_offset=None,
                        right_offset=None):
    """Return camera position and orthonormal axes in model-pixel space.

    Tiger/SmOd's face and horn point toward local -Z. ``forward`` uses the
    positive Java positionRider convention for every stance; the preview's
    model-space camera Z is ``-forward``, matching the rendered face direction.
    The prone spine rotates its head socket forward without reversing that sign.
    Vertex emission has already reflected model X before this function sees
    the posed point.  A pilot looking along model -Z therefore uses +X as
    screen-right.  Reusing the front inspection camera's -X axis here mirrors
    left and right hands a second time.
    """
    socket = FIRST_PERSON_SOCKETS[stance]
    effective_eye_height = (socket["eye_height"] if eye_height is None
                            else float(eye_height))
    effective_forward = (socket["forward"] if forward_offset is None
                         else float(forward_offset))
    pitch_degrees = FIRST_PERSON_PITCH[view]
    pitch = math.radians(pitch_degrees)
    effective_right = 0.0 if right_offset is None else float(right_offset)
    camera = (effective_right * MODEL_PIXELS_PER_BLOCK,
              effective_eye_height * MODEL_PIXELS_PER_BLOCK,
              -effective_forward * MODEL_PIXELS_PER_BLOCK)
    right = (1.0, 0.0, 0.0)
    forward = (0.0, -math.sin(pitch), -math.cos(pitch))
    up = (0.0, math.cos(pitch), -math.sin(pitch))
    return (camera, right, up, forward, pitch_degrees,
            effective_eye_height, effective_forward)


def camera_point(point, camera, right, up, forward):
    relative = tuple(point[index] - camera[index] for index in range(3))
    return (sum(relative[index] * right[index] for index in range(3)),
            sum(relative[index] * up[index] for index in range(3)),
            sum(relative[index] * forward[index] for index in range(3)))


def clip_near_plane(polygon, near):
    """Clip a camera-space polygon against positive depth >= near."""
    if not polygon:
        return []
    output = []
    previous = polygon[-1]
    previous_inside = previous[2] >= near
    for current in polygon:
        current_inside = current[2] >= near
        if current_inside != previous_inside:
            denominator = current[2] - previous[2]
            alpha = 0.0 if denominator == 0.0 else (near - previous[2]) / denominator
            output.append(tuple(previous[index] +
                                (current[index] - previous[index]) * alpha
                                for index in range(3)))
        if current_inside:
            output.append(current)
        previous = current
        previous_inside = current_inside
    return output


def first_person_projection(point, tangent):
    return (point[0] / (point[2] * tangent),
            point[1] / (point[2] * tangent))


def viewport_intersection(polygon, aspect):
    if not polygon:
        return None
    minimum_x = max(-aspect, min(point[0] for point in polygon))
    maximum_x = min(aspect, max(point[0] for point in polygon))
    minimum_y = max(-1.0, min(point[1] for point in polygon))
    maximum_y = min(1.0, max(point[1] for point in polygon))
    if minimum_x > maximum_x or minimum_y > maximum_y:
        return None
    return minimum_x, minimum_y, maximum_x, maximum_y


def collect_first_person_scene(mesh, texture_path, matrices, pivots, parents,
                               stance, view, fov, aspect, near_blocks,
                               eye_height=None, forward_offset=None, right_offset=None,
                               extra_hidden=(), attachments=()):
    (camera, right, up, forward, pitch, effective_eye_height,
     effective_forward) = first_person_camera(
        stance, view, eye_height, forward_offset, right_offset)
    near = near_blocks * MODEL_PIXELS_PER_BLOCK
    tangent = math.tan(math.radians(fov) / 2.0)
    camera_cover_hidden = hidden_bones(parents, FIRST_PERSON_HIDDEN_ROOTS)
    exact_hidden = set(FIRST_PERSON_CAMERA_COVER_PARTS.get(stance, ()))
    # Preview-only exact mesh-part suppression. Unlike the renderer's camera
    # roots this deliberately does not hide descendants, so a pylon comparison
    # cannot accidentally remove the shared torso/arm hierarchy.
    exact_hidden.update(extra_hidden)
    hidden = camera_cover_hidden | exact_hidden
    triangles = []
    visible_bounds = {}
    for source_mesh, source_texture in ((mesh, texture_path), *attachments):
        texture = Image.open(source_texture).convert("RGB")
        pixels = texture.load()
        width, height = texture.size
        stride = int(source_mesh["stride"])
        if stride != 8:
            raise ValueError(f"expected stride 8, got {stride}")
        for bone, part in source_mesh["parts"].items():
            if bone in hidden:
                continue
            matrix = matrices[bone]
            pivot = part["pivot"]
            values = part["vertices"]
            for start in range(0, len(values), stride * 3):
                camera_polygon = []
                uvs = []
                for vertex in range(3):
                    index = start + vertex * stride
                    absolute = [values[index + axis] + pivot[axis] for axis in range(3)]
                    emitted = [-absolute[0], absolute[1], absolute[2]]
                    posed = transform(matrix, emitted)
                    camera_polygon.append(camera_point(posed, camera, right, up, forward))
                    uvs.append(values[index + 3:index + 5])
                camera_polygon = clip_near_plane(camera_polygon, near)
                if len(camera_polygon) < 3:
                    continue
                polygon = [first_person_projection(point, tangent)
                           for point in camera_polygon]
                u = sum(value[0] for value in uvs) / 3.0
                v = sum(value[1] for value in uvs) / 3.0
                colour = pixels[min(width - 1, max(0, int(u * width))),
                                min(height - 1, max(0, int(v * height)))]
                triangles.append((sum(point[2] for point in camera_polygon) /
                                  len(camera_polygon), polygon,
                                  tuple(channel / 255.0 for channel in colour) + (1.0,), bone))
                clipped_bounds = viewport_intersection(polygon, aspect)
                if clipped_bounds is not None:
                    bounds = visible_bounds.setdefault(
                        bone, [float("inf"), float("inf"),
                               float("-inf"), float("-inf"), 0])
                    bounds[0] = min(bounds[0], clipped_bounds[0])
                    bounds[1] = min(bounds[1], clipped_bounds[1])
                    bounds[2] = max(bounds[2], clipped_bounds[2])
                    bounds[3] = max(bounds[3], clipped_bounds[3])
                    bounds[4] += 1
    # Painter's algorithm: distant geometry first, nearby geometry last.
    triangles.sort(key=lambda item: item[0], reverse=True)

    joint_camera = {
        bone: camera_point(transform(matrices[bone], pivots[bone]),
                           camera, right, up, forward)
        for bone in matrices if bone in pivots and bone not in hidden
    }
    joints = {bone: first_person_projection(point, tangent)
              for bone, point in joint_camera.items() if point[2] >= near}
    segments = []
    for bone, parent in parents.items():
        if bone in joints and parent in joints:
            segments.append((joints[parent], joints[bone]))

    def group_metrics(names):
        available = [visible_bounds[name] for name in names if name in visible_bounds]
        if not available:
            return {"visible_polygons": 0, "viewport_bbox": None,
                    "horizontal_centre": None}
        box = [min(item[0] for item in available), min(item[1] for item in available),
               max(item[2] for item in available), max(item[3] for item in available)]
        return {
            "visible_polygons": sum(item[4] for item in available),
            "viewport_bbox": [round(value, 4) for value in box],
            "horizontal_centre": round((box[0] + box[2]) / 2.0, 4),
        }

    left = group_metrics(("arm_l", "forearm_l", "hand_l"))
    right_arm = group_metrics(("arm_r", "forearm_r", "hand_r"))
    bone_visibility = {
        bone: {
            "visible_polygons": values[4],
            "viewport_bbox": [round(value, 4) for value in values[:4]],
        }
        for bone, values in sorted(visible_bounds.items())
    }
    diagnostic = {
        "source_contract": {
            "renderer_scale": 2.5,
            "model_pixels_per_block": MODEL_PIXELS_PER_BLOCK,
            "model_forward_axis": "local -Z (horn direction)",
            "camera_local_position_model_pixels": [round(value, 4) for value in camera],
            "view_forward_model": [round(value, 6) for value in forward],
            "eye_height_blocks": effective_eye_height,
            "forward_blocks": effective_forward,
            "pitch_degrees": pitch,
            "vertical_fov_degrees": fov,
            "aspect": aspect,
            "near_plane_blocks": near_blocks,
            "camera_cover_hidden_bones": sorted(
                camera_cover_hidden.intersection(mesh["parts"])),
            "exact_hidden_mesh_parts": sorted(exact_hidden.intersection(mesh["parts"])),
            "hidden_bones": sorted(hidden.intersection(mesh["parts"])),
        },
        "left_arm": left,
        "right_arm": right_arm,
        "bone_visibility": bone_visibility,
        "both_arm_regions_visible": (left["visible_polygons"] > 0 and
                                     right_arm["visible_polygons"] > 0),
        "arms_read_on_opposite_sides": (
            left["horizontal_centre"] is not None and
            right_arm["horizontal_centre"] is not None and
            left["horizontal_centre"] < 0.0 < right_arm["horizontal_centre"]),
        "visibility_note": ("polygon/viewport intersection before depth occlusion; "
                            "the PNG is authoritative for final visibility"),
    }
    return (triangles, joints, segments), diagnostic


def scene_bounds(scene_by_view, focus_bones=(), padding=1.12):
    """Return one comparable square bound for every requested view.

    ``focus_bones`` is a review aid for hand/weapon and joint close-ups.  It
    changes only the camera crop; the complete body is still transformed and
    rendered, so parent-chain mistakes remain visible if they enter the crop.
    """
    focus = set(focus_bones)
    xs = []
    ys = []
    for triangles, _, _ in scene_by_view.values():
        selected = [item for item in triangles if not focus or item[3] in focus]
        xs.extend(point[0] for _, polygon, _, _ in selected for point in polygon)
        ys.extend(point[1] for _, polygon, _, _ in selected for point in polygon)
    if not xs or not ys:
        requested = ", ".join(sorted(focus)) if focus else "entire mesh"
        raise ValueError(f"mesh contains no renderable triangles for {requested}")
    centre_x = (min(xs) + max(xs)) / 2.0
    centre_y = (min(ys) + max(ys)) / 2.0
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0) * padding
    return centre_x, centre_y, span, min(ys), max(ys)


def pose_metrics(mesh, matrices, pivots, positions, attachments=()):
    """Return contact and joint data in unprojected model-pixel coordinates."""
    bone_bounds = {}
    attachment_endpoints = {}
    overall_minimum = float("inf")
    overall_maximum = float("-inf")
    for mesh_index, source_mesh in enumerate((mesh, *attachments)):
        stride = int(source_mesh["stride"])
        for bone, part in source_mesh["parts"].items():
            values = part["vertices"]
            posed_vertices = []
            minimum = float("inf")
            maximum = float("-inf")
            minimum_xyz = [float("inf"), float("inf"), float("inf")]
            maximum_xyz = [float("-inf"), float("-inf"), float("-inf")]
            for index in range(0, len(values), stride):
                absolute = [values[index + axis] + part["pivot"][axis] for axis in range(3)]
                emitted = [-absolute[0], absolute[1], absolute[2]]
                posed = transform(matrices[bone], emitted)
                posed_vertices.append(posed)
                y = posed[1]
                minimum = min(minimum, y)
                maximum = max(maximum, y)
                for axis in range(3):
                    minimum_xyz[axis] = min(minimum_xyz[axis], posed[axis])
                    maximum_xyz[axis] = max(maximum_xyz[axis], posed[axis])
            key = bone if mesh_index == 0 else f"attachment:{bone}"
            bone_bounds[key] = {
                "min_y": round(minimum, 4),
                "max_y": round(maximum, 4),
                "min_xyz": [round(value, 4) for value in minimum_xyz],
                "max_xyz": [round(value, 4) for value in maximum_xyz],
            }
            if mesh_index > 0 and posed_vertices:
                emitted_pivot = [-part["pivot"][0], part["pivot"][1],
                                 part["pivot"][2]]
                pivot_world = transform(matrices[bone], emitted_pivot)
                distances = [math.sqrt(sum((vertex[axis] - pivot_world[axis]) ** 2
                                                   for axis in range(3)))
                             for vertex in posed_vertices]
                maximum_distance = max(distances)
                # Average the far cap instead of reporting one arbitrary cube
                # corner.  This makes the vector stable for a knife blade,
                # cannon muzzle and the forked Longinus tip alike.
                tolerance = max(0.25, maximum_distance * 0.02)
                far_vertices = [vertex for vertex, distance in zip(posed_vertices, distances)
                                if distance >= maximum_distance - tolerance]
                endpoint = [sum(vertex[axis] for vertex in far_vertices) / len(far_vertices)
                            for axis in range(3)]
                vector = [endpoint[axis] - pivot_world[axis] for axis in range(3)]
                attachment_endpoints[key] = {
                    "pivot": [round(value, 4) for value in pivot_world],
                    "far_endpoint": [round(value, 4) for value in endpoint],
                    "vector_from_pivot": [round(value, 4) for value in vector],
                    "length": round(math.sqrt(sum(value * value for value in vector)), 4),
                    "far_cap_vertex_count": len(far_vertices),
                }
            overall_minimum = min(overall_minimum, minimum)
            overall_maximum = max(overall_maximum, maximum)
    joints = {bone: [round(value, 4) for value in transform(matrix, pivots[bone])]
              for bone, matrix in matrices.items() if bone in pivots}
    hand_distance = None
    if "hand_l" in joints and "hand_r" in joints:
        hand_distance = math.sqrt(sum((joints["hand_l"][axis] - joints["hand_r"][axis]) ** 2
                                      for axis in range(3)))
    return {
        "ground_contract": "bind-pose foot plane y=0; model coordinates are Bedrock pixels",
        "overall_min_y": round(overall_minimum, 4),
        "overall_max_y": round(overall_maximum, 4),
        "root_position": [round(value, 4) for value in positions.get("root", (0, 0, 0))],
        "bone_bounds": bone_bounds,
        "attachment_endpoints": attachment_endpoints,
        "joint_world": joints,
        "hand_pivot_distance": None if hand_distance is None else round(hand_distance, 4),
    }


def render_scene(scene, view, output, title, bounds, skeleton):
    triangles, joints, segments = scene
    centre_x, centre_y, span, minimum_y, _ = bounds
    figure, axis = plt.subplots(figsize=(8, 8), dpi=160)
    figure.patch.set_facecolor("#20232a")
    axis.set_facecolor("#20232a")
    axis.add_collection(PolyCollection(
        [item[1] for item in triangles],
        facecolors=[item[2] for item in triangles],
        edgecolors=(0.04, 0.04, 0.06, 0.32), linewidths=0.16))
    # Bind-space ground is diagnostically useful: red below it means the pose
    # relies on world clipping/translation rather than actual foot placement.
    axis.axhline(0.0, color=(0.95, 0.2, 0.18, 0.72), linewidth=0.9, linestyle="--")
    if skeleton:
        axis.add_collection(LineCollection(segments, colors=(0.1, 0.95, 0.95, 0.82),
                                           linewidths=1.0, zorder=5))
        for bone, point in joints.items():
            if bone in {"arm_l", "arm_r", "forearm_l", "forearm_r", "hand_l", "hand_r",
                        "leg_l", "leg_r", "shin_l", "shin_r", "head", "torso_lower"}:
                axis.scatter(point[0], point[1], s=8, color="#ffcf33", zorder=6)
    axis.set_xlim(centre_x - span / 2.0, centre_x + span / 2.0)
    axis.set_ylim(centre_y - span / 2.0, centre_y + span / 2.0)
    axis.set_aspect("equal")
    axis.axis("off")
    below = " / BELOW GROUND" if minimum_y < -0.5 else ""
    axis.text(0.02, 0.98, f"{title} / {view.upper()}{below}", color="#f0a000",
              fontsize=10, ha="left", va="top", transform=axis.transAxes)
    figure.savefig(output, bbox_inches="tight", pad_inches=0.08,
                   facecolor=figure.get_facecolor())
    plt.close(figure)


def render_first_person_scene(scene, view, stance, output, title, aspect, skeleton):
    triangles, joints, segments = scene
    figure = plt.figure(figsize=(12.8, 7.2), dpi=100)
    figure.patch.set_facecolor("#7fa8df")
    axis = figure.add_axes((0, 0, 1, 1))
    axis.set_facecolor("#7fa8df")
    axis.add_collection(PolyCollection(
        [item[1] for item in triangles],
        facecolors=[item[2] for item in triangles],
        edgecolors=(0.04, 0.04, 0.06, 0.28), linewidths=0.22))
    if skeleton:
        visible_segments = [segment for segment in segments
                            if viewport_intersection(segment, aspect) is not None]
        axis.add_collection(LineCollection(visible_segments,
                                           colors=(0.1, 0.95, 0.95, 0.78),
                                           linewidths=1.25, zorder=5))
        for bone, point in joints.items():
            if (bone in {"arm_l", "arm_r", "forearm_l", "forearm_r",
                         "hand_l", "hand_r", "torso_lower", "torso_upper"}
                    and -aspect <= point[0] <= aspect and -1.0 <= point[1] <= 1.0):
                axis.scatter(point[0], point[1], s=12, color="#ffcf33", zorder=6)
    # A restrained crosshair and thirds make side placement reviewable while
    # leaving the mesh itself unobscured.
    axis.plot((-0.018, 0.018), (0.0, 0.0), color=(1.0, 0.7, 0.1, 0.8),
              linewidth=1.0, zorder=8)
    axis.plot((0.0, 0.0), (-0.032, 0.032), color=(1.0, 0.7, 0.1, 0.8),
              linewidth=1.0, zorder=8)
    for x in (-aspect / 3.0, aspect / 3.0):
        axis.axvline(x, color=(1.0, 1.0, 1.0, 0.10), linewidth=0.7)
    axis.set_xlim(-aspect, aspect)
    axis.set_ylim(-1.0, 1.0)
    axis.set_aspect("equal")
    axis.axis("off")
    axis.text(0.012, 0.982,
              f"{title} / FIRST PERSON {stance.upper()} {view.upper()}",
              color="#f0a000", fontsize=10, ha="left", va="top",
              transform=axis.transAxes,
              bbox={"facecolor": (0.06, 0.07, 0.09, 0.72), "edgecolor": "none", "pad": 4})
    figure.savefig(output, dpi=100, facecolor=figure.get_facecolor())
    plt.close(figure)


def write_contact_sheet(paths, output, title):
    images = [Image.open(path).convert("RGB") for path in paths]
    width = max(image.width for image in images)
    height = max(image.height for image in images)
    sheet = Image.new("RGB", (width * len(images), height + 36), "#20232a")
    for index, image in enumerate(images):
        sheet.paste(image, (index * width + (width - image.width) // 2, 36))
    # Matplotlib is already a dependency and gives consistent title rendering.
    figure = plt.figure(figsize=(sheet.width / 160, sheet.height / 160), dpi=160)
    axis = figure.add_axes((0, 0, 1, 1))
    axis.imshow(sheet)
    axis.text(0.01, 0.985, title, color="#f0a000", fontsize=9,
              ha="left", va="top", transform=axis.transAxes)
    axis.axis("off")
    figure.savefig(output, dpi=160, facecolor="#20232a")
    plt.close(figure)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh", type=Path)
    parser.add_argument("texture", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--geo", type=Path,
                        help="Bedrock geometry JSON; auto-detected beside the mesh")
    parser.add_argument("--animation-json", type=Path,
                        help="GeckoLib/Bedrock animation JSON")
    parser.add_argument("--animation", help="full animation name or short suffix, e.g. crouch")
    parser.add_argument("--time", type=float, default=0.0, help="sample time in seconds")
    parser.add_argument("--overlay-animation",
                        help=("optional second animation sampled from --animation-json; "
                              "its channels override the base pose like the EVA arms controller"))
    parser.add_argument("--overlay-time", type=float, default=0.0,
                        help="sample time for --overlay-animation")
    parser.add_argument("--attachment-mesh", type=Path,
                        help="optional second rigid mesh driven by the same Gecko skeleton")
    parser.add_argument("--attachment-texture", type=Path,
                        help="texture for --attachment-mesh")
    parser.add_argument("--geo-cube-bone", action="append", default=[],
                        help=("selected Gecko cube attachment to render from --geo; "
                              "may be repeated for lance/shield/entry-plug checks"))
    parser.add_argument("--views", nargs="+", choices=tuple(VIEW_AXES),
                        default=("front", "side", "back"))
    parser.add_argument("--focus-bone", action="append", default=[],
                        help=("crop orthographic views around exact mesh bone(s); "
                              "repeat for a hand plus fingers/weapon"))
    parser.add_argument("--focus-padding", type=float, default=1.35,
                        help="close-up crop padding multiplier (default: 1.35)")
    parser.add_argument("--isolate-bone", action="append", default=[],
                        help=("orthographic diagnostic: render only exact mesh "
                              "bone(s); may be repeated"))
    parser.add_argument("--first-person-stance", choices=tuple(FIRST_PERSON_SOCKETS),
                        help=("render the real world-body mesh through Unit-01's "
                              "standing/crouch/prone rider socket instead of orthographic views"))
    parser.add_argument("--first-person-views", nargs="+",
                        choices=tuple(FIRST_PERSON_PITCH),
                        default=("forward", "pitch_down"),
                        help="perspective directions; defaults match the Visual Lab capture rig")
    parser.add_argument("--first-person-fov", type=float, default=70.0,
                        help="vertical FOV in degrees (Minecraft default: 70)")
    parser.add_argument("--first-person-aspect", type=float, default=16.0 / 9.0,
                        help="viewport width/height ratio (default: 16:9)")
    parser.add_argument("--first-person-near", type=float, default=0.05,
                        help="near plane in blocks (default: 0.05)")
    parser.add_argument("--camera-eye-height", type=float,
                        help="preview-only rider eye height override in blocks")
    parser.add_argument("--camera-forward", type=float,
                        help="preview-only rider forward socket override in blocks")
    parser.add_argument("--camera-right", type=float,
                        help="preview-only rider socket offset toward model right in blocks")
    parser.add_argument("--hide-bone", action="append", default=[],
                        help=("preview-only exact mesh bone to omit from first-person output; "
                              "may be repeated"))
    parser.add_argument("--no-skeleton", action="store_true",
                        help="omit diagnostic joint/parent overlay")
    parser.add_argument("--set-rotation", nargs=4, action="append", default=[],
                        metavar=("BONE", "X", "Y", "Z"),
                        help="preview-only rotation override; may be repeated")
    parser.add_argument("--set-position", nargs=4, action="append", default=[],
                        metavar=("BONE", "X", "Y", "Z"),
                        help="preview-only position override; may be repeated")
    parser.add_argument("--pose", choices=("identity", "stress"), default="identity",
                        help="legacy converter smoke-test pose, ignored with --animation")
    return parser.parse_args()


def main():
    args = parse_args()
    if bool(args.animation_json) != bool(args.animation):
        raise SystemExit("--animation-json and --animation must be supplied together")
    if args.overlay_animation and not args.animation_json:
        raise SystemExit("--overlay-animation requires --animation-json")
    if bool(args.attachment_mesh) != bool(args.attachment_texture):
        raise SystemExit("--attachment-mesh and --attachment-texture must be supplied together")
    if not 1.0 < args.first_person_fov < 179.0:
        raise SystemExit("--first-person-fov must be between 1 and 179 degrees")
    if args.first_person_aspect <= 0.0:
        raise SystemExit("--first-person-aspect must be positive")
    if args.first_person_near <= 0.0:
        raise SystemExit("--first-person-near must be positive")
    if ((args.camera_eye_height is not None or args.camera_forward is not None
            or args.camera_right is not None)
            and not args.first_person_stance):
        raise SystemExit("camera overrides require --first-person-stance")
    if args.hide_bone and not args.first_person_stance:
        raise SystemExit("--hide-bone requires --first-person-stance")
    args.output.mkdir(parents=True, exist_ok=True)
    mesh = json.loads(args.mesh.read_text(encoding="utf-8"))
    attachments = []
    if args.attachment_mesh:
        attachments.append((json.loads(args.attachment_mesh.read_text(encoding="utf-8")),
                            args.attachment_texture))
    model_slug, model_label = model_identity(args.mesh)
    geo_path = discover_geo(args.mesh, args.geo)
    pivots, parents, base_rotations = load_skeleton(mesh, geo_path)
    if args.geo_cube_bone:
        attachments.append((load_geo_cube_mesh(geo_path, args.geo_cube_bone), args.texture))

    if args.animation:
        animation_name, sample_time, rotations, positions = select_animation(
            args.animation_json, args.animation, args.time)
        slug = animation_name.rsplit(".", 1)[-1]
        title = f"{model_label} {slug.upper()} @ {sample_time:.3f}s"
        if args.overlay_animation:
            overlay_name, overlay_time, overlay_rotations, overlay_positions = select_animation(
                args.animation_json, args.overlay_animation, args.overlay_time)
            rotations.update(overlay_rotations)
            positions.update(overlay_positions)
            overlay_slug = overlay_name.rsplit(".", 1)[-1]
            slug += f"_plus_{overlay_slug}"
            title += f" + {overlay_slug.upper()} @ {overlay_time:.3f}s"
    else:
        rotations = STRESS_ROTATION if args.pose == "stress" else {}
        positions = {}
        slug = args.pose
        sample_time = 0.0
        title = f"{model_label} RIG {args.pose.upper()}"

    if attachments:
        slug += "_with_attachment"
        title += " / ATTACHMENT MESH"

    for values in args.set_rotation:
        rotations[values[0]] = tuple(float(value) for value in values[1:])
    for values in args.set_position:
        positions[values[0]] = tuple(float(value) for value in values[1:])
    if args.set_rotation or args.set_position:
        slug += "_override"
        title += " / PREVIEW OVERRIDE"

    matrices = {}
    animated_mesh_bones = set(mesh["parts"])
    for attachment, _ in attachments:
        animated_mesh_bones.update(attachment["parts"])
    for bone in animated_mesh_bones:
        bone_matrix(bone, pivots, parents, rotations, positions,
                    base_rotations, matrices)
    metrics = pose_metrics(mesh, matrices, pivots, positions,
                           [attachment for attachment, _ in attachments])
    if args.first_person_stance:
        scenes = {}
        perspective_metrics = {}
        for view in args.first_person_views:
            scene, diagnostic = collect_first_person_scene(
                mesh, args.texture, matrices, pivots, parents,
                args.first_person_stance, view, args.first_person_fov,
                args.first_person_aspect, args.first_person_near,
                args.camera_eye_height, args.camera_forward, args.camera_right,
                args.hide_bone, attachments)
            scenes[view] = scene
            perspective_metrics[view] = diagnostic
        paths = []
        output_slug = f"{slug}_first_person_{args.first_person_stance}"
        if (args.camera_eye_height is not None or args.camera_forward is not None
                or args.camera_right is not None):
            socket = FIRST_PERSON_SOCKETS[args.first_person_stance]
            eye = (socket["eye_height"] if args.camera_eye_height is None
                   else args.camera_eye_height)
            forward = (socket["forward"] if args.camera_forward is None
                       else args.camera_forward)
            camera_tag = f"eye{eye:.2f}_forward{forward:.2f}".replace(".", "p")
            if args.camera_right is not None:
                camera_tag += f"_right{args.camera_right:.2f}".replace(".", "p")
            output_slug += f"_{camera_tag}"
        if args.hide_bone:
            hidden_tag = "_".join(re.sub(r"[^a-zA-Z0-9_-]+", "_", name)
                                  for name in sorted(set(args.hide_bone)))
            output_slug += f"_hidden_{hidden_tag}"
        for view, scene in scenes.items():
            path = args.output / f"{model_slug}_rig_{output_slug}_{sample_time:.3f}_{view}.png"
            render_first_person_scene(scene, view, args.first_person_stance,
                                      path, title, args.first_person_aspect,
                                      not args.no_skeleton)
            paths.append(path)
        sheet = args.output / f"{model_slug}_rig_{output_slug}_{sample_time:.3f}_sheet.png"
        write_contact_sheet(paths, sheet,
                            f"{title} / FIRST PERSON {args.first_person_stance.upper()}")
        metrics["first_person"] = perspective_metrics
        metrics_path = args.output / f"{model_slug}_rig_{output_slug}_{sample_time:.3f}_metrics.json"
    else:
        scenes = {view: collect_scene(mesh, args.texture, view, matrices, pivots, parents,
                                      attachments, args.isolate_bone)
                  for view in args.views}
        if args.focus_padding <= 0.0:
            raise SystemExit("--focus-padding must be positive")
        bounds = scene_bounds(scenes, args.focus_bone, args.focus_padding)
        paths = []
        for view, scene in scenes.items():
            path = args.output / f"{model_slug}_rig_{slug}_{sample_time:.3f}_{view}.png"
            render_scene(scene, view, path, title, bounds, not args.no_skeleton)
            paths.append(path)
        sheet = args.output / f"{model_slug}_rig_{slug}_{sample_time:.3f}_sheet.png"
        write_contact_sheet(paths, sheet, title)
        metrics_path = args.output / f"{model_slug}_rig_{slug}_{sample_time:.3f}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    kind = "first-person" if args.first_person_stance else "orthographic"
    print(f"rendered {len(paths)} {kind} views + contact sheet -> {args.output}")
    print(f"model y=[{metrics['overall_min_y']:.3f}, {metrics['overall_max_y']:.3f}], "
          f"hand pivot distance={metrics['hand_pivot_distance']}")
    if geo_path:
        print(f"skeleton: {geo_path}")


if __name__ == "__main__":
    main()
