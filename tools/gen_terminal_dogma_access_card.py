#!/usr/bin/env python3
"""Generate Project SEELE's original Terminal Dogma access-card texture."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
TARGET = (ROOT / "src/main/resources/assets/projectseele/textures/item"
          / "terminal_dogma_access_card.png")


def main() -> None:
    image = Image.new("RGBA", (32, 32), (11, 13, 16, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 5, 29, 26), radius=3,
                           fill=(218, 220, 211, 255),
                           outline=(74, 17, 24, 255), width=2)
    draw.rectangle((4, 7, 27, 11), fill=(135, 17, 29, 255))
    draw.rectangle((5, 14, 18, 16), fill=(42, 45, 49, 255))
    draw.rectangle((5, 19, 14, 21), fill=(42, 45, 49, 255))
    draw.rectangle((21, 14, 26, 22), fill=(135, 17, 29, 255))
    draw.line((21, 22, 24, 15, 27, 22), fill=(235, 235, 225, 255), width=1)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    image.save(TARGET)
    print(TARGET)


if __name__ == "__main__":
    main()
