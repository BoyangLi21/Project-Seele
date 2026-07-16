#!/usr/bin/env python3
"""Build local-only EVA weapons and entry-plug meshes from downloaded FBX.

The converter intentionally ignores the body mesh in the EVA-02 archive.  It
extracts only its three independently-authored accessories, normalises them to
the Tiger rig sockets, and writes derived files under the ignored local
resource pack.  Nothing from either archive is redistributed by the repo.
"""

from __future__ import annotations

import argparse
import io
import json
import math
from pathlib import Path
import zipfile

from PIL import Image

from fbx_binary import connections, object_nodes, parse


REPO = Path(__file__).resolve().parent.parent
COMMON_ARCHIVE = REPO / "external-assets/incoming/progressive-knife.zip"
UNIT02_ARCHIVE = REPO / "external-assets/incoming/eva-02-rebuild-version-not-rigged.zip"
EUD_ARCHIVE = REPO / "eud-1.1.0-forge-1.20.1.jar"
DEFAULT_OUTPUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
COMMON_SOURCE_URL = (
    "https://sketchfab.com/3d-models/"
    "progressive-knife-e104dbec8c904f9b840c29c4a7d5d770")
UNIT02_SOURCE_URL = (
    "https://sketchfab.com/3d-models/"
    "eva-02-rebuild-version-not-rigged-4d715f56f7aa4f4cbed9703bc02a7171")
EUD_LANCE_MODEL = "assets/eud/models/custom/lanzadelonginusmodel.json"
EUD_LANCE_TEXTURE = "assets/eud/textures/block/texturelanzadelonginus.png"


def clean_name(node):
    return str(node.properties[1]).split("\x00", 1)[0]


def vector_length(value):
    return math.sqrt(sum(component * component for component in value))


def normalise(value):
    length = vector_length(value)
    if length < 1.0e-9:
        raise ValueError("zero-length direction")
    return tuple(component / length for component in value)


def dot(left, right):
    return sum(left[index] * right[index] for index in range(3))


def subtract(left, right):
    return tuple(left[index] - right[index] for index in range(3))


def cross(left, right):
    return (left[1] * right[2] - left[2] * right[1],
            left[2] * right[0] - left[0] * right[2],
            left[0] * right[1] - left[1] * right[0])


def centroid(points):
    return tuple(sum(point[axis] for point in points) / len(points) for axis in range(3))


def rotate_xyz(value, degrees):
    x, y, z = value
    rx, ry, rz = (math.radians(component) for component in degrees)
    cosine, sine = math.cos, math.sin
    y, z = y * cosine(rx) - z * sine(rx), y * sine(rx) + z * cosine(rx)
    x, z = x * cosine(ry) + z * sine(ry), -x * sine(ry) + z * cosine(ry)
    x, y = x * cosine(rz) - y * sine(rz), x * sine(rz) + y * cosine(rz)
    return x, y, z


def rotate_axis(value, origin, axis, degrees):
    """Apply a Java-model element rotation around one Blockbench axis."""
    relative = tuple(value[index] - origin[index] for index in range(3))
    rotation = tuple(degrees if name == axis else 0.0 for name in ("x", "y", "z"))
    rotated = rotate_xyz(relative, rotation)
    return tuple(rotated[index] + origin[index] for index in range(3))


def model_properties(model):
    values = {}
    section = model.child("Properties70")
    if section:
        for child in section.children:
            if child.name == "P" and len(child.properties) >= 7:
                values[str(child.properties[0])] = tuple(
                    float(value) for value in child.properties[4:7])
    return values


def transform_point(point, properties, include_translation=True):
    scale = properties.get("Lcl Scaling", (1.0, 1.0, 1.0))
    rotation = properties.get("Lcl Rotation", (0.0, 0.0, 0.0))
    result = rotate_xyz(tuple(point[axis] * scale[axis] for axis in range(3)), rotation)
    if include_translation:
        translation = properties.get("Lcl Translation", (0.0, 0.0, 0.0))
        result = tuple(result[axis] + translation[axis] for axis in range(3))
    return result


