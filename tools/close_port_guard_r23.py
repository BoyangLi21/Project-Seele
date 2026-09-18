"""Close the measured Port platform return outside the native rail envelope."""
import json, math
from pathlib import Path
import regional_voxels as v
from query_blocks import read_box

v.WORLD=v.ROOT/'run/saves/SEELE_R22_REVIEW'
v.OUT=v.ROOT/'artifacts/facility_r23/transit/gates/port_guard_return'
cells={(1134,y,z) for y in (95,96) for z in (468,469)}
native=json.loads((v.OUT.parent/'built2/native_final.json').read_text(encoding='utf8'))
for rail in native['curves']:
    if rail['mode']!='TRAIN':continue
    for x,y,z in rail['points']:
        if not (1131<=x<=1137 and 466<=z<=473):continue
        core={(math.floor(x+1e-6)+dx,math.floor(y+1e-6)+dy,math.floor(z+1e-6)+dz)
              for dx in (-1,0,1) for dz in (-1,0,1) for dy in range(6)}
        assert not core & cells, 'Guard intersects native train body'
b=read_box(v.WORLD,v.DIM,(1134,95,468),(1134,96,470));p=v.Painter()
for q in sorted(cells):
    assert b[q] in ('minecraft:air','projectseele:clear_glass'),(q,b[q])
    p.match((*q,*q),b[q],'projectseele:clear_glass','r23/port_platform_guard_return')
for y in (95,96):assert b[1134,y,470].startswith('mtr:apg_glass[')
p.apply('fixed_return_outside_native_rail')
path=v.WORLD/'r23_guard_cases.json';cases=json.loads(path.read_text());ids={r['id'] for r in cases}
for i,start,direction in [(0,[1134.5,95,466.5],[0,0,1]),(1,[1135.5,95,469.5],[-1,0,0])]:
    name=f'r23/port_guard_return/{i}'
    if name not in ids:cases.append(dict(id=name,start=start,direction=direction))
path.write_text(json.dumps(cases,ensure_ascii=False),encoding='utf8')
