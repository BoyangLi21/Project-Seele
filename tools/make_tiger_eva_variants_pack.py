#!/usr/bin/env python3
"""Build LOCAL-ONLY Tigerar1 Unit-00, Unit-02 and Mass Production EVA assets.

The downloaded Sketchfab archives remain Git-ignored.  This converter writes
only the derived runtime files selected by ``--output`` and never clears the
surrounding resource pack.  Public redistribution still requires preserving
the source CC BY-SA licence and attribution.
"""

import argparse
import copy
import io
import json
import math
import zipfile
from pathlib import Path

from PIL import Image

try:
    import make_tiger_unit01_pack as tiger
except ModuleNotFoundError:  # Allows import as tools.make_tiger_eva_variants_pack.
    from tools import make_tiger_unit01_pack as tiger


REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
UNIT01_BASE_ANIMATION = (
    REPO / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json")
UNIT_MODEL_HEIGHT = 192.0
# HybridAddonRenderer currently applies a 10x Gecko scale to the detailed MP
# model.  A 48-pixel body therefore renders as a 30-block airframe.
MASS_MODEL_HEIGHT = 48.0
ATLAS_WIDTH = 1024
ATLAS_HEIGHT = 512

UNIT_VARIANTS = {
    "unit00": {
        "target": "eva_unit00",
        "archive": REPO / "external-assets/incoming/evangelion-unit-00.zip",
        "nested": "unit00.zip",
        "obj": "unit00.obj",
        "texture": "textures/e00_201.png",
        "base_geo": REPO / "src/main/resources/assets/projectseele/geo/eva_unit00.geo.json",
        "base_animation": REPO / "src/main/resources/assets/projectseele/animations/eva_unit00.animation.json",
        "base_texture": REPO / "src/main/resources/assets/projectseele/textures/entity/eva_unit00.png",
        "source": "Tigerar1 Evangelion Unit-00 (CC BY-SA), local evaluation only",
        "url": ("https://sketchfab.com/3d-models/"
                "evangelion-unit-00-abe48f0c88914d66b7a5c916704767b3"),
    },
    "unit02": {
        "target": "eva_unit02",
        "archive": REPO / "external-assets/incoming/evangelion-unit-02.zip",
        "nested": "unit02.zip",
        "obj": "unit02.obj",
        "texture": "textures/e02_201.png",
        "base_geo": REPO / "src/main/resources/assets/projectseele/geo/eva_unit02.geo.json",
        "base_animation": REPO / "src/main/resources/assets/projectseele/animations/eva_unit02.animation.json",
        "base_texture": REPO / "src/main/resources/assets/projectseele/textures/entity/eva_unit02.png",
        "source": "Tigerar1 Evangelion Unit-02 (CC BY-SA), local evaluation only",
        "url": ("https://sketchfab.com/3d-models/"
                "evangelion-unit-02-a8731145a84f4e63b0fbc51f4f5948da"),
    },
}

MASS = {
    "target": "mass_production_eva",
    "archive": REPO / "external-assets/incoming/mass-production-evangelion.zip",
    "nested": "mpeva.zip",
    "obj": "mpeva.obj",
    "body_texture": "textures/e26_201.png",
    "wing_texture": "textures/e26_201_chibang.png",
    "source": "Tigerar1 Mass Production Evangelion (CC BY-SA), local evaluation only",
    "url": ("https://sketchfab.com/3d-models/"
            "mass-production-evangelion-a483209197814af99fc536b396813698"),
}


def find_suffix(names, suffix):
    matches = [name for name in names if name.lower().endswith(suffix.lower())]
    if len(matches) != 1:
        raise RuntimeError(f"expected one *{suffix}, found {matches}")
    return matches[0]


def read_unit_source(config):
    with zipfile.ZipFile(config["archive"]) as outer:
        nested_name = find_suffix(outer.namelist(), config["nested"])
        texture_name = find_suffix(outer.namelist(), config["texture"])
        texture = outer.read(texture_name)
        with zipfile.ZipFile(io.BytesIO(outer.read(nested_name))) as nested:
            obj_name = find_suffix(nested.namelist(), config["obj"])
            obj = nested.read(obj_name).decode("utf-8", errors="ignore")
    return obj, texture


def read_mass_source():
    with zipfile.ZipFile(MASS["archive"]) as outer:
        nested_name = find_suffix(outer.namelist(), MASS["nested"])
        body_texture = outer.read(find_suffix(outer.namelist(), MASS["body_texture"]))
        wing_texture = outer.read(find_suffix(outer.namelist(), MASS["wing_texture"]))
        with zipfile.ZipFile(io.BytesIO(outer.read(nested_name))) as nested:
            obj_name = find_suffix(nested.namelist(), MASS["obj"])
            obj = nested.read(obj_name).decode("utf-8", errors="ignore")
    return obj, body_texture, wing_texture


def shift_uv(uv, x_offset):
    if isinstance(uv, list):
        return [uv[0] + x_offset, *uv[1:]]
    if isinstance(uv, dict):
        shifted = copy.deepcopy(uv)
        for face in shifted.values():
            if isinstance(face, dict) and isinstance(face.get("uv"), list):
                face["uv"][0] += x_offset
        return shifted
    return uv


def translate_bone_geometry(bone, delta):
    bone["pivot"] = [bone.get("pivot", [0, 0, 0])[axis] + delta[axis]
                     for axis in range(3)]
    for cube in bone.get("cubes", []):
        cube["origin"] = [cube["origin"][axis] + delta[axis] for axis in range(3)]
        if "pivot" in cube:
            cube["pivot"] = [cube["pivot"][axis] + delta[axis] for axis in range(3)]


def build_unit_skeleton(config, scale, minimum_y):
    data = json.loads(config["base_geo"].read_text(encoding="utf-8"))
    geometry = data["minecraft:geometry"][0]
    geometry["description"]["identifier"] = f"geometry.{config['target']}"
    geometry["description"]["texture_width"] = ATLAS_WIDTH
    geometry["description"]["texture_height"] = ATLAS_HEIGHT
    tiger.ensure_foot_bones(geometry)
    bones = geometry["bones"]
    old_pivots = {bone["name"]: copy.deepcopy(bone.get("pivot", [0, 0, 0]))
                  for bone in bones}

    for bone in bones:
        source_pivot = tiger.SOURCE_PIVOTS.get(bone["name"])
        if source_pivot is not None:
            bone["pivot"] = [round(source_pivot[0] * scale, 5),
                             round((source_pivot[1] - minimum_y) * scale, 5),
                             round(-source_pivot[2] * scale, 5)]

    # Preserve authored attachment offsets (weapons, entry plug, horn and the
    # Unit-00 shield) when their standard parent joint moves to the OBJ rig.
    new_pivots = {bone["name"]: bone.get("pivot", [0, 0, 0]) for bone in bones}
    standard_names = set(tiger.SOURCE_PIVOTS)
    for bone in bones:
        parent = bone.get("parent")
        if bone["name"] in standard_names or parent not in standard_names:
            continue
        delta = [new_pivots[parent][axis] - old_pivots[parent][axis] for axis in range(3)]
        translate_bone_geometry(bone, delta)
        new_pivots[bone["name"]] = bone["pivot"]

    for bone in bones:
        if bone["name"] == "cannon":
            bone.pop("cubes", None)

    for bone in bones:
        if bone["name"] in tiger.BODY_MESH_BONES or bone["name"] == "horn":
            bone.pop("cubes", None)
        else:
            for cube in bone.get("cubes", []):
                if "uv" in cube:
                    cube["uv"] = shift_uv(cube["uv"], 512)
    return data, {bone["name"]: bone.get("pivot", [0, 0, 0]) for bone in bones}


def sync_shared_rig_animations(animation):
    """Use Unit-01 as the sole pose source for the shared 17-part Tiger rig.

    Unit-00 and Unit-02 used to copy only the low/cannon poses.  Switching to
    idle, knife or Longinus could therefore restore their old pre-Tiger arm
    axes even though the body mesh itself never changed.  The three bodies
    now share one semantic skeleton, so every canonical body animation must
    come from the same catalogue; variant-only attachments remain geometry
    bones whose visibility is controlled by the renderer.
    """
    source = json.loads(UNIT01_BASE_ANIMATION.read_text(encoding="utf-8"))["animations"]
    target = animation["animations"]
    for key, pose in source.items():
        target[key] = copy.deepcopy(pose)
    return animation


def add_visual_poses(animation):
    animations = animation["animations"]
    poses = {
        "visual_idle": ("idle", 0.0),
        "visual_walk_contact": ("walk", 0.0),
        "visual_knife_windup": ("knife", 0.12),
        "visual_knife_contact": ("knife", 0.28),
        "visual_knife_recovery": ("knife", 0.50),
        "visual_lance_windup": ("lance_thrust", 0.20),
        "visual_lance_contact": ("lance_thrust", 0.42),
        "visual_lance_recovery": ("lance_thrust", 0.70),
        "visual_cannon": ("aim", 0.0),
    }
    for target, (source, time) in poses.items():
        source_key = f"animation.eva_unit01.{source}"
        target_key = f"animation.eva_unit01.{target}"
        if source_key in animations and target_key not in animations:
            animations[target_key] = tiger.static_pose(
                animations[source_key], time)
    return animation


def build_unit_atlas(source_texture, fallback_texture):
    atlas = Image.new("RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), (0, 0, 0, 0))
    atlas.paste(Image.open(io.BytesIO(source_texture)).convert("RGBA"), (0, 0))
    atlas.paste(Image.open(fallback_texture).convert("RGBA"), (512, 0))
    return atlas


def write_json(path, value, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, separators=(",", ":") if compact else None,
                      ensure_ascii=False, indent=None if compact else 2)
    path.write_text(text + ("" if compact else "\n"), encoding="utf-8")


def validate_mesh(mesh):
    stride = mesh["stride"]
    if stride != 8 or not mesh["parts"]:
        raise RuntimeError("mesh must contain stride-8 parts")
    for bone, part in mesh["parts"].items():
        values = part["vertices"]
        if len(values) % (stride * 3) != 0:
            raise RuntimeError(f"incomplete triangle data in {bone}")
        for index in range(0, len(values), stride):
            if not all(math.isfinite(value) for value in values[index:index + stride]):
                raise RuntimeError(f"non-finite vertex data in {bone}")
            if not 0.0 <= values[index + 3] <= 1.0 or not 0.0 <= values[index + 4] <= 1.0:
                raise RuntimeError(f"UV outside atlas in {bone}")


def write_unit(config, output):
    obj_text, texture = read_unit_source(config)
    positions, texcoords, normals, triangles = tiger.parse_obj(obj_text)
    minimum_y = min(position[1] for position in positions)
    height = max(position[1] for position in positions) - minimum_y
    scale = UNIT_MODEL_HEIGHT / height
    skeleton, pivots = build_unit_skeleton(config, scale, minimum_y)
    mesh, counts = tiger.build_mesh(
        positions, texcoords, normals, triangles, pivots, scale, minimum_y)
    mesh["source"] = config["source"]
    validate_mesh(mesh)
    animation = add_visual_poses(sync_shared_rig_animations(json.loads(
        config["base_animation"].read_text(encoding="utf-8"))))

    target = config["target"]
    write_json(output / "geo" / f"{target}.geo.json", skeleton)
    write_json(output / "animations" / f"{target}.animation.json", animation)
    write_json(output / "mesh" / f"{target}.mesh.json", mesh, compact=True)
    texture_path = output / "textures/entity" / f"{target}.png"
    texture_path.parent.mkdir(parents=True, exist_ok=True)
    build_unit_atlas(texture, config["base_texture"]).save(texture_path)
    print(f"{target}: {len(positions)} vertices / {len(triangles)} triangles")
    print("bone faces: " + ", ".join(
        f"{bone}={count}" for bone, count in sorted(counts.items())))
    return len(triangles)


def obj_index(value, length):
    index = int(value)
    return index - 1 if index > 0 else length + index


def parse_obj_objects(text):
    positions = []
    texcoords = []
    normals = []
    triangles = []
    current_object = "default"
    for raw in text.splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "o":
            current_object = fields[1]
        elif fields[0] == "v":
            positions.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "vt":
            texcoords.append(tuple(float(value) for value in fields[1:3]))
        elif fields[0] == "vn":
            normals.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "f":
            refs = []
            for field in fields[1:]:
                values = field.split("/")
                refs.append((obj_index(values[0], len(positions)),
                             obj_index(values[1], len(texcoords))
                             if len(values) > 1 and values[1] else -1,
                             obj_index(values[2], len(normals))
                             if len(values) > 2 and values[2] else -1))
            for index in range(1, len(refs) - 1):
                triangles.append((refs[0], refs[index], refs[index + 1], current_object))
    return positions, texcoords, normals, triangles


MASS_SOURCE_PIVOTS = {
    "root": (0.0, 0.0, 0.0),
    "torso_lower": (0.0, 2.02, 0.0),
    "torso_upper": (0.0, 2.76, 0.0),
    "head": (0.0, 3.56, 0.04),
    "arm_l": (0.43, 3.40, 0.0), "arm_r": (-0.43, 3.40, 0.0),
    "forearm_l": (0.54, 2.70, -0.02), "forearm_r": (-0.54, 2.70, -0.02),
    "hand_l": (0.56, 2.05, -0.02), "hand_r": (-0.56, 2.05, -0.02),
    "leg_l": (0.25, 2.00, 0.0), "leg_r": (-0.25, 2.00, 0.0),
    "shin_l": (0.34, 1.32, -0.02), "shin_r": (-0.34, 1.32, -0.02),
    "wing_l": (0.18, 3.22, 0.20), "wing_r": (-0.18, 3.22, 0.20),
}

MASS_PARENT = {
    "torso_lower": "root", "torso_upper": "torso_lower", "head": "torso_upper",
    "arm_l": "torso_upper", "forearm_l": "arm_l", "hand_l": "forearm_l",
    "arm_r": "torso_upper", "forearm_r": "arm_r", "hand_r": "forearm_r",
    "leg_l": "torso_lower", "shin_l": "leg_l",
    "leg_r": "torso_lower", "shin_r": "leg_r",
    "wing_l": "torso_upper", "wing_r": "torso_upper",
}


def scaled_pivots(source_pivots, scale, minimum_y):
    return {
        name: [round(value[0] * scale, 5),
               round((value[1] - minimum_y) * scale, 5),
               round(-value[2] * scale, 5)]
        for name, value in source_pivots.items()
    }


def build_mass_skeleton(pivots):
    bones = []
    for name in MASS_SOURCE_PIVOTS:
        bone = {"name": name, "pivot": pivots[name]}
        if name in MASS_PARENT:
            bone["parent"] = MASS_PARENT[name]
        bones.append(bone)
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": "geometry.mass_production_eva",
                "texture_width": ATLAS_WIDTH,
                "texture_height": ATLAS_HEIGHT,
                "visible_bounds_width": 26,
                "visible_bounds_height": 32,
                "visible_bounds_offset": [0, 12, 0],
            },
            "bones": bones,
        }],
    }


