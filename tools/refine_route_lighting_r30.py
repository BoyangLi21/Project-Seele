"""Suspend human-scale fixtures from verified high ceilings and fill measured dark gaps."""
from pathlib import Path
from collections import defaultdict
import argparse,json
import numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import iter_selected_sections,AIR
from install_facility_lighting_r30 import static_ceiling

WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/lighting_refinement';ART=OUT.parent
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();circuit=json.loads((WORLD/'facility_lighting_r30.json').read_text())
    existing=np.asarray(circuit['constant_lamps']);tree=cKDTree(existing);samples=json.loads((ART/'lighting_route_samples_all.json').read_text())
    dark={tuple(r['feet']) for r in json.loads((WORLD/'r30_lighting_review.json').read_text())['samples'] if r['visible_light']<5}
    rails=np.asarray([q for c in json.loads((WORLD/'native_transit_r26.json').read_text())['curves'] if c['mode']=='TRAIN' for q in c['points']]);rail_tree=cKDTree(rails[:,[0,2]])
    proposed={}
    for row in samples:
        x,f,z=row['feet'];roof=row['roof'];q=(x,min(roof-1,f+4),z)
        if any(abs(x-c)<=12 and -271<=z<=-209 and q[1]<=-369 and roof>=-399 for c in [-12,30,72]):continue
        if any(abs(x-c)<=16 and abs(z+36)<=16 and roof>=-411 for c in [-12,30,72]):continue
        if tree.query([x,f+1,z],p=1)[0]<=8 and (x,f,z) not in dark:continue
        if any(rails[i,1]-.2<=q[1]<=rails[i,1]+6.1 for i in rail_tree.query_ball_point([x,z],3.8)):continue
        proposed[q]=dict(pos=q,floor=f,roof=roof,route=row['route'])
    wanted=defaultdict(set);selected=defaultdict(set)
    for q,row in proposed.items():
        x,y,z=q
        for Y in range(y,row['roof']+1):selected[x//16,z//16].add(Y//16);wanted[x//16,z//16,Y//16].add((x,Y,z))
    measured={}
    for cx,cz,sy,pal,ids in iter_selected_sections(WORLD,v.DIM,selected,skip_unfinished=True):
        for q in wanted.get((cx,cz,sy),[]):
            x,y,z=q;measured[q]=pal[ids[(y-sy*16)*256+(z&15)*16+(x&15)]]
    sites=[];held=[];ops={}
    for q,row in proposed.items():
        x,y,z=q;roof=row['roof'];top=measured.get((x,roof,z),'UNKNOWN')
        if not static_ceiling(top):held.append(dict(**row,reason='ceiling changed'));continue
        if any(measured.get((x,Y,z),'UNKNOWN') not in AIR for Y in range(y,roof)):
            held.append(dict(**row,reason='occupied suspension column'));continue
        state='projectseele:nerv_ceiling_light[hanging=true,lit=true]';ops[q]=(measured[q],state)
        for Y in range(y+1,roof):ops[x,Y,z]=(measured[x,Y,z],'minecraft:chain[axis=y,waterlogged=false]')
        sites.append(row)
    for q,(old,new) in ops.items():p.match((*q,*q),old,new,'r30/interior_route_pendant')
    p.meta.update(lights=len(sites),sites=sites,held=held,clearance='Fixture underside >=3.875m over surveyed feet, static ceiling suspension, active rail gauge excluded')
    p.save_plan('interior_route_pendants');print('Pendant lights',len(sites),'held',len(held),flush=True)
    if apply:
        p.apply('interior_route_pendants');circuit['constant_lamps']+=[r['pos'] for r in sites];(WORLD/'facility_lighting_r30.json').write_text(json.dumps(circuit,indent=2));(OUT/'sites.json').write_text(json.dumps(sites,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
