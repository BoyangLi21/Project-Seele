"""Apply the measured TV facility payload to the fresh preview, with exact rollback.

Minecraft must be closed. Only the named generated preview is writable.
The existing Anvil writer is reused; query_blocks verifies every changed
before-state and every selected after-state. Source worlds are read-only.
"""
import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import time

import nbtlib
import numpy as np

from query_blocks import read_box, dimension_dir
from transplant_s22_authority import (read_region, parse_chunk, build_region,
    decoded_sections, flush_decoded, chunk_blob)
from apply_s20_approved_semantic_repairs import parse_state, atomic_replace

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
PAYLOAD = ROOT / 'artifacts/tv_world_preview_20260906/facility_payload'
DIM = 'projectseele:geofront'


def position(cx, cz, low, offset):
    y, rest = divmod(int(offset), 256)
    z, x = divmod(rest, 16)
    return cx * 16 + x, low + y, cz * 16 + z


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    marker_path = TARGET / '.projectseele_tv_world_preview.json'
    marker = json.loads(marker_path.read_text())
    if marker.get('handed_off') or not (TARGET / 'tv_preview_terrain_generated.json').is_file():
        raise RuntimeError('Preview already handed off or fresh terrain incomplete')
    actual_generator = nbtlib.load(TARGET / 'level.dat')['Data']['WorldGenSettings']['dimensions'][DIM]['generator']
    if not bool(actual_generator.get('tv_preview', False)) or int(actual_generator['surface_datum']) != 80:
        raise RuntimeError('The saved dimension did not retain the verified TV generation profile')
    manifest = json.loads((PAYLOAD / 'manifest.json').read_text())
    print(f"Payload: {manifest['cells']} measured cells in {len(manifest['chunks'])} chunks", flush=True)
    if not args.apply and not args.verify_only:
        return
    # Java holds the save lock while running; prevent an offline/live writer race.
    import msvcrt
    lock = (TARGET / 'session.lock').open('r+b')
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    if args.verify_only:
        verify(manifest)
        return
    out = ROOT / 'artifacts/tv_world_preview_20260906' / ('transplant_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    (out / 'region_before').mkdir(parents=True)
    (out / 'inverse').mkdir()
    by_region, entities = defaultdict(list), defaultdict(list)
    for item in manifest['chunks']:
        cx, cz = item['chunk']
        by_region[cx >> 5, cz >> 5].append(item)
    for item in json.loads((PAYLOAD / 'block_entities.json').read_text()):
        x, _, z = item['position']
        entities[x >> 4, z >> 4].append(nbtlib.parse_nbt(item['snbt']))
    region_root = dimension_dir(TARGET, DIM) / 'region'
    touched, receipts = [], []
    started = time.monotonic()
    try:
        for (rx, rz), selected in sorted(by_region.items()):
            path = region_root / f'r.{rx}.{rz}.mca'
            backup = out / 'region_before' / path.name
            shutil.copy2(path, backup)
            timestamps, chunks = read_region(path)
            for item in selected:
                cx, cz = item['chunk']
                with np.load(PAYLOAD / f'c.{cx}.{cz}.npz') as payload:
                    low = int(payload['low'])
                    offsets, source_ids = payload['offsets'].copy(), payload['indices'].copy()
                    source_palette = payload['palette'].tolist()
                slot = (cx & 31) + (cz & 31) * 32
                if chunks[slot] is None:
                    raise RuntimeError(f'Fresh target chunk not generated: {cx},{cz}')
                chunk = parse_chunk(chunks[slot])
                decoded = decoded_sections(chunk)
                before = read_box(TARGET, DIM, (cx * 16, low, cz * 16),
                                  (cx * 16 + 15, item['max_y'], cz * 16 + 15))
                ys = offsets.astype(np.int32) // 256 + low
                inverse_offsets, inverse_ids, inverse_palette, inverse_lookup = [], [], [], {}
                for sy in np.unique(ys // 16).tolist():
                    active = (ys // 16) == sy
                    if sy not in decoded:
                        section = nbtlib.Compound({'Y': nbtlib.Byte(sy), 'biomes': nbtlib.Compound({
                            'palette': nbtlib.List[nbtlib.String](['projectseele:geofront_surface'])})})
                        chunk['sections'].append(section)
                        decoded[sy] = ([parse_state('minecraft:air')], np.zeros(4096, dtype=np.int32), {'minecraft:air': 0})
                    palette, indices, lookup = decoded[sy]
                    remap = []
                    for state in source_palette:
                        if state not in lookup:
                            lookup[state] = len(palette)
                            palette.append(parse_state(state))
                        remap.append(lookup[state])
                    selected_offsets = offsets[active]
                    local = (ys[active] & 15) * 256 + selected_offsets % 256
                    desired = np.asarray(remap, dtype=np.int32)[source_ids[active]]
                    changed = indices[local] != desired
                    current_names = {index: state for state, index in lookup.items()}
                    for offset, prior in zip(selected_offsets[changed].tolist(), indices[local[changed]].tolist()):
                        pos = position(cx, cz, low, offset)
                        old = current_names[prior]
                        if before.get(pos, 'minecraft:air') != old:
                            raise RuntimeError(f'Before-state mismatch at {pos}')
                        if old not in inverse_lookup:
                            inverse_lookup[old] = len(inverse_palette)
                            inverse_palette.append(old)
                        inverse_offsets.append(offset)
                        inverse_ids.append(inverse_lookup[old])
                    indices[local] = desired
                selected_offsets_set = set(offsets.tolist())

                def owned(tag):
                    if not all(k in tag for k in ('x', 'y', 'z')):
                        return False
                    x, y, z = (int(tag[k]) for k in ('x', 'y', 'z'))
                    return (x >> 4, z >> 4) == (cx, cz) and ((y - low) * 256 + (z & 15) * 16 + (x & 15)) in selected_offsets_set

                kept = [tag for tag in chunk.get('block_entities', []) if not owned(tag)]
                chunk['block_entities'] = nbtlib.List[nbtlib.Compound](kept + entities[cx, cz])
                for key in ('block_ticks', 'fluid_ticks'):
                    if key in chunk:
                        chunk[key] = nbtlib.List[nbtlib.Compound]([tag for tag in chunk[key] if not owned(tag)])
                flush_decoded(chunk, decoded)
                chunk['isLightOn'] = nbtlib.Byte(0)
                chunk.pop('Heightmaps', None)
                for section in chunk['sections']:
                    section.pop('BlockLight', None)
                    section.pop('SkyLight', None)
                chunks[slot] = chunk_blob(chunk)
                np.savez_compressed(out / 'inverse' / f'c.{cx}.{cz}.npz', low=low,
                    offsets=np.asarray(inverse_offsets, dtype=np.uint32),
                    indices=np.asarray(inverse_ids, dtype=np.uint16), palette=np.asarray(inverse_palette))
                receipts.append({'chunk': [cx, cz], 'changes': len(inverse_offsets), 'block_entities': len(entities[cx, cz])})
                if len(receipts) % 64 == 0:
                    print(f'Prepared {len(receipts)}/{len(manifest["chunks"])} target chunks ({time.monotonic() - started:.1f}s)', flush=True)
            atomic_replace(path, build_region(timestamps, chunks))
            touched.append((path, backup))
        verify(manifest)
    except Exception:
        for path, backup in touched:
            atomic_replace(path, backup.read_bytes())
        raise
    report = {'changes': sum(c['changes'] for c in receipts), 'chunks': receipts,
              'exact_readback': True, 'elapsed_seconds': time.monotonic() - started}
    (out / 'receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    marker['phase'] = 'geometry_transplanted'
    marker['geometry_receipt'] = str(out / 'receipt.json')
    marker_path.write_text(json.dumps(marker, indent=2), encoding='utf-8')
    print(f'Transplant and exact readback complete: {report["changes"]} changed cells. {out}', flush=True)


def verify(manifest):
    for number, item in enumerate(manifest['chunks']):
        cx, cz = item['chunk']
        with np.load(PAYLOAD / f'c.{cx}.{cz}.npz') as p:
            low, offsets, ids, palette = int(p['low']), p['offsets'], p['indices'], p['palette']
            cells = read_box(TARGET, DIM, (cx * 16, low, cz * 16),
                             (cx * 16 + 15, item['max_y'], cz * 16 + 15))
            for offset, value in zip(offsets.tolist(), ids.tolist()):
                pos = position(cx, cz, low, offset)
                if cells.get(pos, 'minecraft:air') != str(palette[value]):
                    raise RuntimeError(f'Payload readback mismatch at {pos}')
        if (number + 1) % 128 == 0:
            print(f'Verified {number + 1}/{len(manifest["chunks"])} target chunks', flush=True)


if __name__ == '__main__':
    main()
