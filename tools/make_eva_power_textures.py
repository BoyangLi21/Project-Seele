#!/usr/bin/env python3
"""Split the local Tiger EVA eye pixels into cold and powered textures.

The private source converters write their normal painted atlases first. This
post-pass stores only a transparent eye overlay beside each atlas, then makes
the base eye pigments nearly black. The renderer draws the overlay full-bright
only when the airframe's authoritative power circuit is online.
"""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
BUNDLED_TEXTURES = (
    ROOT
    / "src"
    / "main"
    / "resources"
    / "assets"
    / "projectseele"
    / "textures"
    / "entity"
)
TEXTURES = (
    ROOT
    / "run"
    / "resourcepacks"
    / "eva_real_model"
    / "assets"
    / "projectseele"
    / "textures"
    / "entity"
)


def yellow(pixel):
    red, green, blue, alpha = pixel
    return alpha > 0 and red > 120 and green > 65 and blue < 105


def red_lens(pixel):
    red, green, blue, alpha = pixel
    return (
        alpha > 0
        and red > 95
        and red > green * 1.25
        and red > blue * 1.35
    )


MASKS = {
    "eva_unit00": ((50, 7, 80, 31, red_lens),),
    "eva_unit01": ((118, 74, 149, 97, yellow),),
    "eva_unit02": ((122, 74, 144, 92, yellow),),
}


def ensure_bundled_fallbacks():
    """Keep the renderer safe when the private high-detail pack is absent.

    The bundled fallback models do not yet have a reviewed eye UV mask. A
    transparent overlay is preferable to Minecraft's missing-texture pattern;
    the high-detail local pack still receives the real cold/live split below.
    """
    BUNDLED_TEXTURES.mkdir(parents=True, exist_ok=True)
    for name in MASKS:
        texture_path = BUNDLED_TEXTURES / f"{name}.png"
        overlay_path = BUNDLED_TEXTURES / f"{name}_eyes.png"
        if overlay_path.exists() or not texture_path.exists():
            continue
        size = Image.open(texture_path).size
        Image.new("RGBA", size, (0, 0, 0, 0)).save(overlay_path)
        print(f"{name}: added transparent bundled eye fallback")


def restore_previous_overlay(base, overlay_path):
    if not overlay_path.exists():
        return
    previous = Image.open(overlay_path).convert("RGBA")
    if previous.size != base.size:
        return
    base.alpha_composite(previous)


def split_texture(name, regions):
    texture_path = TEXTURES / f"{name}.png"
    if not texture_path.exists():
        raise SystemExit(f"missing generated EVA texture: {texture_path}")
    overlay_path = TEXTURES / f"{name}_eyes.png"
    base = Image.open(texture_path).convert("RGBA")
    restore_previous_overlay(base, overlay_path)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    selected = 0
    for left, top, right, bottom, predicate in regions:
        for y in range(max(0, top), min(base.height, bottom)):
            for x in range(max(0, left), min(base.width, right)):
                pixel = base.getpixel((x, y))
                if not predicate(pixel):
                    continue
                overlay.putpixel((x, y), pixel)
                red, green, blue, alpha = pixel
                base.putpixel(
                    (x, y),
                    (
                        max(2, round(red * 0.035)),
                        max(2, round(green * 0.035)),
                        max(2, round(blue * 0.035)),
                        alpha,
                    ),
                )
                selected += 1
    if selected < 8:
        raise RuntimeError(f"{name}: eye mask selected only {selected} pixels")
    base.save(texture_path)
    overlay.save(overlay_path)
    print(f"{name}: cold eye + {selected}-pixel powered overlay")


def main():
    ensure_bundled_fallbacks()
    for name, regions in MASKS.items():
        split_texture(name, regions)


if __name__ == "__main__":
    main()
