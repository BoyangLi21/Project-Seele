#!/usr/bin/env python3
"""Build a LOCAL-ONLY rigged Unit-01 mesh pack from Tigerar1's OBJ source.

The downloaded mesh is CC BY-SA fan art and is never written into Git-tracked
resources. This tool keeps the original triangles/UVs, assigns them to the
Project SEELE bone contract, and writes only to the ignored run resource pack.
"""

import copy
import io
import json
import math
import sys
import zipfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    REPO / "external-assets/incoming/evangelion-unit-01.zip")
OUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
BASE_GEO = REPO / "src/main/resources/assets/projectseele/geo/eva_unit01.geo.json"
BASE_ANIMATION = REPO / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json"
BASE_TEXTURE = REPO / "src/main/resources/assets/projectseele/textures/entity/eva_unit01.png"
MODEL_HEIGHT = 192.0
ATLAS_WIDTH = 1024
ATLAS_HEIGHT = 512
# Triangles below this neutral OBJ height belong to the rigid foot shell.
# The old 15-part rig welded them to the shin, making a planted one-knee pose
# mathematically impossible: correcting the knee also tipped the entire foot.
FOOT_CUT_Y = 0.35

# Joint centres measured on the downloaded neutral-pose mesh. Keeping these in
# source OBJ space makes the rig reproducible if MODEL_HEIGHT changes.
SOURCE_PIVOTS = {
    "root": (0.0, 0.0, 0.0),
    "torso_lower": (0.0, 2.08, 0.0),
    "torso_upper": (0.0, 2.86, 0.0),
    "head": (0.0, 3.60, 0.02),
    "pylon_l": (0.44, 3.64, 0.0), "pylon_r": (-0.44, 3.64, 0.0),
    "arm_l": (0.44, 3.54, 0.0), "arm_r": (-0.44, 3.54, 0.0),
    "forearm_l": (0.54, 2.80, -0.03), "forearm_r": (-0.54, 2.80, -0.03),
    "hand_l": (0.56, 2.13, -0.02), "hand_r": (-0.56, 2.13, -0.02),
    "leg_l": (0.25, 2.06, 0.0), "leg_r": (-0.25, 2.06, 0.0),
    "shin_l": (0.35, 1.37, -0.02), "shin_r": (-0.35, 1.37, -0.02),
    "foot_l": (0.35, 0.42, -0.02), "foot_r": (-0.35, 0.42, -0.02),
}
BODY_MESH_BONES = frozenset(SOURCE_PIVOTS) - {"root"}


def read_source():
    with zipfile.ZipFile(SOURCE) as outer:
        nested_name = next(name for name in outer.namelist() if name.lower().endswith("unit01.zip"))
        texture_name = next(name for name in outer.namelist()
                            if name.lower().endswith("e01_201.png") and name.startswith("textures/"))
        texture = outer.read(texture_name)
        with zipfile.ZipFile(io.BytesIO(outer.read(nested_name))) as nested:
            obj_name = next(name for name in nested.namelist() if name.lower().endswith(".obj"))
            return nested.read(obj_name).decode("utf-8", errors="ignore"), texture


def parse_obj(text):
    positions = []
    texcoords = []
    normals = []
    triangles = []
    for raw in text.splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "v":
            positions.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "vt":
            texcoords.append(tuple(float(value) for value in fields[1:3]))
        elif fields[0] == "vn":
            normals.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "f":
            refs = []
            for field in fields[1:]:
                values = field.split("/")
                refs.append((int(values[0]) - 1,
                             int(values[1]) - 1 if len(values) > 1 and values[1] else -1,
                             int(values[2]) - 1 if len(values) > 2 and values[2] else -1))
            for index in range(1, len(refs) - 1):
                triangles.append((refs[0], refs[index], refs[index + 1]))
    return positions, texcoords, normals, triangles


