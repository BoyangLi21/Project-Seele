#!/usr/bin/env python3
"""Render an exact, read-only S20 recovery proposal from a known-good save.

The script never opens an Anvil region for writing.  It loads the selected
volume twice, applies the canonical S20 phase-09/10 launch-well geometry to one
in-memory copy, and emits an auditable block diff plus matched camera views.
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


AIR = "minecraft:air"
LODESTONE = "minecraft:lodestone"
REINFORCED = "minecraft:reinforced_deepslate"
POLISHED = "minecraft:polished_deepslate"
GLASS = "minecraft:gray_stained_glass"
BASALT = "minecraft:polished_basalt[axis=y]"
LADDER = "minecraft:ladder[facing=north,waterlogged=false]"
SEA_LANTERN = "minecraft:sea_lantern"
IRON = "minecraft:iron_block"
ACCENTS = (
    "minecraft:orange_concrete",
    "minecraft:purple_concrete",
    "minecraft:red_concrete",
)

WELL_CENTRES = (-12, 30, 72)
WELL_Z = 220
BED_Y = -443
OUTER_RADIUS = 17
CLEAR_RADIUS = 15
GUIDE_OFFSET = 16
INTERFACE_HEIGHT = 72
CARRIER_DOOR_HEIGHT = 68
OBSERVATION_HEIGHT = 60

REMOVED = 1
ADDED = 2
REPLACED = 3
DIFF_COLOURS = {
    0: (16, 16, 22),
    REMOVED: (238, 55, 55),
    ADDED: (55, 225, 105),
    REPLACED: (255, 210, 55),
}


def set_state(volume: survey.Volume, x: int, y: int, z: int,
              state: str) -> None:
    if not (volume.x0 <= x <= volume.x1
            and volume.y0 <= y <= volume.y1
            and volume.z0 <= z <= volume.z1):
        raise RuntimeError(f"preview write outside surveyed box: {(x, y, z)}")
    volume.code[x - volume.x0, y - volume.y0, z - volume.z0] = \
        volume._state_id(state)


def shaft_wall(relative_y: int, dx: int, dz: int, accent: str) -> str:
    if relative_y % 32 == 0:
        return accent
    if relative_y % 8 == 0 and (dx == 0 or dz == 0):
        return SEA_LANTERN
    if abs(dx) == OUTER_RADIUS and abs(dz) == OUTER_RADIUS:
        return IRON
    return REINFORCED


def apply_phase_09_foundations(volume: survey.Volume) -> None:
    for centre_x in WELL_CENTRES:
        for dy in (-2, -1):
            for dx in range(-OUTER_RADIUS, OUTER_RADIUS + 1):
                for dz in range(-OUTER_RADIUS, OUTER_RADIUS + 1):
                    beam = dy == -2 or dx % 8 == 0 or dz % 8 == 0
                    set_state(volume, centre_x + dx, BED_Y + dy,
                              WELL_Z + dz, REINFORCED if beam else POLISHED)


def apply_phase_10_lower_shells(volume: survey.Volume) -> None:
    for variant, centre_x in enumerate(WELL_CENTRES):
        accent = ACCENTS[variant]
        set_state(volume, centre_x, BED_Y, WELL_Z, LODESTONE)
        bottom_y = BED_Y + 1
        for y in range(bottom_y, bottom_y + INTERFACE_HEIGHT + 1):
            relative_y = y - bottom_y
            for dx in range(-OUTER_RADIUS, OUTER_RADIUS + 1):
                for dz in range(-OUTER_RADIUS, OUTER_RADIUS + 1):
                    edge = max(abs(dx), abs(dz))
                    if edge <= CLEAR_RADIUS:
                        state = AIR
                    elif edge == OUTER_RADIUS:
                        carrier_door = (relative_y <= CARRIER_DOOR_HEIGHT
                                        and dz == -OUTER_RADIUS
                                        and abs(dx) <= CLEAR_RADIUS)
                        observation_window = (
                            relative_y <= OBSERVATION_HEIGHT
                            and dz == OUTER_RADIUS
                            and abs(dx) <= CLEAR_RADIUS)
                        if carrier_door:
                            state = AIR
                        elif observation_window:
                            state = GLASS
                        else:
                            state = shaft_wall(relative_y, dx, dz, accent)
                    else:
                        state = AIR
                    set_state(volume, centre_x + dx, y, WELL_Z + dz, state)

            for dx in (-GUIDE_OFFSET, GUIDE_OFFSET):
                for dz in (-GUIDE_OFFSET, GUIDE_OFFSET):
                    set_state(volume, centre_x + dx, y, WELL_Z + dz, BASALT)
            set_state(volume, centre_x, y, WELL_Z + GUIDE_OFFSET, LADDER)

        for dx in range(-OUTER_RADIUS, OUTER_RADIUS + 1):
            for dz in range(-OUTER_RADIUS, OUTER_RADIUS + 1):
                if max(abs(dx), abs(dz)) != OUTER_RADIUS:
                    continue
                carrier_aperture = dz == -OUTER_RADIUS and abs(dx) <= CLEAR_RADIUS
                if carrier_aperture:
                    state = AIR
                else:
                    state = accent if dx == 0 or dz == 0 else REINFORCED
                set_state(volume, centre_x + dx, BED_Y, WELL_Z + dz, state)


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
    x0, x1, y0, _y1, z0, z1 = box
    layer = diff[:, y - y0, :].transpose(1, 0)
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
    ax, _ay, az = anchor
    px = 76 + (ax - x0) * scale + scale // 2
    pz = 28 + (az - z0) * scale + scale // 2
    draw.ellipse((px - 7, pz - 7, px + 7, pz + 7),
                 outline=(255, 255, 255), width=2)
    draw.text((76, 5), f"{title} y={y}", fill=(255, 214, 84))
    draw.text((6, image.height - 18),
              "RED removed  GREEN added  YELLOW replaced | PREVIEW ONLY",
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
    parser.add_argument("--world", required=True,
                        help="Save directory name below run/saves")
    parser.add_argument("--emit", required=True)
    args = parser.parse_args()

    box = (-31, 89, -449, -366, 199, 241)
    anchor = (30, -408, 220)
    dimension = "dimensions/projectseele/geofront"
    world_root = ROOT / "run" / "saves" / args.world / dimension
    output = ROOT / args.emit
    output.mkdir(parents=True, exist_ok=True)
    layers_dir = output / "layers"
    layers_dir.mkdir(exist_ok=True)

    before = survey.Volume(world_root, box)
    after = survey.Volume(world_root, box)
    apply_phase_09_foundations(after)
    apply_phase_10_lower_shells(after)

    states, before_code, after_code = canonical_codes(before, after)
    changed = before_code != after_code
    roles = np.asarray([survey.role_of(state) for state in states])
    before_air = roles[before_code] == "air"
    after_air = roles[after_code] == "air"
    diff = np.zeros(changed.shape, dtype=np.uint8)
    diff[changed & ~before_air & after_air] = REMOVED
    diff[changed & before_air & ~after_air] = ADDED
    diff[changed & ~before_air & ~after_air] = REPLACED
    diff[changed & (diff == 0)] = REPLACED

    transition_counts = Counter()
    counts_by_y = Counter()
    touched = [10**9, 10**9, 10**9, -10**9, -10**9, -10**9]
    rows = 0
    with gzip.open(output / "block_diff.csv.gz", "wt",
                   encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("x", "y", "z", "before", "after", "change",
                         "proposal_source"))
        for ix, iy, iz in zip(*np.nonzero(changed)):
            x, y, z = before.world_position(ix, iy, iz)
            old = states[int(before_code[ix, iy, iz])]
            new = states[int(after_code[ix, iy, iz])]
            kind = {REMOVED: "removed", ADDED: "added",
                    REPLACED: "replaced"}[int(diff[ix, iy, iz])]
            source = "phase09_foundation" if y in (BED_Y - 2, BED_Y - 1) \
                else "phase10_lower_shell"
            writer.writerow((x, y, z, old, new, kind, source))
            transition_counts[(old, new)] += 1
            counts_by_y[y] += 1
            touched[0] = min(touched[0], x)
            touched[1] = min(touched[1], y)
            touched[2] = min(touched[2], z)
            touched[3] = max(touched[3], x)
            touched[4] = max(touched[4], y)
            touched[5] = max(touched[5], z)
            rows += 1

    levels = sorted(counts_by_y,
                    key=lambda level: (-counts_by_y[level], level))[:28]
    pages = []
    for y in sorted(levels):
        image = render_diff_plan(diff, box, y, anchor,
                                 "S20 RECOVERY PHASE 09/10")
        image.save(layers_dir / f"y{y}.png")
        pages.append(image)
    if pages:
        pages[0].save(output / "03_diff_layers.pdf", "PDF", save_all=True,
                      append_images=pages[1:], resolution=120.0)

    survey.output_anchor = anchor
    before_masks = before.masks()
    after_masks = after.masks()
    before_orthos = output / "01_before_orthos.png"
    after_orthos = output / "02_after_orthos.png"
    survey.orthographic_packet(before, before_masks,
                               survey.colour_table(before), anchor,
                               before_orthos)
    survey.orthographic_packet(after, after_masks,
                               survey.colour_table(after), anchor,
                               after_orthos)
    iso_panels = [
        survey.iso_projection(before, before_masks, anchor, 1, 1,
                              "BASE 15:07 +X/+Z"),
        survey.iso_projection(before, before_masks, anchor, -1, -1,
                              "BASE 15:07 -X/-Z"),
        survey.iso_projection(after, after_masks, anchor, 1, 1,
                              "PROPOSAL +X/+Z"),
        survey.iso_projection(after, after_masks, anchor, -1, -1,
                              "PROPOSAL -X/-Z"),
    ]
    survey.combine_panels(iso_panels, 2,
                          output / "04_before_after_same_views.png")
    survey.write_glb(after, after_masks, output / "05_after_preview.glb")

    summary = {
        "mode": "READ_ONLY_IN_MEMORY_PREVIEW",
        "world_files_written": False,
        "source_save": args.world,
        "source_dimension": dimension,
        "proposal": [
            "S20 phase 09: three launch-well two-layer foundation rafts",
            "S20 phase 10: three canonical lower pressure shells",
        ],
        "excluded": [
            "all rejected coordinate-driven field repairs (phases 11-16)",
            "pyramid/gold cleanup",
            "public lift repair",
            "observation gallery height changes",
            "personnel corridor seam changes",
            "surface cleanup replay",
        ],
        "box": list(box),
        "anchor": list(anchor),
        "changed_blocks": rows,
        "removed": int((diff == REMOVED).sum()),
        "added": int((diff == ADDED).sum()),
        "replaced": int((diff == REPLACED).sum()),
        "touched_extent": touched if rows else None,
        "changed_by_y": {str(y): counts_by_y[y]
                         for y in sorted(counts_by_y)},
        "top_transitions": [
            {"before": old, "after": new, "count": count}
            for (old, new), count in transition_counts.most_common(40)
        ],
        "implementation_contract": {
            "well_centres": [[x, BED_Y, WELL_Z] for x in WELL_CENTRES],
            "outer_radius": OUTER_RADIUS,
            "clear_radius": CLEAR_RADIUS,
            "foundation_y": [BED_Y - 2, BED_Y - 1],
            "shell_y": [BED_Y, BED_Y + 1 + INTERFACE_HEIGHT],
            "north_carrier_aperture_preserved": True,
            "south_observation_glass_preserved": True,
        },
        "approval_gate": ("Evidence only. Do not write any save until the "
                          "matched views and exact diff are approved."),
    }
    (output / "00_manifest.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    digest = write_sha(output)
    print(f"[preview] changed={rows} removed={summary['removed']} "
          f"added={summary['added']} replaced={summary['replaced']}")
    print(f"[output] {output}")
    print(f"[packet-sha] {digest}")


if __name__ == "__main__":
    main()