def transform_normal(value, properties):
    scale = properties.get("Lcl Scaling", (1.0, 1.0, 1.0))
    safe = tuple(value[axis] / scale[axis] if abs(scale[axis]) > 1.0e-9 else value[axis]
                 for axis in range(3))
    return normalise(rotate_xyz(safe, properties.get("Lcl Rotation", (0.0, 0.0, 0.0))))


def layer(geometry, name):
    return next((child for child in geometry.children if child.name == name), None)


def layer_tuple(section, name):
    if section is None:
        return ()
    child = section.child(name)
    if child is None or not child.properties:
        return ()
    value = child.properties[0]
    return value if isinstance(value, tuple) else ()


def mapped_index(section, vertex_index, polygon_vertex_index, polygon_index):
    mapping_node = section.child("MappingInformationType") if section else None
    reference_node = section.child("ReferenceInformationType") if section else None
    mapping = mapping_node.properties[0] if mapping_node and mapping_node.properties else "AllSame"
    reference = (reference_node.properties[0]
                 if reference_node and reference_node.properties else "Direct")
    if mapping == "ByPolygonVertex":
        index = polygon_vertex_index
    elif mapping in ("ByVertice", "ByVertex"):
        index = vertex_index
    elif mapping == "ByPolygon":
        index = polygon_index
    elif mapping == "AllSame":
        index = 0
    else:
        raise ValueError(f"unsupported FBX layer mapping {mapping}")
    if reference == "IndexToDirect":
        lookup_name = {
            "LayerElementNormal": "NormalsIndex",
            "LayerElementUV": "UVIndex",
        }.get(section.name)
        lookup = layer_tuple(section, lookup_name) if lookup_name else ()
        if lookup:
            index = int(lookup[index])
    elif reference != "Direct":
        raise ValueError(f"unsupported FBX layer reference {reference}")
    return index


def direct_vector(section, value_name, width, vertex_index,
                  polygon_vertex_index, polygon_index, fallback):
    if section is None:
        return fallback
    direct = layer_tuple(section, value_name)
    if not direct:
        return fallback
    index = mapped_index(section, vertex_index, polygon_vertex_index, polygon_index)
    start = index * width
    return tuple(float(value) for value in direct[start:start + width])


def polygon_materials(geometry):
    material_layer = layer(geometry, "LayerElementMaterial")
    return tuple(int(value) for value in layer_tuple(material_layer, "Materials"))


def material_index(material_values, polygon_index):
    if not material_values:
        return 0
    return material_values[min(polygon_index, len(material_values) - 1)]


def read_scene(data):
    _, nodes = parse(data)
    objects = object_nodes(nodes)
    by_id = {int(node.properties[0]): node for node in objects if node.properties}
    links = [value for value in connections(nodes)
             if len(value) >= 3 and value[0] == "OO"]
    parent = {int(value[1]): int(value[2]) for value in links}
    materials = {int(node.properties[0]): clean_name(node)
                 for node in objects if node.name == "Material"}
    model_materials = {}
    for value in links:
        child, target = int(value[1]), int(value[2])
        if child in materials:
            model_materials.setdefault(target, []).append(materials[child])

    result = {}
    for geometry in objects:
        if geometry.name != "Geometry":
            continue
        model = by_id[parent[int(geometry.properties[0])]]
        model_name = clean_name(model)
        properties = model_properties(model)
        source_vertices = layer_tuple(geometry, "Vertices")
        source_indices = layer_tuple(geometry, "PolygonVertexIndex")
        normals = layer(geometry, "LayerElementNormal")
        uv_layer = layer(geometry, "LayerElementUV")
        material_values = polygon_materials(geometry)
        material_names = model_materials.get(int(model.properties[0]), ["material_default"])
        points = [transform_point(point, properties) for point in
                  zip(source_vertices[0::3], source_vertices[1::3], source_vertices[2::3])]
        polygons = []
        current = []
        polygon_vertex_index = 0
        polygon_index = 0
        for encoded in source_indices:
            vertex_index = -int(encoded) - 1 if encoded < 0 else int(encoded)
            normal = direct_vector(normals, "Normals", 3, vertex_index,
                                   polygon_vertex_index, polygon_index, (0.0, 1.0, 0.0))
            uv = direct_vector(uv_layer, "UV", 2, vertex_index,
                               polygon_vertex_index, polygon_index, (0.5, 0.5))
            current.append((points[vertex_index], transform_normal(normal, properties), uv))
            polygon_vertex_index += 1
            if encoded < 0:
                material_slot = material_index(material_values, polygon_index)
                material = (material_names[material_slot]
                            if 0 <= material_slot < len(material_names) else material_names[0])
                for index in range(1, len(current) - 1):
                    polygons.append((current[0], current[index], current[index + 1], material))
                current = []
                polygon_index += 1
        result[model_name] = {"points": points, "triangles": polygons}
    return result