def connected_components(positions, triangles):
    # UV seams duplicate position indices. Weld only for component discovery;
    # the exported render mesh retains every original UV vertex.
    welded = {}
    position_key = []
    for position in positions:
        key = tuple(round(value, 6) for value in position)
        position_key.append(welded.setdefault(key, len(welded)))
    by_position = {}
    for face_index, triangle in enumerate(triangles):
        for ref in triangle:
            by_position.setdefault(position_key[ref[0]], []).append(face_index)
    adjacency = [set() for _ in triangles]
    for face_indices in by_position.values():
        for face_index in face_indices:
            adjacency[face_index].update(face_indices)
    components = []
    seen = set()
    for start in range(len(triangles)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component = []
        while stack:
            face_index = stack.pop()
            component.append(face_index)
            for neighbour in adjacency[face_index]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        components.append(component)
    return components


def component_bounds(component, positions, triangles):
    points = [positions[ref[0]] for face_index in component for ref in triangles[face_index]]
    return ([min(point[axis] for point in points) for axis in range(3)],
            [max(point[axis] for point in points) for axis in range(3)])


def side_name(x, left, right):
    # Positive OBJ X is the Unit's anatomical left (viewer's right).
    return left if x >= 0 else right


def component_family(component, bounds, positions, triangles):
    minimum, maximum = bounds
    vertex_indices = {ref[0] for face_index in component for ref in triangles[face_index]}
    centre = [sum(positions[index][axis] for index in vertex_indices) / len(vertex_indices)
              for axis in range(3)]
    absolute_x = abs(centre[0])
    if maximum[1] > 4.30 and absolute_x > 0.30:
        return "pylon"
    # The two 451-face components are the continuous upper-arm/forearm/hand
    # shells. Smaller detached wrist and elbow armour lives in the same zone.
    if (len(component) > 350 and absolute_x > 0.30) or (
            absolute_x > 0.42 and minimum[1] > 1.75):
        return "arm_chain"
    # Separate face/helmet shells sit wholly above the collar. The 804-face
    # central body component intentionally remains torso to keep the neck seam
    # from being cut merely because a few points rise into this range.
    if len(component) < 400 and minimum[1] > 3.30 and absolute_x < 0.42:
        return "head"
    if maximum[1] < 1.80:
        return "shin"
    if maximum[1] < 2.82 and minimum[1] > 1.30 and absolute_x > 0.10:
        return "leg"
    if minimum[1] > 3.25 and absolute_x >= 0.36:
        return "arm_chain"
    return "torso"


def assign_bone(centroid, family):
    x, y, _ = centroid
    if family == "pylon":
        return side_name(x, "pylon_l", "pylon_r")
    if family == "head":
        return "head"
    if family == "arm_chain":
        if y < 2.18:
            return side_name(x, "hand_l", "hand_r")
        if y < 2.82:
            return side_name(x, "forearm_l", "forearm_r")
        return side_name(x, "arm_l", "arm_r")
    if family == "shin":
        if y < FOOT_CUT_Y:
            return side_name(x, "foot_l", "foot_r")
        return side_name(x, "shin_l", "shin_r")
    if family == "leg":
        return side_name(x, "leg_l", "leg_r")
    if y < 2.78:
        return "torso_lower"
    return "torso_upper"


def face_normal(points):
    ax, ay, az = (points[1][axis] - points[0][axis] for axis in range(3))
    bx, by, bz = (points[2][axis] - points[0][axis] for axis in range(3))
    nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


def shift_uv(uv, x_offset):
    if isinstance(uv, list):
        return [uv[0] + x_offset, *uv[1:]]
    if isinstance(uv, dict):
        result = copy.deepcopy(uv)
        for face in result.values():
            if isinstance(face.get("uv"), list):
                face["uv"][0] += x_offset
        return result
    return uv


def build_skeleton(scale, minimum_y):
    data = json.loads(BASE_GEO.read_text(encoding="utf-8"))
    geometry = data["minecraft:geometry"][0]
    geometry["description"]["texture_width"] = ATLAS_WIDTH
    geometry["description"]["texture_height"] = ATLAS_HEIGHT
    ensure_foot_bones(geometry)
    for bone in geometry["bones"]:
        if bone["name"] in SOURCE_PIVOTS:
            source_pivot = SOURCE_PIVOTS[bone["name"]]
            bone["pivot"] = [round(source_pivot[0] * scale, 5),
                             round((source_pivot[1] - minimum_y) * scale, 5),
                             round(-source_pivot[2] * scale, 5)]
        # The reviewed local pack is fail-closed: never reveal the obsolete
        # cube body (or its extra horn) if its triangle mesh cannot load.
        # Attachment bones are retained and shifted into the fallback half of
        # the atlas; the launcher validator prevents starting with no body.
        if bone["name"] in BODY_MESH_BONES or bone["name"] == "horn":
            bone.pop("cubes", None)
        else:
            for cube in bone.get("cubes", []):
                if "uv" in cube:
                    cube["uv"] = shift_uv(cube["uv"], 512)
    pivots = {bone["name"]: bone.get("pivot", [0, 0, 0]) for bone in geometry["bones"]}
    # Keep temporary weapon/socket geometry attached to the new right hand.
    for name in ("knife", "cannon", "lance"):
        bone = next(item for item in geometry["bones"] if item["name"] == name)
        old_pivot = bone.get("pivot", [0, 0, 0])
        new_pivot = [pivots["hand_r"][0], pivots["hand_r"][1] - 5.0, pivots["hand_r"][2]]
        delta = [new_pivot[axis] - old_pivot[axis] for axis in range(3)]
        bone["pivot"] = new_pivot
        for cube in bone.get("cubes", []):
            cube["origin"] = [cube["origin"][axis] + delta[axis] for axis in range(3)]
            if "pivot" in cube:
                cube["pivot"] = [cube["pivot"][axis] + delta[axis] for axis in range(3)]
        if name == "cannon":
            bone.pop("cubes", None)
        pivots[name] = new_pivot
    return data, pivots


def ensure_foot_bones(geometry):
    """Add the ankle layer to a legacy 15-bone fallback skeleton."""
    bones = geometry["bones"]
    existing = {bone["name"] for bone in bones}
    for name, parent in (("foot_l", "shin_l"), ("foot_r", "shin_r")):
        if name not in existing:
            bones.append({"name": name, "parent": parent})


def build_mesh(positions, texcoords, normals, triangles, pivots, scale, minimum_y):
    components = connected_components(positions, triangles)
    face_family = {}
    for component in components:
        bounds = component_bounds(component, positions, triangles)
        family = component_family(component, bounds, positions, triangles)
        for face_index in component:
            face_family[face_index] = family
    parts = {}
    counts = {}
    for face_index, triangle in enumerate(triangles):
        source_points = [positions[ref[0]] for ref in triangle]
        centroid = tuple(sum(point[axis] for point in source_points) / 3.0 for axis in range(3))
        bone = assign_bone(centroid, face_family[face_index])
        pivot = pivots[bone]
        fallback_normal = face_normal(source_points)
        output = parts.setdefault(bone, [])
        for ref in triangle:
            position = positions[ref[0]]
            uv = texcoords[ref[1]] if ref[1] >= 0 else (0.0, 0.0)
            normal = normals[ref[2]] if ref[2] >= 0 else fallback_normal
            output.extend([
                round(position[0] * scale - pivot[0], 5),
                round((position[1] - minimum_y) * scale - pivot[1], 5),
                # Tigerar1's OBJ faces +Z; Project SEELE/Gecko entities face
                # -Z. Reflect Z once during import so cameras and weapons use
                # the same forward convention.
                round(-position[2] * scale - pivot[2], 5),
                round(uv[0] * 0.5, 6), round(1.0 - uv[1], 6),
                round(normal[0], 5), round(normal[1], 5), round(-normal[2], 5),
            ])
        counts[bone] = counts.get(bone, 0) + 1
    return {
        "format_version": 1,
        "source": "Tigerar1 Evangelion Unit-01 (CC BY-SA), local evaluation only",
        "model_height": MODEL_HEIGHT,
        "stride": 8,
        "parts": {bone: {"pivot": pivots[bone], "vertices": values}
                  for bone, values in sorted(parts.items())},
    }, counts


def build_atlas(source_texture):
    atlas = Image.new("RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), (0, 0, 0, 0))
    atlas.paste(Image.open(io.BytesIO(source_texture)).convert("RGBA"), (0, 0))
    atlas.paste(Image.open(BASE_TEXTURE).convert("RGBA"), (512, 0))
    return atlas


def sample_channel(channel, time):
    if not isinstance(channel, dict):
        return copy.deepcopy(channel)
    keyed = []
    for key, value in channel.items():
        try:
            keyed.append((float(key), value))
        except (TypeError, ValueError):
            pass
    if not keyed:
        return copy.deepcopy(channel)
    keyed.sort(key=lambda item: item[0])
    before = max((item for item in keyed if item[0] <= time),
                 default=keyed[0], key=lambda item: item[0])
    after = min((item for item in keyed if item[0] >= time),
                default=keyed[-1], key=lambda item: item[0])
    left = before[1].get("post", before[1].get("pre")) if isinstance(before[1], dict) else before[1]
    right = after[1].get("pre", after[1].get("post")) if isinstance(after[1], dict) else after[1]
    if before[0] == after[0] or not isinstance(left, list) or not isinstance(right, list):
        return copy.deepcopy(left)
    factor = (time - before[0]) / (after[0] - before[0])
    return [a + (b - a) * factor if isinstance(a, (int, float)) and isinstance(b, (int, float)) else a
            for a, b in zip(left, right)]


def static_pose(animation, time):
    bones = {}
    for bone, channels in animation.get("bones", {}).items():
        sampled = {name: {"0.0": sample_channel(channel, time)}
                   for name, channel in channels.items()}
        if sampled:
            bones[bone] = sampled
    return {"loop": True, "animation_length": 1.0, "bones": bones}


def build_animations():
    data = json.loads(BASE_ANIMATION.read_text(encoding="utf-8"))
    animations = data["animations"]
    animations["animation.eva_unit01.visual_idle"] = static_pose(
        animations["animation.eva_unit01.idle"], 0.0)
    animations["animation.eva_unit01.visual_walk_contact"] = static_pose(
        animations["animation.eva_unit01.walk"], 0.0)
    animations["animation.eva_unit01.visual_knife_windup"] = static_pose(
        animations["animation.eva_unit01.knife"], 0.12)
    animations["animation.eva_unit01.visual_knife_contact"] = static_pose(
        animations["animation.eva_unit01.knife"], 0.28)
    animations["animation.eva_unit01.visual_knife_recovery"] = static_pose(
        animations["animation.eva_unit01.knife"], 0.50)
    animations.setdefault("animation.eva_unit01.visual_lance_windup", static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.20))
    animations.setdefault("animation.eva_unit01.visual_lance_contact", static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.42))
    animations.setdefault("animation.eva_unit01.visual_lance_recovery", static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.70))
    animations["animation.eva_unit01.visual_cannon"] = static_pose(
        animations["animation.eva_unit01.aim"], 0.0)
    return data


