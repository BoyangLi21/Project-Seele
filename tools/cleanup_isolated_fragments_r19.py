"""Remove verified air-isolated soil and obsolete C1 asphalt fragments only."""
import argparse,gzip,json,math
from collections import defaultdict
from itertools import product
import numpy as np
from scipy.ndimage import label,generate_binary_structure
from scipy.spatial import cKDTree
import regional_voxels as vox
from query_blocks import AIR,read_box,iter_selected_sections
from scan_world_components_r19 import WATER

OUT=vox.ROOT/'artifacts/world_repair_r19/global_cleanup'
SOURCE=OUT.parent/'global_components'

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter()
    with gzip.open(SOURCE/'isolated_soil_points.json.gz','rt') as f:soil=json.load(f)
    selected={tuple(r['pos']):(r['state'],'r19/isolated_soil_fragment') for r in soil}
    raw=json.loads((SOURCE/'report.json').read_text())['candidates'];groups=json.loads((SOURCE/'contact_classification.json').read_text())['groups']
    retired=[]
    grade=np.load(OUT.parent/'roads/rail_street_crossings_v2/surface_contract.npz');gx,gz=map(int,grade['origin'])
    rails=np.asarray([v for r in json.loads((OUT.parent/'rails/current_train_samples.json').read_text()) for v in r['points']]);rail_index=cKDTree(rails[:,[0,2]])
    for group in groups:
        if group['kind']!='isolated_structure' or not set(group['states'])<={'minecraft:black_concrete','minecraft:white_concrete'}:continue
        lo,hi=group['lo'],group['hi']
        if not(-780<=lo[0]<=hi[0]<=-400 and 610<=lo[2]<=hi[2]<=715 and 75<=lo[1]<=hi[1]<=120):continue
        cells={}
        for index in group['components']:
            r=raw[index];lo,hi=r['lo'],r['hi'];b=read_box(vox.WORLD,vox.DIM,tuple(lo),tuple(hi))
            shape=(hi[1]-lo[1]+1,hi[2]-lo[2]+1,hi[0]-lo[0]+1);coords=[(x,y,z) for y in range(lo[1],hi[1]+1) for z in range(lo[2],hi[2]+1) for x in range(lo[0],hi[0]+1)]
            solid=np.array([b[q].split('[')[0] not in AIR|WATER|{'minecraft:light'} for q in coords]).reshape(shape);labels,_=label(solid,generate_binary_structure(3,1));x,y,z=np.asarray(r['seed'])-lo;code=labels[y,z,x]
            indices=np.flatnonzero(labels.ravel()==code);assert code and len(indices)==r['cells']
            cells.update({coords[int(i)]:b[coords[int(i)]] for i in indices})
        # These pieces are several metres above the commissioned pavement,
        # have no connections at either end, and are not part of its floor.
        checked=[]
        for (x,y,z),state in cells.items():
            if 0<=z-gz<grade['mask'].shape[0] and 0<=x-gx<grade['mask'].shape[1] and grade['mask'][z-gz,x-gx]:checked.append(y-grade['after'][z-gz,x-gx]/2)
        if checked and min(checked)<1.5:continue
        if not checked:
            # Stale strips can lie completely outside today's road mask.
            # Limit this retirement to the measured C1 engineering corridor,
            # where they float well above the retained native railway.
            q=np.asarray(list(cells));distance,nearest=rail_index.query(q[:,[0,2]]+.5)
            if np.max(distance)>6.5 or np.min(q[:,1]-rails[nearest,1])<2:continue
        selected.update({q:(state,'r19/retired_detached_asphalt') for q,state in cells.items()});retired.append(group)
    sections=defaultdict(set)
    for x,y,z in selected:
        for cx in range((x-1)//16,(x+1)//16+1):
            for cz in range((z-1)//16,(z+1)//16+1):sections[cx,cz].update(range((y-1)//16,(y+1)//16+1))
    cache={(cx,cz,sy):(pal,a) for cx,cz,sy,pal,a in iter_selected_sections(vox.WORLD,vox.DIM,sections)}
    def state(q):
        x,y,z=q;pal,a=cache[x//16,z//16,y//16];return pal[int(a[((y&15)<<8)|((z&15)<<4)|(x&15)])]
    for q,(before,owner) in selected.items():
        assert state(q)==before,('Fragment changed since scan',q)
        for dx,dy,dz in product((-1,0,1),repeat=3):
            neighbour=(q[0]+dx,q[1]+dy,q[2]+dz)
            if neighbour in selected:continue
            if state(neighbour).split('[')[0] not in AIR|{'minecraft:light'}:raise RuntimeError(('Fragment acquired an external contact',q,neighbour,state(neighbour)))
    # A named walking route must never lose its support, even if its platform
    # is an isolated part of an older architectural assembly.
    paths={c['id']:c for c in json.loads((vox.WORLD/'quality_walk_cases.json').read_text())}
    paths.update({c['id']:c for c in json.loads((OUT.parent/'native_crossings_v2_pass/results.json').read_text())})
    by_chunk=defaultdict(list)
    for q in selected:by_chunk[q[0]//16,q[2]//16].append(q)
    for case in paths.values():
        path=case.get('path',[case.get('start'),case.get('end')])
        for aa,bb in zip(path,path[1:]):
            a=np.asarray(aa,float);b=np.asarray(bb,float);delta=b-a;near=[]
            for cx in range(math.floor((min(a[0],b[0])-.3)/16),math.floor((max(a[0],b[0])+.3)/16)+1):
                for cz in range(math.floor((min(a[2],b[2])-.3)/16),math.floor((max(a[2],b[2])+.3)/16)+1):near.extend(by_chunk.get((cx,cz),()))
            for q in near:
                lo=np.asarray(q)+[-.3,.85,-.3];hi=np.asarray(q)+[1.3,1.2,1.3];low,high=0.,1.
                for axis in range(3):
                    if abs(delta[axis])<1e-9:
                        if not lo[axis]<=a[axis]<=hi[axis]:high=-1;break
                    else:
                        t=sorted(((lo[axis]-a[axis])/delta[axis],(hi[axis]-a[axis])/delta[axis]));low=max(low,t[0]);high=min(high,t[1])
                if low<=high:raise RuntimeError(('Named route uses fragment as a floor',case['id'],q))
    for q,(before,owner) in sorted(selected.items()):p.match((*q,*q),before,'minecraft:air',owner)
    p.meta.update(isolated_soil_cells=len(soil),retired_asphalt_cells=sum(r['cells'] for r in retired),retired_asphalt_groups=retired,
        confirmed_no_26_neighbour_contacts=True,named_route_floor_intersections=0,all_other_structures_preserved=True)
    p.apply('verified_isolated_fragments') if apply else p.save_plan('verified_isolated_fragments')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
