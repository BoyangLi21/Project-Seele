#!/usr/bin/env python3
"""Generate local Entry Plug unit designations from the office NERV logo."""

from __future__ import annotations

import argparse
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
    0: ("EVA-00 PROTO TYPE", (205, 151, 38, 255)),
    1: ("EVA-01 TEST TYPE", (100, 42, 151, 255)),
    2: ("EVA-02 PRODUCTION MODEL", (178, 25, 38, 255)),
}


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
                pixels[x, y] = (red, green, blue, 0)
            elif alpha > 0 and red > green * 1.35 and red > blue * 1.35:
                # Preserve the supplied exact silhouette but normalize its
                # baked checkerboard antialiasing to NERV signal red.
                pixels[x, y] = (220, 18, 24, alpha)
            else:
                pixels[x, y] = (red, green, blue, 0)
    crop = logo.getbbox()
    return logo.crop(crop) if crop else logo


def fit_font(draw: ImageDraw.ImageDraw, text: str, maximum_width: int):
    font_path = Path(r"C:\Windows\Fonts\arialbd.ttf")
    for size in range(40, 17, -1):
        font = ImageFont.truetype(str(font_path), size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= maximum_width:
            return font
    return ImageFont.load_default()


def main() -> None:
    args = parse_args()
    logo_path = args.logo
    if logo_path is None:
        logo_path = next((path for path in LOGO_CANDIDATES if path.is_file()), None)
    if logo_path is None:
        raise FileNotFoundError(
            "NERV logo not found; expected run/projectseele-local-maps/nerv_logo.png"
        )
    logo = clean_logo(logo_path)
    output = args.output / "textures/entity"
    output.mkdir(parents=True, exist_ok=True)

    for variant, (text, accent) in LABELS.items():
        image = Image.new("RGBA", (512, 160), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # The actual NERV mark is deliberately small; the unit designation is
        # the primary distance-readable stencil on the pressure shell.
        logo_copy = logo.copy()
        logo_copy.thumbnail((92, 92), Image.Resampling.LANCZOS)
        image.alpha_composite(logo_copy, (12, (160 - logo_copy.height) // 2))
        draw.rounded_rectangle((112, 30, 505, 130), radius=9,
                               fill=(236, 239, 242, 238),
                               outline=accent, width=7)
        font = fit_font(draw, text, 365)
        box = draw.textbbox((0, 0), text, font=font)
        x = 112 + (393 - (box[2] - box[0])) // 2
        y = 30 + (100 - (box[3] - box[1])) // 2 - box[1]
        draw.text((x, y), text, font=font, fill=(18, 22, 28, 255))
        image.save(output / f"entry_plug_decal_unit{variant:02d}.png",
                   optimize=True)
    print(f"Entry Plug decals: logo={logo_path} variants=3 output={output}")


if __name__ == "__main__":
    main()
