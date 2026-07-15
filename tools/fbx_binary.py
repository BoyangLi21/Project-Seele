#!/usr/bin/env python3
"""Small, dependency-free reader for the mesh subset of binary FBX files.

Project SEELE receives local evaluation assets as FBX archives.  Requiring a
particular Blender installation made those assets impossible to inspect on a
fresh machine, so this module reads the FBX node tree directly.  It is not a
general FBX SDK replacement: animation curves and skin deformers are outside
its contract.  Geometry arrays, object metadata, transforms and connections
are deliberately preserved for the local-only mesh converters.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct
import zlib


MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"


@dataclass(frozen=True)
class Node:
    name: str
    properties: tuple
    children: tuple["Node", ...]

    def child(self, name: str) -> "Node | None":
        return next((value for value in self.children if value.name == name), None)

    def children_named(self, name: str):
        return (value for value in self.children if value.name == name)


class FbxError(RuntimeError):
    pass


class _Reader:
    def __init__(self, data: bytes):
        self.data = memoryview(data)
        self.offset = 0

    def take(self, length: int) -> memoryview:
        end = self.offset + length
        if end > len(self.data):
            raise FbxError(f"unexpected end of FBX at {self.offset} + {length}")
        result = self.data[self.offset:end]
        self.offset = end
        return result

    def unpack(self, pattern: str):
        size = struct.calcsize(pattern)
        return struct.unpack(pattern, self.take(size))


def _decode_property(reader: _Reader):
    kind = bytes(reader.take(1))
    scalar = {
        b"Y": ("<h", 2),
        b"C": ("<B", 1),
        b"I": ("<i", 4),
        b"F": ("<f", 4),
        b"D": ("<d", 8),
        b"L": ("<q", 8),
    }
    if kind in scalar:
        pattern, length = scalar[kind]
        value = struct.unpack(pattern, reader.take(length))[0]
        return bool(value) if kind == b"C" else value
    if kind in (b"S", b"R"):
        length, = reader.unpack("<I")
        raw = bytes(reader.take(length))
        return raw.decode("utf-8", errors="replace") if kind == b"S" else raw
    array_formats = {
        b"f": "f",
        b"d": "d",
        b"l": "q",
        b"i": "i",
        b"b": "B",
        b"c": "b",
    }
    if kind in array_formats:
        count, encoding, stored_length = reader.unpack("<III")
        payload = bytes(reader.take(stored_length))
        if encoding == 1:
            payload = zlib.decompress(payload)
        elif encoding != 0:
            raise FbxError(f"unsupported FBX array encoding {encoding}")
        pattern = array_formats[kind]
        expected = struct.calcsize("<" + pattern) * count
        if len(payload) != expected:
            raise FbxError(
                f"FBX array {kind!r} expected {expected} bytes, got {len(payload)}")
        return struct.unpack("<" + pattern * count, payload)
    raise FbxError(f"unsupported FBX property type {kind!r} at {reader.offset - 1}")


def _read_node(reader: _Reader, version: int) -> Node | None:
    if version >= 7500:
        end_offset, property_count, property_length = reader.unpack("<QQQ")
        null_header_size = 25
    else:
        end_offset, property_count, property_length = reader.unpack("<III")
        null_header_size = 13
    name_length, = reader.unpack("<B")
    if end_offset == 0 and property_count == 0 and property_length == 0 and name_length == 0:
        return None
    name = bytes(reader.take(name_length)).decode("utf-8", errors="replace")
    property_start = reader.offset
    properties = tuple(_decode_property(reader) for _ in range(property_count))
    consumed = reader.offset - property_start
    if consumed != property_length:
        raise FbxError(
            f"node {name!r} property bytes {consumed}, header says {property_length}")
    children = []
    # Nodes with children terminate with a zero node record.  Leaf records end
    # exactly at end_offset and therefore never consume an extra null header.
    while reader.offset < end_offset:
        remaining = end_offset - reader.offset
        if remaining == null_header_size:
            marker = bytes(reader.take(null_header_size))
            if any(marker):
                raise FbxError(f"invalid null record after node {name!r}")
            break
        child = _read_node(reader, version)
        if child is None:
            break
        children.append(child)
    if reader.offset != end_offset:
        raise FbxError(
            f"node {name!r} ended at {reader.offset}, header says {end_offset}")
    return Node(name, properties, tuple(children))


def parse(data: bytes) -> tuple[int, tuple[Node, ...]]:
    if not data.startswith(MAGIC):
        raise FbxError("not a binary FBX file")
    reader = _Reader(data)
    reader.offset = len(MAGIC)
    version, = reader.unpack("<I")
    roots = []
    null_size = 25 if version >= 7500 else 13
    while reader.offset + null_size <= len(reader.data):
        start = reader.offset
        node = _read_node(reader, version)
        if node is None:
            break
        roots.append(node)
        if reader.offset <= start:
            raise FbxError("FBX parser made no progress")
    return version, tuple(roots)


def root(nodes: tuple[Node, ...], name: str) -> Node | None:
    return next((node for node in nodes if node.name == name), None)


def object_nodes(nodes: tuple[Node, ...]):
    objects = root(nodes, "Objects")
    return objects.children if objects else ()


def connections(nodes: tuple[Node, ...]):
    section = root(nodes, "Connections")
    if section is None:
        return ()
    return tuple(node.properties for node in section.children if node.name == "C")
