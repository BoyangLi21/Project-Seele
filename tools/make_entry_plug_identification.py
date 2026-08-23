#!/usr/bin/env python3
"""Bake unit lettering and the supplied NERV mark into Entry Plug meshes.

The markings are shallow model geometry conforming to both pressure-shell
sides.  They are not a second decal layer, billboard, framed texture plate or
runtime overlay, so they cannot float away from the capsule when it rotates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
LOGO_CANDIDATES = (
    REPO / "run/projectseele-local-maps/nerv_logo.png",
    Path(r"C:\Users\liboy\Desktop\images.png"),
    REPO / "artifacts/Project_SEELE_Server_Ready_20260812/CLIENT"
           "/projectseele-local-maps/nerv_logo.png",
)
LABELS = {
    0: "EVA-00 PROTO TYPE",
    1: "EVA-01 TEST TYPE",
    2: "EVA-02 PRODUCTION MODEL",
}
PALETTE_SIZE = 12
TEXT_PALETTE_INDEX = 1
LOGO_PALETTE_INDEX = 11
SIDE_INNER_X = 4.002
SIDE_OUTER_X = 4.055
MARK_Z_MIN = 34.6
MARK_Z_MAX = 46.5
MARK_Y_MIN = -1.25
MARK_Y_MAX = 1.25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--logo", type=Path)
    return parser.parse_args()


def clean_logo(path: Path) -> Image.Image:
    logo = Image.open(path).convert("RGBA")
    pixels = logo.load()
    for y in range(logo.height):
        for x in range(logo.width):
            red, green, blue, alpha = pixels[x, y]
            neutral = max(red, green, blue) - min(red, green, blue) <= 13
            if neutral and min(red, green, blue) >= 205:
                pixels[x, y] = (0, 0, 0, 0)
            elif alpha > 0 and red > green * 1.35 and red > blue * 1.35:
                pixels[x, y] = (255, 255, 255, alpha)
            else:
                pixels[x, y] = (0, 0, 0, 0)
    crop = logo.getbbox()
    return logo.crop(crop) if crop else logo


def fit_font(draw: ImageDraw.ImageDraw, text: str, width: int, height: int):
    candidates = (
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\bahnschrift.ttf"),
    )
    font_path = next((path for path in candidates if path.is_file()), None)
    if font_path is None:
        return ImageFont.load_default()
    for size in range(height, 7, -1):
        font = ImageFont.truetype(str(font_path), size)
        box = draw.textbbox((0, 0), text, font=font, stroke_width=0)
        if box[2] - box[0] <= width and box[3] - box[1] <= height:
            return font
    return ImageFont.load_default()


def identification_masks(text: str, logo: Image.Image):
    width, height = 256, 52
    logo_width = 42
    text_mask = Image.new("L", (width, height), 0)
    logo_mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(text_mask)
    font = fit_font(draw, text, width - logo_width - 12, 27)
    box = draw.textbbox((0, 0), text, font=font)
    text_x = logo_width + 8
    text_y = (height - (box[3] - box[1])) // 2 - box[1]
    draw.text((text_x, text_y), text, font=font, fill=255)

    logo_copy = logo.copy()
    logo_copy.thumbnail((logo_width, height - 8), Image.Resampling.LANCZOS)
    alpha = logo_copy.getchannel("A")
    logo_mask.paste(alpha, (2, (height - logo_copy.height) // 2))
    # Geometry should be legible, not an antialiasing cloud of micro-prisms.
    return (text_mask.point(lambda value: 255 if value >= 120 else 0),
            logo_mask.point(lambda value: 255 if value >= 100 else 0))


def uv(index: int) -> tuple[float, float]:
    return ((index + 0.5) / PALETTE_SIZE, 0.5)


def append_quad(values: list[float], points, normal, palette_index: int):
    texture_uv = uv(palette_index)
    for index in (0, 1, 2, 0, 2, 3):
        point = points[index]
        values.extend((round(point[0], 5), round(point[1], 5),
                       round(point[2], 5), round(texture_uv[0], 6),
                       round(texture_uv[1], 6), *normal))


def append_box(values: list[float], x0: float, x1: float,
               y0: float, y1: float, z0: float, z1: float,
               palette_index: int):
    append_quad(values, ((x1, y0, z0), (x1, y1, z0),
                         (x1, y1, z1), (x1, y0, z1)),
                (1.0, 0.0, 0.0), palette_index)
    append_quad(values, ((x0, y0, z1), (x0, y1, z1),
                         (x0, y1, z0), (x0, y0, z0)),
                (-1.0, 0.0, 0.0), palette_index)
    append_quad(values, ((x0, y1, z0), (x0, y1, z1),
                         (x1, y1, z1), (x1, y1, z0)),
                (0.0, 1.0, 0.0), palette_index)
    append_quad(values, ((x0, y0, z1), (x0, y0, z0),
                         (x1, y0, z0), (x1, y0, z1)),
                (0.0, -1.0, 0.0), palette_index)
    append_quad(values, ((x0, y0, z1), (x1, y0, z1),
                         (x1, y1, z1), (x0, y1, z1)),
                (0.0, 0.0, 1.0), palette_index)
    append_quad(values, ((x1, y0, z0), (x0, y0, z0),
                         (x0, y1, z0), (x1, y1, z0)),
                (0.0, 0.0, -1.0), palette_index)


def append_mask_geometry(values: list[float], mask: Image.Image,
                         palette_index: int):
    width, height = mask.size
    pixels = mask.load()
    for row in range(height):
        column = 0
        while column < width:
            while column < width and pixels[column, row] == 0:
                column += 1
            start = column
            while column < width and pixels[column, row] != 0:
                column += 1
            if start == column:
                continue
            u0, u1 = start / width, column / width
            v0, v1 = row / height, (row + 1) / height
            y1 = MARK_Y_MAX - v0 * (MARK_Y_MAX - MARK_Y_MIN)
            y0 = MARK_Y_MAX - v1 * (MARK_Y_MAX - MARK_Y_MIN)
            # LocalTriangleMeshLayer's model transform reverses the plug's
            # authored X-facing projection relative to the raw OBJ frame.  The
            # previous mapping compensated in the wrong direction, so every
            # modelled NERV mark and unit designation read horizontally
            # mirrored in game.  Map raster-left to +Z on the +X face and to
            # -Z on the -X face; both outside views now read left-to-right.
            plus_z0 = MARK_Z_MIN + u0 * (MARK_Z_MAX - MARK_Z_MIN)
            plus_z1 = MARK_Z_MIN + u1 * (MARK_Z_MAX - MARK_Z_MIN)
            minus_z0 = MARK_Z_MAX - u1 * (MARK_Z_MAX - MARK_Z_MIN)
            minus_z1 = MARK_Z_MAX - u0 * (MARK_Z_MAX - MARK_Z_MIN)
            append_box(values, SIDE_INNER_X, SIDE_OUTER_X,
                       y0, y1, plus_z0, plus_z1, palette_index)
            append_box(values, -SIDE_OUTER_X, -SIDE_INNER_X,
                       y0, y1, minus_z0, minus_z1, palette_index)


def main() -> None:
    args = parse_args()
    root = args.output.resolve()
    base_path = root / "mesh/entry_plug.mesh.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    logo_path = args.logo or next(
        (path for path in LOGO_CANDIDATES if path.is_file()), None)
    if logo_path is None:
        raise FileNotFoundError("NERV logo source is missing")
    logo = clean_logo(logo_path)

    for variant, label in LABELS.items():
        mesh = json.loads(json.dumps(base))
        values = mesh["parts"]["entry_plug"]["vertices"]
        before = len(values)
        text_mask, logo_mask = identification_masks(label, logo)
        append_mask_geometry(values, text_mask, TEXT_PALETTE_INDEX)
        append_mask_geometry(values, logo_mask, LOGO_PALETTE_INDEX)
        added_triangles = (len(values) - before) // (8 * 3)
        mesh["triangle_count"] = mesh.get("triangle_count", 0) + added_triangles
        mesh.setdefault("audit", {})["modelled_identification_triangles"] = (
            added_triangles)
        mesh["audit"]["identification"] = (
            f"{label}; exact local NERV silhouette; bilateral shell geometry")
        target = root / f"mesh/entry_plug_unit{variant:02d}.mesh.json"
        target.write_text(json.dumps(mesh, separators=(",", ":")),
                          encoding="utf-8")
    print(f"Entry Plug model identification: logo={logo_path} variants=3")


if __name__ == "__main__":
    main()