def face_normal(points):
    ax, ay, az = (points[1][axis] - points[0][axis] for axis in range(3))
    bx, by, bz = (points[2][axis] - points[0][axis] for axis in range(3))
    nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


def mass_body_assignments(positions, triangles):
    assignments = {}
    for face_index, entry in enumerate(triangles):
        triangle = entry[:3]
        points = [positions[ref[0]] for ref in triangle]
        centroid = tuple(sum(point[axis] for point in points) / 3.0 for axis in range(3))
        x, y, _ = centroid
        absolute_x = abs(x)
        # Unlike Units 00/01/02, the production EVA exports its chest, neck
        # and both complete arms as one connected shell.  Component-level
        # assignment would therefore weld the arms to the torso.  These cuts
        # follow the visible shoulder/elbow/wrist gaps in source coordinates.
        if y > 3.34 and absolute_x < 0.37:
            bone = "head"
        elif absolute_x > 0.43 and 1.78 < y < 3.58:
            if y < 2.18:
                bone = tiger.side_name(x, "hand_l", "hand_r")
            elif y < 2.78:
                bone = tiger.side_name(x, "forearm_l", "forearm_r")
            else:
                bone = tiger.side_name(x, "arm_l", "arm_r")
        elif y < 1.80:
            bone = tiger.side_name(x, "shin_l", "shin_r")
        elif y < 2.72 and absolute_x > 0.10:
            bone = tiger.side_name(x, "leg_l", "leg_r")
        elif y < 2.72:
            bone = "torso_lower"
        else:
            bone = "torso_upper"
        assignments[face_index] = bone
    return assignments


