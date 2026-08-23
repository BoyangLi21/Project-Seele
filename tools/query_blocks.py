"""Read exact block states out of a saved world box.

Measurement helper for coordinate-specific repairs on a frozen save: no
world writing, no semantic guessing, just "what block is actually at these
coordinates".  Prints full states (name plus properties) so a repair can be
authored against the real palette instead of an assumed one.

Usage:
    python tools/query_blocks.py <world> --dim projectseele:geofront \
        --box x0 y0 z0 x1 y1 z1 [--mode list|census|slice]

Modes:
    list    every non-air cell in the box (default; capped)
    census  counts per block state
    slice   per-y ASCII plan of the box using single-character legend
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from inspect_map_assets import (  # noqa: E402
    decode_modern_section,
    iter_chunks,
    palette_state,
)

AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def dimension_dir(world: Path, dimension: str) -> Path:
    if dimension in ("minecraft:overworld", "overworld"):
        return world
    namespace, path = dimension.split(":", 1)
    if namespace == "minecraft":
        return world / "DIM-1" if path == "the_nether" else world / "DIM1"
    return world / "dimensions" / namespace / path


def read_box(world: Path, dimension: str,
             lo: tuple[int, int, int], hi: tuple[int, int, int],
             namespace: str | None = None,
             ) -> dict[tuple[int, int, int], str]:
    return dict(iter_box_cells(world, dimension, lo, hi, namespace))


def iter_box_cells(world: Path, dimension: str,
                   lo: tuple[int, int, int], hi: tuple[int, int, int],
                   namespace: str | None = None):
    """Yield exact loaded cells without materializing a large world box."""
    root = dimension_dir(world, dimension)
    bounds = (lo[0] >> 4, hi[0] >> 4, lo[2] >> 4, hi[2] >> 4)
    for chunk_x, chunk_z, chunk in iter_chunks(root, bounds):
        base_x, base_z = chunk_x * 16, chunk_z * 16
        for section in chunk.get("sections", []):
            section_y = int(section.get("Y", 0))
            base_y = section_y * 16
            if base_y > hi[1] or base_y + 15 < lo[1]:
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            names = [palette_state(entry) for entry in palette]
            accepted = None if namespace is None else {
                index for index, state in enumerate(names)
                if state.startswith(namespace + ":")
            }
            if accepted is not None and not accepted:
                continue
            for offset in range(4096):
                y = base_y + (offset >> 8)
                if not lo[1] <= y <= hi[1]:
                    continue
                z = base_z + ((offset >> 4) & 15)
                if not lo[2] <= z <= hi[2]:
                    continue
                x = base_x + (offset & 15)
                if not lo[0] <= x <= hi[0]:
                    continue
                if accepted is not None and indices[offset] not in accepted:
                    continue
                yield (x, y, z), names[indices[offset]]


def iter_block_entities(world: Path, dimension: str,
                        lo: tuple[int, int, int], hi: tuple[int, int, int]):
    """Yield exact block-entity NBT entries inside a loaded world box."""
    root = dimension_dir(world, dimension)
    bounds = (lo[0] >> 4, hi[0] >> 4, lo[2] >> 4, hi[2] >> 4)
    for _chunk_x, _chunk_z, chunk in iter_chunks(root, bounds):
        for entry in chunk.get("block_entities", []):
            if not all(key in entry for key in ("x", "y", "z")):
                continue
            x, y, z = int(entry["x"]), int(entry["y"]), int(entry["z"])
            if (lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1]
                    and lo[2] <= z <= hi[2]):
                yield (x, y, z), entry


def short(state: str) -> str:
    return state.split("[", 1)[0].replace("minecraft:", "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--dim", default="projectseele:geofront")
    parser.add_argument("--box", type=int, nargs=6, required=True,
                        metavar=("X0", "Y0", "Z0", "X1", "Y1", "Z1"))
    parser.add_argument("--mode", default="list",
                        choices=("list", "census", "slice"))
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--air", action="store_true",
                        help="include air cells in list mode")
    parser.add_argument("--namespace",
                        help="only report states in this namespace (for example: create)")
    args = parser.parse_args()

    x0, y0, z0, x1, y1, z1 = args.box
    lo = (min(x0, x1), min(y0, y1), min(z0, z1))
    hi = (max(x0, x1), max(y0, y1), max(z0, z1))
    cells = read_box(args.world, args.dim, lo, hi, args.namespace)

    if args.mode == "census":
        counter = Counter(cells.values())
        total = (hi[0] - lo[0] + 1) * (hi[1] - lo[1] + 1) * (hi[2] - lo[2] + 1)
        missing = total - len(cells)
        if missing:
            print(f"  (unloaded/absent cells: {missing})")
        for state, count in counter.most_common():
            print(f"{count:8d}  {state}")
        return

    if args.mode == "slice":
        legend: dict[str, str] = {}
        alphabet = "#=+*oxXO%&$@ABCDEFGHJKLMNPQRSTUVWYZ"
        for y in range(lo[1], hi[1] + 1):
            print(f"--- y={y}  (x {lo[0]}..{hi[0]} left->right, "
                  f"z {lo[2]}..{hi[2]} top->bottom) ---")
            for z in range(lo[2], hi[2] + 1):
                row = []
                for x in range(lo[0], hi[0] + 1):
                    state = cells.get((x, y, z))
                    if state is None:
                        row.append("?")
                    elif state in AIR:
                        row.append(".")
                    else:
                        key = short(state)
                        if key not in legend:
                            legend[key] = alphabet[
                                len(legend) % len(alphabet)]
                        row.append(legend[key])
                print(f"  z={z:5d} " + "".join(row))
        print("legend: " + ", ".join(
            f"{char}={name}" for name, char in sorted(
                legend.items(), key=lambda item: item[1])))
        return

    shown = 0
    for position in sorted(cells, key=lambda p: (p[1], p[2], p[0])):
        state = cells[position]
        if not args.air and state in AIR:
            continue
        print(f"  {position[0]:5d} {position[1]:5d} {position[2]:5d}  {state}")
        shown += 1
        if shown >= args.limit:
            print(f"  ... capped at {args.limit}")
            break
    if shown == 0:
        print("  (no matching cells)")


if __name__ == "__main__":
    main()
