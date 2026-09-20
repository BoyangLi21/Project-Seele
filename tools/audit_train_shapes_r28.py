"""Whole-network clearance using measured collision boxes, not opaque block cubes."""
from pathlib import Path
from collections import defaultdict,Counter
import json,math,numpy as np
from scipy.spatial import cKDTree
from query_blocks import iter_selected_sections,AIR
import regional_voxels as v
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/train_shapes'

def main():
    OUT.mkdir(parents=True,exist_ok=True);native=json.loads((WORLD/'native_transit_r28.json').read_text());points=[];selected=defaultdict(set)
    rails=[r for r in native['curves'] if r['mode']=='TRAIN']
    for rail in rails:
        a=np.asarray(rail['points'])
        for p,q in zip(a,a[1:]):
            for t in (0,.25,.5,.75):points.append(p+(q-p)*t)
        points.append(a[-1])
        for x,y,z in a:
            x,y,z=map(math.floor,(x,y,z))
            for cx in range((x-2)//16,(x+2)//16+1):
                for cz in range((z-2)//16,(z+2)//16+1):selected[cx,cz].update(range(y//16,(y+6)//16+1))
    points=np.asarray(points);tree=cKDTree(points[:,[0,2]]);shapes=json.loads((WORLD/'native_collision_shapes.json').read_text());fail=[];counts=Counter();samples=0
    for cx,cz,sy,pal,indices in iter_selected_sections(WORLD,v.DIM,selected,skip_unfinished=True):
        for pid,state in enumerate(pal):
            if state.split('[')[0] in AIR|{'minecraft:light'}:continue
            key=state.replace(',propagate_property=0','');boxes=shapes.get(key,[[0,0,0,1,1,1]])
            if not boxes:continue
            for i in np.flatnonzero(indices==pid):
                q=np.array([cx*16+(int(i)&15),sy*16+(int(i)>>8),cz*16+((int(i)>>4)&15)],float)
                ids=tree.query_ball_point(q[[0,2]]+.5,2.1)
                if not ids:continue
                candidates=points[ids];candidates=candidates[(candidates[:,1]+.05<q[1]+1)&(candidates[:,1]+5.5>q[1])]
                if not len(candidates):continue
                samples+=1;hit=None
                for box in boxes:
                    low=q+box[:3];high=q+box[3:];dx=np.maximum(np.maximum(low[0]-candidates[:,0],candidates[:,0]-high[0]),0);dz=np.maximum(np.maximum(low[2]-candidates[:,2],candidates[:,2]-high[2]),0)
                    mask=(dx*dx+dz*dz<1.10**2)&(candidates[:,1]+.05<high[1])&(candidates[:,1]+5.5>low[1])
                    if mask.any():hit=candidates[np.flatnonzero(mask)[0]].tolist();break
                if hit is not None:counts[state]+=1;fail.append(dict(position=q.astype(int).tolist(),state=state,rail=hit))
    report=dict(passed=not fail,rails=len(rails),curve_samples=len(points),candidate_collision_blocks=samples,collisions=len(fail),states=dict(counts),items=fail,scope='Actual block collision boxes against dense native train-centre paths, 1.10m lateral radius and 5.5m body clearance; thin platform panels retain their real shapes')
    (OUT/'report.json').write_text(json.dumps(report,indent=2));print('Precise train sweep',len(rails),'rails',len(fail),'collisions',dict(counts),flush=True)

if __name__=='__main__':main()