def append_mesh_triangle(parts, counts, bone, triangle, positions, texcoords,
                         normals, pivot, scale, minimum_y, u_offset):
    points = [positions[ref[0]] for ref in triangle]
    fallback_normal = face_normal(points)
    output = parts.setdefault(bone, [])
    for ref in triangle:
        position = positions[ref[0]]
        uv = texcoords[ref[1]] if ref[1] >= 0 else (0.0, 0.0)
        normal = normals[ref[2]] if ref[2] >= 0 else fallback_normal
        output.extend([
            round(position[0] * scale - pivot[0], 5),
            round((position[1] - minimum_y) * scale - pivot[1], 5),
            round(-position[2] * scale - pivot[2], 5),
            round(uv[0] * 0.5 + u_offset, 6), round(1.0 - uv[1], 6),
            round(normal[0], 5), round(normal[1], 5), round(-normal[2], 5),
        ])
    counts[bone] = counts.get(bone, 0) + 1


def build_mass_mesh(positions, texcoords, normals, triangles, pivots, scale, minimum_y):
    body = [entry for entry in triangles if "chibang" not in entry[3].lower()
            and not entry[3].lower().startswith("w26")]
    wings = [entry for entry in triangles if "chibang" in entry[3].lower()]
    assignments = mass_body_assignments(positions, body)
    parts = {}
    counts = {}
    for face_index, entry in enumerate(body):
        triangle = entry[:3]
        bone = assignments[face_index]
        append_mesh_triangle(parts, counts, bone, triangle, positions, texcoords,
                             normals, pivots[bone], scale, minimum_y, 0.0)
    for entry in wings:
        triangle = entry[:3]
        points = [positions[ref[0]] for ref in triangle]
        centroid_x = sum(point[0] for point in points) / 3.0
        bone = "wing_l" if centroid_x >= 0 else "wing_r"
        append_mesh_triangle(parts, counts, bone, triangle, positions, texcoords,
                             normals, pivots[bone], scale, minimum_y, 0.5)
    return {
        "format_version": 1,
        "source": MASS["source"],
        "model_height": MASS_MODEL_HEIGHT,
        "stride": 8,
        "parts": {bone: {"pivot": pivots[bone], "vertices": values}
                  for bone, values in sorted(parts.items())},
    }, counts, len(body), len(wings)


