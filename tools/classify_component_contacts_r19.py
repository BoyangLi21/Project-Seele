"""Distinguish real air gaps from diagonal voxel joints in the global 3D audit."""
from collections import Counter,defaultdict
from itertools import product
import gzip,json
import numpy as np
from scipy.ndimage import label,generate_binary_structure
from query_blocks import iter_selected_sections,AIR
from regional_voxels import ROOT,WORLD,DIM
from scan_world_components_r19 import WATER,SOIL

OUT=ROOT/'artifacts/world_repair_r19/global_components'

def main():
    candidates=json.loads((OUT/'report.json').read_text())['candidates'];selected=defaultdict(set)
    for r in candidates:
        lo=np.asarray(r['lo'])-1;hi=np.asarray(r['hi'])+1
        for cx in range(lo[0]//16,hi[0]//16+1):
            for cz in range(lo[2]//16,hi[2]//16+1):selected[int(cx),int(cz)].update(range(int(lo[1]//16),int(hi[1]//16)+1))
    cache={(cx,cz,sy):(pal,idx) for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected)}
    def state(p):
        x,y,z=map(int,p);pal,a=cache[x//16,z//16,y//16];return pal[int(a[((y&15)<<8)|((z&15)<<4)|(x&15)])]
    def solid(s):return s.split('[')[0] not in AIR|WATER|{'minecraft:light'}
    owned={};materials=[];sets=[]
    for index,r in enumerate(candidates):
        lo=np.asarray(r['lo']);hi=np.asarray(r['hi']);shape=(int(hi[1]-lo[1]+1),int(hi[2]-lo[2]+1),int(hi[0]-lo[0]+1))
        coords=[(x,y,z) for y in range(int(lo[1]),int(hi[1])+1) for z in range(int(lo[2]),int(hi[2])+1) for x in range(int(lo[0]),int(hi[0])+1)]
        values=[state(p) for p in coords];a=np.array([solid(s) for s in values]).reshape(shape);groups,n=label(a,generate_binary_structure(3,1))
        sx,sy,sz=np.asarray(r['seed'])-lo;group=int(groups[sy,sz,sx]);assert group
        indices=np.flatnonzero(groups.ravel()==group);assert len(indices)==r['cells'],('World changed since scan',r)
        cells=[];counts=Counter()
        for offset in indices:
            p=coords[int(offset)];assert p not in owned;owned[p]=index;cells.append(p);counts[values[int(offset)]]+=1
        sets.append(cells);materials.append(counts)
        if index%200==0:print('Reidentified components',index,'/',len(candidates),flush=True)
    parent=list(range(len(candidates)));touch=set();wet=set();evidence=defaultdict(list)
    def find(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    offsets=[p for p in product((-1,0,1),repeat=3) if p!=(0,0,0)]
    for p,index in owned.items():
        for dx,dy,dz in offsets:
            q=(p[0]+dx,p[1]+dy,p[2]+dz)
            if q in owned:
                a,b=find(index),find(owned[q])
                if a!=b:parent[b]=a
                continue
            s=state(q)
            if solid(s):
                if abs(dx)+abs(dy)+abs(dz)==1:raise RuntimeError(('Global six-connected audit missed a solid neighbour',p,q,s))
                touch.add(index)
                if len(evidence[index])<3:evidence[index].append(dict(pos=q,state=s))
            elif s.split('[')[0] in WATER:wet.add(index)
    groups=defaultdict(list)
    for i in range(len(candidates)):groups[find(i)].append(i)
    result=[];points=[]
    for indices in groups.values():
        counts=sum((materials[i] for i in indices),Counter());base={s.split('[')[0] for s in counts}
        soil=all(n in SOIL or n.endswith('_ore') for n in base)
        vegetation=all(n.endswith(('_leaves','_log')) or n in {'minecraft:grass','minecraft:fern','minecraft:tall_grass','minecraft:vine'} for n in base)
        kind='edge_connected_to_world' if any(i in touch for i in indices) else 'fluid_contact' if any(i in wet for i in indices) else 'isolated_soil' if soil else 'isolated_vegetation' if vegetation else 'isolated_structure'
        row=dict(kind=kind,components=indices,cells=sum(candidates[i]['cells'] for i in indices),states=dict(counts),
            lo=np.min([candidates[i]['lo'] for i in indices],axis=0).tolist(),hi=np.max([candidates[i]['hi'] for i in indices],axis=0).tolist(),
            contacts=[e for i in indices for e in evidence[i]][:6]);result.append(row)
        if kind=='isolated_soil':
            points.extend(dict(pos=p,state=state(p),component=index) for index in indices for p in sets[index])
    summary=Counter()
    for r in result:summary[r['kind']]+=r['cells']
    report=dict(world=str(WORLD),source='report.json',verified_six_connected_components=len(candidates),groups=sorted(result,key=lambda r:(r['kind'],-r['cells'])),cells_by_class=dict(summary),
        interpretation='Diagonal edge/corner contact is retained for voxelized slopes and architectural shells. Only isolated_soil has no solid or fluid contact in any of the 26 neighbouring positions.')
    (OUT/'contact_classification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    with gzip.open(OUT/'isolated_soil_points.json.gz','wt',encoding='utf8') as f:json.dump(points,f)
    print('Contact classification',dict(summary),flush=True)

if __name__=='__main__':main()