def remap_vertex(vertex, origin, basis, scales):
    point, normal, uv = vertex
    relative = subtract(point, origin)
    position = tuple(dot(relative, basis[axis]) * scales[axis] for axis in range(3))
    # For a diagonal scale in the chosen orthonormal basis, normals use the
    # inverse transpose.  This matters for the deliberately narrowed plug.
    mapped_normal = normalise(tuple(dot(normal, basis[axis]) / scales[axis]
                                    for axis in range(3)))
    return position, mapped_normal, uv


def mesh_part(objects, names, origin, basis, scales, pivot, uv_mapper):
    values = []
    triangle_count = 0
    for name in names:
        for triangle in objects[name]["triangles"]:
            material = triangle[3]
            for vertex in triangle[:3]:
                position, normal, uv = remap_vertex(vertex, origin, basis, scales)
                mapped_uv = uv_mapper(material, uv)
                values.extend([*(round(value, 5) for value in position),
                               round(mapped_uv[0], 6), round(mapped_uv[1], 6),
                               *(round(value, 5) for value in normal)])
            triangle_count += 1
    return {"pivot": list(pivot), "vertices": values}, triangle_count


def all_points(objects, names):
    return [point for name in names for point in objects[name]["points"]]


def span_scale(points, basis, target_spans):
    scales = []
    for axis, target in enumerate(target_spans):
        values = [dot(point, basis[axis]) for point in points]
        scales.append(target / (max(values) - min(values)))
    return tuple(scales)


def read_pivots(output):
    result = {}
    for unit in ("eva_unit00", "eva_unit01", "eva_unit02"):
        path = output / "geo" / f"{unit}.geo.json"
        if not path.exists():
            raise FileNotFoundError(f"generate Tiger EVA pack before accessories: {path}")
        geometry = json.loads(path.read_text(encoding="utf-8"))["minecraft:geometry"][0]
        result[unit] = {bone["name"]: tuple(float(value) for value in bone.get("pivot", (0, 0, 0)))
                        for bone in geometry["bones"]}
    return result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")


def make_mesh(source, part_name, part, triangles):
    return {
        "format_version": 1,
        "source": source,
        "model_height": 190.0,
        "stride": 8,
        "parts": {part_name: part},
        "triangle_count": triangles,
    }


def build_common_knife(output, pivots):
    with zipfile.ZipFile(COMMON_ARCHIVE) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read("source/knife.zip"))) as inner:
            objects = read_scene(inner.read("progknife.fbx"))
        names = tuple(objects)
        grip = centroid(objects["handle_low"]["points"])
        blade = centroid(objects["blade_low"]["points"])
        handle_end = centroid(objects["handle_end_low"]["points"])
        blade_axis = normalise(subtract(blade, handle_end))
        thickness = normalise(subtract((0.0, 1.0, 0.0),
                                       tuple(dot((0.0, 1.0, 0.0), blade_axis) * value
                                             for value in blade_axis)))
        side = normalise(cross(thickness, blade_axis))
        basis = (side, tuple(-value for value in blade_axis), thickness)
        points = all_points(objects, names)
        length_values = [dot(subtract(point, grip), blade_axis) for point in points]
        uniform = 42.0 / (max(length_values) - min(length_values))
        material_tiles = {"blade_low": 0, "text": 1, "handle_low": 2}

        def uv_mapper(material, uv):
            tile = material_tiles[material]
            return ((tile + min(1.0, max(0.0, uv[0]))) / 3.0,
                    min(1.0, max(0.0, 1.0 - uv[1])))

        part, triangles = mesh_part(objects, names, grip, basis,
                                    (uniform, uniform, uniform),
                                    pivots["eva_unit01"]["knife"], uv_mapper)
        write_json(output / "mesh/progressive_knife.mesh.json",
                   make_mesh("Udon-San Progressive Knife, CC BY 4.0, local only",
                             "knife", part, triangles))
        tile_size = 512
        atlas = Image.new("RGBA", (tile_size * 3, tile_size), (0, 0, 0, 0))
        images = ("knife_low_blade_low_BaseColor.png",
                  "knife_low_text_BaseColor.png",
                  "knife_low_handle_low_BaseColor.png")
        for index, suffix in enumerate(images):
            name = next(value for value in outer.namelist() if value.endswith(suffix))
            image = Image.open(io.BytesIO(outer.read(name))).convert("RGBA")
            atlas.paste(image.resize((tile_size, tile_size), Image.Resampling.LANCZOS),
                        (index * tile_size, 0))
        atlas.save(output / "textures/entity/progressive_knife.png")
    return triangles


