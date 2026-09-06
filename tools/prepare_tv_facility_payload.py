"""Read current authored facility volumes, including room air, into a local payload.

Uses query_blocks as the sole world-block reader. No world is changed here.
The new world's terrain is generated independently; only these named envelopes
and their block entities may be transplanted at the original coordinates.
"""
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np

from query_blocks import read_box, iter_block_entities

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'run/saves/SEELE_PYRAMID_TV_PREVIEW_20260905'
OUT = ROOT / 'artifacts/tv_world_preview_20260906/facility_payload'
DIM = 'projectseele:geofront'
BOXES = [
    ('accepted-pyramid-and-TV-interior', (-68, -468, 207, 159, -273, 400)),
    ('wet-cages-observation-and-transfer-plant', (-38, -500, 122, 104, -370, 241)),
    ('terminal-dogma-interior', (-32, -600, 220, 96, -520, 370)),
    ('command-lift-and-landing-stack', (8, -568, 249, 16, -314, 261)),
    ('public-surface-lift', (123, -443, 265, 137, 89, 281)),
    ('eva-00-launch-line', (-30, -500, 202, 6, 89, 238)),
    ('eva-01-launch-line', (12, -500, 202, 48, 89, 238)),
    ('eva-02-launch-line', (54, -500, 202, 90, 89, 238)),
    ('existing-moving-city-baseline', (-194, 79, -4, 254, 239, 444)),
]


def main():
    if OUT.exists():
        raise RuntimeError(f'Payload already exists; keep its evidence: {OUT}')
    OUT.mkdir(parents=True)
    atlas = json.loads((ROOT / 'artifacts/map_understanding/S20-R27-SEMANTIC-PRESERVE-ATLAS-READONLY/01_preserve_masks.json').read_text())
    boxes = list(BOXES)
    for item in atlas['masks']:
        for x0, x1, y0, y1, z0, z1 in item.get('boxes', []):
            boxes.append((item['mask_id'], (x0, y0, z0, x1, y1, z1)))
    chunks = sorted({(cx, cz) for _, (x0, y0, z0, x1, y1, z1) in boxes
                     for cx in range(x0 >> 4, (x1 >> 4) + 1)
                     for cz in range(z0 >> 4, (z1 >> 4) + 1)})
    report, counts, block_entities = [], Counter(), []
    started = time.monotonic()
    for number, (cx, cz) in enumerate(chunks):
        selected = [b for _, b in boxes if b[0] >> 4 <= cx <= b[3] >> 4 and b[2] >> 4 <= cz <= b[5] >> 4]
        low, high = min(b[1] for b in selected), max(b[4] for b in selected)
        mask = np.zeros((high - low + 1, 16, 16), dtype=bool)
        for x0, y0, z0, x1, y1, z1 in selected:
            mask[y0 - low:y1 - low + 1,
                 max(0, z0 - cz * 16):min(16, z1 - cz * 16 + 1),
                 max(0, x0 - cx * 16):min(16, x1 - cx * 16 + 1)] = True
        lo, hi = (cx * 16, low, cz * 16), (cx * 16 + 15, high, cz * 16 + 15)
        cells = read_box(SOURCE, DIM, lo, hi)
        palette, palette_lookup, indices = [], {}, []
        offsets = np.flatnonzero(mask).astype(np.uint32)
        for offset in offsets.tolist():
            yy, rem = divmod(offset, 256)
            zz, xx = divmod(rem, 16)
            pos = (cx * 16 + xx, low + yy, cz * 16 + zz)
            if pos not in cells:
                raise RuntimeError(f'Unmeasured authored source cell {pos}')
            state = cells[pos]
            if state not in palette_lookup:
                palette_lookup[state] = len(palette)
                palette.append(state)
            indices.append(palette_lookup[state])
            counts[state.split('[')[0]] += 1
        for pos, tag in iter_block_entities(SOURCE, DIM, lo, hi):
            if mask[pos[1] - low, pos[2] - cz * 16, pos[0] - cx * 16]:
                block_entities.append({'position': pos, 'snbt': tag.snbt()})
        np.savez_compressed(OUT / f'c.{cx}.{cz}.npz', low=np.int32(low), offsets=offsets,
                            palette=np.asarray(palette), indices=np.asarray(indices, dtype=np.uint16))
        report.append({'chunk': [cx, cz], 'min_y': low, 'max_y': high,
                       'cells': len(indices), 'palette': len(palette)})
        if (number + 1) % 64 == 0:
            print(f'Prepared {number + 1}/{len(chunks)} source chunks ({time.monotonic() - started:.1f}s)', flush=True)
    (OUT / 'block_entities.json').write_text(json.dumps(block_entities, indent=2), encoding='utf-8')
    (OUT / 'manifest.json').write_text(json.dumps({'source': str(SOURCE),
        'boxes': boxes, 'chunks': report, 'cells': sum(r['cells'] for r in report),
        'block_entities': len(block_entities), 'top_states': counts.most_common(35),
        'source_terrain_outside_envelopes': 'excluded', 'coordinate_transform': [0, 0, 0],
        'elapsed_seconds': time.monotonic() - started}, indent=2), encoding='utf-8')
    print(f'Payload complete: {len(report)} chunks, {len(block_entities)} block entities.', flush=True)


if __name__ == '__main__':
    main()
