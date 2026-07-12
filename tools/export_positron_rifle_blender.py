#!/usr/bin/env python3
"""Blender-side exporter for Kantrophe's downloaded positron rifle.

Run with Blender 3.x/4.x, not regular Python::

    blender --background Rifledone.blend --python tools/export_positron_rifle_blender.py -- \
      --output external-assets/work/positron_rifle_export/positron_rifle.obj

The exporter uses Blender's mesh API directly, so no OBJ add-on is required.
It never saves or modifies the source .blend file.
"""

import argparse
import sys
from pathlib import Path

import bpy


def parse_args():
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--decimate", type=float, default=0.36,
                        help="collapse ratio; 0.36 targets roughly 20k triangles")
    parser.add_argument("--exclude", action="append", default=[],
                        help="case-insensitive object-name substring to omit")
    return parser.parse_args(arguments)


def visible_meshes(excluded):
    excluded = [value.lower() for value in excluded]
    return [obj for obj in bpy.context.scene.objects
            if obj.type == "MESH" and not obj.hide_render
            and not any(value in obj.name.lower() for value in excluded)]


def main():
    args = parse_args()
    if not 0.0 < args.decimate <= 1.0:
        raise SystemExit("--decimate must be in (0, 1]")
    objects = visible_meshes(args.exclude)
    if not objects:
        raise SystemExit("no visible mesh objects found")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    vertices = []
    texcoords = []
    normals = []
    vertex_lookup = {}
    face_groups = []
    source_triangles = 0

    for obj in objects:
        modifier = None
        if args.decimate < 0.999:
            modifier = obj.modifiers.new("__project_seele_export_decimate", "DECIMATE")
            modifier.ratio = args.decimate
            modifier.use_collapse_triangulate = True
            # Force the dependency graph to see the temporary modifier before
            # obtaining the evaluated mesh in background mode.
            bpy.context.view_layer.update()
            depsgraph.update()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        mesh.calc_loop_triangles()
        uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        material_names = [slot.material.name if slot.material else f"material_{index}"
                          for index, slot in enumerate(obj.material_slots)]
        groups = {}
        for triangle in mesh.loop_triangles:
            source_triangles += 1
            material = (material_names[triangle.material_index]
                        if triangle.material_index < len(material_names) else "material_default")
            face = []
            world_normal = (normal_matrix @ triangle.normal).normalized()
            for loop_index in triangle.loops:
                loop = mesh.loops[loop_index]
                world = obj.matrix_world @ mesh.vertices[loop.vertex_index].co
                uv = uv_layer[loop_index].uv if uv_layer else (0.0, 0.0)
                key = (round(world.x, 7), round(world.y, 7), round(world.z, 7),
                       round(uv[0], 7), round(uv[1], 7),
                       round(world_normal.x, 7), round(world_normal.y, 7),
                       round(world_normal.z, 7))
                index = vertex_lookup.get(key)
                if index is None:
                    index = len(vertices) + 1
                    vertex_lookup[key] = index
                    vertices.append(key[:3])
                    texcoords.append(key[3:5])
                    normals.append(key[5:8])
                face.append(index)
            groups.setdefault(material, []).append(tuple(face))
        for material, faces in groups.items():
            face_groups.append((obj.name, material, faces))
        evaluated.to_mesh_clear()
        if modifier is not None:
            obj.modifiers.remove(modifier)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# Project SEELE local intermediate; source remains CC BY.\n")
        for x, y, z in vertices:
            stream.write(f"v {x:.7f} {y:.7f} {z:.7f}\n")
        for u, v in texcoords:
            stream.write(f"vt {u:.7f} {v:.7f}\n")
        for x, y, z in normals:
            stream.write(f"vn {x:.7f} {y:.7f} {z:.7f}\n")
        for object_name, material, faces in face_groups:
            stream.write(f"o {object_name.replace(' ', '_')}\n")
            stream.write(f"usemtl {material.replace(' ', '_')}\n")
            for face in faces:
                stream.write("f " + " ".join(f"{index}/{index}/{index}" for index in face) + "\n")
    print(f"exported {len(objects)} objects / {source_triangles} triangles / "
          f"{len(vertices)} split vertices -> {args.output}")


if __name__ == "__main__":
    main()