def palette_mapper(materials, total_tiles=None):
    material_index = {name: index for index, name in enumerate(materials)}
    tile_count = total_tiles or len(materials)

    def mapper(material, _uv):
        index = material_index[material]
        return ((index + 0.5) / tile_count, 0.5)
    return mapper


def save_palette(path, colours):
    tile = 16
    image = Image.new("RGBA", (tile * len(colours), tile), (0, 0, 0, 255))
    for index, colour in enumerate(colours):
        cell = Image.new("RGBA", (tile, tile), (*colour, 255))
        image.paste(cell, (index * tile, 0))
    image.save(path)


def prism_part(pivot, polygon, z_min, z_max, palette_index, palette_size):
    """Create a small bone-local extruded polygon for a mechanical hatch."""
    values = []
    triangles = 0
    uv = ((palette_index + 0.5) / palette_size, 0.5)

    def emit(points, normal):
        nonlocal triangles
        for point in points:
            values.extend([round(point[0], 5), round(point[1], 5), round(point[2], 5),
                           round(uv[0], 6), round(uv[1], 6),
                           round(normal[0], 5), round(normal[1], 5), round(normal[2], 5)])
        triangles += 1

    for index in range(1, len(polygon) - 1):
        emit(((polygon[0][0], polygon[0][1], z_max),
              (polygon[index][0], polygon[index][1], z_max),
              (polygon[index + 1][0], polygon[index + 1][1], z_max)),
             (0.0, 0.0, 1.0))
        emit(((polygon[0][0], polygon[0][1], z_min),
              (polygon[index + 1][0], polygon[index + 1][1], z_min),
              (polygon[index][0], polygon[index][1], z_min)),
             (0.0, 0.0, -1.0))
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        edge = (end[0] - start[0], end[1] - start[1])
        normal = normalise((edge[1], -edge[0], 0.0))
        a = (start[0], start[1], z_min)
        b = (end[0], end[1], z_min)
        c = (end[0], end[1], z_max)
        d = (start[0], start[1], z_max)
        emit((a, b, c), normal)
        emit((a, c, d), normal)
    return {"pivot": list(pivot), "vertices": values}, triangles


def merge_parts(*parts):
    if not parts:
        raise ValueError("cannot merge empty hatch parts")
    pivot = parts[0][0]["pivot"]
    values = []
    triangles = 0
    for part, count in parts:
        if part["pivot"] != pivot:
            raise ValueError("hatch sub-parts must share one bone pivot")
        values.extend(part["vertices"])
        triangles += count
    return {"pivot": pivot, "vertices": values}, triangles


