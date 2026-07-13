#!/usr/bin/env python3
"""Render the current Third Impact tableau without starting Minecraft.

The script deliberately reads the Java sources instead of carrying a second
hand-maintained layout.  It projects the current front-capture camera onto a
1280x720 canvas, draws the red Tree backplate and labels, and places simple
silhouettes at the nine Mass-Production EVA nodes plus a cruciform Unit-01 at
Tiferet.  The silhouettes are composition probes, not model replacements.

The body silhouettes remain deliberately schematic, but their screen-space
envelopes come from the real local SmOd triangle meshes after the ritual and
crucified GeckoLib animations are sampled.  This lets the strict report reject
an overlapping formation without pretending that gameplay hitboxes describe
the rendered models.

This is an offline framing/readability check.  It cannot approve depth-test
behaviour or Minecraft's exact font rasterisation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont

try:
    import render_unit01_rig_preview as rig
except ModuleNotFoundError:  # Support ``python -m tools.render_tree_of_life_preview``.
    from tools import render_unit01_rig_preview as rig


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_SOURCE = ROOT / "src/main/java/com/projectseele/fx/TreeOfLifeLayout.java"
FX_SOURCE = ROOT / "src/main/java/com/projectseele/client/fx/ClientFxManager.java"
CAPTURE_SOURCE = ROOT / "src/main/java/com/projectseele/client/visual/VisualCaptureManager.java"
ENTITY_SOURCE = ROOT / "src/main/java/com/projectseele/registry/ModEntities.java"
CLIENT_EVENTS_SOURCE = ROOT / "src/main/java/com/projectseele/client/ClientEvents.java"
UNIT_RENDERER_SOURCE = ROOT / "src/main/java/com/projectseele/client/render/EvaUnit01Renderer.java"
DEFAULT_ASSET_ROOT = (
    ROOT / "run/resourcepacks/eva_real_model/assets/projectseele"
)
DEFAULT_OUTPUT = ROOT / "external-assets/work/tree-of-life-preview"

RED = (255, 0, 0, 255)
RED_DIM = (142, 0, 0, 255)
RED_SOFT = (92, 0, 0, 255)
BODY_FILL = (23, 25, 31, 255)
MASS_OUTLINE = (225, 229, 236, 255)
UNIT_OUTLINE = (195, 255, 206, 255)


@dataclass(frozen=True)
class VisualEnvelope:
    model: str
    animation: str
    renderer_scale: float
    sample_time: float
    vertex_count: int
    # Posed renderer-local bounds in blocks: min x/y/z, max x/y/z.
    bounds: tuple[float, float, float, float, float, float]
    source_files: tuple[Path, ...]

    @property
    def width(self) -> float:
        return self.bounds[3] - self.bounds[0]

    @property
    def height(self) -> float:
        return self.bounds[4] - self.bounds[1]


@dataclass(frozen=True)
class TreeData:
    tableau_orientation: str
    column_x: float
    row_y: float
    keter: int
    tiferet: int
    malkuth: int
    nodes: tuple[tuple[float, float], ...]
    paths: tuple[tuple[int, int], ...]
    names: tuple[str, ...]
    hebrew: tuple[str, ...]
    numerals: tuple[str, ...]
    divine_names: tuple[str, ...]
    archangels: tuple[str, ...]
    choirs: tuple[str, ...]
    letters: tuple[str, ...]
    path_numerals: tuple[str, ...]
    camera_distance: float
    frame_bottom: float
    frame_top_margin: float
    tree_depth: float
    mass_width: float
    mass_height: float
    unit_width: float
    unit_height: float
    mass_visual: VisualEnvelope
    unit_visual: VisualEnvelope
    outer_radius: float
    centre_radius: float
    path_offset: float
    path_outer_width: float
    path_inner_width: float
    ring_outer_width: float
    ring_inner_width: float
    node_tick_count: int
    node_name_y: float
    node_name_scale: float
    divine_name_y: float
    divine_name_scale: float
    external_archangel_y: float
    external_archangel_scale: float
    external_choir_y: float
    external_choir_scale: float
    path_letter_offset: float
    path_letter_scale: float
    glory_scale: float
    glory_length_base: float
    glory_length_step: float
    glory_width_base: float
    glory_width_step: float
    label_rotation_degrees: float
    diagram_text_z: float
    internal_name_scale: float
    internal_divine_scale: float
    internal_archangel_scale: float
    internal_choir_scale: float
    path_number_scale: float
    label_x_offsets: tuple[float, ...]
    path_label_offsets: tuple[tuple[float, float], ...]
    all_labels_backed: bool

    def node_world(self, index: int) -> tuple[float, float]:
        x, y = self.nodes[index]
        return x * self.column_x, y * self.row_y


@dataclass(frozen=True)
class Projection:
    width: int
    height: int
    fov_degrees: float
    camera_distance: float
    target_y: float

    @property
    def focal(self) -> float:
        return self.height * 0.5 / math.tan(math.radians(self.fov_degrees) * 0.5)

    def point(self, x: float, y: float, depth: float = 0.0) -> tuple[float, float]:
        distance = self.camera_distance - depth
        if distance <= 0.0:
            raise ValueError(f"point is behind camera: depth={depth}, camera={self.camera_distance}")
        scale = self.focal / distance
        return self.width * 0.5 + x * scale, self.height * 0.5 - (y - self.target_y) * scale

    def length(self, value: float, depth: float = 0.0) -> float:
        return value * self.focal / (self.camera_distance - depth)


@dataclass
class LabelBox:
    identifier: str
    kind: str
    text: str
    logical_text: str
    position: tuple[float, float]
    scale: float
    bbox: tuple[float, float, float, float]
    projected_height: float
    backed: bool
    depth_layer: str
    rotation_degrees: float


@dataclass(frozen=True)
class LabelSpec:
    identifier: str
    kind: str
    text: str
    logical_text: str
    position: tuple[float, float]
    scale: float
    force_backing: bool = False
    depth_layer: str = "foreground"
    rotation_degrees: float = 0.0


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_match(pattern: str, source: str, label: str, flags: int = 0) -> re.Match[str]:
    match = re.search(pattern, source, flags)
    if not match:
        raise ValueError(f"could not parse {label}")
    return match


def java_initializer(source: str, name: str) -> str:
    match = require_match(rf"\b{re.escape(name)}\b\s*=\s*\{{", source, name)
    start = source.find("{", match.start())
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ValueError(f"unclosed Java initializer: {name}")


def java_string(raw: str) -> str:
    # Java strings used by the tree are JSON-compatible (quoted text and
    # \uXXXX escapes).  json.loads gives us the actual Hebrew glyphs.
    return json.loads(f'"{raw}"')


def quoted_values(initializer: str) -> tuple[str, ...]:
    raw = re.findall(r'"((?:\\.|[^"\\])*)"', initializer)
    return tuple(java_string(value) for value in raw)


def float_constant(source: str, name: str) -> float:
    match = require_match(
        rf"\b{name}\s*=\s*(-?\d+(?:\.\d+)?)(?:D|F)?\s*;", source, name
    )
    return float(match.group(1))


def int_constant(source: str, name: str) -> int:
    match = require_match(rf"\b{name}\s*=\s*(\d+)\s*;", source, name)
    return int(match.group(1))


def string_constant(source: str, name: str) -> str:
    match = require_match(rf'\b{name}\s*=\s*"([^"]+)"\s*;', source, name)
    return match.group(1)


def entity_size(source: str, registry_name: str) -> tuple[float, float]:
    pattern = (
        rf'\.build\("{re.escape(registry_name)}"\)|'
        rf'\.build\("{re.escape(registry_name)}"\)'
    )
    end = require_match(pattern, source, f"{registry_name} entity registration").end()
    prefix = source[:end]
    sizes = list(re.finditer(r"\.sized\((\d+(?:\.\d+)?)F,\s*(\d+(?:\.\d+)?)F\)", prefix))
    if not sizes:
        raise ValueError(f"could not parse {registry_name} entity size")
    match = sizes[-1]
    return float(match.group(1)), float(match.group(2))


def renderer_scales() -> tuple[float, float]:
    client = read(CLIENT_EVENTS_SOURCE)
    unit_renderer = read(UNIT_RENDERER_SOURCE)
    mass = require_match(
        r'ColossalHumanoidRenderer\.Style\.MASS_PRODUCTION,\s*'
        r'"mass_production_eva",\s*([\d.]+)F',
        client,
        "Mass Production renderer scale",
        re.S,
    )
    unit = require_match(
        r"\bwithScale\(([\d.]+)F\)",
        unit_renderer,
        "Unit-01 renderer scale",
    )
    return float(mass.group(1)), float(unit.group(1))


def posed_visual_envelope(asset_root: Path, model: str, animation: str,
                           renderer_scale: float, sample_time: float = 0.0) -> VisualEnvelope:
    mesh_path = asset_root / "mesh" / f"{model}.mesh.json"
    geo_path = asset_root / "geo" / f"{model}.geo.json"
    animation_path = asset_root / "animations" / f"{model}.animation.json"
    missing = [path for path in (mesh_path, geo_path, animation_path) if not path.is_file()]
    if missing:
        raise ValueError(
            "high-detail visual envelope requires the generated local SmOd pack; missing: "
            + ", ".join(str(path) for path in missing)
        )

    mesh = json.loads(mesh_path.read_text(encoding="utf-8"))
    pivots, parents, base_rotations = rig.load_skeleton(mesh, geo_path)
    selected, sampled, rotations, positions = rig.select_animation(
        animation_path, animation, sample_time
    )
    matrices: dict[str, list[list[float]]] = {}
    for bone in mesh.get("parts", {}):
        rig.bone_matrix(
            bone, pivots, parents, rotations, positions,
            base_rotations, matrices,
        )

    # LocalTriangleMeshLayer emits one model pixel as 1/16 block.  Its X
    # reflection only swaps the extrema, so retain the exact front envelope by
    # applying the same reflection here before renderer scale.
    factor = renderer_scale / 16.0
    points: list[tuple[float, float, float]] = []
    stride = int(mesh.get("stride", 0))
    if stride != 8:
        raise ValueError(f"{model} mesh stride must be 8, got {stride}")
    for bone, part in mesh.get("parts", {}).items():
        if bone not in matrices:
            raise ValueError(f"{model} has no pose matrix for mesh bone {bone}")
        values = part.get("vertices", ())
        pivot = part.get("pivot", (0.0, 0.0, 0.0))
        for index in range(0, len(values), stride):
            absolute = [values[index + axis] + pivot[axis] for axis in range(3)]
            posed = rig.transform(matrices[bone], absolute)
            points.append((-posed[0] * factor, posed[1] * factor, -posed[2] * factor))
    if not points:
        raise ValueError(f"{model} high-detail mesh contains no vertices")

    return VisualEnvelope(
        model=model,
        animation=selected,
        renderer_scale=renderer_scale,
        sample_time=sampled,
        vertex_count=len(points),
        bounds=(
            min(point[0] for point in points),
            min(point[1] for point in points),
            min(point[2] for point in points),
            max(point[0] for point in points),
            max(point[1] for point in points),
            max(point[2] for point in points),
        ),
        source_files=(mesh_path, geo_path, animation_path),
    )


def parse_tree(asset_root: Path) -> TreeData:
    layout = read(LAYOUT_SOURCE)
    fx = read(FX_SOURCE)
    capture = read(CAPTURE_SOURCE)
    entities = read(ENTITY_SOURCE)

    nodes = tuple(
        (float(x), float(y))
        for x, y in re.findall(
            r"\{\s*(-?\d+(?:\.\d+)?)F?\s*,\s*(-?\d+(?:\.\d+)?)F?\s*\}",
            java_initializer(layout, "NODES"),
        )
    )
    paths = tuple(
        (int(left), int(right))
        for left, right in re.findall(
            r"\{\s*(\d+)\s*,\s*(\d+)\s*\}", java_initializer(layout, "PATHS")
        )
    )
    names = quoted_values(java_initializer(fx, "SEPHIRA_NAMES"))
    hebrew = quoted_values(java_initializer(fx, "SEPHIRA_HEBREW"))
    numerals = quoted_values(java_initializer(fx, "SEPHIRA_NUMERALS"))
    divine_names = quoted_values(java_initializer(fx, "SEPHIRA_DIVINE_NAMES"))
    archangels = quoted_values(java_initializer(fx, "SEPHIRA_ARCHANGELS"))
    choirs = quoted_values(java_initializer(fx, "SEPHIRA_CHOIRS"))
    letters = quoted_values(java_initializer(fx, "PATH_LETTERS"))
    path_numerals = quoted_values(java_initializer(fx, "PATH_NUMERALS"))
    if (len(nodes), len(paths), len(names), len(hebrew), len(numerals),
            len(divine_names), len(archangels), len(choirs),
            len(letters), len(path_numerals)) \
            != (10, 22, 10, 10, 10, 10, 10, 10, 22, 22):
        raise ValueError(
            "unexpected Tree contract: "
            f"nodes={len(nodes)} paths={len(paths)} names={len(names)} "
            f"hebrew={len(hebrew)} numerals={len(numerals)} "
            f"divine={len(divine_names)} letters={len(letters)} "
            f"archangels={len(archangels)} choirs={len(choirs)} "
            f"pathNumerals={len(path_numerals)}"
        )

    radii = require_match(
        r"float\s+radius\s*=\s*\(centre\s*\?\s*([\d.]+)F\s*:\s*([\d.]+)F\)",
        fx,
        "Sephira radii",
    )
    path_offset = float(require_match(
        r"Vector3f\s+offset\s*=.*?\.mul\(([\d.]+)F\)", fx, "path lane offset", re.S
    ).group(1))
    path_widths = require_match(
        r"drawStarRibbon\(pose,\s*consumer,\s*\n\s*new Vector3f\(from\).*?\n\s*([\d.]+)F,\s*([\d.]+)F,.*?"
        r"drawStarRibbon\(pose,\s*consumer,\s*\n\s*new Vector3f\(from\).*?\n\s*([\d.]+)F,\s*([\d.]+)F,",
        fx,
        "path ribbon widths",
        re.S,
    )
    ring_widths = require_match(
        r"drawPolyRing\(nodePose,\s*consumer,\s*axisX,\s*axisY,\s*32,\s*\n\s*radius,\s*([\d.]+)F,.*?"
        r"drawPolyRing\(nodePose,\s*consumer,\s*axisX,\s*axisY,\s*32,\s*\n\s*radius\s*\*\s*0\.72F,\s*([\d.]+)F,",
        fx,
        "ring widths",
        re.S,
    )
    tree_depth = float(require_match(
        r"poseStack\.translate\(0\.0D,\s*0\.0D,\s*(-?[\d.]+)D\)\s*;\s*\n\s*Matrix4f pose",
        fx,
        "tree backplate depth",
    ).group(1))

    label_x_offsets = tuple(
        float(value)
        for value in re.findall(
            r"(-?\d+(?:\.\d+)?)F", java_initializer(fx, "LABEL_X_OFFSETS")
        )
    )
    path_label_offsets = tuple(
        (float(x), float(y))
        for x, y in re.findall(
            r"\{\s*(-?\d+(?:\.\d+)?)F\s*,\s*(-?\d+(?:\.\d+)?)F\s*\}",
            java_initializer(fx, "PATH_LABEL_OFFSETS"),
        )
    )
    if len(label_x_offsets) != len(nodes) or len(path_label_offsets) != len(paths):
        raise ValueError(
            "unexpected adopted label contract: "
            f"nodeOffsets={len(label_x_offsets)}/{len(nodes)} "
            f"pathOffsets={len(path_label_offsets)}/{len(paths)}"
        )

    glory = require_match(
        r"float\s+s\s*=\s*([\d.]+)F;.*?"
        r"float\s+len\s*=\s*\(([\d.]+)F\s*-\s*f\s*\*\s*([\d.]+)F\).*?"
        r"\(([\d.]+)F\s*-\s*f\s*\*\s*([\d.]+)F\)\s*\*\s*s",
        fx[fx.index("private static void drawTiferetGlory"):],
        "Tiferet glory geometry",
        re.S,
    )

    mass_size = entity_size(entities, "mass_production_eva")
    unit_size = entity_size(entities, "eva_unit01")
    mass_scale, unit_scale = renderer_scales()
    mass_visual = posed_visual_envelope(
        asset_root, "mass_production_eva", "animation.entity_mp.ritual", mass_scale
    )
    unit_visual = posed_visual_envelope(
        asset_root, "eva_unit01", "animation.eva_unit01.crucified", unit_scale
    )
    return TreeData(
        tableau_orientation=string_constant(layout, "TABLEAU_ORIENTATION"),
        column_x=float_constant(layout, "COLUMN_X"),
        row_y=float_constant(layout, "ROW_Y"),
        keter=int_constant(layout, "KETER"),
        tiferet=int_constant(layout, "TIFERET"),
        malkuth=int_constant(layout, "MALKUTH"),
        nodes=nodes,
        paths=paths,
        names=names,
        hebrew=hebrew,
        numerals=numerals,
        divine_names=divine_names,
        archangels=archangels,
        choirs=choirs,
        letters=letters,
        path_numerals=path_numerals,
        camera_distance=float_constant(capture, "CAMERA_DISTANCE"),
        frame_bottom=float_constant(capture, "FRAME_BOTTOM"),
        frame_top_margin=float_constant(capture, "FRAME_TOP_MARGIN"),
        tree_depth=tree_depth,
        mass_width=mass_size[0],
        mass_height=mass_size[1],
        unit_width=unit_size[0],
        unit_height=unit_size[1],
        mass_visual=mass_visual,
        unit_visual=unit_visual,
        centre_radius=float(radii.group(1)),
        outer_radius=float(radii.group(2)),
        path_offset=path_offset,
        path_outer_width=float(path_widths.group(1)),
        path_inner_width=float(path_widths.group(3)),
        ring_outer_width=float(ring_widths.group(1)),
        ring_inner_width=float(ring_widths.group(2)),
        node_tick_count=int_constant(fx, "NODE_TICK_COUNT"),
        node_name_y=float_constant(fx, "EXTERNAL_NAME_Y"),
        node_name_scale=float_constant(fx, "EXTERNAL_NAME_SCALE"),
        divine_name_y=float_constant(fx, "EXTERNAL_DIVINE_Y"),
        divine_name_scale=float_constant(fx, "EXTERNAL_DIVINE_SCALE"),
        external_archangel_y=float_constant(fx, "EXTERNAL_ARCHANGEL_Y"),
        external_archangel_scale=float_constant(fx, "EXTERNAL_ARCHANGEL_SCALE"),
        external_choir_y=float_constant(fx, "EXTERNAL_CHOIR_Y"),
        external_choir_scale=float_constant(fx, "EXTERNAL_CHOIR_SCALE"),
        path_letter_offset=0.0,
        path_letter_scale=float_constant(fx, "PATH_LETTER_SCALE"),
        glory_scale=float(glory.group(1)),
        glory_length_base=float(glory.group(2)),
        glory_length_step=float(glory.group(3)),
        glory_width_base=float(glory.group(4)),
        glory_width_step=float(glory.group(5)),
        label_rotation_degrees=float_constant(fx, "LABEL_ROTATION_DEGREES"),
        diagram_text_z=float_constant(fx, "DIAGRAM_TEXT_Z"),
        internal_name_scale=float_constant(fx, "INTERNAL_NAME_SCALE"),
        internal_divine_scale=float_constant(fx, "INTERNAL_DIVINE_SCALE"),
        internal_archangel_scale=float_constant(fx, "INTERNAL_ARCHANGEL_SCALE"),
        internal_choir_scale=float_constant(fx, "INTERNAL_CHOIR_SCALE"),
        path_number_scale=float_constant(fx, "PATH_NUMBER_SCALE"),
        label_x_offsets=label_x_offsets,
        path_label_offsets=path_label_offsets,
        all_labels_backed=(
            "Font.DisplayMode.SEE_THROUGH" in fx
            and re.search(r"Font\.DisplayMode\.SEE_THROUGH,\s*\n\s*0xA0000000,", fx) is not None
        ),
    )


def reverse_hebrew(text: str) -> str:
    # ClientFxManager.displayHebrew reverses logical Hebrew for an LTR UI.
    return text[::-1]


def font_path(bold: bool = False) -> Path | None:
    candidates = (
        [Path(r"C:\Windows\Fonts\arialbd.ttf"), Path(r"C:\Windows\Fonts\segoeuib.ttf")]
        if bold
        else [Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\segoeui.ttf")]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_font(pixel_height: float, supersample: int, bold: bool = False) -> ImageFont.ImageFont:
    size = max(7, round(pixel_height * supersample))
    path = font_path(bold)
    if path is not None:
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def scaled_point(point: tuple[float, float], supersample: int) -> tuple[int, int]:
    return round(point[0] * supersample), round(point[1] * supersample)


def scaled_bbox(box: Sequence[float], supersample: int) -> tuple[int, int, int, int]:
    return tuple(round(value * supersample) for value in box)  # type: ignore[return-value]


def bbox_intersection(a: Sequence[float], b: Sequence[float]) -> float:
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return width * height


def bbox_area(box: Sequence[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def union_bbox(boxes: Iterable[Sequence[float]]) -> tuple[float, float, float, float]:
    boxes = list(boxes)
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def screen_bbox(projection: Projection, centre: tuple[float, float], width: float,
                height: float, depth: float = 0.0) -> tuple[float, float, float, float]:
    x, y = projection.point(*centre, depth)
    half_width = projection.length(width, depth) * 0.5
    half_height = projection.length(height, depth) * 0.5
    return x - half_width, y - half_height, x + half_width, y + half_height


def posed_entity_screen_bbox(projection: Projection, node: tuple[float, float],
                             gameplay_height: float,
                             visual: VisualEnvelope) -> tuple[float, float, float, float]:
    """Conservatively project the real posed mesh envelope at a ritual node.

    ThirdImpactDirector positions each entity at nodeY minus half its gameplay
    hitbox height.  The high-detail mesh is then rendered around that entity
    origin.  Project all eight corners because the front/back extent changes
    perspective scale even though the tableau is nominally planar.
    """
    min_x, min_y, min_z, max_x, max_y, max_z = visual.bounds
    entity_y = node[1] - gameplay_height * 0.5
    points = [
        projection.point(node[0] + x, entity_y + y, z)
        for x in (min_x, max_x)
        for y in (min_y, max_y)
        for z in (min_z, max_z)
    ]
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def world_box_centre_and_size(node: tuple[float, float], gameplay_height: float,
                              visual: VisualEnvelope) -> tuple[tuple[float, float], float, float]:
    min_x, min_y, _, max_x, max_y, _ = visual.bounds
    entity_y = node[1] - gameplay_height * 0.5
    return (
        (node[0] + (min_x + max_x) * 0.5,
         entity_y + (min_y + max_y) * 0.5),
        max_x - min_x,
        max_y - min_y,
    )


def draw_mass_silhouette(draw: ImageDraw.ImageDraw, projection: Projection,
                         centre: tuple[float, float], width: float, height: float,
                         supersample: int) -> tuple[float, float, float, float]:
    # A compact front-facing winged humanoid.  It is intentionally simple; its
    # width/height now come from the sampled SmOd ritual mesh, not the hitbox.
    cx, cy = centre
    sx = width / 10.0
    sy = height / 26.0
    points = [
        (cx, cy + 13.0 * sy), (cx - 2.1 * sx, cy + 10.8 * sy),
        (cx - 2.8 * sx, cy + 6.0 * sy), (cx - 5.0 * sx, cy + 2.0 * sy),
        (cx - 3.3 * sx, cy - 1.2 * sy), (cx - 2.1 * sx, cy - 7.0 * sy),
        (cx - 3.2 * sx, cy - 13.0 * sy), (cx - 0.6 * sx, cy - 12.7 * sy),
        (cx, cy - 5.5 * sy), (cx + 0.6 * sx, cy - 12.7 * sy),
        (cx + 3.2 * sx, cy - 13.0 * sy), (cx + 2.1 * sx, cy - 7.0 * sy),
        (cx + 3.3 * sx, cy - 1.2 * sy), (cx + 5.0 * sx, cy + 2.0 * sy),
        (cx + 2.8 * sx, cy + 6.0 * sy), (cx + 2.1 * sx, cy + 10.8 * sy),
    ]
    polygon = [scaled_point(projection.point(x, y), supersample) for x, y in points]
    outline = max(1, round(projection.length(0.55) * supersample))
    draw.polygon(polygon, fill=BODY_FILL, outline=MASS_OUTLINE, width=outline)
    # Face slit and core make front/back unmistakable in the composition probe.
    face_a = scaled_point(projection.point(cx - 1.25 * sx, cy + 9.5 * sy), supersample)
    face_b = scaled_point(projection.point(cx + 1.25 * sx, cy + 9.5 * sy), supersample)
    draw.line([face_a, face_b], fill=RED, width=max(1, outline // 2))
    core = screen_bbox(projection, (cx, cy + 2.2 * sy), 1.25 * sx, 1.25 * sy)
    draw.ellipse(scaled_bbox(core, supersample), fill=RED)
    return screen_bbox(projection, centre, width, height)


def draw_unit_cross(draw: ImageDraw.ImageDraw, projection: Projection,
                    centre: tuple[float, float], width: float, height: float,
                    supersample: int) -> tuple[float, float, float, float]:
    cx, cy = centre
    half_height = height * 0.5
    arm_y = height / 6.0
    # The sampled crucified mesh already includes the true horizontal arm
    # span.  Expanding this value again recreated the old fake cross geometry.
    arm_span = width
    head_width = min(width * 0.18, height * 0.20)
    head_height = height * 0.16
    edge_width = max(2, round(projection.length(0.7) * supersample))
    body_width = max(3, round(projection.length(4.4) * supersample))
    limb_width = max(3, round(projection.length(2.4) * supersample))
    body_line = [
        scaled_point(projection.point(cx, cy - half_height + 0.5), supersample),
        scaled_point(projection.point(cx, cy + half_height - head_height), supersample),
    ]
    arm_line = [
        scaled_point(projection.point(cx - arm_span * 0.5, cy + arm_y), supersample),
        scaled_point(projection.point(cx + arm_span * 0.5, cy + arm_y), supersample),
    ]
    # Draw the pale edge first and the dark body second.  The former ordering
    # painted a thin pale stripe through the centre of each limb, making the
    # crucified Unit read as a wire even though its sampled envelope was wide.
    draw.line(body_line, fill=UNIT_OUTLINE, width=body_width + edge_width * 2)
    draw.line(arm_line, fill=UNIT_OUTLINE, width=limb_width + edge_width * 2)
    draw.line(
        body_line,
        fill=BODY_FILL, width=body_width,
    )
    draw.line(
        arm_line,
        fill=BODY_FILL, width=limb_width,
    )
    head_centre_y = cy + half_height - head_height * 0.5
    head = screen_bbox(projection, (cx, head_centre_y), head_width, head_height)
    draw.ellipse(scaled_bbox(head, supersample), fill=BODY_FILL, outline=UNIT_OUTLINE, width=edge_width)
    horn_a = scaled_point(projection.point(cx, cy + half_height - 0.6), supersample)
    horn_b = scaled_point(projection.point(cx, cy + half_height + height * 0.10), supersample)
    draw.line([horn_a, horn_b], fill=UNIT_OUTLINE, width=max(1, edge_width // 2))
    core_size = min(width, height) * 0.06
    core = screen_bbox(projection, (cx, cy + height * 0.07), core_size, core_size)
    draw.ellipse(scaled_bbox(core, supersample), fill=RED)
    return screen_bbox(projection, centre, arm_span, height)


def label_specs(data: TreeData) -> list[LabelSpec]:
    labels: list[LabelSpec] = []
    for index in range(len(data.nodes)):
        x, y = data.node_world(index)
        label_x = x + data.label_x_offsets[index]
        primary = f"{data.numerals[index]}  {data.hebrew[index]}"
        labels.append(LabelSpec(
            f"node_{index + 1}_name", "sephira_name",
            reverse_hebrew(primary), primary,
            (label_x, y + data.node_name_y), data.node_name_scale,
            force_backing=data.all_labels_backed,
            rotation_degrees=data.label_rotation_degrees,
        ))
        labels.append(LabelSpec(
            f"node_{index + 1}_divine", "divine_name",
            reverse_hebrew(data.divine_names[index]), data.divine_names[index],
            (label_x, y + data.divine_name_y), data.divine_name_scale,
            force_backing=data.all_labels_backed,
            rotation_degrees=data.label_rotation_degrees,
        ))
        labels.append(LabelSpec(
            f"node_{index + 1}_archangel", "archangel_name",
            reverse_hebrew(data.archangels[index]), data.archangels[index],
            (label_x, y + data.external_archangel_y),
            data.external_archangel_scale,
            force_backing=data.all_labels_backed,
            rotation_degrees=data.label_rotation_degrees,
        ))
        labels.append(LabelSpec(
            f"node_{index + 1}_choir", "choir_name",
            reverse_hebrew(data.choirs[index]), data.choirs[index],
            (label_x, y + data.external_choir_y), data.external_choir_scale,
            force_backing=data.all_labels_backed,
            rotation_degrees=data.label_rotation_degrees,
        ))
        labels.append(LabelSpec(
            f"node_{index + 1}_inner_name", "inner_name",
            reverse_hebrew(data.hebrew[index]), data.hebrew[index],
            (x, y + 9.4), data.internal_name_scale,
            depth_layer="backplate",
            rotation_degrees=data.label_rotation_degrees,
        ))
        labels.append(LabelSpec(
            f"node_{index + 1}_inner_archangel", "inner_archangel",
            reverse_hebrew(data.archangels[index]), data.archangels[index],
            (x, y + 5.7), data.internal_archangel_scale,
            depth_layer="backplate",
            rotation_degrees=data.label_rotation_degrees,
        ))
        labels.append(LabelSpec(
            f"node_{index + 1}_inner_choir", "inner_choir",
            reverse_hebrew(data.choirs[index]), data.choirs[index],
            (x, y - 5.7), data.internal_choir_scale,
            depth_layer="backplate",
            rotation_degrees=data.label_rotation_degrees,
        ))
        labels.append(LabelSpec(
            f"node_{index + 1}_inner_divine", "inner_divine",
            reverse_hebrew(data.divine_names[index]), data.divine_names[index],
            (x, y - 9.4), data.internal_divine_scale,
            depth_layer="backplate",
            rotation_degrees=data.label_rotation_degrees,
        ))
    for index, (left, right) in enumerate(data.paths):
        ax, ay = data.node_world(left)
        bx, by = data.node_world(right)
        offset_x, offset_y = data.path_label_offsets[index]
        position = (
            (ax + bx) * 0.5 + offset_x,
            (ay + by) * 0.5 + offset_y,
        )
        labels.append(LabelSpec(
            f"path_{index + 1:02d}_{left + 1}_{right + 1}", "path_letter",
            data.letters[index], data.letters[index], position, data.path_letter_scale,
            force_backing=data.all_labels_backed,
            rotation_degrees=data.label_rotation_degrees,
        ))
        number_position = (position[0] + 1.8, position[1] - 2.6)
        labels.append(LabelSpec(
            f"path_number_{index + 1:02d}_{left + 1}_{right + 1}", "path_number",
            reverse_hebrew(data.path_numerals[index]), data.path_numerals[index],
            number_position, data.path_number_scale,
            depth_layer="backplate",
            rotation_degrees=data.label_rotation_degrees,
        ))
    return labels


def entity_probe_boxes(data: TreeData, projection: Projection) -> dict[str, tuple[float, float, float, float]]:
    boxes: dict[str, tuple[float, float, float, float]] = {}
    for index in range(len(data.nodes)):
        x, y = data.node_world(index)
        if index == data.tiferet:
            arm_span = max(data.unit_width * 3.75, data.unit_height * 1.05)
            boxes["unit01_tiferet"] = screen_bbox(
                projection, (x, y + data.unit_height * 0.05),
                arm_span, data.unit_height * 1.20,
            )
        else:
            boxes[f"mass_{index + 1}"] = screen_bbox(
                projection, (x, y), data.mass_width, data.mass_height
            )
    return boxes


def candidate_label_specs(
    data: TreeData,
    projection: Projection,
    supersample: int,
) -> tuple[list[LabelSpec], list[tuple[tuple[float, float], tuple[float, float]]], dict[str, object]]:
    """Reconstruct the adopted candidate from parsed Java source values."""
    del projection, supersample  # Kept in the signature for CLI compatibility.
    specs = label_specs(data)
    leaders: list[tuple[tuple[float, float], tuple[float, float]]] = []
    node_recommendations: list[dict[str, object]] = []
    for index in range(len(data.nodes)):
        x, y = data.node_world(index)
        offset = data.label_x_offsets[index]
        anchor_x = x + offset
        side = math.copysign(1.0, offset)
        radius = data.centre_radius if index == data.tiferet else data.outer_radius
        leader_start = (x + side * (radius + 0.8), y)
        leader_end = (anchor_x - side * 3.0, y)
        leaders.append((leader_start, leader_end))
        node_recommendations.append({
            "node": index + 1,
            "name": data.names[index],
            "anchor_local": [anchor_x, y],
            "offset_from_node": [offset, 0.0],
            "hebrew_name_y_offset": data.node_name_y,
            "divine_name_y_offset": data.divine_name_y,
            "leader": [list(leader_start), list(leader_end)],
        })

    path_recommendations: list[dict[str, object]] = []
    for index, (left, right) in enumerate(data.paths):
        ax, ay = data.node_world(left)
        bx, by = data.node_world(right)
        midpoint = ((ax + bx) * 0.5, (ay + by) * 0.5)
        offset = data.path_label_offsets[index]
        position = (midpoint[0] + offset[0], midpoint[1] + offset[1])
        path_recommendations.append({
            "path": index + 1,
            "endpoints": [left + 1, right + 1],
            "letter": data.letters[index],
            "hebrew_number": data.path_numerals[index],
            "local_position": [round(position[0], 3), round(position[1], 3)],
            "offset_from_midpoint": [
                round(position[0] - midpoint[0], 3),
                round(position[1] - midpoint[1], 3),
            ],
        })

    recommendation: dict[str, object] = {
        "status": "adopted in ClientFxManager.java",
        "node_hebrew_scale": data.node_name_scale,
        "node_divine_name_scale": data.divine_name_scale,
        "path_letter_scale": data.path_letter_scale,
        "path_number_scale": data.path_number_scale,
        "internal_name_scale": data.internal_name_scale,
        "internal_divine_scale": data.internal_divine_scale,
        "label_rotation_degrees": data.label_rotation_degrees,
        "detached_title_rows": 0,
        "horizon_row": False,
        "frame_top_margin": data.frame_top_margin,
        "display_modes": {
            "foreground": "Font.DisplayMode.SEE_THROUGH",
            "backplate_microtext": "Font.DisplayMode.NORMAL",
        },
        "background_argb": ("0xA0000000" if data.all_labels_backed else "0x00000000"),
        "node_anchors": node_recommendations,
        "path_letter_positions": path_recommendations,
        "unresolved_path_letters": [],
    }
    return specs, leaders, recommendation


def label_geometry(projection: Projection, spec: LabelSpec,
                   supersample: int) -> tuple[ImageFont.ImageFont, tuple[int, int, int, int],
                                               float, float, float, float, float]:
    screen = projection.point(*spec.position)
    pixel_height = projection.length(8.0 * spec.scale)
    font = load_font(pixel_height, supersample,
                     bold=spec.kind == "sephira_name")
    measured = font.getbbox(spec.text)
    width = measured[2] - measured[0]
    height = measured[3] - measured[1]
    left = screen[0] * supersample - width * 0.5
    top = screen[1] * supersample - height * 0.5
    return font, measured, width, height, left, top, pixel_height


def draw_label(layer: Image.Image, projection: Projection, spec: LabelSpec,
               supersample: int) -> LabelBox:
    font, measured, width, height, left, top, pixel_height = label_geometry(
        projection, spec, supersample
    )
    backed = spec.force_backing
    padding = max(1, round(0.9 * supersample))
    if backed:
        draw = ImageDraw.Draw(layer)
        draw.rectangle(
            [round(left - padding), round(top - padding), round(left + width + padding), round(top + height + padding)],
            fill=(0, 0, 0, 152),
        )
    # Render each glyph row on its own tile before rotating it.  Rotating the
    # whole label layer would preserve the old upright lettering instead of
    # reproducing EoE's 180-degree rotation of the complete printed diagram.
    tile_padding = max(2, supersample * 2)
    tile = Image.new(
        "RGBA", (max(1, round(width) + tile_padding * 2),
                 max(1, round(height) + tile_padding * 2)), (0, 0, 0, 0)
    )
    tile_draw = ImageDraw.Draw(tile)
    baseline = tile_padding - measured[1]
    if backed:
        # Kept only for the parser's historical comparison mode; the adopted
        # Java contract deliberately has neither backdrop nor shadow.
        shadow = max(1, supersample)
        tile_draw.text((tile_padding + shadow, baseline + shadow), spec.text,
                       font=font, fill=(38, 0, 0, 230))
    tile_draw.text((tile_padding, baseline), spec.text, font=font, fill=RED)
    rotation = spec.rotation_degrees % 360.0
    if math.isclose(rotation, 180.0, abs_tol=1.0e-6):
        tile = tile.transpose(Image.Transpose.ROTATE_180)
    elif not math.isclose(rotation, 0.0, abs_tol=1.0e-6):
        tile = tile.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=False)
    layer.alpha_composite(
        tile,
        (round(left) - tile_padding, round(top) - tile_padding),
    )
    bbox = (
        left / supersample,
        top / supersample,
        (left + width) / supersample,
        (top + height) / supersample,
    )
    return LabelBox(
        spec.identifier, spec.kind, spec.text, spec.logical_text,
        spec.position, spec.scale, bbox, height / supersample, backed,
        spec.depth_layer, spec.rotation_degrees,
    )


def render(data: TreeData, projection: Projection, supersample: int,
           layout_mode: str) -> tuple[Image.Image, dict[str, object]]:
    canvas = Image.new("RGBA", (projection.width * supersample, projection.height * supersample),
                       (4, 5, 10, 255))
    draw = ImageDraw.Draw(canvas)
    geometry_boxes: list[tuple[float, float, float, float]] = []
    specs, leaders, adopted_java_layout = candidate_label_specs(
        data, projection, supersample
    )

    # Subtle horizon/star field is deterministic and keeps the red-only Tree
    # contract visible against the same kind of night plate used in Visual Lab.
    for index in range(76):
        x = (index * 811 + 97) % projection.width
        y = (index * 337 + 43) % projection.height
        radius = 1 if index % 9 else 2
        draw.ellipse((
            (x * supersample - radius), (y * supersample - radius),
            (x * supersample + radius), (y * supersample + radius),
        ), fill=(75, 80, 92, 150))

    # Tree geometry sits eight blocks behind the ritual bodies in current Java.
    tree_depth = data.tree_depth
    outer_width = max(1, round(projection.length(data.path_outer_width, tree_depth) * supersample))
    inner_width = max(1, round(projection.length(data.path_inner_width, tree_depth) * supersample))
    for left, right in data.paths:
        ax, ay = data.node_world(left)
        bx, by = data.node_world(right)
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        for side in (-1.0, 1.0):
            shift_x = nx * data.path_offset * side
            shift_y = ny * data.path_offset * side
            a = projection.point(ax + shift_x, ay + shift_y, tree_depth)
            b = projection.point(bx + shift_x, by + shift_y, tree_depth)
            points = [scaled_point(a, supersample), scaled_point(b, supersample)]
            draw.line(points, fill=RED_DIM, width=outer_width)
            draw.line(points, fill=RED, width=inner_width)
            pad = max(data.path_outer_width, 0.25) * 0.5
            geometry_boxes.append(screen_bbox(
                projection, ((ax + bx) * 0.5 + shift_x, (ay + by) * 0.5 + shift_y),
                abs(bx - ax) + pad * 2.0, abs(by - ay) + pad * 2.0, tree_depth
            ))

    # Nominal fully-lit radius.  The report separately includes the 4.5%
    # maximum breathing expansion from ClientFxManager.
    for index in range(len(data.nodes)):
        x, y = data.node_world(index)
        radius = data.centre_radius if index == data.tiferet else data.outer_radius
        cx, cy = projection.point(x, y, tree_depth)
        rx = projection.length(radius, tree_depth)
        outer = (cx - rx, cy - rx, cx + rx, cy + rx)
        outer_width_px = max(1, round(projection.length(data.ring_outer_width, tree_depth) * supersample))
        inner_width_px = max(1, round(projection.length(data.ring_inner_width, tree_depth) * supersample))
        draw.ellipse(scaled_bbox(outer, supersample), outline=RED, width=outer_width_px)
        inner_radius = rx * 0.72
        inner = (cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius)
        draw.ellipse(scaled_bbox(inner, supersample), outline=RED, width=inner_width_px)
        tick_width = max(1, round(projection.length(0.09, tree_depth) * supersample))
        for tick in range(data.node_tick_count):
            angle = math.tau * tick / data.node_tick_count
            inner_tick = projection.point(
                x + math.cos(angle) * radius * 0.79,
                y + math.sin(angle) * radius * 0.79,
                tree_depth,
            )
            outer_tick = projection.point(
                x + math.cos(angle) * radius * 0.93,
                y + math.sin(angle) * radius * 0.93,
                tree_depth,
            )
            draw.line(
                [scaled_point(inner_tick, supersample),
                 scaled_point(outer_tick, supersample)],
                fill=RED_DIM, width=tick_width,
            )
        geometry_boxes.append(outer)

    leader_width = max(1, round(projection.length(0.18, tree_depth) * supersample))
    for start, end in leaders:
        draw.line(
            [scaled_point(projection.point(*start, tree_depth), supersample),
             scaled_point(projection.point(*end, tree_depth), supersample)],
            fill=RED_DIM,
            width=leader_width,
        )

    # Six Tiferet glory rays (the real Unit-01 path uses wings only).  Their
    # dimensions are parsed from Java so the preview catches another red-wall
    # regression instead of carrying the previous 2x wing span forever.
    tx, ty = data.node_world(data.tiferet)
    for side in (-1.0, 1.0):
        for feather, angle_degrees in enumerate((28.0, 50.0, 72.0)):
            length = (data.glory_length_base - feather * data.glory_length_step) * data.glory_scale
            width = (data.glory_width_base - feather * data.glory_width_step) * data.glory_scale
            wing_width = max(1, round(projection.length(width, tree_depth) * supersample))
            angle = math.radians(angle_degrees)
            start_y = ty + 2.0 * data.glory_scale
            start = projection.point(tx, start_y, tree_depth)
            tip = projection.point(
                tx + side * math.cos(angle) * length,
                start_y + math.sin(angle) * length,
                tree_depth,
            )
            draw.line([scaled_point(start, supersample), scaled_point(tip, supersample)],
                      fill=RED_SOFT, width=wing_width)

    # Internal ring/path inscriptions use NORMAL depth in Java.  Render their
    # preview layer before bodies so model silhouettes visibly occlude them.
    backplate_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    backplate_labels = [
        draw_label(backplate_layer, projection, spec, supersample)
        for spec in specs if spec.depth_layer == "backplate"
    ]
    canvas = Image.alpha_composite(canvas, backplate_layer)
    draw = ImageDraw.Draw(canvas)

    # Bodies render in front of the backplate.  Drawing remains schematic, but
    # every collision/readability box below is the conservative perspective
    # projection of the real posed high-detail mesh envelope.
    entity_boxes: dict[str, tuple[float, float, float, float]] = {}
    for index in range(len(data.nodes)):
        node = data.node_world(index)
        if index == data.tiferet:
            centre, width, height = world_box_centre_and_size(
                node, data.unit_height, data.unit_visual
            )
            draw_unit_cross(draw, projection, centre, width, height, supersample)
            entity_boxes["unit01_tiferet"] = posed_entity_screen_bbox(
                projection, node, data.unit_height, data.unit_visual
            )
        else:
            centre, width, height = world_box_centre_and_size(
                node, data.mass_height, data.mass_visual
            )
            draw_mass_silhouette(draw, projection, centre, width, height, supersample)
            entity_boxes[f"mass_{index + 1}"] = posed_entity_screen_bbox(
                projection, node, data.mass_height, data.mass_visual
            )

    # External names and the large path letters use SEE_THROUGH in Java, so
    # they remain a separate foreground pass.
    label_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    foreground_labels = [
        draw_label(label_layer, projection, spec, supersample)
        for spec in specs if spec.depth_layer == "foreground"
    ]
    canvas = Image.alpha_composite(canvas, label_layer)
    labels = backplate_labels + foreground_labels

    label_pairs: list[dict[str, object]] = []
    label_pairs_any: list[dict[str, object]] = []
    for index, first in enumerate(labels):
        for second in labels[index + 1 :]:
            overlap = bbox_intersection(first.bbox, second.bbox)
            if overlap <= 0.0:
                continue
            smaller = min(bbox_area(first.bbox), bbox_area(second.bbox))
            ratio = overlap / smaller if smaller else 0.0
            if overlap >= 0.5:
                label_pairs_any.append({
                    "labels": [first.identifier, second.identifier],
                    "overlap_pixels": round(overlap, 2),
                    "smaller_box_fraction": round(ratio, 4),
                })
            if ratio >= 0.05:
                label_pairs.append({
                    "labels": [first.identifier, second.identifier],
                    "overlap_pixels": round(overlap, 2),
                    "smaller_box_fraction": round(ratio, 4),
                })

    label_entity: list[dict[str, object]] = []
    label_entity_any: list[dict[str, object]] = []
    for label in foreground_labels:
        for entity, box in entity_boxes.items():
            overlap = bbox_intersection(label.bbox, box)
            area = bbox_area(label.bbox)
            ratio = overlap / area if area else 0.0
            if overlap >= 0.5:
                label_entity_any.append({
                    "label": label.identifier,
                    "entity": entity,
                    "overlap_pixels": round(overlap, 2),
                    "label_box_fraction": round(ratio, 4),
                })
            if ratio >= 0.05:
                label_entity.append({
                    "label": label.identifier,
                    "entity": entity,
                    "label_box_fraction": round(ratio, 4),
                })

    entity_pairs: list[dict[str, object]] = []
    entity_pairs_any: list[dict[str, object]] = []
    entity_items = list(entity_boxes.items())
    for index, (first_name, first_box) in enumerate(entity_items):
        for second_name, second_box in entity_items[index + 1 :]:
            overlap = bbox_intersection(first_box, second_box)
            if overlap <= 0.0:
                continue
            smaller = min(bbox_area(first_box), bbox_area(second_box))
            ratio = overlap / smaller if smaller else 0.0
            record = {
                "entities": [first_name, second_name],
                "overlap_pixels": round(overlap, 2),
                "smaller_box_fraction": round(ratio, 4),
            }
            if overlap >= 0.5:
                entity_pairs_any.append(record)
            if ratio >= 0.05:
                entity_pairs.append(record)

    clipped = [
        label.identifier for label in labels
        if label.bbox[0] < 0 or label.bbox[1] < 0
        or label.bbox[2] > projection.width or label.bbox[3] > projection.height
    ]
    small = [
        {"label": label.identifier, "height_pixels": round(label.projected_height, 2)}
        for label in labels if label.projected_height < 8.0
    ]
    role_minimums = {
        # The tableau intentionally uses fine engraving rather than HUD-size
        # captions. These floors reject disappearing glyphs while allowing
        # the dense, mysterious register requested for the ritual backplate.
        "sephira_name": 5.0,
        "divine_name": 3.25,
        "archangel_name": 2.5,
        "choir_name": 2.25,
        "path_letter": 5.5,
        "inner_name": 2.5,
        "inner_divine": 1.75,
        "inner_archangel": 1.75,
        "inner_choir": 1.5,
        "path_number": 2.5,
    }
    undersized = [
        {
            "label": label.identifier,
            "kind": label.kind,
            "height_pixels": round(label.projected_height, 2),
            "required_pixels": role_minimums[label.kind],
        }
        for label in labels
        if label.projected_height < role_minimums[label.kind]
    ]
    all_bounds = geometry_boxes + [label.bbox for label in labels] + list(entity_boxes.values())
    composition = union_bbox(all_bounds)
    occupancy_width = (composition[2] - composition[0]) / projection.width
    occupancy_height = (composition[3] - composition[1]) / projection.height

    raw_backplate_overlap: list[dict[str, object]] = []
    for entity, entity_box in entity_boxes.items():
        intersections = sum(bbox_intersection(entity_box, box) for box in geometry_boxes)
        # Bounding boxes over-count crossings; this is a conservative signal,
        # capped to make it explicit that the metric is not a pixel mask.
        ratio = min(1.0, intersections / max(1.0, bbox_area(entity_box)))
        raw_backplate_overlap.append({
            "entity": entity,
            "conservative_bbox_fraction": round(ratio, 4),
            "visible_obscuration_after_depth_order": 0.0,
        })

    node_positions = [data.node_world(index) for index in range(len(data.nodes))]
    ys = [point[1] for point in node_positions]
    semantic_names = (
        "KETER", "CHOKMAH", "BINAH", "CHESED", "GEVURAH",
        "TIFERET", "NETZACH", "HOD", "YESOD", "MALKUTH",
    )
    semantic_hebrew = (
        "כתר", "חכמה", "בינה", "חסד", "גבורה",
        "תפארת", "נצח", "הוד", "יסוד", "מלכות",
    )
    inverted_semantics = (
        data.tableau_orientation == "EOE_INVERTED"
        and data.keter == 0 and data.tiferet == 5 and data.malkuth == 9
        and node_positions[data.keter][1] == min(ys)
        and node_positions[data.malkuth][1] == max(ys)
    )
    tiferet_centre = (
        node_positions[data.tiferet][0] == 0.0
        and abs(node_positions[data.tiferet][1]
                - (min(ys) + max(ys)) * 0.5) < 1.0e-6
    )
    semantic_labels = data.names == semantic_names and data.hebrew == semantic_hebrew
    all_labels_rotated = (
        math.isclose(data.label_rotation_degrees, 180.0, abs_tol=1.0e-6)
        and all(math.isclose(label.rotation_degrees % 360.0, 180.0,
                             abs_tol=1.0e-6) for label in labels)
    )
    no_horizon_row = (
        adopted_java_layout["detached_title_rows"] == 0
        and adopted_java_layout["horizon_row"] is False
        and not any(label.kind == "title" for label in labels)
    )
    dense_internal_marks = (
        data.node_tick_count == 12
        and len(backplate_labels) == len(data.nodes) * 4 + len(data.paths)
        and len(labels) == len(data.nodes) * 8 + len(data.paths) * 2
    )

    checks = {
        "eoe_inverted_semantic_order": inverted_semantics,
        "semantic_label_index_mapping": semantic_labels,
        "tiferet_remains_geometric_centre": tiferet_centre,
        "all_diagram_labels_rotated_180_degrees": all_labels_rotated,
        "no_detached_title_or_horizon_row": no_horizon_row,
        "dense_internal_marks_present": dense_internal_marks,
        "all_labels_on_screen": not clipped,
        "label_height_meets_role_threshold": not undersized,
        "no_material_label_label_overlap": not label_pairs,
        "no_material_label_entity_overlap": not label_entity,
        "composition_height_below_80_percent": occupancy_height <= 0.80,
        "composition_width_below_70_percent": occupancy_width <= 0.70,
        "no_label_bbox_collisions": not label_pairs_any,
        "no_entity_bbox_collisions": not entity_pairs_any,
        "pure_red_labels_have_no_backdrop": all(
            not label.backed for label in labels
        ),
    }
    if layout_mode == "candidate":
        checks["candidate_has_zero_label_bbox_collisions"] = not label_pairs_any
        checks["candidate_has_zero_entity_bbox_collisions"] = not entity_pairs_any
        checks["candidate_pure_red_labels_have_no_backdrop"] = all(
            not label.backed for label in labels
        )
        checks["candidate_has_all_parsed_path_offsets"] = not adopted_java_layout["unresolved_path_letters"]
    report: dict[str, object] = {
        "schema": 3,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scope": (
            "offline composition using real posed high-detail mesh envelopes; "
            "not depth/font/runtime visual acceptance"
        ),
        "layout_mode": layout_mode,
        "source": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                LAYOUT_SOURCE, FX_SOURCE, CAPTURE_SOURCE, ENTITY_SOURCE,
                CLIENT_EVENTS_SOURCE, UNIT_RENDERER_SOURCE,
                *data.mass_visual.source_files, *data.unit_visual.source_files,
            )
        },
        "camera": {
            "resolution": [projection.width, projection.height],
            "vertical_fov_degrees": projection.fov_degrees,
            "distance_blocks": projection.camera_distance,
            "target_y": round(projection.target_y, 3),
            "tree_backplate_depth": data.tree_depth,
            "focal_pixels": round(projection.focal, 3),
        },
        "parsed_contract": {
            "tableau_orientation": data.tableau_orientation,
            "semantic_indices": {
                "keter": data.keter,
                "tiferet": data.tiferet,
                "malkuth": data.malkuth,
            },
            "semantic_extrema": {
                "nadir": data.names[min(range(len(ys)), key=ys.__getitem__)],
                "crown": data.names[max(range(len(ys)), key=ys.__getitem__)],
                "centre": data.names[data.tiferet],
            },
            "nodes": len(data.nodes),
            "paths": len(data.paths),
            "latin_names": len(data.names),
            "hebrew_names": len(data.hebrew),
            "hebrew_numerals": len(data.numerals),
            "hebrew_divine_names": len(data.divine_names),
            "hebrew_archangel_names": len(data.archangels),
            "hebrew_choir_names": len(data.choirs),
            "hebrew_path_letters": len(data.letters),
            "hebrew_path_numerals": len(data.path_numerals),
            "label_rotation_degrees": data.label_rotation_degrees,
            "node_radial_register_marks": data.node_tick_count,
            "backplate_microtext_labels": len(backplate_labels),
            "posed_model_envelopes": len(entity_boxes),
            "mass_entity_size": [data.mass_width, data.mass_height],
            "unit01_entity_size": [data.unit_width, data.unit_height],
            "mass_visual_envelope": {
                "model": data.mass_visual.model,
                "animation": data.mass_visual.animation,
                "sample_time": data.mass_visual.sample_time,
                "renderer_scale": data.mass_visual.renderer_scale,
                "vertex_count": data.mass_visual.vertex_count,
                "renderer_local_bounds_blocks": [
                    round(value, 4) for value in data.mass_visual.bounds
                ],
                "width_blocks": round(data.mass_visual.width, 4),
                "height_blocks": round(data.mass_visual.height, 4),
            },
            "unit01_visual_envelope": {
                "model": data.unit_visual.model,
                "animation": data.unit_visual.animation,
                "sample_time": data.unit_visual.sample_time,
                "renderer_scale": data.unit_visual.renderer_scale,
                "vertex_count": data.unit_visual.vertex_count,
                "renderer_local_bounds_blocks": [
                    round(value, 4) for value in data.unit_visual.bounds
                ],
                "width_blocks": round(data.unit_visual.width, 4),
                "height_blocks": round(data.unit_visual.height, 4),
            },
            "nominal_outer_radius": data.outer_radius,
            "maximum_breathing_outer_radius": round(data.outer_radius * 1.045, 3),
            "path_lane_offset": data.path_offset,
            "path_ribbon_widths": [data.path_outer_width, data.path_inner_width],
            "tiferet_glory": {
                "scale": data.glory_scale,
                "length_base": data.glory_length_base,
                "length_step": data.glory_length_step,
                "width_base": data.glory_width_base,
                "width_step": data.glory_width_step,
            },
        },
        "composition": {
            "screen_bbox": [round(value, 2) for value in composition],
            "width_fraction": round(occupancy_width, 4),
            "height_fraction": round(occupancy_height, 4),
            "posed_entity_screen_bboxes": {
                name: [round(value, 2) for value in box]
                for name, box in entity_boxes.items()
            },
        },
        "readability": {
            "labels_total": len(labels),
            "minimum_projected_height_pixels": round(min(label.projected_height for label in labels), 2),
            "clipped_labels": clipped,
            "labels_below_8px": small,
            "labels_below_role_threshold": undersized,
            "label_label_overlaps": label_pairs,
            "label_label_any_bbox_overlaps": label_pairs_any,
            "label_entity_overlaps": label_entity,
            "label_entity_any_bbox_overlaps": label_entity_any,
            "entity_entity_overlaps": entity_pairs,
            "entity_entity_any_bbox_overlaps": entity_pairs_any,
        },
        "occlusion": {
            "render_order": [
                "tree_geometry", "backplate_microtext",
                "posed_model_silhouettes", "foreground_labels",
            ],
            "raw_backplate_bbox_overlap": raw_backplate_overlap,
            "note": (
                "Tree/entity bbox intersections are conservative. NORMAL-depth "
                "microtext is previewed behind bodies; only SEE_THROUGH foreground "
                "labels count as entity-occlusion failures."
            ),
        },
        "checks": checks,
        "labels": [
            {
                "id": label.identifier,
                "kind": label.kind,
                "text": label.text,
                "logical_text": label.logical_text,
                "world_position": [round(value, 3) for value in label.position],
                "screen_bbox": [round(value, 2) for value in label.bbox],
                "height_pixels": round(label.projected_height, 2),
                "backed": label.backed,
                "depth_layer": label.depth_layer,
                "rotation_degrees": label.rotation_degrees,
            }
            for label in labels
        ],
    }
    report["adopted_java_layout"] = adopted_java_layout
    if supersample > 1:
        canvas = canvas.resize((projection.width, projection.height), Image.Resampling.LANCZOS)
    return canvas.convert("RGB"), report


def text_report(report: dict[str, object], png_path: Path) -> str:
    camera = report["camera"]
    composition = report["composition"]
    readability = report["readability"]
    checks = report["checks"]
    lines = [
        "Project SEELE - Tree of Life offline composition report",
        f"STATUS: {report['status']}",
        f"LAYOUT: {report['layout_mode']}",
        f"TABLEAU ORIENTATION: {report['parsed_contract']['tableau_orientation']}",
        f"PNG: {png_path}",
        "",
        "Camera",
        f"  resolution: {camera['resolution'][0]}x{camera['resolution'][1]}",
        f"  vertical FOV: {camera['vertical_fov_degrees']} degrees (CLI assumption; Minecraft option is not source-constant)",
        f"  distance: {camera['distance_blocks']} blocks",
        f"  target Y: {camera['target_y']}",
        "",
        "Composition",
        f"  width: {composition['width_fraction'] * 100:.1f}% of frame",
        f"  height: {composition['height_fraction'] * 100:.1f}% of frame",
        f"  labels: {readability['labels_total']}",
        f"  minimum label height: {readability['minimum_projected_height_pixels']} px",
        f"  clipped labels: {len(readability['clipped_labels'])}",
        f"  label/label overlaps: {len(readability['label_label_overlaps'])}",
        f"  label/entity overlaps: {len(readability['label_entity_overlaps'])}",
        f"  any label bbox collisions: {len(readability['label_label_any_bbox_overlaps'])}",
        f"  any label/entity bbox collisions: {len(readability['label_entity_any_bbox_overlaps'])}",
        f"  material entity/entity overlaps: {len(readability['entity_entity_overlaps'])}",
        f"  any entity/entity bbox collisions: {len(readability['entity_entity_any_bbox_overlaps'])}",
        "",
        "Checks",
    ]
    lines.extend(f"  [{'PASS' if passed else 'FAIL'}] {name}" for name, passed in checks.items())
    lines.extend([
        "",
        "Boundary",
        "  This preview samples real local meshes and Gecko animation into conservative visual envelopes.",
        "  It does not approve silhouette aesthetics, Minecraft depth testing or exact font rendering.",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--asset-root", type=Path, default=DEFAULT_ASSET_ROOT,
        help=("generated local SmOd assets/projectseele directory used for real posed "
              "mesh envelopes"),
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument(
        "--fov-degrees", type=float, default=70.0,
        help="vertical FOV assumption; camera distance/target are parsed from Java (default: 70)",
    )
    parser.add_argument("--supersample", type=int, default=3)
    parser.add_argument(
        "--layout", choices=("current", "candidate"), default="current",
        help="current Java labels or the adopted-candidate regression reconstruction (default: current)",
    )
    parser.add_argument("--strict", action="store_true", help="return exit code 2 when report status is FAIL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.width <= 0 or args.height <= 0 or args.supersample <= 0:
        raise SystemExit("width, height and supersample must be positive")
    if not 20.0 <= args.fov_degrees <= 140.0:
        raise SystemExit("--fov-degrees must be between 20 and 140")

    data = parse_tree(args.asset_root.resolve())
    frame_top = data.node_world(data.malkuth)[1] + data.frame_top_margin
    target_y = (data.frame_bottom + frame_top) * 0.5
    projection = Projection(
        width=args.width,
        height=args.height,
        fov_degrees=args.fov_degrees,
        camera_distance=data.camera_distance,
        target_y=target_y,
    )
    image, report = render(data, projection, args.supersample, args.layout)

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    suffix = "candidate" if args.layout == "candidate" else "front"
    png_path = output / f"tree_of_life_{suffix}.png"
    json_path = output / f"tree_of_life_{suffix}.report.json"
    text_path = output / f"tree_of_life_{suffix}.report.txt"
    image.save(png_path)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text_path.write_text(text_report(report, png_path), encoding="utf-8")
    print(text_report(report, png_path), end="")
    print(f"JSON: {json_path}")
    return 2 if args.strict and report["status"] != "PASS" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"tree preview failed: {error}", file=sys.stderr)
        sys.exit(1)
