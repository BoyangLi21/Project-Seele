#!/usr/bin/env python3
"""Generate an original pixel-art transformation capsule icon."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (ROOT / "src/main/resources/assets/projectseele/textures/item"
          / "beta_capsule.png")


def main() -> None:
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 3, 19, 28), radius=3,
                           fill=(210, 214, 218, 255),
                           outline=(42, 45, 50, 255), width=2)
    draw.rectangle((13, 8, 18, 19), fill=(185, 20, 28, 255))
    draw.ellipse((13, 4, 18, 9), fill=(230, 234, 238, 255),
                 outline=(42, 45, 50, 255))
    draw.ellipse((14, 10, 17, 13), fill=(75, 210, 245, 255))
    draw.rectangle((14, 21, 17, 26), fill=(80, 84, 92, 255))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