def build_unit02_weapons(output, pivots, objects):
    materials = ("rosso.002", "nero.002", "arancione.004", "bianco.002", "viola.002")
    uv_mapper = palette_mapper(materials)
    parts = {}
    counts = {}

    knife_points = objects["prog knife"]["points"]
    knife_basis = ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0))
    knife_centre = centroid(knife_points)
    knife_min_y = min(point[1] for point in knife_points)
    knife_max_y = max(point[1] for point in knife_points)
    # The handle occupies the rear fifth of this mesh; place the hand socket
    # there while still removing the FBX display-scene translation on X/Z.
    knife_origin = (knife_centre[0],
                    knife_min_y + (knife_max_y - knife_min_y) * 0.20,
                    knife_centre[2])
    knife_scale = 42.0 / (max(point[1] for point in knife_points)
                          - min(point[1] for point in knife_points))
    parts["knife"], counts["knife"] = mesh_part(
        objects, ("prog knife",), knife_origin, knife_basis,
        (knife_scale, knife_scale, knife_scale), pivots["eva_unit02"]["knife"], uv_mapper)

    sword_points = objects["sword"]["points"]
    sword_basis = knife_basis
    sword_origin = centroid(sword_points)
    sword_scale = 100.0 / (max(point[1] for point in sword_points)
                          - min(point[1] for point in sword_points))
    sword_pivot = pivots["eva_unit02"].get("sword", pivots["eva_unit02"]["lance"])
    parts["sword"], counts["sword"] = mesh_part(
        objects, ("sword",), sword_origin, sword_basis,
        (sword_scale, sword_scale, sword_scale), sword_pivot, uv_mapper)

    write_json(output / "mesh/eva02_weapons.mesh.json", {
        "format_version": 1,
        "source": "EVA-02 Rebuild accessories, CC BY, local only",
        "model_height": 190.0,
        "stride": 8,
        "parts": parts,
    })
    # Runtime layers are bone-driven.  Keep the archival combined mesh above,
    # but also emit one-part contracts: the knife follows the standard knife
    # socket and EVA-02's double-ended special weapon follows its existing
    # lance socket without inventing an unmapped `sword` Gecko bone.
    write_json(output / "mesh/eva02_knife.mesh.json",
               make_mesh("EVA-02 Rebuild progressive knife, CC BY, local only",
                         "knife", parts["knife"], counts["knife"]))
    write_json(output / "mesh/eva02_special_weapon.mesh.json",
               make_mesh("EVA-02 Rebuild special weapon, CC BY, local only",
                         "lance", parts["sword"], counts["sword"]))
    save_palette(output / "textures/entity/eva02_weapons.png", (
        (164, 13, 2), (5, 5, 5), (149, 66, 9), (229, 229, 229), (68, 57, 88)))
    return counts


def build_entry_plug(output, pivots, objects):
    name = "entry plug"
    points = objects[name]["points"]
    centre = centroid(points)
    # Source Z is the capsule axis.  Width and depth are deliberately narrowed
    # to fit the Tiger dorsal socket instead of importing EVA-02's backpack.
    basis = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
    scales = span_scale(points, basis, (8.0, 38.0, 9.0))
    # Bind the socket to the plug's trailing cap, not its geometric centre.
    # With the former centre anchor, the zero animation pose left half of the
    # 38px capsule above the armour and made a fully inserted plug look stuck
    # outside the EVA.  Source +Z is the long axis; anchoring at max Z maps the
    # complete capsule into local Y [-38, 0], so position Y=0 is genuinely
    # seated below the dorsal opening while positive animation offsets raise it.
    axis_max = max(dot(point, basis[1]) for point in points)
    centre_axis = dot(centre, basis[1])
    socket_anchor = tuple(centre[index]
                          + basis[1][index] * (axis_max - centre_axis)
                          for index in range(3))
    materials = ("rosso.002", "nero.002", "arancione.004")
    plug_part, plug_triangles = mesh_part(
        objects, (name,), socket_anchor, basis, scales,
        pivots["eva_unit01"]["entry_plug"], palette_mapper(materials, 6))

    # Replace the legacy 32px grey rectangles with compact, tapered doors that
    # sit on the Tiger dorsal armour. They remain separate Gecko bones so the
    # authored open/close animation still drives the exact runtime geometry.
    left_shape = ((0.0, -24.0), (6.0, -21.0), (7.0, -5.0),
                  (2.0, -1.0), (0.0, -2.0))
    left_inset = ((0.8, -20.0), (5.0, -18.5), (5.7, -6.0),
                  (2.0, -3.0), (0.8, -3.5))
    left_stripe = ((1.2, -17.0), (2.2, -16.2), (2.8, -7.0), (1.7, -6.5))

    def mirror(shape):
        return tuple((-x, y) for x, y in reversed(shape))

    hatch_parts = {}
    hatch_triangles = 0
    for bone, shape, inset, stripe in (
            ("plug_hatch_l", left_shape, left_inset, left_stripe),
            ("plug_hatch_r", mirror(left_shape), mirror(left_inset), mirror(left_stripe))):
        pivot = pivots["eva_unit01"][bone]
        hatch, count = merge_parts(
            prism_part(pivot, shape, 0.0, 2.0, 3, 6),
            prism_part(pivot, inset, 2.01, 2.18, 4, 6),
            prism_part(pivot, stripe, 2.19, 2.28, 5, 6))
        hatch_parts[bone] = hatch
        hatch_triangles += count

    triangles = plug_triangles + hatch_triangles
    write_json(output / "mesh/entry_plug.mesh.json", {
        "format_version": 1,
        "source": "EVA-02 Rebuild plug + Project SEELE Tiger dorsal hatch, local only",
        "model_height": 190.0,
        "stride": 8,
        "parts": {"entry_plug": plug_part, **hatch_parts},
        "triangle_count": triangles,
    })
    # TV-like neutral plug treatment plus Tiger-compatible dorsal armour.
    save_palette(output / "textures/entity/entry_plug.png",
                 ((232, 235, 239), (52, 55, 61), (226, 102, 18),
                  (50, 25, 79), (17, 20, 27), (45, 181, 85)))
    return triangles


