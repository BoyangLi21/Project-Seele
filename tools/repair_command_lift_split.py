"""Restore the exact 84-cell split-cabin incident observed on 2026-09-06.

The healthy R28 cabin is the reference. This refuses any different damage
pattern, never replaces a whole region with another world's region, and backs
up the touched region plus the elevator capability before an explicit --apply.
Run with Minecraft closed. Default is a read-only plan.
"""
import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

from query_blocks import read_box, dimension_dir
from apply_s20_approved_semantic_repairs import Change, rewrite_region, atomic_replace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'run/saves/SEELE_S20_RECOVERY_R28'
DIM = 'projectseele:geofront'
LO, HI = (10, -567, 251), (14, -405, 255)
EXPECTED = '80398029ecfac2632189c187fd69f2d68b22e9d5ca00bab746459856ccd82d6f'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world', required=True, choices=[
        'SEELE_LIFT_REVIEW_PREVIEW_20260906',
        'SEELE_PYRAMID_TV_PREVIEW_20260905'])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    world = ROOT / 'run/saves' / args.world
    healthy = read_box(SOURCE, DIM, LO, HI)
    current = read_box(world, DIM, LO, HI)
    patch = sorted([{'pos': list(p), 'before': current[p], 'after': s}
                    for p, s in healthy.items() if current[p] != s],
                   key=lambda c: tuple(c['pos']))
    if not patch:
        print('Cabin already matches the healthy R28 reference; no writes.')
        return
    digest = hashlib.sha256(json.dumps(patch, sort_keys=True).encode()).hexdigest()
    if len(patch) != 84 or digest != EXPECTED:
        raise RuntimeError(f'Unrecognized incident/reference; refusing repair: {len(patch)} cells, {digest}')
    print(f'Exact incident verified: {len(patch)} cells in the 5x5 car shaft.')
    if not args.apply:
        return
    out = ROOT / 'artifacts/command_lift_recovery_20260906' / (
        args.world + '_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True, exist_ok=False)
    dim = dimension_dir(world, DIM)
    region = dim / 'region/r.0.0.mca'
    for path in [region, dim / 'data/capabilities.dat']:
        shutil.copy2(path, out / path.name)
    (out / 'forward_patch.json').write_text(json.dumps(patch, indent=2), encoding='utf-8')
    (out / 'inverse_patch.json').write_text(json.dumps([
        {**c, 'before': c['after'], 'after': c['before']} for c in patch
    ], indent=2), encoding='utf-8')
    by_chunk = defaultdict(list)
    for c in patch:
        x, y, z = c['pos']
        by_chunk[x >> 4, z >> 4].append(Change(
            'command-lift-split-20260906', x, y, z, c['before'], c['after'],
            'restore', 'Restore the measured whole R28 cabin after overlapping-source capture'))
    atomic_replace(region, rewrite_region(region, by_chunk))
    result = read_box(world, DIM, LO, HI)
    assert result == healthy, 'Exact shaft readback failed'
    (out / 'receipt.json').write_text(json.dumps({
        'world': str(world), 'reference': str(SOURCE), 'cells': 84,
        'patch_sha256': digest, 'verified': True,
        'capabilities_changed': False,
        'region_after_sha256': hashlib.sha256(region.read_bytes()).hexdigest()
    }, indent=2), encoding='utf-8')
    print(f'Repaired and verified. Backup and inverse patch: {out}')


if __name__ == '__main__':
    main()
