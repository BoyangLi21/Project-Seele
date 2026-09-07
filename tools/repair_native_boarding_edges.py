"""Restore native MTR platform recognition and close the excess platform-to-car gap."""
import argparse,json
import regional_voxels as vox
from regional_voxels import WORLD,DIM
from query_blocks import read_box,AIR
from quality_structures import Builder,Station,OUT,OLD,load

def repair(stairs_only=False):
    vox.OUT=OUT
    old=load(WORLD/'regional_boarding_gates.json');clear=Builder()
    for gate in old['gates']:
        cells={tuple(v[:3]):v[3] for v in gate['stairs']};lo=tuple(min(p[i] for p in cells) for i in range(3));hi=tuple(max(p[i] for p in cells) for i in range(3))
        actual=read_box(WORLD,DIM,lo,hi)
        for p,expected in cells.items():
            state=actual.get(p)
            if state in AIR:continue
            if state!=expected and not (state and state.split('[')[0]==expected.split('[')[0]=='mtr:platform'):raise RuntimeError(f'Unexpected boarding cell {p}: {state}')
            clear.put(*p,'minecraft:air','retract_previous_boarding_stairs')
    if clear.ops:clear.apply('boarding_stairs_retract')
    if stairs_only:return
    p=Builder();platforms=[d for d in load(OLD/'transit_plan.json')['platforms'] if d.get('mode')!='AIRPLANE']+load(OUT/'extension_plan.json')['transit']['platforms']
    for d in platforms:Station(p,d).boarding_edges()
    p.apply('native_platform_edges')
    states=set(load(WORLD/'regional_states.json'))
    states.update(f'mtr:platform[door_type=none,facing={f},side=0]' for f in ['north','south','east','west'])
    (WORLD/'regional_states.json').write_text(json.dumps(sorted(states)),encoding='utf-8')
    (WORLD/'regional_native_platforms_ready.json').write_text(json.dumps(dict(platforms=len(platforms),edges=2*len(platforms))),encoding='utf-8')
    print('Native boarding platform edges restored',len(platforms))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--stairs-only',action='store_true');args=ap.parse_args();repair(args.stairs_only)
