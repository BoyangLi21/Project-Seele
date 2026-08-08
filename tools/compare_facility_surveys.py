#!/usr/bin/env python3
"""Compare two saved GeoFront voxel volumes without mutating either world.

This is an incident-analysis companion to ``survey_facility_target.py``.  It
uses identical bounds and cameras for both saves, emits every changed block,
and renders red/green/yellow diff layers.  The output is evidence only; it is
not an applicable repair patch.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import survey_facility_target as survey  # noqa: E402


REMOVED = 1
ADDED = 2
REPLACED = 3
DIFF_COLOURS = {
    0: (16, 16, 22),
    REMOVED: (238, 55, 55),
    ADDED: (55, 225, 105),
    REPLACED: (255, 210, 55),
}


def canonical_codes(before: survey.Volume, after: survey.Volume):
    states = sorted(set(before.states) | set(after.states))
    mapping = {state: index for index, state in enumerate(states)}
    before_map = np.asarray([mapping[state] for state in before.states],
                            dtype=np.uint16)
    after_map = np.asarray([mapping[state] for state in after.states],
                           dtype=np.uint16)
    return states, before_map[before.code], after_map[after.code]


def render_diff_plan(diff: np.ndarray, box, y: int,
                     anchor: tuple[int, int, int], title: str,
                     scale: int = 5) -> Image.Image:
    x0, x1, y0, y1, z0, z1 = box
    iy = y - y0
    layer = diff[:, iy, :].transpose(1, 0)
    rgb = np.zeros((layer.shape[0], layer.shape[1], 3), dtype=np.uint8)
    for code, colour in DIFF_COLOURS.items():
        rgb[layer == code] = colour
    body = Image.fromarray(rgb, "RGB").resize(
        (layer.shape[1] * scale, layer.shape[0] * scale),
        Image.Resampling.NEAREST)
    image = Image.new("RGB", (body.width + 96, body.height + 56),
                      (16, 16, 22))
    image.paste(body, (76, 28))
    draw = ImageDraw.Draw(image)
    survey.add_grid(draw, 76, 28, x1 - x0 + 1, z1 - z0 + 1,
                    scale, x0, z0)
    ax, ay, az = anchor
    px = 76 + (ax - x0) * scale + scale // 2
    pz = 28 + (az - z0) * scale + scale // 2
    draw.ellipse((px - 7, pz - 7, px + 7, pz + 7),
                 outline=(255, 255, 255), width=2)
    draw.text((76, 5), f"{title} y={y}", fill=(255, 214, 84))
    draw.text((6, image.height - 18),
              "RED removed  GREEN added  YELLOW replaced  | evidence only",
              fill=(225, 225, 232))
    return image


def write_sha(directory: Path) -> str:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "packet.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
                        f"{path.relative_to(directory).as_posix()}")
    payload = "\n".join(rows) + "\n"
    (directory / "packet.sha256").write_text(payload, encoding="ascii")
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-world", required=True)
    parser.add_argument("--after-world", required=True)
    parser.add_argument("--anchor", nargs=3, type=int, required=True)
    parser.add_argument("--horizontal", type=int, default=48)
    parser.add_argument("--vertical", type=int, default=32)
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--emit")
    args = parser.parse_args()
    anchor = tuple(args.anchor)
    box = (anchor[0] - args.horizontal, anchor[0] + args.horizontal,
           anchor[1] - args.vertical, anchor[1] + args.vertical,
           anchor[2] - args.horizontal, anchor[2] + args.horizontal)
    dimension = "dimensions/projectseele/geofront"
    before_root = ROOT / "run/saves" / args.before_world / dimension
    after_root = ROOT / "run/saves" / args.after_world / dimension
    output = ROOT / (args.emit or f"artifacts/map_incidents/{args.incident_id}")
    output.mkdir(parents=True, exist_ok=True)
    layers_dir = output / "layers"
    layers_dir.mkdir(exist_ok=True)
    before = survey.Volume(before_root, box)
    after = survey.Volume(after_root, box)
    states, before_code, after_code = canonical_codes(before, after)
    changed = before_code != after_code
    before_air = np.asarray([survey.role_of(state) == "air" for state in states])[before_code]
    after_air = np.asarray([survey.role_of(state) == "air" for state in states])[after_code]
    diff = np.zeros(changed.shape, dtype=np.uint8)
    diff[changed & ~before_air & after_air] = REMOVED
    diff[changed & before_air & ~after_air] = ADDED
    diff[changed & ~before_air & ~after_air] = REPLACED
    # Light/air state changes remain replacements so the ledger is complete.
    diff[changed & (diff == 0)] = REPLACED

    transition_counts = Counter()
    rows = 0
    with gzip.open(output / "block_diff.csv.gz", "wt",
                   encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("x", "y", "z", "before", "after", "change"))
        for ix, iy, iz in zip(*np.nonzero(changed)):
            x, y, z = before.world_position(ix, iy, iz)
            old = states[int(before_code[ix, iy, iz])]
            new = states[int(after_code[ix, iy, iz])]
            kind = {REMOVED: "removed", ADDED: "added",
                    REPLACED: "replaced"}[int(diff[ix, iy, iz])]
            writer.writerow((x, y, z, old, new, kind))
            transition_counts[(old, new)] += 1
            rows += 1

    counts_by_y = Counter()
    for _, iy, _ in zip(*np.nonzero(changed)):
        counts_by_y[before.y0 + int(iy)] += 1
    levels = sorted(counts_by_y, key=lambda y: (-counts_by_y[y], y))[:24]
    levels = sorted(levels)
    pages = []
    for y in levels:
        image = render_diff_plan(diff, box, y, anchor,
                                 f"INCIDENT DIFF {args.incident_id}")
        image.save(layers_dir / f"y{y}.png")
        pages.append(image)
    if pages:
        pages[0].save(output / "diff_layers.pdf", "PDF", save_all=True,
                      append_images=pages[1:], resolution=120.0)

    before_masks = before.masks()
    after_masks = after.masks()
    survey.output_anchor = anchor
    before_iso_a = survey.iso_projection(before, before_masks, anchor, 1, 1,
                                          "BASE +X/+Z")
    before_iso_b = survey.iso_projection(before, before_masks, anchor, -1, -1,
                                          "BASE -X/-Z")
    after_iso_a = survey.iso_projection(after, after_masks, anchor, 1, 1,
                                         "DAMAGED +X/+Z")
    after_iso_b = survey.iso_projection(after, after_masks, anchor, -1, -1,
                                         "DAMAGED -X/-Z")
    survey.combine_panels([before_iso_a, before_iso_b, after_iso_a, after_iso_b],
                          2, output / "before_after_same_views.png")

    summary = {
        "incident_id": args.incident_id,
        "mode": "READ_ONLY_INCIDENT_COMPARISON",
        "editable_mask": [],
        "before_world": args.before_world,
        "after_world": args.after_world,
        "anchor": list(anchor),
        "box": list(box),
        "changed_blocks": rows,
        "removed": int((diff == REMOVED).sum()),
        "added": int((diff == ADDED).sum()),
        "replaced": int((diff == REPLACED).sum()),
        "changed_by_y": {str(y): counts_by_y[y]
                         for y in sorted(counts_by_y)},
        "top_transitions": [
            {"before": old, "after": new, "count": count}
            for (old, new), count in transition_counts.most_common(40)
        ],
        "warning": ("This comparison includes every change between the two "
                    "save times. It does not prove which changes were accepted "
                    "or caused by the rejected round."),
    }
    (output / "incident_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    digest = write_sha(output)
    print(f"[incident] {args.incident_id} changed={rows} "
          f"removed={summary['removed']} added={summary['added']} "
          f"replaced={summary['replaced']}")
    print(f"[output] {output}")
    print(f"[packet-sha] {digest}")


if __name__ == "__main__":
    main()
