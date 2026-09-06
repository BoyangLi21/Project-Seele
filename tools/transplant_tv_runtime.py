"""Restore stable authored actors and controllers after the TV geometry transplant.

Keep all canonical EVA/plug UUIDs at the same coordinates. Select one standby
pilot per station and one Lilith, and exclude retired block-lift text labels.
No old terrain, map-generation jobs or LOD databases are copied.
"""
from collections import Counter, defaultdict
import copy
from datetime import datetime
import json
import math
from pathlib import Path
import shutil

import nbtlib

from transplant_s22_authority import read_region, parse_chunk, build_region, chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'run/saves/SEELE_PYRAMID_TV_PREVIEW_20260905'
TARGET = ROOT / 'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
REL = Path('dimensions/projectseele/geofront')
OUT = ROOT / 'artifacts/tv_world_preview_20260906'


def uuid(entity):
    return tuple(int(v) for v in entity.get('UUID', []))


def identities(entity):
    yield uuid(entity)
    for passenger in entity.get('Passengers', []):
        yield from identities(passenger)


def main():
    marker_path = TARGET / '.projectseele_tv_world_preview.json'
    marker = json.loads(marker_path.read_text())
    if marker['phase'] != 'geometry_transplanted' or marker.get('handed_off'):
        raise RuntimeError('Runtime requires the verified, not-yet-activated preview')
    import msvcrt
    lock = (TARGET / 'session.lock').open('r+b')
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    out = OUT / ('runtime_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir()
    manifest = json.loads((OUT / 'facility_payload/manifest.json').read_text())
    boxes = [b for _, b in manifest['boxes']]
    fleet = nbtlib.load(SOURCE / 'data/projectseele_eva_fleet.dat')['data']['Fleet']
    canonical = {tuple(int(v) for v in e['Canonical']) for e in fleet}
    plugs = {tuple(int(v) for v in e['EntryPlug']) for e in fleet}
    if any(str(e['Phase']) != 'PARKED' for e in fleet):
        raise RuntimeError('Source fleet is active; preserve it before migration')
    chosen, omitted, seen_slots, found_ids = [], Counter(), set(), set()
    source_regions = {(cx >> 5, cz >> 5) for item in manifest['chunks'] for cx, cz in [item['chunk']]}
    for rx, rz in sorted(source_regions):
        path = SOURCE / REL / 'entities' / f'r.{rx}.{rz}.mca'
        if not path.is_file() or path.stat().st_size == 0:
            continue
        _, chunks = read_region(path)
        for blob in chunks:
            if blob is None:
                continue
            for entity in parse_chunk(blob).get('Entities', []):
                ident = str(entity.get('id'))
                x, y, z = (float(v) for v in entity['Pos'])
                inside = any(a <= x < d + 1 and b <= y < e + 1 and c <= z < f + 1
                             for a, b, c, d, e, f in boxes)
                if not inside:
                    omitted['outside_authored_envelopes'] += 1
                    continue
                if any(str(t).startswith('projectseele.s20.lift.') for t in entity.get('Tags', [])):
                    omitted['retired_lift_text_label'] += 1
                    continue
                if not (ident.startswith('projectseele:') or ident in {
                        'minecraft:armor_stand', 'minecraft:item_frame', 'minecraft:glow_item_frame',
                        'minecraft:text_display', 'minecraft:block_display', 'minecraft:item_display'}):
                    omitted['natural_or_unrelated_actor'] += 1
                    continue
                if 'eva_unit' in ident and uuid(entity) not in canonical:
                    omitted['noncanonical_eva'] += 1
                    continue
                slot = (ident, round(x, 2), round(y, 2), round(z, 2))
                if ident in {'projectseele:lilith', 'projectseele:training_pilot'} and slot in seen_slots:
                    omitted['duplicate_' + ident] += 1
                    continue
                ids = set(identities(entity))
                if ids & found_ids:
                    raise RuntimeError('Overlapping entity UUIDs in selected runtime')
                seen_slots.add(slot)
                found_ids.update(ids)
                chosen.append(copy.deepcopy(entity))
    if not canonical <= found_ids or not plugs <= found_ids:
        raise RuntimeError('Canonical fleet/entry-plug identity missing from selected actors')
    if sum(str(e['id']) == 'projectseele:lilith' for e in chosen) != 1:
        raise RuntimeError('Expected exactly one contained Lilith')
    by_chunk = defaultdict(list)
    for entity in chosen:
        x, _, z = (float(v) for v in entity['Pos'])
        by_chunk[math.floor(x) >> 4, math.floor(z) >> 4].append(entity)
    by_region = defaultdict(dict)
    for (cx, cz), entities in by_chunk.items():
        by_region[cx >> 5, cz >> 5][(cx & 31) + (cz & 31) * 32] = chunk_blob(nbtlib.File({
            'DataVersion': nbtlib.Int(3465), 'Position': nbtlib.IntArray([cx, cz]),
            'Entities': nbtlib.List[nbtlib.Compound](entities)}))
    entity_dir = TARGET / REL / 'entities'
    entity_dir.mkdir(parents=True, exist_ok=True)
    for (rx, rz), additions in by_region.items():
        path = entity_dir / f'r.{rx}.{rz}.mca'
        if path.exists():
            shutil.copy2(path, out / path.name)
            if path.stat().st_size == 0:
                timestamps, chunks = bytes(4096), [None] * 1024
            else:
                timestamps, chunks = read_region(path)
        else:
            timestamps, chunks = bytes(4096), [None] * 1024
        for index, blob in additions.items():
            # This is a fresh generated preview, so retain any native actors
            # in the chunk while adding only the selected authored actors.
            if chunks[index] is not None:
                root = parse_chunk(blob)
                root['Entities'].extend(parse_chunk(chunks[index]).get('Entities', []))
                blob = chunk_blob(root)
            chunks[index] = blob
        atomic_replace(path, build_region(timestamps, chunks))
    copied_data = []
    for relative in [Path('data'), REL / 'data']:
        (TARGET / relative).mkdir(parents=True, exist_ok=True)
        for path in (SOURCE / relative).glob('*.dat'):
            if not (path.name.startswith('projectseele_') or path.name in {'capabilities.dat', 'an_redstone_signals.dat'}):
                continue
            if path.name == 'projectseele_s20_physical_elevators_v1.dat':
                continue  # obsolete integer-cabin fault states
            destination = TARGET / relative / path.name
            if destination.exists():
                backup = out / relative / path.name
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
            shutil.copy2(path, destination)
            copied_data.append(str(relative / path.name))
    for name in ['.projectseele_s20_rebuild.json', '.projectseele_command_sliding_doors_r01.json',
                 '.projectseele_lift_sliding_doors_r01.json']:
        if (SOURCE / name).is_file():
            shutil.copy2(SOURCE / name, TARGET / name)
    report = {'retained': dict(Counter(str(e['id']) for e in chosen)), 'omitted': dict(omitted),
              'canonical_eva_ids_preserved': len(canonical), 'entry_plug_ids_preserved': len(plugs),
              'copied_saved_data': copied_data, 'entity_roots': len(chosen),
              'terrain_and_lod_caches_copied': False}
    (out / 'receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    marker['phase'] = 'runtime_transplanted'
    marker['runtime_receipt'] = str(out / 'receipt.json')
    marker_path.write_text(json.dumps(marker, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
