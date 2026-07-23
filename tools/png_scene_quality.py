"""Dependency-free visual sanity checks for Minecraft PNG screenshots."""

from __future__ import annotations

from pathlib import Path
import struct
import zlib


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_error = abs(estimate - left)
    up_error = abs(estimate - up)
    corner_error = abs(estimate - upper_left)
    if left_error <= up_error and left_error <= corner_error:
        return left
    return up if up_error <= corner_error else upper_left


def png_scene_metrics(path: Path) -> tuple[float, float, int]:
    """Return dark fraction, horizontal texture and quantised colour count.

    Minecraft writes non-interlaced 8-bit RGB/RGBA screenshots. Decoding that
    small PNG subset keeps the launcher independent of Pillow while preventing
    loading screens, black frames and empty horizons from passing by file count.
    """
    payload = path.read_bytes()
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG")
    width = height = colour_type = bit_depth = interlace = None
    compressed = bytearray()
    cursor = 8
    while cursor + 12 <= len(payload):
        length = struct.unpack(">I", payload[cursor:cursor + 4])[0]
        kind = payload[cursor + 4:cursor + 8]
        chunk = payload[cursor + 8:cursor + 8 + length]
        cursor += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, colour_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk)
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break
    if not width or not height or bit_depth != 8 or colour_type not in (2, 6):
        raise ValueError("unsupported Minecraft PNG format")
    if interlace:
        raise ValueError("interlaced PNG is unsupported")
    channels = 3 if colour_type == 2 else 4
    stride = width * channels
    decoded = zlib.decompress(bytes(compressed))
    if len(decoded) != height * (stride + 1):
        raise ValueError("truncated PNG scanlines")

    rows: list[bytearray] = []
    offset = 0
    previous = bytearray(stride)
    for _ in range(height):
        filter_type = decoded[offset]
        row = bytearray(decoded[offset + 1:offset + 1 + stride])
        offset += stride + 1
        for index in range(stride):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 1:
                row[index] = (row[index] + left) & 0xFF
            elif filter_type == 2:
                row[index] = (row[index] + up) & 0xFF
            elif filter_type == 3:
                row[index] = (row[index] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                row[index] = (row[index] + _paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter {filter_type}")
        rows.append(row)
        previous = row

    x_step = max(1, width // 96)
    y_step = max(1, height // 54)
    dark = samples = 0
    horizontal_delta = 0.0
    horizontal_pairs = 0
    colours: set[tuple[int, int, int]] = set()
    for y in range(y_step // 2, height, y_step):
        prior_luma: float | None = None
        row = rows[y]
        for x in range(x_step // 2, width, x_step):
            index = x * channels
            red, green, blue = row[index:index + 3]
            luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            dark += luma < 10.0
            samples += 1
            colours.add((red >> 4, green >> 4, blue >> 4))
            if prior_luma is not None:
                horizontal_delta += abs(luma - prior_luma)
                horizontal_pairs += 1
            prior_luma = luma
    return (dark / max(1, samples),
            horizontal_delta / max(1, horizontal_pairs), len(colours))


def invalid_scene_pngs(pngs: list[Path]) -> list[str]:
    invalid: list[str] = []
    for path in pngs:
        try:
            dark_fraction, horizontal_texture, colour_count = png_scene_metrics(path)
        except (OSError, ValueError, zlib.error) as exc:
            invalid.append(f"{path.name}: unreadable ({exc})")
            continue
        reasons = []
        if dark_fraction >= 0.965:
            reasons.append(f"{dark_fraction:.1%} near-black")
        if horizontal_texture < 0.55:
            reasons.append(f"horizontal texture {horizontal_texture:.2f}")
        if colour_count < 12:
            reasons.append(f"only {colour_count} colour bins")
        if reasons:
            invalid.append(f"{path.name}: {', '.join(reasons)}")
    return invalid
