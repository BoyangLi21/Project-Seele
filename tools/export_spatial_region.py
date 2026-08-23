#!/usr/bin/env python3
"""Export one exact semantic world region as a block-accurate GLB.

This is the incremental companion to ``export_spatial_twin.py``.  It reads
only the requested bounding box and never changes the save.  At the default
LOD 1, one Minecraft block is one model unit; greedy face merging changes
mesh size only and does not reduce spatial resolution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from export_spatial_twin import (  # noqa: E402
    Bounds,
    CATEGORY_NAMES,
    DimensionSpec,
    scan_dimension,
    surface_meshes,
    write_glb,
)


ROOT = Path(__file__).resolve().parents[1]


def dimension_path(identifier: str) -> str:
    """Translate a Minecraft dimension id to its save-relative directory."""
    if identifier in ("minecraft:overworld", "overworld", ""):
        return ""
    if ":" in identifier:
        namespace, name = identifier.split(":", 1)
        return f"dimensions/{namespace}/{name}"
    return identifier.replace("\\", "/").strip("/")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path,
                        default=ROOT / "run/saves/SEELE_S20_RECOVERY_R28")
    parser.add_argument("--dim", default="projectseele:geofront")
    parser.add_argument("--box", type=int, nargs=6, required=True,
                        metavar=("X0", "Y0", "Z0", "X1", "Y1", "Z1"))
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lod", type=int, default=1)
    args = parser.parse_args()

    if args.lod < 1:
        parser.error("--lod must be >= 1")
    x0, y0, z0, x1, y1, z1 = args.box
    bounds = Bounds(min(x0, x1), max(x0, x1),
                    min(y0, y1), max(y0, y1),
                    min(z0, z1), max(z0, z1))
    world = args.world if args.world.is_absolute() else ROOT / args.world
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    spec = DimensionSpec(args.label, dimension_path(args.dim), bounds)
    result = scan_dimension(world.resolve(), spec, args.lod,
                            collect_chunks=False)
    mesh_stats = write_glb(
        output,
        surface_meshes(result["grid"], bounds, args.lod),
        {
            "dimension": args.dim,
            "selection": args.label,
            "bounds": bounds.as_list(),
            "lod": args.lod,
            "worldCoordinates": True,
            "blockAccurate": args.lod == 1,
        },
    )
    receipt = {
        "status": "READ_ONLY_EXACT_REGION_EXPORTED",
        "world": str(world.resolve()),
        "dimension": args.dim,
        "label": args.label,
        "bounds": bounds.as_list(),
        "lod": args.lod,
        "blockAccurate": args.lod == 1,
        "model": str(output.resolve()),
        "categories": {
            CATEGORY_NAMES[key]: int(value)
            for key, value in sorted(result["category_totals"].items())
        },
        "meshStats": mesh_stats,
    }
    receipt_path = output.with_suffix(output.suffix + ".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
