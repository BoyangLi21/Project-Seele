#!/usr/bin/env python3
"""Build a LOCAL-ONLY articulated Unit-00 using EUD's voxel head sculpture.

EUD ships a 20-cube structure, not a complete entity. This converter keeps
Project SEELE's animated Unit-00 body and replaces only its head with a
rotated, colour-preserving, greedily merged version of that sculpture.
"""
import gzip
import io
import json
import struct
import zipfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "eud-1.1.0-forge-1.20.1.jar"
BASE_GEO = REPO / "src/main/resources/assets/projectseele/geo/eva_unit00.geo.json"
BASE_TEXTURE = REPO / "src/main/resources/assets/projectseele/textures/entity/eva_unit00.png"
OUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
SCALE = 1.05

COLOURS = {
    "yellow": (226, 169, 30, 255),
    "black": (27, 29, 33, 255),
    "white": (226, 229, 224, 255),
    "purple": (104, 52, 142, 255),
    "blue": (75, 188, 208, 255),
    "red": (205, 43, 36, 255),
    "metal": (103, 100, 91, 255),
}
UV_PIXEL = {name: [248 + index, 255] for index, name in enumerate(COLOURS)}


def read_nbt(data):
    stream = io.BytesIO(gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data)

    def u8(): return stream.read(1)[0]
    def i16(): return struct.unpack(">h", stream.read(2))[0]
    def i32(): return struct.unpack(">i", stream.read(4))[0]
    def i64(): return struct.unpack(">q", stream.read(8))[0]
    def string(): return stream.read(i16()).decode("utf-8")

    def payload(tag):
        if tag == 1: return struct.unpack(">b", stream.read(1))[0]
        if tag == 2: return i16()
        if tag == 3: return i32()
        if tag == 4: return i64()
        if tag == 5: return struct.unpack(">f", stream.read(4))[0]
        if tag == 6: return struct.unpack(">d", stream.read(8))[0]
        if tag == 7: return stream.read(i32())
        if tag == 8: return string()
        if tag == 9:
            child, length = u8(), i32()
            return [payload(child) for _ in range(length)]
        if tag == 10:
            result = {}
            while True:
                child = u8()
                if child == 0:
                    return result
                key = string()
                result[key] = payload(child)
        if tag == 11:
            length = i32()
            return list(struct.unpack(f">{length}i", stream.read(length * 4)))
        if tag == 12:
            length = i32()
            return list(struct.unpack(f">{length}q", stream.read(length * 8)))
        raise ValueError(f"unsupported NBT tag {tag}")

    root_tag = u8()
    string()  # root name
    return payload(root_tag)


def colour_for(block_name):
    name = block_name.split(":")[-1]
    if "yellow" in name or "orange" in name:
        return "yellow"
    if "black" in name or "coal" in name:
        return "black"
    if "white" in name or "quartz" in name or "diorite" in name:
        return "white"
    if "purple" in name:
        return "purple"
    if "light_blue" in name or "sea_lantern" in name or "emerald" in name:
        return "blue"
    if "red" in name:
        return "red"
    return "metal"


def greedy_boxes(voxels):
    remaining = dict(voxels)
    boxes = []
    while remaining:
        x, y, z = min(remaining, key=lambda p: (p[1], p[0], p[2]))
        colour = remaining[(x, y, z)]
        dx = 1
        while remaining.get((x + dx, y, z)) == colour:
            dx += 1
        dz = 1
        while all(remaining.get((xx, y, z + dz)) == colour for xx in range(x, x + dx)):
            dz += 1
        dy = 1
        while all(remaining.get((xx, y + dy, zz)) == colour
                  for xx in range(x, x + dx) for zz in range(z, z + dz)):
            dy += 1
        for xx in range(x, x + dx):
            for yy in range(y, y + dy):
                for zz in range(z, z + dz):
                    remaining.pop((xx, yy, zz), None)
        boxes.append((x, y, z, dx, dy, dz, colour))
    return boxes


def face_uv(colour):
    pixel = UV_PIXEL[colour]
    face = {"uv": pixel, "uv_size": [1, 1]}
    return {name: dict(face) for name in ("north", "east", "south", "west", "up", "down")}


def main():
    if not SOURCE.exists():
        raise SystemExit(f"EUD jar not found: {SOURCE}")
    with zipfile.ZipFile(SOURCE) as archive:
        structure = read_nbt(archive.read("data/eud/structures/eva00structure.nbt"))
    palette = structure["palette"]
    voxels = {}
    for block in structure["blocks"]:
        name = palette[block["state"]]["Name"]
        if name != "minecraft:air":
            voxels[tuple(block["pos"])] = colour_for(name)

    geometry = json.loads(BASE_GEO.read_text(encoding="utf-8"))
    bones = geometry["minecraft:geometry"][0]["bones"]
    head = next(bone for bone in bones if bone["name"] == "head")
    horn = next(bone for bone in bones if bone["name"] == "horn")
    head["cubes"] = []
    horn["cubes"] = []

    # The structure's face looks along X. Rotate it into Gecko's Z-facing
    # convention: source Z becomes model X and source X becomes model Z.
    for x, y, z, dx, dy, dz, colour in greedy_boxes(voxels):
        origin = [
            (z - 10.0) * SCALE,
            148.0 + y * SCALE,
            (x - 8.5) * SCALE,
        ]
        size = [dz * SCALE, dy * SCALE, dx * SCALE]
        head["cubes"].append({"origin": origin, "size": size, "uv": face_uv(colour)})

    geo_path = OUT / "geo/eva_unit00.geo.json"
    texture_path = OUT / "textures/entity/eva_unit00.png"
    geo_path.parent.mkdir(parents=True, exist_ok=True)
    texture_path.parent.mkdir(parents=True, exist_ok=True)
    geo_path.write_text(json.dumps(geometry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    texture = Image.open(BASE_TEXTURE).convert("RGBA")
    for name, rgba in COLOURS.items():
        texture.putpixel(tuple(UV_PIXEL[name]), rgba)
    texture.save(texture_path)

    note = REPO / "run/resourcepacks/eva_real_model/_SOURCE.txt"
    existing = note.read_text(encoding="utf-8") if note.exists() else ""
    line = "EUD Unit-00 voxel head structure: local testing only; CC BY-NC 4.0 attribution required."
    if line not in existing:
        note.write_text(existing.rstrip() + "\n" + line + "\n", encoding="utf-8")
    print(f"Installed local EUD Unit-00 head: {len(voxels)} voxels -> {len(head['cubes'])} cuboids")


if __name__ == "__main__":
    main()
