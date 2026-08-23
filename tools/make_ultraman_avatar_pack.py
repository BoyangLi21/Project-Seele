"""Blender-side converter for the user-supplied rigged Ultraman FBX.

Run with:
  blender --background --python tools/make_ultraman_avatar_pack.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "external-assets/incoming/ultraman-rig-updated"
          / "source/ULTRAMAN.fbx")
SOURCE_TEXTURE = (ROOT / "external-assets/incoming/ultraman-rig-updated"
                  / "textures/Ultraman_body_color.png")
ASSETS = ROOT / "run/resourcepacks/eva_real_model/assets/projectseele"
GEO = ASSETS / "geo/ultraman_avatar.geo.json"
MESH = ASSETS / "mesh/ultraman_avatar.mesh.json"
ANIMATION = ASSETS / "animations/ultraman_avatar.animation.json"
TEXTURE = ASSETS / "textures/entity/ultraman_avatar.png"
MODEL_HEIGHT = 32.0


def load_scene() -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SOURCE), use_anim=True)
    armatures = [obj for obj in bpy.context.scene.objects
                 if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects
              if obj.type == "MESH"]
    if len(armatures) != 1 or not meshes:
        raise RuntimeError(
            f"expected one armature and meshes, got {armatures}/{meshes}")
    armature = armatures[0]
    armature.data.pose_position = "POSE"
    bpy.context.scene.frame_set(0)
    # Bake one clean neutral stance with both arms naturally at the sides.
    # The previous runtime bone split rotated these signs the other way and
    # raised both arms vertically over the head.
    for name, degrees in (("CC_Base_L_Upperarm", -82.0),
                          ("CC_Base_R_Upperarm", 82.0)):
        pose_bone = armature.pose.bones.get(name)
        if pose_bone is None:
            raise RuntimeError(f"missing required arm bone {name}")
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler.z = math.radians(degrees)
    bpy.context.view_layer.update()
    return armature, meshes


def world_vertices(meshes: list[bpy.types.Object]) -> list[Vector]:
    result = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        result.extend(evaluated.matrix_world @ vertex.co
                      for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    return result


def converter(points: list[Vector]):
    minimum = Vector((min(p.x for p in points), min(p.y for p in points),
                      min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points),
                      max(p.z for p in points)))
    height = maximum.z - minimum.z
    if height <= 0.0:
        raise RuntimeError("Ultraman model has no vertical extent")
    scale = MODEL_HEIGHT / height
    centre_x = (minimum.x + maximum.x) * 0.5
    centre_y = (minimum.y + maximum.y) * 0.5

    def position(point: Vector) -> tuple[float, float, float]:
        # LocalTriangleMeshLayer reflects stored X once. Store the inverse so
        # the final model keeps the FBX's authored handedness.
        return (-(point.x - centre_x) * scale,
                (point.z - minimum.z) * scale,
                -(point.y - centre_y) * scale)

    def normal(vector: Vector) -> tuple[float, float, float]:
        vector = vector.normalized()
        return (-vector.x, vector.z, -vector.y)

    return position, normal, minimum, maximum


def main() -> None:
    if not SOURCE.is_file() or not SOURCE_TEXTURE.is_file():
        raise FileNotFoundError(SOURCE)
    armature, meshes = load_scene()
    convert_position, convert_normal, minimum, maximum = converter(
        world_vertices(meshes))

    bones = [{"name": "root", "pivot": [0.0, 0.0, 0.0]}]
    values: list[float] = []
    rejected_stretched_triangles = 0
    rejected_peripheral_fragments = 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None
        normal_matrix = evaluated.matrix_world.to_3x3().inverted().transposed()
        for triangle in mesh.loop_triangles:
            converted = [convert_position(
                evaluated.matrix_world @ mesh.vertices[mesh.loops[index].vertex_index].co)
                for index in triangle.loops]
            longest = max(math.dist(converted[a], converted[b])
                          for a, b in ((0, 1), (1, 2), (2, 0)))
            # 198 FBX polygons reference non-imported finger-tip helper nodes
            # and stretch 10 model units across empty space. Healthy surface
            # triangles top out below 2 units. Reject only those corrupt
            # polygons; all valid palm and finger surfaces remain continuous.
            if longest > 2.5:
                rejected_stretched_triangles += 1
                continue
            centroid_x = sum(point[0] for point in converted) / 3.0
            if abs(centroid_x) > 10.5:
                # The FBX also contains two disconnected fingertip helper
                # islands roughly five model units beyond each real hand.
                # They are not part of the continuous body surface.
                rejected_peripheral_fragments += 1
                continue
            for loop_index in triangle.loops:
                loop = mesh.loops[loop_index]
                absolute = converted[list(triangle.loops).index(loop_index)]
                nx, ny, nz = convert_normal(normal_matrix @ loop.normal)
                if uv_layer is None:
                    u, v = 0.0, 0.0
                else:
                    uv = uv_layer[loop_index].uv
                    u, v = float(uv.x), 1.0 - float(uv.y)
                values.extend((
                    round(absolute[0], 5),
                    round(absolute[1], 5),
                    round(absolute[2], 5),
                    round(u, 6), round(v, 6),
                    round(nx, 5), round(ny, 5), round(nz, 5),
                ))
        evaluated.to_mesh_clear()

    mesh_payload = {
        "format_version": 1,
        "source": "User-supplied ultraman-rig-updated.zip; local private use only",
        "local_only": True,
        "release_approved": False,
        "model_height": MODEL_HEIGHT,
        "stride": 8,
        "parts": {"root": {"pivot": [0.0, 0.0, 0.0],
                            "vertices": values}},
    }
    geo_payload = {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": "geometry.ultraman_avatar",
                "texture_width": 2048,
                "texture_height": 2048,
                "visible_bounds_width": 40,
                "visible_bounds_height": 40,
                "visible_bounds_offset": [0, 18, 0],
            },
            "bones": bones,
        }],
    }
    animation_payload = {
        "format_version": "1.8.0",
        "animations": {
            "animation.ultraman.idle": {
                "loop": True,
                "animation_length": 2.0,
                "bones": {
                    "root": {"position": {
                        "0.0": [0, 0, 0], "1.0": [0, 0.10, 0],
                        "2.0": [0, 0, 0]}},
                },
            },
            "animation.ultraman.walk": {
                "loop": True,
                "animation_length": 1.0,
                "bones": {
                    "root": {"position": {
                        "0.0": [0, 0, 0], "0.25": [0, 0.16, 0],
                        "0.5": [0, 0, 0], "0.75": [0, 0.16, 0],
                        "1.0": [0, 0, 0]}},
                },
            },
            "animation.ultraman.run": {
                "loop": True,
                "animation_length": 0.62,
                "bones": {
                    "root": {"position": {
                        "0.0": [0, 0, 0], "0.155": [0, 0.24, 0],
                        "0.31": [0, 0, 0], "0.465": [0, 0.24, 0],
                        "0.62": [0, 0, 0]}},
                },
            },
        },
    }

    for path, payload in ((GEO, geo_payload), (MESH, mesh_payload),
                          (ANIMATION, animation_payload)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, separators=(",", ":")),
                        encoding="utf-8")
    TEXTURE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_TEXTURE, TEXTURE)
    triangles = len(values) // 24
    print(json.dumps({
        "source": str(SOURCE), "triangles": triangles,
        "parts": 1, "bones": len(bones),
        "rejected_stretched_triangles": rejected_stretched_triangles,
        "rejected_peripheral_fragments": rejected_peripheral_fragments,
        "source_bounds": [list(minimum), list(maximum)],
        "outputs": [str(GEO), str(MESH), str(ANIMATION), str(TEXTURE)],
    }, indent=2))


if __name__ == "__main__":
    main()