def build_mass_animations():
    idle = {
        "loop": True, "animation_length": 3.2, "bones": {
            "torso_upper": {"rotation": {"0.0": [0, 0, 0], "1.6": [1.4, 0, 0],
                                           "3.2": [0, 0, 0]}},
            "head": {"rotation": {"0.0": [0, 0, 0], "1.6": [-1.4, 0, 0],
                                    "3.2": [0, 0, 0]}},
            "arm_r": {"rotation": {"0.0": [-95.55, 4, -9.92],
                                      "1.6": [-97.0, 4, -9.92],
                                      "3.2": [-95.55, 4, -9.92]}},
            "forearm_r": {"rotation": {"0.0": [5.53, 0.38, -3.97]}},
            "wing_l": {"rotation": {"0.0": [0, -2, 0], "1.6": [0, 2, 0],
                                      "3.2": [0, -2, 0]}},
            "wing_r": {"rotation": {"0.0": [0, 2, 0], "1.6": [0, -2, 0],
                                      "3.2": [0, 2, 0]}},
        },
    }
    move = {
        "loop": True, "animation_length": 1.0, "bones": {
            "leg_l": {"rotation": {"0.0": [-28, 0, 0], "0.5": [28, 0, 0],
                                     "1.0": [-28, 0, 0]}},
            "leg_r": {"rotation": {"0.0": [28, 0, 0], "0.5": [-28, 0, 0],
                                     "1.0": [28, 0, 0]}},
            "shin_l": {"rotation": {"0.0": [10, 0, 0], "0.5": [2, 0, 0],
                                      "1.0": [10, 0, 0]}},
            "shin_r": {"rotation": {"0.0": [2, 0, 0], "0.5": [10, 0, 0],
                                      "1.0": [2, 0, 0]}},
            "arm_l": {"rotation": {"0.0": [18, 0, 2], "0.5": [-18, 0, 2],
                                     "1.0": [18, 0, 2]}},
            "arm_r": {"rotation": {"0.0": [-95.55, 4, -9.92],
                                     "0.5": [-97.0, 4, -9.92],
                                     "1.0": [-95.55, 4, -9.92]}},
            "forearm_r": {"rotation": {"0.0": [5.53, 0.38, -3.97]}},
            "wing_l": {"rotation": {"0.0": [0, -5, -2], "0.5": [0, 9, 3],
                                      "1.0": [0, -5, -2]}},
            "wing_r": {"rotation": {"0.0": [0, 5, 2], "0.5": [0, -9, -3],
                                      "1.0": [0, 5, 2]}},
        },
    }
    ritual = {
        "loop": True, "animation_length": 3.0, "bones": {
            "torso_upper": {"rotation": {"0.0": [3, 0, 0]}},
            "head": {"rotation": {"0.0": [15, 0, 0], "1.5": [18, 0, 0],
                                    "3.0": [15, 0, 0]}},
            "arm_l": {"rotation": {"0.0": [0, 0, 86]}},
            "arm_r": {"rotation": {"0.0": [0, 0, -86]}},
            "forearm_l": {"rotation": {"0.0": [0, 0, 0]}},
            "forearm_r": {"rotation": {"0.0": [0, 0, 0]}},
            "leg_l": {"rotation": {"0.0": [0, 0, -2]}},
            "leg_r": {"rotation": {"0.0": [0, 0, 2]}},
            "wing_l": {"rotation": {"0.0": [0, 0, -2]}},
            "wing_r": {"rotation": {"0.0": [0, 0, 2]}},
        },
    }
    attack = {
        "animation_length": 0.62, "bones": {
            "torso_upper": {"rotation": {"0.0": [0, -10, 0], "0.14": [0, 8, 0],
                                           "0.62": [0, 0, 0]}},
            "arm_r": {"rotation": {"0.0": [18, 0, -14], "0.14": [-108, -8, 5],
                                     "0.38": [-92, -4, 3], "0.62": [0, 0, 0]}},
            "forearm_r": {"rotation": {"0.0": [26, 0, 0], "0.14": [-8, 0, 0],
                                         "0.62": [0, 0, 0]}},
            "arm_l": {"rotation": {"0.0": [-34, 0, 18], "0.14": [-62, 0, 24],
                                     "0.62": [0, 0, 0]}},
            "wing_l": {"rotation": {"0.0": [0, 8, -4], "0.14": [0, -3, 1],
                                      "0.62": [0, 8, -4]}},
            "wing_r": {"rotation": {"0.0": [0, -8, 4], "0.14": [0, 3, -1],
                                      "0.62": [0, -8, 4]}},
        },
    }
    # Visual Lab holds the strike contact instead of racing a one-shot trigger
    # while seven camera angles are captured one after another.
    visual_attack = {
        "loop": True, "animation_length": 1.0, "bones": {
            "torso_upper": {"rotation": {"0.0": [0, 8, 0]}},
            "head": {"rotation": {"0.0": [-6, -4, 0]}},
            "arm_r": {"rotation": {"0.0": [-108, -8, 5]}},
            "forearm_r": {"rotation": {"0.0": [-8, 0, 0]}},
            "hand_r": {"rotation": {"0.0": [0, 0, -5]}},
            "arm_l": {"rotation": {"0.0": [-62, 0, 24]}},
            "forearm_l": {"rotation": {"0.0": [18, 0, -8]}},
            "wing_l": {"rotation": {"0.0": [0, -3, 1]}},
            "wing_r": {"rotation": {"0.0": [0, 3, -1]}},
        },
    }
    # The synchronized revive state is a suspended, folded corpse silhouette.
    # A static key makes all seven regression views directly comparable.
    revive = {
        "loop": True, "animation_length": 1.0, "bones": {
            "root": {"position": {"0.0": [0, 4, 0]}},
            "torso_lower": {"rotation": {"0.0": [28, 0, 0]}},
            "torso_upper": {"rotation": {"0.0": [22, 0, 0]}},
            "head": {"rotation": {"0.0": [38, 0, 0]}},
            "arm_l": {"rotation": {"0.0": [18, 0, 28]}},
            "arm_r": {"rotation": {"0.0": [18, 0, -28]}},
            "forearm_l": {"rotation": {"0.0": [32, 0, -8]}},
            "forearm_r": {"rotation": {"0.0": [32, 0, 8]}},
            "leg_l": {"rotation": {"0.0": [-38, 0, -5]}},
            "leg_r": {"rotation": {"0.0": [18, 0, 5]}},
            "shin_l": {"rotation": {"0.0": [72, 0, 0]}},
            "shin_r": {"rotation": {"0.0": [48, 0, 0]}},
            "wing_l": {"rotation": {"0.0": [0, 30, -14]}},
            "wing_r": {"rotation": {"0.0": [0, -30, 14]}},
        },
    }
    return {"format_version": "1.8.0", "animations": {
        "animation.entity_mp.idle_1": idle,
        "animation.entity_mp.move": move,
        "animation.entity_mp.ritual": ritual,
        "animation.entity_mp.attack": attack,
        "animation.entity_mp.visual_attack": visual_attack,
        "animation.entity_mp.revive": revive,
    }}