def main():
    if not SOURCE.exists():
        sys.exit(f"Unit-01 source not found: {SOURCE}")
    obj_text, texture = read_source()
    positions, texcoords, normals, triangles = parse_obj(obj_text)
    minimum_y = min(position[1] for position in positions)
    height = max(position[1] for position in positions) - minimum_y
    scale = MODEL_HEIGHT / height
    skeleton, pivots = build_skeleton(scale, minimum_y)
    mesh, counts = build_mesh(positions, texcoords, normals, triangles, pivots, scale, minimum_y)

    geo_dir = OUT / "geo"
    animation_dir = OUT / "animations"
    texture_dir = OUT / "textures/entity"
    mesh_dir = OUT / "mesh"
    for directory in (geo_dir, animation_dir, texture_dir, mesh_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (geo_dir / "eva_unit01.geo.json").write_text(
        json.dumps(skeleton, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (animation_dir / "eva_unit01.animation.json").write_text(
        json.dumps(build_animations(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (mesh_dir / "eva_unit01.mesh.json").write_text(
        json.dumps(mesh, separators=(",", ":")), encoding="utf-8")
    build_atlas(texture).save(texture_dir / "eva_unit01.png")
    pack_root = OUT.parent.parent
    (pack_root / "pack.mcmeta").write_text(json.dumps({
        "pack": {
            "pack_format": 15,
            "description": "Project SEELE local external model evaluation - not for redistribution",
        }
    }, indent=2) + "\n", encoding="utf-8")
    source_note = pack_root / "_SOURCE.txt"
    existing_note = source_note.read_text(encoding="utf-8") if source_note.exists() else ""
    source_title = "Tigerar1 Evangelion Unit-01 (Sketchfab, CC BY-SA).\n"
    source_url = ("https://sketchfab.com/3d-models/"
                  "evangelion-unit-01-9fddeb0a7143436598c805dab2f147bf\n")
    if source_url not in existing_note:
        addition = "" if "Tigerar1 Evangelion Unit-01" in existing_note else source_title
        addition += source_url
        if "Converted from the user-downloaded OBJ" not in existing_note:
            addition += "Converted from the user-downloaded OBJ for LOCAL TESTING ONLY.\n"
        source_note.write_text(existing_note + addition, encoding="utf-8")
    print(f"Tigerar1 Unit-01: {len(positions)} vertices / {len(triangles)} triangles")
    print("bone faces: " + ", ".join(f"{bone}={count}" for bone, count in sorted(counts.items())))
    print(f"local mesh pack written -> {OUT}")


if __name__ == "__main__":
    main()