BLOCK_FACE_LAYOUT = {
    "north": (((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), (0.0, 0.0, -1.0)),
    "south": (((1, 0, 1), (0, 0, 1), (0, 1, 1), (1, 1, 1)), (0.0, 0.0, 1.0)),
    "west": (((0, 0, 1), (0, 0, 0), (0, 1, 0), (0, 1, 1)), (-1.0, 0.0, 0.0)),
    "east": (((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)), (1.0, 0.0, 0.0)),
    "down": (((0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0)), (0.0, -1.0, 0.0)),
    "up": (((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)), (0.0, 1.0, 0.0)),
}


def build_eud_lance(output, pivots):
    """Retarget EUD's local Blockbench Longinus model to the EVA lance socket."""
    with zipfile.ZipFile(EUD_ARCHIVE) as archive:
        model = json.loads(archive.read(EUD_LANCE_MODEL).decode("utf-8"))
        texture = Image.open(io.BytesIO(archive.read(EUD_LANCE_TEXTURE))).convert("RGBA")

    # The source is a vertical hand item: shaft tail y=-16, fork tip y=32.
    # The lance socket belongs to the rear/right hand, not the forward guide
    # hand. Put that grip at y=-15.5: only 1.8 model pixels remain behind the
    # palm while 171.0 extend toward the target. The old y=-6 split left 36 pixels
    # behind the hand and visibly drove the butt into the EVA's chest in first
    # person. Flip +Y into rig-local -Y (entity-forward). Length and
    # cross-section are scaled independently:
    # scaling the hand-item model uniformly made its fork wider than Unit-01's
    # torso and pushed the decorative coils down around the pilot's feet.
    centre_xz = (8.0, 8.0)
    grip_y = -15.5
    length_scale = 3.6
    cross_scale = 1.4
    values = []
    triangle_count = 0
    uv_corners = ((0, 3), (2, 3), (2, 1), (0, 1))
    for element in model.get("elements", []):
        minimum = tuple(float(value) for value in element["from"])
        maximum = tuple(float(value) for value in element["to"])
        element_rotation = element.get("rotation", {})
        angle = float(element_rotation.get("angle", 0.0))
        axis = element_rotation.get("axis", "y")
        origin = tuple(float(value) for value in element_rotation.get("origin", (8, 8, 8)))
        for face_name, face in element.get("faces", {}).items():
            layout = BLOCK_FACE_LAYOUT.get(face_name)
            if layout is None:
                continue
            corner_selectors, source_normal = layout
            corners = []
            for selector in corner_selectors:
                point = tuple(maximum[index] if selector[index] else minimum[index]
                              for index in range(3))
                if abs(angle) > 1.0e-8:
                    point = rotate_axis(point, origin, axis, angle)
                corners.append(point)
            edge_a = subtract(corners[1], corners[0])
            edge_b = subtract(corners[2], corners[0])
            if vector_length(cross(edge_a, edge_b)) < 1.0e-7:
                continue
            normal = source_normal
            if abs(angle) > 1.0e-8:
                normal = rotate_axis(normal, (0.0, 0.0, 0.0), axis, angle)
            normal = normalise((normal[0] / cross_scale,
                                -normal[1] / length_scale,
                                normal[2] / cross_scale))
            uv = tuple(float(value) for value in face.get("uv", (0, 0, 16, 16)))
            mapped_uv = tuple((uv[index[0]] / 16.0, uv[index[1]] / 16.0)
                              for index in uv_corners)
            for triangle in ((0, 1, 2), (0, 2, 3)):
                for corner_index in triangle:
                    point = corners[corner_index]
                    position = ((point[0] - centre_xz[0]) * cross_scale,
                                -(point[1] - grip_y) * length_scale,
                                (point[2] - centre_xz[1]) * cross_scale)
                    texcoord = mapped_uv[corner_index]
                    values.extend([*(round(value, 5) for value in position),
                                   round(texcoord[0], 6), round(texcoord[1], 6),
                                   *(round(value, 5) for value in normal)])
                triangle_count += 1
    part = {"pivot": list(pivots["eva_unit01"]["lance"]), "vertices": values}
    write_json(output / "mesh/longinus_lance.mesh.json",
               make_mesh("EUD 1.1.0 Longinus model, local testing / permission pending",
                         "lance", part, triangle_count))
    texture.save(output / "textures/entity/longinus_lance.png")
    return triangle_count


def append_source_note(output):
    pack_root = output.parent.parent
    note = pack_root / "_SOURCE.txt"
    existing = note.read_text(encoding="utf-8") if note.exists() else ""
    additions = []
    if COMMON_SOURCE_URL not in existing:
        additions.append(
            "Udon-San Progressive Knife (CC BY 4.0), LOCAL TESTING ONLY.\n"
            + COMMON_SOURCE_URL + "\n")
    if UNIT02_SOURCE_URL not in existing:
        additions.append(
            "EVA-02 Rebuild (not rigged) accessories (CC BY), LOCAL TESTING ONLY; "
            "body mesh excluded.\n" + UNIT02_SOURCE_URL + "\n")
    if "EUD 1.1.0 Longinus" not in existing:
        additions.append(
            "EUD 1.1.0 Longinus model, LOCAL TESTING ONLY; permission pending.\n")
    if additions:
        note.write_text(existing.rstrip() + "\n" + "".join(additions), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if (not COMMON_ARCHIVE.exists() or not UNIT02_ARCHIVE.exists()
            or not EUD_ARCHIVE.exists()):
        raise SystemExit("downloaded knife, EVA-02 and local EUD archives are required")
    output = args.output.resolve()
    (output / "mesh").mkdir(parents=True, exist_ok=True)
    (output / "textures/entity").mkdir(parents=True, exist_ok=True)
    pivots = read_pivots(output)
    with zipfile.ZipFile(UNIT02_ARCHIVE) as archive:
        unit02_objects = read_scene(archive.read("source/eva 02.fbx"))
    common_triangles = build_common_knife(output, pivots)
    unit02_counts = build_unit02_weapons(output, pivots, unit02_objects)
    plug_triangles = build_entry_plug(output, pivots, unit02_objects)
    lance_triangles = build_eud_lance(output, pivots)
    append_source_note(output)
    print(f"common progressive knife: {common_triangles} triangles")
    print("EVA-02 weapons: " + ", ".join(
        f"{name}={count}" for name, count in sorted(unit02_counts.items())))
    print(f"adapted entry plug: {plug_triangles} triangles / 8x38x9 model pixels / trailing-cap socket")
    print(f"EUD Longinus attachment: {lance_triangles} triangles")
    print(f"local accessories written -> {output}")


if __name__ == "__main__":
    main()
