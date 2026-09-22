"""Sample actual registered interior routes, including gaps far from any new light."""
from pathlib import Path
from collections import defaultdict
import json,math,sys
import numpy as np
from query_blocks import iter_selected_sections,AIR
from install_facility_lighting_r30 import static_ceiling

ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R30_WORLD';REVIEW=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';ART=ROOT/'artifacts/facility_r30'
routes=json.loads((WORLD/'quality_walk_cases.json').read_text());points={}
for case in routes:
    path=case.get('path') or [case.get('start'),case.get('end')]
    if not all(p is not None for p in path):continue
    for aa,bb in zip(path,path[1:]):
        a,b=np.asarray(aa,float),np.asarray(bb,float)
        if abs(a[1]-b[1])>8:continue
        for q in np.linspace(a,b,max(2,math.ceil(np.linalg.norm(b-a)/12)+1)):
            if abs(q[1]-round(q[1]))>.05:continue
            x,y,z=map(math.floor,q);key=(x//12,y,z//12)
            points.setdefault(key,{'feet':[x,y,z],'route':case['id']})
selected=defaultdict(set);wanted=defaultdict(set)
for row in points.values():
    x,y,z=row['feet']
    for Y in range(y-1,min(319,y+17)+1):selected[x//16,z//16].add(Y//16);wanted[x//16,z//16,Y//16].add((x,Y,z))
observed={}
for cx,cz,sy,palette,indices in iter_selected_sections(WORLD,'projectseele:geofront',selected,skip_unfinished=True):
    for q in wanted.get((cx,cz,sy),[]):
        x,y,z=q;observed[q]=palette[indices[(y-sy*16)*256+(z&15)*16+(x&15)]]
covered=[]
for row in points.values():
    x,y,z=row['feet']
    if not static_ceiling(observed.get((x,y-1,z),'UNKNOWN')):continue
    if observed.get((x,y,z)) not in AIR or observed.get((x,y+1,z)) not in AIR:continue
    roof=next((Y for Y in range(y+3,min(319,y+17)+1) if static_ceiling(observed.get((x,Y,z),'UNKNOWN'))),None)
    if roof is None:continue
    if 6<=x<=52 and 272<=z<=365 and -445<=y<=-406:continue
    row=dict(row,roof=roof);covered.append(row)
covered.sort(key=lambda r:(r['feet'][0]//16,r['feet'][2]//16,r['feet'][1]))
(ART/'lighting_route_samples_all.json').write_text(json.dumps(covered,ensure_ascii=False,indent=2),encoding='utf8')
# Full set remains available; a bounded native pass samples every area deterministically.
stride=max(1,math.ceil(len(covered)/800));chosen=covered[::stride]
(REVIEW/'r30_lighting_samples.json').write_text(json.dumps(chosen,ensure_ascii=False,indent=2),encoding='utf8')
print('Interior route candidates',len(covered),'native samples',len(chosen),'stride',stride)
