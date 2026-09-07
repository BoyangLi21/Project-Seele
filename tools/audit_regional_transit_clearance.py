"""Check native MTR swept corridors against actual saved blocks, using query_blocks."""
from collections import defaultdict,Counter
import json
import numpy as np
from query_blocks import iter_selected_sections,AIR
from regional_voxels import WORLD,OUT,DIM


def free(state):
    name=state.split('[')[0]
    return name in AIR or name=='minecraft:light' or name.endswith(('_button','_sign','_torch')) or name=='minecraft:torch'


def mark(masks,x0,y0,z0,x1,y1,z1):
    for cx in range(x0//16,x1//16+1):
        for cz in range(z0//16,z1//16+1):
            for sy in range(y0//16,y1//16+1):
                key=(cx,cz,sy)
                if key not in masks:masks[key]=np.zeros((16,16,16),dtype=bool)
                masks[key][max(y0-sy*16,0):min(y1-sy*16+1,16),max(z0-cz*16,0):min(z1-cz*16+1,16),max(x0-cx*16,0):min(x1-cx*16+1,16)]=True


def main():
    samples=json.loads((OUT/'transit2/track_samples.json').read_text(encoding='utf-8'))
    rails={};selected=defaultdict(set)
    for rail in samples:
        masks={};floor={};plane=rail['mode']=='AIRPLANE';r=17 if plane else 1
        for p in rail['points'][::2 if plane else 1]:
            x,y,z=map(round,p);mark(masks,x-r,y+(2 if plane else 1),z-r,x+r,y+(10 if plane else 4),z+r)
            if not plane:mark(floor,x,y-3,z,x,y-1,z)
        rails[rail['id']]=(masks,floor)
        for cx,cz,sy in masks.keys()|floor.keys():selected[cx,cz].add(sy)
    measured={}
    for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected):measured[cx,cz,sy]=(pal,idx.reshape(16,16,16))
    result=[]
    for name,(masks,floors) in rails.items():
        collisions=Counter();unsupported=0;examples=[]
        for key,mask in masks.items():
            if key not in measured:raise RuntimeError(f'Unmeasured railway envelope {name} {key}')
            pal,a=measured[key];bad=mask & ~np.asarray([free(s) for s in pal])[a]
            if not bad.any():continue
            values,counts=np.unique(a[bad],return_counts=True);collisions.update({pal[v]:int(c) for v,c in zip(values,counts)})
            if len(examples)<12:
                cx,cz,sy=key
                for y,z,x in np.argwhere(bad)[:3]:examples.append([cx*16+int(x),sy*16+int(y),cz*16+int(z),pal[a[y,z,x]]])
        if floors:
            definition=next(r for r in samples if r['id']==name)
            for x,y,z in {tuple(map(round,v)) for v in definition['points']}:
                supported=False
                for yy in range(y-3,y):
                    pal,a=measured[x//16,z//16,yy//16]
                    supported|=not free(pal[a[yy&15,z&15,x&15]])
                if not supported:
                    unsupported+=1
                    if len(examples)<12:examples.append([x,y-1,z,'no bed within three metres'])
        result.append(dict(id=name,obstructed_cells=sum(collisions.values()),unsupported_center_cells=unsupported,states=dict(collisions),examples=examples))
        if collisions or unsupported:print('CLEARANCE FAIL',name,sum(collisions.values()),unsupported,examples[:2],flush=True)
    report=dict(rails=len(result),passed=sum(r['obstructed_cells']==0 and r['unsupported_center_cells']==0 for r in result),results=result,
        envelope='TRAIN: centre +/-1, y+1..4; AIRPLANE: +/-17 square, y+2..10 sampled every 2m (overlapping conservative wing envelopes)')
    (OUT/'transit_clearance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('TRANSIT CLEARANCE',report['passed'],'/',len(result),flush=True)


if __name__=='__main__':main()
