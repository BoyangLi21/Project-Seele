"""Cache actual facility volumes and identify detached natural leftovers above GeoFront floor."""
import json
from collections import Counter
import numpy as np
from scipy.ndimage import label,find_objects
from scan_regional_completion import volume
from regional_voxels import ROOT
OUT=ROOT/'artifacts/world_refinement_r08/facilities';OUT.mkdir(parents=True,exist_ok=True)
AREAS={'pyramid':((-94,-477,203),(154,-286,451)),'hangar':((-55,-514,-151),(162,-336,14)),'shafts':((-33,-348,-57),(94,88,-14)),'dogma':((-39,-631,242),(100,-528,405))}
report={}
for name,(lo,hi) in AREAS.items():
    a,p=volume(lo,hi);np.savez_compressed(OUT/(name+'_before.npz'),blocks=a,palette=np.array(p),lo=lo,hi=hi)
    naturals=np.array([s.split('[')[0] in {'minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:stone','minecraft:deepslate'} for s in p])[a]
    if name in ('hangar','pyramid'):naturals[:max(0,-477-lo[1])]=False
    components,n=label(naturals);items=[]
    for i,box in enumerate(find_objects(components),1):
        size=int((components[box]==i).sum())
        if size:items.append(dict(cells=size,lo=[box[2].start+lo[0],box[0].start+lo[1],box[1].start+lo[2]],hi=[box[2].stop-1+lo[0],box[0].stop-1+lo[1],box[1].stop-1+lo[2]]))
    report[name]=dict(natural_cells=int(naturals.sum()),components=sorted(items,key=lambda x:-x['cells'])[:100])
    if name=='hangar':
        profiles={}
        for x,z in [(-12,-100),(30,-100),(72,-100),(-30,-100),(90,-100),(30,-140),(30,-56),(110,-100)]:
            c=a[:,z-lo[2],x-lo[0]];profiles[str((x,z))]=[(int(y+lo[1]),p[int(i)]) for y,i in enumerate(c) if y==0 or i!=c[y-1]]
        report[name]['columns']=profiles
    print(name,'natural',int(naturals.sum()),'largest',report[name]['components'][:6],flush=True)
(OUT/'survey.json').write_text(json.dumps(report,indent=2),encoding='utf8')
