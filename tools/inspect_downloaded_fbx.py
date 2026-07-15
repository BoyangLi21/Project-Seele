#!/usr/bin/env python3
"""Report separable objects in the downloaded EVA evaluation FBX archives."""

from __future__ import annotations

import io
from pathlib import Path
import zipfile

from fbx_binary import connections, object_nodes, parse


REPO = Path(__file__).resolve().parent.parent


def downloaded_files():
    knife_archive = REPO / "external-assets/incoming/progressive-knife.zip"
    with zipfile.ZipFile(knife_archive) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read("source/knife.zip"))) as inner:
            yield "progressive-knife/progknife.fbx", inner.read("progknife.fbx")
    unit02_archive = REPO / "external-assets/incoming/eva-02-rebuild-version-not-rigged.zip"
    with zipfile.ZipFile(unit02_archive) as archive:
        yield "eva-02-rebuild/source/eva 02.fbx", archive.read("source/eva 02.fbx")


def property_value(node, child_name):
    child = node.child(child_name)
    if child is None or not child.properties:
        return None
    value = child.properties[0]
    return value if isinstance(value, tuple) else None


def object_id(node):
    return int(node.properties[0]) if node.properties else None


def clean_name(node):
    if len(node.properties) < 2:
        return "?"
    return str(node.properties[1]).split("\x00", 1)[0]


def report(label, data):
    version, nodes = parse(data)
    objects = object_nodes(nodes)
    object_by_id = {object_id(node): node for node in objects if object_id(node) is not None}
    parents = {}
    for connection in connections(nodes):
        if len(connection) >= 3 and connection[0] == "OO":
            parents.setdefault(int(connection[1]), []).append(int(connection[2]))
    print(f"\n=== {label} / FBX {version} / {len(data)} bytes ===")
    print("object type counts:")
    counts = {}
    for node in objects:
        counts[node.name] = counts.get(node.name, 0) + 1
    print("  " + ", ".join(f"{name}={count}" for name, count in sorted(counts.items())))
    print("mesh geometries:")
    for node in objects:
        if node.name != "Geometry" or len(node.properties) < 3:
            continue
        vertices = property_value(node, "Vertices") or ()
        polygons = property_value(node, "PolygonVertexIndex") or ()
        points = list(zip(vertices[0::3], vertices[1::3], vertices[2::3]))
        bounds = []
        for axis in range(3):
            values = [point[axis] for point in points]
            bounds.append((min(values), max(values)))
        parent_names = [clean_name(object_by_id[value]) for value in parents.get(object_id(node), [])
                        if value in object_by_id]
        print(f"  id={object_id(node)} name={clean_name(node)!r} "
              f"verts={len(points)} polygon_indices={len(polygons)} "
              f"bounds={bounds} parents={parent_names}")
    print("models/materials:")
    for node in objects:
        if node.name not in {"Model", "Material"}:
            continue
        subtype = node.properties[2] if len(node.properties) > 2 else ""
        parent_names = [clean_name(object_by_id[value]) for value in parents.get(object_id(node), [])
                        if value in object_by_id]
        print(f"  {node.name:<8} id={object_id(node)} name={clean_name(node)!r} "
              f"subtype={subtype!r} parents={parent_names}")


def main():
    for label, data in downloaded_files():
        report(label, data)


if __name__ == "__main__":
    main()
