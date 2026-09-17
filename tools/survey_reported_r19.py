"""Cold baseline and measured volumes for the owner's September 17 defect reports."""
from pathlib import Path
import argparse, collections, datetime, hashlib, json, msvcrt, shutil
import numpy as np
from query_blocks import AIR
from scan_regional_completion import volume

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / 'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
OUT = ROOT / 'artifacts/world_repair_r19'
POINTS = {
    'surface_rail_valley': (-602, 103, 682),
    'shore_join': (510, 55, 360),
    'arrival_station_trees': (-306, -466, 774),
    'command_escalator': (26, -403, 258),
    'dogma_floating_signs': (12, -566, 278),
    'dogma_lift': (14, -566, 256),
    'pyramid_hangar_link': (105, -448, 252),
    'hangar_south_link': (116, -442, -16),
    'hangar_station': (93, -442, -41),
    'hangar_upper_link': (107, -395, -98),
}


def baseline():
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = OUT / 'baseline.json'
    if receipt.exists():
        print('Existing cold baseline:', json.loads(receipt.read_text())['backup'])
        return
    backup = ROOT / 'backups' / ('SEELE_R19_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    assert backup.resolve().is_relative_to((ROOT / 'backups').resolve())
    with (WORLD / 'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        shutil.copytree(WORLD, backup, ignore=shutil.ignore_patterns('session.lock'))
        retained = {}
        for rel in (
            'src/main/resources/assets/projectseele/animations/eva_unit01.animation.json',
            'src/main/resources/assets/projectseele/geo/eva_unit00.geo.json',
            'src/main/resources/assets/projectseele/geo/eva_unit02.geo.json',
        ):
            retained[rel] = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        data = {'world': str(WORLD), 'backup': str(backup), 'user_files': retained,
                'reported_points': POINTS, 'created': datetime.datetime.now().isoformat()}
        receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
    print('Cold backup complete:', backup, flush=True)


def survey():
    folder = OUT / 'reported_before'
    folder.mkdir(parents=True, exist_ok=True)
    for name, point in POINTS.items():
        x, y, z = point
        lo, hi = (x-14, y-10, z-14), (x+14, y+10, z+14)
        a, pal = volume(lo, hi)
        counts = collections.Counter({s: int((a == i).sum()) for i, s in enumerate(pal)})
        np.savez_compressed(folder / (name + '.npz'), blocks=a, palette=np.asarray(pal), bounds=[lo, hi])
        lines = [name + ' ' + str(point), 'Rows: Z increasing downward. Columns: X increasing rightward.']
        symbols = {}
        def symbol(state):
            if state.split('[')[0] in AIR: return '.'
            if state.startswith('minecraft:water'): return '~'
            if 'lcl' in state: return 'L'
            if state not in symbols:
                symbols[state] = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@#$%&*+'[len(symbols) % 69]
            return symbols[state]
        for yy in (y-2, y-1, y, y+1, y+3, y+6):
            lines.append('\nY=' + str(yy))
            for zz in range(lo[2], hi[2]+1):
                lines.append(f'{zz:5} ' + ''.join(symbol(pal[int(a[yy-lo[1], zz-lo[2], xx-lo[0]])]) for xx in range(lo[0], hi[0]+1)))
        lines.extend('\n' + char + ' = ' + state for state, char in symbols.items())
        (folder / (name + '.txt')).write_text('\n'.join(lines), encoding='utf8')
        (folder / (name + '.json')).write_text(json.dumps({'point': point, 'bounds': [lo, hi], 'census': counts}, indent=2), encoding='utf8')
        print(name, 'states=', len(pal), 'special=', {s:n for s,n in counts.items() if any(k in s for k in ('mtr:', 'moving', 'sign', 'chair', 'leaves', '_log', 'button'))}, flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['baseline', 'survey'])
    action = ap.parse_args().action
    baseline() if action == 'baseline' else survey()
