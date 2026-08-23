#!/usr/bin/env python3
"""Build the local high-detail Entry Plug and its visible cockpit.

Run this script with the bundled Blender rather than the system Python::

    blender --background --python tools/make_entry_plug_model.py -- \
        --source external-assets/incoming/entry-plug/crymsin-2501188/files/ObjWithMaterial/EntryPlugSolidv3.obj \
        --output run/resourcepacks/eva_real_model/assets/projectseele

The source OBJ is a very dense 3D-print shell.  This converter:

* preserves its five authored material groups while decimating them separately;
* removes a real opening from the forward shell instead of painting on a door;
* adds a local-only cockpit inspired by the DONW999 Soul Throne reference
  renders (the downloaded archive contains only ``Stand.stl``, not the seat);
* emits the same compact bone-driven triangle format used by the EVA renderers.

Downloaded source files and generated meshes remain in Git-ignored directories.
Only this reproducible conversion code is distributed by Project SEELE.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

try:
    import bpy
    from mathutils import Vector
except ModuleNotFoundError:
    bpy = None
    Vector = None


REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = (
    REPO
    / "external-assets/incoming/entry-plug/crymsin-2501188/files"
    / "ObjWithMaterial/EntryPlugSolidv3.obj"
)
DEFAULT_OUTPUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"

LEGACY_MODEL_LENGTH = 58.0
LEGACY_MODEL_WIDTH = 14.0
LEGACY_MODEL_DEPTH = 14.0
# The original 3D-print conversion read as a short, oversized barrel beside a
# 60-block EVA. Canon line art instead shows a long spinal capsule: narrower,
# with only a compact boarding hatch near its forward third.
MODEL_LENGTH = 50.0
MODEL_WIDTH = 8.0
MODEL_DEPTH = 8.0
COCKPIT_SCALE = (
    MODEL_WIDTH / LEGACY_MODEL_WIDTH,
    MODEL_LENGTH / LEGACY_MODEL_LENGTH,
    MODEL_DEPTH / LEGACY_MODEL_DEPTH,
)
# The source-normalisation helpers below first produce the legacy intermediate
# frame C (length on -Y, hatch on +Z).  Before export every vertex, normal,
# cockpit part and hatch is baked once into the reviewed canonical plug frame
# P: width +X, hatch/top +Y, length outward +Z, insertion tip at the origin.
# Runtime code must therefore never add a second pivot or corrective rotation.
PIVOT = (0.0, 0.0, 0.0)
HATCH_PIVOT = PIVOT

PALETTE = (
    (232, 236, 239, 255),  # Body2: cool white pressure shell
    (18, 22, 28, 255),     # Black: labels and seams
    (224, 91, 12, 255),    # Features: NERV orange
    (154, 113, 16, 255),   # Rear1: rear machinery
    (112, 121, 130, 255),  # Gray: metal details
    (13, 17, 24, 255),     # cockpit cavity
    (56, 28, 82, 255),     # Soul Throne upholstery
    (102, 109, 123, 255),  # control hardware
    (244, 150, 18, 255),   # warning / harness
    (190, 82, 12, 255),    # LCL-lit interior trim
    (112, 121, 130, 255),  # variant-owned crane/identification collar
    (220, 18, 24, 255),    # supplied NERV logo red
)

COLLAR_INDEX = 10
FEATURE_INDEX = 2
VARIANT_FEATURES = {
    0: PALETTE[FEATURE_INDEX],       # Prototype: retain authored orange band
    1: (100, 42, 151, 255),         # Test Type: Unit-01 violet band
    2: (178, 25, 38, 255),          # Production Model: Unit-02 red band
}
VARIANT_SEATS = {
    0: (174, 122, 20, 255),         # Unit-00: ochre prototype seat
    1: PALETTE[6],                  # Unit-01: violet test-type seat
    2: (132, 24, 38, 255),          # Unit-02: crimson production seat
}

MATERIAL_INDEX = {
    "Body2": 0,
    "Black": 1,
    "Features": 2,
    "Rear1": 3,
    "Gray": 4,
}

# A single collapse ratio erases the lettering and rear fittings long before
# the 3D-print body's flat tessellation is under control.  Per-material budgets
# keep the visible identity while bringing 250,554 source triangles down to a
# level suitable for three simultaneous hangar capsules.
TARGETS = {
    "Body2": 7000,
    "Black": 1500,
    "Features": 1200,
    "Rear1": 700,
    "Gray": 800,
}


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(values)


def run_blender(args: argparse.Namespace):
    configured = os.environ.get("BLENDER_EXE") or os.environ.get("BLENDER")
    candidates = [
        Path(configured) if configured else None,
        Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        (REPO / "external-assets/tools/blender-3.6.0-portable"
         / "blender-3.6.0-windows-x64/blender.exe"),
    ]
    blender = next(
        (candidate for candidate in candidates
         if candidate is not None and candidate.is_file()),
        None,
    )
    if blender is None:
        raise SystemExit(
            "Blender was not found. Set BLENDER_EXE to blender.exe."
        )
    command = [
        str(blender), "--background", "--python", str(Path(__file__).resolve()),
        "--", "--source", str(args.source.resolve()),
        "--output", str(args.output.resolve()),
    ]
    result = subprocess.call(command, cwd=REPO)
    if result == 0:
        result = subprocess.call([
            sys.executable,
            str(REPO / "tools/make_entry_plug_identification.py"),
            "--output", str(args.output.resolve()),
        ], cwd=REPO)
    raise SystemExit(result)


def read_obj(path: Path):
    vertices: list[tuple[float, float, float]] = []
    faces: dict[str, list[tuple[int, int, int]]] = {
        name: [] for name in MATERIAL_INDEX
    }
    current = "Body2"
    with path.open("r", encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append((float(x), float(y), float(z)))
            elif line.startswith("usemtl "):
                name = line.split(None, 1)[1].strip()
                current = name if name in faces else "Body2"
            elif line.startswith("f "):
                indices = []
                for value in line.split()[1:]:
                    raw = int(value.split("/", 1)[0])
                    indices.append(raw - 1 if raw > 0 else len(vertices) + raw)
                for index in range(1, len(indices) - 1):
                    faces[current].append(
                        (indices[0], indices[index], indices[index + 1])
                    )
    if not vertices or not any(faces.values()):
        raise RuntimeError(f"OBJ contains no usable geometry: {path}")
    return vertices, faces


def source_bounds(vertices):
    return tuple(
        (min(value[axis] for value in vertices),
         max(value[axis] for value in vertices))
        for axis in range(3)
    )


def is_hatch_face(face, vertices, bounds) -> bool:
    centre = tuple(
        sum(vertices[index][axis] for index in face) / 3.0
        for axis in range(3)
    )
    normalised = tuple(
        (centre[axis] - bounds[axis][0])
        / max(1.0e-9, bounds[axis][1] - bounds[axis][0])
        for axis in range(3)
    )
    # Source +Z is the face presented to the wet-cage boarding bridge.  The
    # compact rounded window exposes the seat without turning half the capsule
    # into a two-piece clamshell.
    x_centre = (bounds[0][0] + bounds[0][1]) * 0.5
    x_radius = (bounds[0][1] - bounds[0][0]) * 0.32
    return (
        0.38 <= normalised[1] <= 0.62
        and abs(centre[0] - x_centre) <= x_radius
        and normalised[2] >= 0.80
    )


def make_material_object(name, source_vertices, source_faces, bounds):
    kept = [
        face for face in source_faces
        if not is_hatch_face(face, source_vertices, bounds)
    ]
    used = sorted({index for face in kept for index in face})
    remap = {source: target for target, source in enumerate(used)}
    vertices = [source_vertices[index] for index in used]
    faces = [tuple(remap[index] for index in face) for face in kept]
    mesh = bpy.data.meshes.new(f"EntryPlug_{name}")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"EntryPlug_{name}", mesh)
    bpy.context.collection.objects.link(obj)
    obj["palette_index"] = MATERIAL_INDEX[name]
    return obj


def decimate(obj, target: int):
    count = len(obj.data.polygons)
    if count <= target:
        return
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    modifier = obj.modifiers.new("RuntimeDecimate", "DECIMATE")
    modifier.decimate_type = "COLLAPSE"
    modifier.ratio = max(0.001, min(1.0, target / float(count)))
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def normalise(value):
    length = math.sqrt(sum(component * component for component in value))
    if length < 1.0e-9:
        return (0.0, 0.0, 1.0)
    return tuple(component / length for component in value)


def mapped_position(point, bounds):
    centres = (
        (bounds[0][0] + bounds[0][1]) * 0.5,
        bounds[1][1],
        (bounds[2][0] + bounds[2][1]) * 0.5,
    )
    spans = (
        bounds[0][1] - bounds[0][0],
        bounds[1][1] - bounds[1][0],
        bounds[2][1] - bounds[2][0],
    )
    return (
        (point[0] - centres[0]) * MODEL_WIDTH / spans[0],
        (point[1] - centres[1]) * MODEL_LENGTH / spans[1],
        (point[2] - centres[2]) * MODEL_DEPTH / spans[2],
    )


def mapped_normal(value, bounds):
    spans = (
        (bounds[0][1] - bounds[0][0]) / MODEL_WIDTH,
        (bounds[1][1] - bounds[1][0]) / MODEL_LENGTH,
        (bounds[2][1] - bounds[2][0]) / MODEL_DEPTH,
    )
    return normalise(tuple(value[index] * spans[index] for index in range(3)))


def uv_for(index: int):
    return ((index + 0.5) / len(PALETTE), 0.5)


def append_triangle(values, points, palette_index, normal=None):
    if normal is None:
        left = Vector(points[1]) - Vector(points[0])
        right = Vector(points[2]) - Vector(points[0])
        normal = normalise(tuple(left.cross(right)))
    uv = uv_for(palette_index)
    for point in points:
        values.extend((
            round(point[0], 5), round(point[1], 5), round(point[2], 5),
            round(uv[0], 6), round(uv[1], 6),
            round(normal[0], 5), round(normal[1], 5), round(normal[2], 5),
        ))


def append_quad(values, points, palette_index):
    append_triangle(values, (points[0], points[1], points[2]), palette_index)
    append_triangle(values, (points[0], points[2], points[3]), palette_index)


def rotated(point, centre, degrees):
    x, y, z = (point[index] - centre[index] for index in range(3))
    rx, ry, rz = (math.radians(value) for value in degrees)
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return (x + centre[0], y + centre[1], z + centre[2])


def append_box(values, centre, size, palette_index, degrees=(0.0, 0.0, 0.0)):
    hx, hy, hz = (value * 0.5 for value in size)
    corners = [
        (-hx, -hy, -hz), (hx, -hy, -hz),
        (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz),
        (hx, hy, hz), (-hx, hy, hz),
    ]
    points = [
        rotated(
            (corner[0] + centre[0], corner[1] + centre[1],
             corner[2] + centre[2]),
            centre, degrees,
        )
        for corner in corners
    ]
    for face in (
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5),
        (2, 3, 7, 6), (3, 0, 4, 7),
    ):
        append_quad(values, tuple(points[index] for index in face), palette_index)


def append_cylinder(values, start, end, radius, sides, palette_index):
    axis = Vector(end) - Vector(start)
    direction = axis.normalized()
    reference = Vector((0.0, 0.0, 1.0))
    if abs(direction.dot(reference)) > 0.95:
        reference = Vector((1.0, 0.0, 0.0))
    side = direction.cross(reference).normalized() * radius
    up = direction.cross(side).normalized() * radius
    rings = []
    for centre in (Vector(start), Vector(end)):
        rings.append([
            tuple(centre + side * math.cos(index * math.tau / sides)
                  + up * math.sin(index * math.tau / sides))
            for index in range(sides)
        ])
    for index in range(sides):
        following = (index + 1) % sides
        append_quad(values, (
            rings[0][index], rings[0][following],
            rings[1][following], rings[1][index],
        ), palette_index)
    for index in range(1, sides - 1):
        append_triangle(
            values,
            (start, rings[0][index + 1], rings[0][index]),
            palette_index,
        )
        append_triangle(
            values,
            (end, rings[1][index], rings[1][index + 1]),
            palette_index,
        )


def append_shell_objects(values, objects, bounds):
    triangles = 0
    for obj in objects:
        palette_index = int(obj["palette_index"])
        uv = uv_for(palette_index)
        mesh = obj.data
        mesh.calc_loop_triangles()
        for triangle in mesh.loop_triangles:
            positions = [
                mapped_position(mesh.vertices[index].co, bounds)
                for index in triangle.vertices
            ]
            normal = mapped_normal(triangle.normal, bounds)
            for point in positions:
                values.extend((
                    round(point[0], 5), round(point[1], 5), round(point[2], 5),
                    round(uv[0], 6), round(uv[1], 6),
                    round(normal[0], 5), round(normal[1], 5),
                    round(normal[2], 5),
                ))
            triangles += 1
    return triangles


def add_cockpit(values):
    before = len(values)
    # Pressure-cavity backing and structural side cheeks.  The first cabin
    # liner stopped roughly 1.0 model unit below the hatch skin, so an occupied
    # first-person camera could see daylight along both sides even with the
    # leaves shut.  These walls and bulkheads overlap the pressure-door plane.
    append_box(values, (0.0, -30.0, -5.35), (11.5, 25.0, 0.65), 5)
    append_box(values, (-5.75, -30.0, 0.75), (0.55, 25.0, 13.0), 5)
    append_box(values, (5.75, -30.0, 0.75), (0.55, 25.0, 13.0), 5)
    append_box(values, (0.0, -43.0, 0.5), (11.0, 1.0, 13.0), 4)
    append_box(values, (0.0, -17.0, 0.5), (11.0, 1.0, 13.0), 4)
    # Inward-facing roof jambs bridge the real shell opening to the two moving
    # leaves.  They overlap both the side cheeks and hatch prism by a small
    # amount, producing a light-tight pressure seal without closing the hatch.
    for side in (-1.0, 1.0):
        append_box(values, (side * 4.98, -30.0, 6.80),
                   (1.42, 25.0, 0.72), 4)
    append_box(values, (0.0, -42.25, 6.80), (10.4, 1.65, 0.72), 4)
    append_box(values, (0.0, -17.75, 6.80), (10.4, 1.65, 0.72), 4)

    # Soul Throne silhouette: reclined back, head restraint, cushion and deep
    # side bolsters.  These are clean-room runtime pieces because the supplied
    # DONW999 ZIP contains only its display stand.
    append_box(values, (0.0, -33.0, -3.65), (7.0, 13.5, 1.55), 6,
               degrees=(8.0, 0.0, 0.0))
    append_box(values, (0.0, -40.2, -3.15), (5.4, 4.4, 1.8), 6,
               degrees=(5.0, 0.0, 0.0))
    append_box(values, (0.0, -23.6, -2.15), (6.4, 6.2, 1.8), 6,
               degrees=(-12.0, 0.0, 0.0))
    append_box(values, (-3.7, -31.0, -2.55), (1.0, 15.5, 2.0), 6,
               degrees=(8.0, 0.0, -3.0))
    append_box(values, (3.7, -31.0, -2.55), (1.0, 15.5, 2.0), 6,
               degrees=(8.0, 0.0, 3.0))

    # Shoulder harness and lap restraint.
    append_box(values, (-1.6, -34.0, -2.7), (0.55, 10.0, 0.24), 8,
               degrees=(8.0, 0.0, 11.0))
    append_box(values, (1.6, -34.0, -2.7), (0.55, 10.0, 0.24), 8,
               degrees=(8.0, 0.0, -11.0))
    append_box(values, (0.0, -25.8, -1.0), (6.0, 0.55, 0.3), 8)

    # Two induction levers: articulated bases, stalks, hand grips and triggers.
    for side in (-1.0, 1.0):
        x = side * 4.25
        append_box(values, (x, -27.0, -2.1), (1.5, 4.5, 1.8), 7,
                   degrees=(4.0, 0.0, side * 5.0))
        append_cylinder(
            values, (x, -25.4, -1.25), (side * 4.65, -21.2, 1.8),
            0.34, 8, 7,
        )
        append_box(
            values, (side * 4.7, -20.4, 2.25), (1.15, 3.0, 1.25), 7,
            degrees=(18.0, 0.0, side * 4.0),
        )
        append_box(
            values, (side * 4.38, -19.8, 2.88), (0.24, 1.1, 0.4), 8,
            degrees=(18.0, 0.0, side * 4.0),
        )

    # Foot rests, cable spine and restrained orange cabin guide lights.
    append_box(values, (-2.0, -17.8, -2.2), (2.7, 4.5, 0.7), 7,
               degrees=(-12.0, 0.0, 0.0))
    append_box(values, (2.0, -17.8, -2.2), (2.7, 4.5, 0.7), 7,
               degrees=(-12.0, 0.0, 0.0))
    append_box(values, (0.0, -30.0, -5.0), (0.55, 23.0, 0.25), 9)
    append_box(values, (-5.3, -30.0, 3.9), (0.22, 21.0, 0.22), 9)
    append_box(values, (5.3, -30.0, 3.9), (0.22, 21.0, 0.22), 9)
    scale_vertices(values, before, COCKPIT_SCALE)
    return (len(values) - before) // (8 * 3)


def scale_vertices(values, start, scale):
    """Non-uniformly scales generated geometry and inverse-scales normals."""
    sx, sy, sz = scale
    for index in range(start, len(values), 8):
        values[index] = round(values[index] * sx, 5)
        values[index + 1] = round(values[index + 1] * sy, 5)
        values[index + 2] = round(values[index + 2] * sz, 5)
        normal = normalise((
            values[index + 5] / sx,
            values[index + 6] / sy,
            values[index + 7] / sz,
        ))
        values[index + 5] = round(normal[0], 5)
        values[index + 6] = round(normal[1], 5)
        values[index + 7] = round(normal[2], 5)


def canonicalise_vertices(values, start=0):
    """Bake T_PC: (x_C,y_C,z_C) -> (x_C,z_C,-y_C)."""
    for index in range(start, len(values), 8):
        x, y, z = values[index:index + 3]
        nx, ny, nz = values[index + 5:index + 8]
        values[index:index + 3] = (
            round(x, 5), round(z, 5), round(-y, 5),
        )
        values[index + 5:index + 8] = (
            round(nx, 5), round(nz, 5), round(-ny, 5),
        )


def hatch_polygon(left: bool):
    legacy_shape = (
        (-4.35, -34.0), (-4.0, -36.0), (0.12, -36.0),
        (0.04, -22.0), (-4.0, -22.0), (-4.35, -24.0),
    )
    shape = tuple((
        x * COCKPIT_SCALE[0],
        y * COCKPIT_SCALE[1],
    ) for x, y in legacy_shape)
    if left:
        return shape
    return tuple((-x, y) for x, y in reversed(shape))


def sealed_hatch_polygon(left: bool):
    """Slightly overlap the pressure jamb and centre seam when closed."""
    shape = hatch_polygon(left)
    centre_x = sum(point[0] for point in shape) / len(shape)
    centre_y = sum(point[1] for point in shape) / len(shape)
    return tuple((
        centre_x + (x - centre_x) * 1.045,
        centre_y + (y - centre_y) * 1.030,
    ) for x, y in shape)


def make_prism_part(pivot, polygon, z_min, z_max, palette_index):
    values = []
    for index in range(1, len(polygon) - 1):
        append_triangle(values, (
            (polygon[0][0], polygon[0][1], z_max),
            (polygon[index][0], polygon[index][1], z_max),
            (polygon[index + 1][0], polygon[index + 1][1], z_max),
        ), palette_index)
        append_triangle(values, (
            (polygon[0][0], polygon[0][1], z_min),
            (polygon[index + 1][0], polygon[index + 1][1], z_min),
            (polygon[index][0], polygon[index][1], z_min),
        ), palette_index)
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        append_quad(values, (
            (start[0], start[1], z_min),
            (end[0], end[1], z_min),
            (end[0], end[1], z_max),
            (start[0], start[1], z_max),
        ), palette_index)
    return {"pivot": list(pivot), "vertices": values}


def add_hatch_detail(part, polygon, palette_index):
    values = part["vertices"]
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    centre_x = (min(xs) + max(xs)) * 0.5
    centre_y = (min(ys) + max(ys)) * 0.5
    # Sit the detail only a hair above the pressure shell.  The former
    # legacy-Z value was scaled independently from the normalized shell and
    # left the entire hatch floating outside it in side view.
    # Keep raised trim almost flush with the door skin.  At the runtime scale
    # the former 0.12-model-unit standoff read as a visible air gap in oblique
    # first-person views even though the pressure-door prism itself was sealed.
    hatch_surface = MODEL_DEPTH * 0.507
    append_box(values, (centre_x, centre_y, hatch_surface),
               (max(xs) - min(xs) - 1.3, 0.55, 0.22), palette_index)
    append_box(values, (centre_x, centre_y - 3.2, hatch_surface),
               (max(xs) - min(xs) - 1.8, 0.32, 0.20), 2)
    append_box(values, (centre_x, centre_y + 3.2, hatch_surface),
               (max(xs) - min(xs) - 1.8, 0.32, 0.20), 1)


def make_crane_collar_part():
    """Build the rigid wet-cage lock ring around the canonical tail marker.

    This part is authored directly in plug frame P, so unlike source OBJ and
    hatch geometry it must not pass through ``canonicalise_vertices`` again.
    The slightly oversized four-jaw ring makes the block-scale crane terminate
    on visible machinery rather than a bare white pressure shell.
    """
    values = []
    # Four interlocking jaws around the 8x8 pressure shell.
    append_box(values, (0.0, 4.75, 49.0), (11.0, 1.5, 2.2), COLLAR_INDEX)
    append_box(values, (0.0, -4.75, 49.0), (11.0, 1.5, 2.2), COLLAR_INDEX)
    append_box(values, (-4.75, 0.0, 49.0), (1.5, 8.0, 2.2), COLLAR_INDEX)
    append_box(values, (4.75, 0.0, 49.0), (1.5, 8.0, 2.2), COLLAR_INDEX)
    # Dorsal lifting lug and paired gussets meet the centre crane ram.
    append_box(values, (0.0, 5.75, 49.5), (3.2, 1.0, 2.8), 3)
    append_box(values, (-2.55, 5.05, 48.7),
               (3.1, 0.65, 0.8), 3, degrees=(0.0, 0.0, 15.0))
    append_box(values, (2.55, 5.05, 48.7),
               (3.1, 0.65, 0.8), 3, degrees=(0.0, 0.0, -15.0))
    return {"pivot": list(PIVOT), "vertices": values}


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")


def png_chunk(name: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + name
        + payload
        + struct.pack(">I", zlib.crc32(name + payload) & 0xFFFFFFFF)
    )


def write_palette(path: Path, palette=PALETTE):
    tile = 16
    width = tile * len(palette)
    rows = []
    for _ in range(tile):
        row = bytearray((0,))
        for colour in palette:
            row.extend(bytes(colour) * tile)
        rows.append(bytes(row))
    data = zlib.compress(b"".join(rows), 9)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, tile, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", data)
        + png_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def write_decal_mesh(path: Path):
    """One flush top plate; its long texture axis follows the plug spine."""
    y = 4.46
    x0, x1 = -3.15, 3.15
    z0, z1 = 37.0, 46.0
    normal = (0.0, 1.0, 0.0)
    vertices = []

    def vertex(point, uv):
        vertices.extend((point[0], point[1], point[2],
                         uv[0], uv[1], *normal))

    # Texture width runs from the insertion end toward the coloured collar;
    # texture height runs across the pressure shell.  This keeps the long
    # designation readable while the capsule lies on its boarding bridge.
    for point, uv in (
            ((x0, y, z0), (0.0, 1.0)),
            ((x1, y, z0), (0.0, 0.0)),
            ((x1, y, z1), (1.0, 0.0)),
            ((x0, y, z0), (0.0, 1.0)),
            ((x1, y, z1), (1.0, 0.0)),
            ((x0, y, z1), (1.0, 1.0))):
        vertex(point, uv)
    write_json(path, {
        "format_version": 1,
        "model_height": 190.0,
        "stride": 8,
        "parts": {
            "entry_plug": {
                "pivot": [0.0, 0.0, 0.0],
                "vertices": vertices,
            },
        },
        "triangle_count": 2,
    })


def main():
    args = parse_args()
    if bpy is None:
        run_blender(args)
    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    source_vertices, grouped_faces = read_obj(source)
    bounds = source_bounds(source_vertices)
    objects = []
    for name in MATERIAL_INDEX:
        obj = make_material_object(
            name, source_vertices, grouped_faces[name], bounds
        )
        decimate(obj, TARGETS[name])
        objects.append(obj)

    shell_values = []
    shell_triangles = append_shell_objects(shell_values, objects, bounds)
    cockpit_triangles = add_cockpit(shell_values)
    canonicalise_vertices(shell_values)

    # The leaves must overlap the shell lip in depth, not merely be made wider.
    # Sink the pressure face into the new inward jamb while retaining one
    # unambiguous outer skin; this removes the side-light slit from the cabin.
    hatch_inner = MODEL_DEPTH * 0.440
    hatch_outer = MODEL_DEPTH * 0.505
    left_polygon = sealed_hatch_polygon(True)
    right_polygon = sealed_hatch_polygon(False)
    left = make_prism_part(
        HATCH_PIVOT, left_polygon, hatch_inner, hatch_outer, 0
    )
    right = make_prism_part(
        HATCH_PIVOT, right_polygon, hatch_inner, hatch_outer, 0
    )
    add_hatch_detail(left, left_polygon, 4)
    add_hatch_detail(right, right_polygon, 4)
    canonicalise_vertices(left["vertices"])
    canonicalise_vertices(right["vertices"])
    # Fixed hinge barrels remain on the pressure shell while the two leaves
    # rotate around their outer edges.  Three knuckles per side read as actual
    # load-bearing machinery instead of two detached floating panels.
    hinge_start = len(shell_values)
    for hinge_x in (-2.5, 2.5):
        for hinge_z in (24.0, 29.0, 34.0):
            append_box(shell_values, (hinge_x, 4.08, hinge_z),
                       (0.42, 0.34, 3.2), 4)
    hinge_triangles = (len(shell_values) - hinge_start) // (8 * 3)
    hatch_triangles = (
        len(left["vertices"]) + len(right["vertices"])
    ) // (8 * 3)
    collar = make_crane_collar_part()
    collar_triangles = len(collar["vertices"]) // (8 * 3)

    parts = {
        "entry_plug": {"pivot": list(PIVOT), "vertices": shell_values},
        "plug_hatch_l": left,
        "plug_hatch_r": right,
        "plug_crane_collar": collar,
    }
    total = (shell_triangles + cockpit_triangles + hinge_triangles
             + hatch_triangles
             + collar_triangles)
    write_json(output / "mesh/entry_plug.mesh.json", {
        "format_version": 1,
        "source": (
            "Crymsin Entry Plug exterior (CC BY) + Project SEELE clean-room "
            "cockpit guided by DONW999 Soul Throne reference renders (CC BY); "
            "local evaluation only"
        ),
        "model_height": 190.0,
        "stride": 8,
        "dimensions": [MODEL_WIDTH, MODEL_DEPTH, MODEL_LENGTH],
        "canonical_frame": {
            "version": 1,
            "origin": "insertion_tip",
            "right_axis": "+X",
            "hatch_top_axis": "+Y",
            "outward_axis": "+Z",
            "insertion_axis": "-Z",
            "world_scale": "EvaScale.ENTRY_PLUG_RENDER_SCALE/16",
        },
        # Runtime clearance uses a deliberately conservative block-space OBB.
        # Keep it separate from the exact model-space bounds so future shell
        # detail cannot silently shrink the mechanical safety envelope.
        "collision_contract_blocks": {
            "body_obb": {
                "centre": [0.0, 0.0, 5.0],
                "half_extents": [1.0, 1.0, 5.0],
            },
            "tip_plane_z": 0.0,
            "length": 10.0,
        },
        "markers_model_units": {
            "plug_tip": [0.0, 0.0, 0.0],
            "plug_body_obb": {
                "centre": [0.0, 0.0, 25.0],
                "half_extents": [4.0, 4.0, 25.0],
            },
            "plug_hatch_portal_obb": {
                "centre": [0.0, 4.0, 29.0],
                "half_extents": [2.5, 0.4, 7.0],
            },
            "pilot_seat": [0.0, -2.0, 31.0],
            "pilot_eye": [0.0, 0.8, 27.5],
            "pilot_dismount_left": [-6.4, 5.2, 29.0],
            "pilot_dismount_right": [6.4, 5.2, 29.0],
            "plug_lock_reference": [0.0, 0.0, 50.0],
        },
        "hatch_transforms_model_units": {
            "left": {
                "closed_translation": [0.0, 0.0, 0.0],
                "hinge_pivot": [-2.5, 4.12, 29.0],
                "open_rotation_z_degrees": 82.0,
            },
            "right": {
                "closed_translation": [0.0, 0.0, 0.0],
                "hinge_pivot": [2.5, 4.12, 29.0],
                "open_rotation_z_degrees": -82.0,
            },
        },
        "parts": parts,
        "triangle_count": total,
        "audit": {
            "shell_triangles": shell_triangles,
            "hatch_hinge_triangles": hinge_triangles,
            "cockpit_triangles": cockpit_triangles,
            "hatch_triangles": hatch_triangles,
            "crane_collar_triangles": collar_triangles,
            "source_triangles": sum(len(value) for value in grouped_faces.values()),
            "hatch_is_real_opening": True,
            "donw999_mesh_available": False,
        },
    })
    write_palette(output / "textures/entity/entry_plug.png")
    for variant, feature in VARIANT_FEATURES.items():
        palette = list(PALETTE)
        # The unit colour belongs to the orange authored pressure-shell band,
        # not to the extra crane collar added by this converter.
        palette[FEATURE_INDEX] = feature
        palette[6] = VARIANT_SEATS[variant]
        write_palette(output / (
            f"textures/entity/entry_plug_unit{variant:02d}.png"), palette)
    print(
        "Project SEELE Entry Plug:",
        f"{total} triangles",
        f"(shell={shell_triangles}, cockpit={cockpit_triangles},",
        f"hatches={hatch_triangles}, collar={collar_triangles})",
        f"dimensions={MODEL_WIDTH}x{MODEL_LENGTH}x{MODEL_DEPTH}px",
    )


if __name__ == "__main__":
    main()
