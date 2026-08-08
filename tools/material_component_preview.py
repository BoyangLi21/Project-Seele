#!/usr/bin/env python3
"""Create a read-only removal preview for one bounded material component.

An F3 coordinate is treated only as an observation anchor.  The selected
object is the nearest complete six-neighbour component made solely from the
explicit material allow-list.  Components that touch the survey boundary are
never considered safe to preview.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
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


def six_components(mask: np.ndarray, volume: survey.Volume) -> tuple[np.ndarray, list[dict]]:
    labels = np.full(mask.shape, -1, dtype=np.int32)
    components = []
    sx, sy, sz = mask.shape
    for start in zip(*np.nonzero(mask)):
        if labels[start] >= 0:
            continue
        component_id = len(components)
        labels[start] = component_id
        queue = deque([start])
        points = []
        mins = [sx, sy, sz]
        maxs = [-1, -1, -1]
        states = Counter()
        touches = False
        while queue:
            x, y, z = queue.popleft()
            points.append((x, y, z))
            mins = [min(mins[0], x), min(mins[1], y), min(mins[2], z)]
            maxs = [max(maxs[0], x), max(maxs[1], y), max(maxs[2], z)]
            touches |= (x in (0, sx - 1) or y in (0, sy - 1)
                        or z in (0, sz - 1))
            states[volume.state(x, y, z)] += 1
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0),
                               (0, 1, 0), (0, -1, 0),
                               (0, 0, 1), (0, 0, -1)):
                nx, ny, nz = x + dx, y + dy, z + dz
                if (0 <= nx < sx and 0 <= ny < sy and 0 <= nz < sz
                        and mask[nx, ny, nz] and labels[nx, ny, nz] < 0):
                    labels[nx, ny, nz] = component_id
                    queue.append((nx, ny, nz))
        components.append({
            "id": int(component_id),
            "count": int(len(points)),
            "local_bbox": [int(value) for value in mins + maxs],
            "world_bbox": [int(volume.x0 + mins[0]),
                           int(volume.y0 + mins[1]),
                           int(volume.z0 + mins[2]),
                           int(volume.x0 + maxs[0]),
                           int(volume.y0 + maxs[1]),
                           int(volume.z0 + maxs[2])],
            "states": dict(states),
            "touches_survey_boundary": touches,
            "points": points,
        })
    return labels, components


def write_sha(directory: Path) -> str:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "packet.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
                        f"{path.relative_to(directory).as_posix()}")
    payload = "\n".join(rows) + "\n"
    (directory / "packet.sha256").write_text(payload, encoding="ascii")
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def diff_plan(volume: survey.Volume, selected: np.ndarray, y: int,
              anchor: tuple[int, int, int], scale: int = 6) -> Image.Image:
    layer = selected[:, y - volume.y0, :].transpose(1, 0)
    rgb = np.zeros((volume.sz, volume.sx, 3), dtype=np.uint8)
    rgb[:] = (16, 16, 22)
    rgb[layer] = (238, 55, 55)
    body = Image.fromarray(rgb, "RGB").resize(
        (volume.sx * scale, volume.sz * scale), Image.Resampling.NEAREST)
    image = Image.new("RGB", (body.width + 96, body.height + 56),
                      (16, 16, 22))
    image.paste(body, (76, 28))
    draw = ImageDraw.Draw(image)
    survey.add_grid(draw, 76, 28, volume.sx, volume.sz, scale,
                    volume.x0, volume.z0)
    ax, _ay, az = anchor
    px = 76 + (ax - volume.x0) * scale + scale // 2
    pz = 28 + (az - volume.z0) * scale + scale // 2
    draw.ellipse((px - 7, pz - 7, px + 7, pz + 7),
                 outline=(255, 255, 255), width=2)
    draw.text((76, 5), f"SELECTED COMPONENT y={y}", fill=(255, 214, 84))
    draw.text((6, image.height - 18),
              "RED = proposed component removal | PREVIEW ONLY",
              fill=(225, 225, 232))
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True)
    parser.add_argument("--anchor", nargs=3, type=int, required=True)
    parser.add_argument("--state", action="append", required=True,
                        help="Exact full block state; repeat for allow-list")
    parser.add_argument("--horizontal", type=int, default=48)
    parser.add_argument("--vertical", type=int, default=32)
    parser.add_argument("--repair-id", required=True)
    parser.add_argument("--emit", required=True)
    args = parser.parse_args()

    anchor = tuple(args.anchor)
    box = (anchor[0] - args.horizontal, anchor[0] + args.horizontal,
           anchor[1] - args.vertical, anchor[1] + args.vertical,
           anchor[2] - args.horizontal, anchor[2] + args.horizontal)
    dimension = "dimensions/projectseele/geofront"
    world_root = ROOT / "run" / "saves" / args.world / dimension
    output = ROOT / args.emit
    output.mkdir(parents=True, exist_ok=True)

    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    allowed = set(args.state)
    allowed_ids = {index for index, state in enumerate(before.states)
                   if state in allowed}
    material_mask = np.isin(before.code, list(allowed_ids))
    labels, components = six_components(material_mask, before)
    if not components:
        raise RuntimeError("no component made from the requested states")

    ax, ay, az = anchor
    ranked = []
    for component in components:
        distance = min(abs(before.x0 + x - ax)
                       + abs(before.y0 + y - ay)
                       + abs(before.z0 + z - az)
                       for x, y, z in component["points"])
        ranked.append((distance, component["id"]))
    ranked.sort()
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        raise RuntimeError("nearest component is ambiguous")
    selected_component = components[ranked[0][1]]
    if selected_component["touches_survey_boundary"]:
        raise RuntimeError("selected component touches survey boundary")

    selected = labels == selected_component["id"]
    air_id = after._state_id("minecraft:air")
    after.code[selected] = air_id
    with gzip.open(output / "block_diff.csv.gz", "wt",
                   encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("x", "y", "z", "before", "after", "change",
                         "reason"))
        for ix, iy, iz in zip(*np.nonzero(selected)):
            x, y, z = before.world_position(ix, iy, iz)
            writer.writerow((x, y, z, before.state(ix, iy, iz),
                             "minecraft:air", "removed",
                             "approved-material-component"))

    survey.output_anchor = anchor
    before_masks = before.masks()
    after_masks = after.masks()
    panels = [
        survey.iso_projection(before, before_masks, anchor, 1, 1,
                              "BEFORE +X/+Z"),
        survey.iso_projection(before, before_masks, anchor, -1, -1,
                              "BEFORE -X/-Z"),
        survey.iso_projection(after, after_masks, anchor, 1, 1,
                              "PROPOSAL +X/+Z"),
        survey.iso_projection(after, after_masks, anchor, -1, -1,
                              "PROPOSAL -X/-Z"),
    ]
    survey.combine_panels(panels, 2,
                          output / "01_before_after_same_views.png")
    levels = sorted({before.y0 + int(iy)
                     for _ix, iy, _iz in zip(*np.nonzero(selected))})
    layer_images = []
    for y in levels:
        image = diff_plan(before, selected, y, anchor)
        image.save(output / f"02_selected_y{y}.png")
        layer_images.append(image)
    if layer_images:
        layer_images[0].save(output / "02_selected_layers.pdf", "PDF",
                             save_all=True,
                             append_images=layer_images[1:], resolution=120.0)

    public_components = []
    for component in components:
        public = {key: value for key, value in component.items()
                  if key != "points"}
        public["distance_to_observation_anchor"] = int(next(
            distance for distance, component_id in ranked
            if component_id == component["id"]))
        public_components.append(public)
    manifest = {
        "repair_id": args.repair_id,
        "mode": "READ_ONLY_IN_MEMORY_COMPONENT_PREVIEW",
        "world_files_written": False,
        "source_save": args.world,
        "source_dimension": dimension,
        "observation_anchor": list(anchor),
        "observation_anchor_is_edit_target": False,
        "survey_box": list(box),
        "material_allow_list": sorted(allowed),
        "components": public_components,
        "selected_component_id": selected_component["id"],
        "selected_block_count": selected_component["count"],
        "selected_world_bbox": selected_component["world_bbox"],
        "selection_rule": "unique nearest complete six-neighbour component",
        "approval_gate": ("Evidence only. Apply requires explicit repair ID, "
                          "revision and packet hash approval."),
    }
    (output / "00_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    digest = write_sha(output)
    print(f"[preview] repair={args.repair_id} "
          f"selected={selected_component['count']} "
          f"bbox={selected_component['world_bbox']}")
    print(f"[output] {output}")
    print(f"[packet-sha] {digest}")


if __name__ == "__main__":
    main()