def build_mass_atlas(body_texture, wing_texture):
    atlas = Image.new("RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), (0, 0, 0, 0))
    atlas.paste(Image.open(io.BytesIO(body_texture)).convert("RGBA"), (0, 0))
    atlas.paste(Image.open(io.BytesIO(wing_texture)).convert("RGBA"), (512, 0))
    return atlas


def write_mass(output):
    obj_text, body_texture, wing_texture = read_mass_source()
    positions, texcoords, normals, triangles = parse_obj_objects(obj_text)
    body_vertex_indices = {ref[0] for entry in triangles
                           if "chibang" not in entry[3].lower()
                           and not entry[3].lower().startswith("w26")
                           for ref in entry[:3]}
    minimum_y = min(positions[index][1] for index in body_vertex_indices)
    body_height = max(positions[index][1] for index in body_vertex_indices) - minimum_y
    scale = MASS_MODEL_HEIGHT / body_height
    pivots = scaled_pivots(MASS_SOURCE_PIVOTS, scale, minimum_y)
    mesh, counts, body_faces, wing_faces = build_mass_mesh(
        positions, texcoords, normals, triangles, pivots, scale, minimum_y)
    validate_mesh(mesh)
    target = MASS["target"]
    write_json(output / "geo" / f"{target}.geo.json", build_mass_skeleton(pivots))
    write_json(output / "animations" / f"{target}.animation.json", build_mass_animations())
    write_json(output / "mesh" / f"{target}.mesh.json", mesh, compact=True)
    texture_path = output / "textures/entity" / f"{target}.png"
    texture_path.parent.mkdir(parents=True, exist_ok=True)
    build_mass_atlas(body_texture, wing_texture).save(texture_path)
    excluded = len(triangles) - body_faces - wing_faces
    print(f"{target}: body={body_faces} / wings={wing_faces} / excluded weapon={excluded} triangles")
    print("bone faces: " + ", ".join(
        f"{bone}={count}" for bone, count in sorted(counts.items())))
    return body_faces + wing_faces


def update_pack_metadata(output, installed):
    pack_root = output.parent.parent
    pack_root.mkdir(parents=True, exist_ok=True)
    pack_meta = pack_root / "pack.mcmeta"
    if not pack_meta.exists():
        write_json(pack_meta, {"pack": {
            "pack_format": 15,
            "description": "Project SEELE local external model evaluation - not for redistribution",
        }})
    source_note = pack_root / "_SOURCE.txt"
    existing = source_note.read_text(encoding="utf-8") if source_note.exists() else ""
    additions = []
    for key in installed:
        config = MASS if key == "mass" else UNIT_VARIANTS[key]
        if config["url"] not in existing:
            additions.append(f"{config['source']}\n{config['url']}\n")
    if additions:
        source_note.write_text(existing.rstrip() + "\n" + "".join(additions)
                               + "Converted from user-downloaded OBJ files for LOCAL TESTING ONLY.\n",
                               encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="assets/projectseele output; files are written incrementally")
    parser.add_argument("--only", choices=("all", "unit00", "unit02", "mass"), default="all")
    args = parser.parse_args()
    output = args.output.resolve()
    selected = list(UNIT_VARIANTS) + ["mass"] if args.only == "all" else [args.only]
    for key in selected:
        config = MASS if key == "mass" else UNIT_VARIANTS[key]
        if not config["archive"].exists():
            raise SystemExit(f"source archive not found: {config['archive']}")
    for key in selected:
        if key == "mass":
            write_mass(output)
        else:
            write_unit(UNIT_VARIANTS[key], output)
    update_pack_metadata(output, selected)
    print(f"local Tiger variant pack written incrementally -> {output}")


if __name__ == "__main__":
    main()
