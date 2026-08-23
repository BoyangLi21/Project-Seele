#!/usr/bin/env python3
"""Generate the original static GeoFront magic-weave cutout texture."""

from pathlib import Path

from PIL import Image


OUTPUT = Path(
    "src/main/resources/assets/projectseele/textures/block/"
    "geofront_skyweave.png"
)


def main() -> None:
    size = 32
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(size):
        for x in range(size):
            diagonal_a = (x + y) % 16 == 0
            diagonal_b = (x - y) % 16 == 0
            if not (diagonal_a or diagonal_b):
                continue
            mix = (x + 2 * y) / (3 * (size - 1))
            red = round(74 + 92 * mix)
            green = round(224 - 82 * mix)
            pixels[x, y] = (red, green, 246, 255)
    for y in range(0, size, 8):
        for x in range(0, size, 8):
            pixels[x, y] = (226, 244, 255, 255)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)


if __name__ == "__main__":
    main()
