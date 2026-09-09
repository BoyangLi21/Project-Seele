"""Separate actual surface holes from the inward stair-step void, and isolate old Dogma geometry."""
import json,math
import numpy as np
from scipy.ndimage import label,find_objects
import regional_voxels as v
from query_blocks import AIR
OUT=v.ROOT/'artifacts/world_refinement_r09'
def components(mask,lo):
    a,n=label(mask);rows=[]
    for i,b in enumerate(find_objects(a),1):
        size=int((a[b]==i).sum())
        if size:rows.append(dict(cells=size,lo=[b[2].start+lo[0],b[0].start+lo[1],b[1].start+lo[2]],hi=[b[2].stop-1+lo[0],b[0].stop-1+lo[1],b[1].stop-1+lo[2]]))
    return sorted(rows,key=lambda x:-x['cells'])
d=np.load(OUT/'pyramid_before.npz');a=d['blocks'];pal=d['palette'];lo=d['lo'];hi=d['hi'];y,z,x=np.ogrid[lo[1]:hi[1]+1,lo[2]:hi[2]+1,lo[0]:hi[0]+1]
r=np.floor(120*(1-(y+466)/172)+.5);ring=(y>=-466)&(y<=-294)&(abs(x-30)<=r)&(abs(z-327)<=r)&((abs(x-30)==r)|(abs(z-327)==r))
missing=ring&np.array([s in AIR for s in pal])[a]
report=dict(outer_ring_cells=int(ring.sum()),outer_ring_missing=int(missing.sum()),openings=components(missing,lo))
np.savez_compressed(OUT/'outer_ring.npz',mask=ring,missing=missing,lo=lo,hi=hi)
print('TRUE OUTER RING',report['outer_ring_cells'],report['outer_ring_missing'],report['openings'][:10],flush=True)
import refine_eva_world_r04 as old
p=v.Painter();old.dogma(p);old.junctions(p)
d=np.load(OUT/'dogma_before.npz');a=d['blocks'];pal=d['palette'];lo=d['lo'];hi=d['hi'];desired=np.full(a.shape,65535,np.uint16);codes={};names=[]
for op in p.ops:
    x0,y0,z0,x1,y1,z1=op.box
    x0=max(x0,int(lo[0]));y0=max(y0,int(lo[1]));z0=max(z0,int(lo[2]));x1=min(x1,int(hi[0]));y1=min(y1,int(hi[1]));z1=min(z1,int(hi[2]))
    if x0>x1 or y0>y1 or z0>z1:continue
    if op.state not in codes:codes[op.state]=len(names);names.append(op.state)
    desired[y0-lo[1]:y1-lo[1]+1,z0-lo[2]:z1-lo[2]+1,x0-lo[0]:x1-lo[0]+1]=codes[op.state]
for keep in p.keep_boxes:
    x0,y0,z0,x1,y1,z1=keep['box'];x0=max(x0,int(lo[0]));y0=max(y0,int(lo[1]));z0=max(z0,int(lo[2]));x1=min(x1,int(hi[0]));y1=min(y1,int(hi[1]));z1=min(z1,int(hi[2]));desired[y0-lo[1]:y1-lo[1]+1,z0-lo[2]:z1-lo[2]+1,x0-lo[0]:x1-lo[0]+1]=65535
aircodes=[i for i,s in enumerate(names) if s in AIR];extra=np.isin(desired,aircodes)&np.array([s not in AIR and s.split('[')[0] not in ('minecraft:light','minecraft:water','projectseele:lcl') for s in pal])[a]
report['dogma_unexpected_in_open_space']=components(extra,lo)
report['dogma_unexpected_materials']={str(pal[int(i)]):int(n) for i,n in zip(*np.unique(a[extra],return_counts=True))}
np.savez_compressed(OUT/'dogma_expected.npz',desired=desired,desired_palette=np.array(names),unexpected=extra,lo=lo,hi=hi)
(OUT/'legacy_geometry_analysis.json').write_text(json.dumps(report,indent=2,default=int),encoding='utf8')
print('DOGMA UNEXPECTED',int(extra.sum()),report['dogma_unexpected_in_open_space'][:10],flush=True)
