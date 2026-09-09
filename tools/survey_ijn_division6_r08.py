"""Locate the imported destroyer builds using the existing saved-block reader."""
from pathlib import Path
from collections import Counter
import json,numpy as np
from query_blocks import iter_selected_sections,AIR

ROOT=Path(__file__).resolve().parents[1]
WORLD=ROOT/'external-assets/work/ships/nekoseal_division6/Destroyer Division 6'
OUT=ROOT/'artifacts/world_refinement_r08/ships';OUT.mkdir(exist_ok=True)
selected={}
for p in (WORLD/'region').glob('r.*.*.mca'):
    _,rx,rz,_=p.name.split('.');rx,rz=int(rx),int(rz)
    for cx in range(rx*32,rx*32+32):
        for cz in range(rz*32,rz*32+32):selected[cx,cz]=set(range(0,16))
natural=AIR|{'minecraft:water','minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:bedrock','minecraft:sand','minecraft:gravel','minecraft:deepslate','minecraft:seagrass','minecraft:tall_seagrass','minecraft:kelp','minecraft:kelp_plant'}
points=[];counts=Counter();sections=0
for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,'minecraft:overworld',selected,skip_unfinished=True):
    keep=np.array([s.split('[')[0] not in natural for s in pal])[idx].reshape(16,16,16)
    if not keep.any():continue
    xyz=np.argwhere(keep)[:,[2,0,1]]+[cx*16,sy*16,cz*16];points.append(xyz.astype(np.int32))
    a,c=np.unique(idx.reshape(16,16,16)[keep],return_counts=True);counts.update({pal[int(i)]:int(n) for i,n in zip(a,c)});sections+=1
all_points=np.concatenate(points);np.savez_compressed(OUT/'authored_points.npz',xyz=all_points)
columns=np.unique(all_points[:,[0,2]],axis=0);lo=columns.min(0);hi=columns.max(0)
from scipy.ndimage import label,find_objects
mask=np.zeros(tuple(hi-lo+1),bool);mask[tuple((columns-lo).T)]=True
components,n=label(mask);objects=find_objects(components);items=[]
for i,s in enumerate(objects,1):
    size=int((components[s]==i).sum())
    if size>=50:items.append(dict(columns=size,x=[int(s[0].start+lo[0]),int(s[0].stop-1+lo[0])],z=[int(s[1].start+lo[1]),int(s[1].stop-1+lo[1])]))
report=dict(source=str(WORLD),bounds=[all_points.min(0).tolist(),all_points.max(0).tolist()],voxels=len(all_points),components=sorted(items,key=lambda x:-x['columns']),states=dict(counts))
(OUT/'source_survey.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='states'},indent=2),flush=True)
