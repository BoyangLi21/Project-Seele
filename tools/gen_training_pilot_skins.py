#!/usr/bin/env python3
"""Generate original 64x64 Project SEELE dummy-pilot skins."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path("src/main/resources/assets/projectseele/textures/entity")

def paint(draw, boxes, colour):
    for box in boxes:
        draw.rectangle(box, fill=colour)

def skin(name, hair, skin_colour, suit, accent, eye):
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    head = ((8, 0, 15, 7), (16, 0, 23, 7), (0, 8, 7, 15),
            (8, 8, 15, 15), (16, 8, 23, 15), (24, 8, 31, 15))
    paint(draw, head, skin_colour)
    draw.rectangle((8, 8, 15, 10), fill=hair)
    draw.rectangle((8, 11, 8, 15), fill=hair)
    draw.rectangle((15, 11, 15, 15), fill=hair)
    draw.rectangle((10, 12, 11, 12), fill=eye)
    draw.rectangle((13, 12, 14, 12), fill=eye)
    draw.rectangle((11, 15, 13, 15), fill=(145, 72, 72, 255))
    hair_layer = ((40, 0, 47, 7), (32, 8, 39, 15), (40, 8, 47, 15),
                  (48, 8, 55, 15), (56, 8, 63, 15))
    paint(draw, hair_layer, hair)
    draw.rectangle((41, 11, 46, 15), fill=(0, 0, 0, 0))
    torso = ((20, 16, 27, 19), (28, 16, 35, 19), (16, 20, 19, 31),
             (20, 20, 27, 31), (28, 20, 31, 31), (32, 20, 39, 31))
    right_arm = ((44, 16, 47, 19), (48, 16, 51, 19), (40, 20, 43, 31),
                 (44, 20, 47, 31), (48, 20, 51, 31), (52, 20, 55, 31))
    right_leg = ((4, 16, 7, 19), (8, 16, 11, 19), (0, 20, 3, 31),
                 (4, 20, 7, 31), (8, 20, 11, 31), (12, 20, 15, 31))
    left_leg = ((20, 48, 23, 51), (24, 48, 27, 51), (16, 52, 19, 63),
                (20, 52, 23, 63), (24, 52, 27, 63), (28, 52, 31, 63))
    left_arm = ((36, 48, 39, 51), (40, 48, 43, 51), (32, 52, 35, 63),
                (36, 52, 39, 63), (40, 52, 43, 63), (44, 52, 47, 63))
    paint(draw, torso + right_arm + right_leg + left_leg + left_arm, suit)
    draw.rectangle((21, 20, 26, 22), fill=accent)
    draw.rectangle((23, 23, 24, 30), fill=accent)
    draw.rectangle((20, 29, 27, 31), fill=accent)
    for x0 in (44, 48):
        draw.rectangle((x0, 24, x0 + 3, 25), fill=accent)
    for x0 in (36, 40):
        draw.rectangle((x0, 56, x0 + 3, 57), fill=accent)
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / f"training_pilot_{name}.png")

def main():
    skin("rei", (151, 210, 226, 255), (238, 213, 199, 255),
         (235, 238, 241, 255), (194, 36, 42, 255), (185, 46, 58, 255))
    skin("shinji", (53, 42, 43, 255), (222, 183, 160, 255),
         (238, 238, 230, 255), (38, 76, 148, 255), (44, 55, 70, 255))
    skin("asuka", (176, 73, 38, 255), (237, 190, 155, 255),
         (190, 24, 34, 255), (38, 42, 48, 255), (55, 92, 158, 255))

if __name__ == "__main__":
    main()