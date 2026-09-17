"""Resolve measured rail-bed/street conflicts with graded, native-height crossings."""
import argparse,collections,gzip,heapq,json,math
import numpy as np
from scipy.spatial import cKDTree
import regional_voxels as vox
from query_blocks import AIR
from scan_regional_completion import volume
from quality_roads import envelopes

OUT=vox.ROOT/'artifacts/world_repair_r19/roads'
PAVING={'minecraft:black_concrete','minecraft:white_concrete','minecraft:gray_concrete','minecraft:light_gray_concrete','minecraft:smooth_stone','minecraft:polished_blackstone','minecraft:polished_blackstone_slab','minecraft:smooth_stone_slab','minecraft:quartz_slab','minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel'}

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();report=json.loads((OUT.parent/'global_roads/road_actual_audit.json').read_text());bad=report['bad']
    xs=[r['pos'][0] for r in bad];zs=[r['pos'][2] for r in bad];x0,x1=min(xs)-32,max(xs)+32;z0,z1=min(zs)-32,max(zs)+32
    src=np.load(vox.ROOT/'artifacts/world_quality_r02/road_surfaces.npz');ox,oz=map(int,src['origin']);sl=np.s_[z0-oz:z1-oz+1,x0-ox:x1-ox+1]
    h=src['height2'][sl].copy();mask=src['mask'][sl].copy();carriage=src['carriage'][sl];stripe=src['stripe'][sl]
    prior=np.load(OUT/'C1_street_grade/surface_contract.npz');px,pz=map(int,prior['origin'])
    ax,az=max(x0,px),max(z0,pz);bx,bz=min(x1,px+prior['after'].shape[1]-1),min(z1,pz+prior['after'].shape[0]-1)
    h[az-z0:bz-z0+1,ax-x0:bx-x0+1]=prior['after'][az-pz:bz-pz+1,ax-px:bx-px+1]
    points=np.array([v for r in json.loads((OUT.parent/'rails/current_train_samples.json').read_text()) for v in r['points']]);tree=cKDTree(points[:,[0,2]])
    with gzip.open(OUT.parent/'rails/rail_envelopes/ops.json.gz','rt') as f:ops=json.load(f)
    support={tuple(o['box'][:3]):o for o in ops if o['owner']=='r19/missing_rail_support'}
    replacements={};target=h.astype(float);queue=[];anchors=[]
    for row in bad:
        x,by,z=row['pos'];dist,index=tree.query([x+.5,z+.5]);native=points[index,1]
        for dy,state in enumerate(row['blocks'][1:],1):
            if state!='minecraft:gray_concrete':continue
            pos=(x,by+dy,z)
            if pos not in support:raise RuntimeError(('Unowned obstruction',pos))
            replacements[pos]=support[pos]['extra'][0]
        if row['type']=='head_obstruction' and dist<=1.6:
            required=math.floor(native*2+1e-6);iz,ix=z-z0,x-x0
            if required>target[iz,ix]:target[iz,ix]=required;heapq.heappush(queue,(-required,iz,ix));anchors.append([x,z,native])
    # A local max-plus envelope spreads each raised crossing along the actual
    # road graph at 10%, stopping when it meets the existing road elevation.
    while queue:
        neg,iz,ix=heapq.heappop(queue);value=-neg
        if value<target[iz,ix]-1e-7:continue
        for dz,dx in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            zz,xx=iz+dz,ix+dx
            if not(0<=zz<h.shape[0] and 0<=xx<h.shape[1]) or not mask[zz,xx]:continue
            wanted=value-.2
            if wanted>target[zz,xx]+1e-7:target[zz,xx]=wanted;heapq.heappush(queue,(-wanted,zz,xx))
    target=np.ceil(target-1e-6).astype(np.int16)
    # A nearby lower portion of a curved rail can cross the same street.
    # It constrains the approach too; propagating a high crossing alone would
    # build its ramp through that lower train envelope. Existing bridges keep
    # their separate vertical clearance; other caps never lower the old road.
    ceiling=np.full(h.shape,30000,dtype=np.int32)
    for rx,ry,rz in points:
        if ry<0 or not(x0-2<=rx<=x1+2 and z0-2<=rz<=z1+2):continue
        cx,cz=round(rx),round(rz)
        for x in range(cx-1,cx+2):
            for z in range(cz-1,cz+2):
                if not(x0<=x<=x1 and z0<=z<=z1) or not mask[z-z0,x-x0]:continue
                original=h[z-z0,x-x0]
                if original/2>=ry+6:continue
                cap=max(int(original),math.floor(ry*2+1e-6))
                ceiling[z-z0,x-x0]=min(ceiling[z-z0,x-x0],cap)
    target=envelopes(mask,np.where(mask,np.minimum(target,ceiling),30000)).astype(np.int16)
    assert np.all(target[mask]>=h[mask])
    changed=mask&(target!=h)
    if changed[0].any() or changed[-1].any() or changed[:,0].any() or changed[:,-1].any():raise RuntimeError('Crossing grade reaches survey boundary')
    plan=json.loads((vox.ROOT/'artifacts/world_quality_r02/road_plan.json').read_text(encoding='utf8'))
    pins=[e['pos'] for e in plan['entrances']]+[[q['points'][0][0],0,q['points'][0][1]] for q in plan['station_paths']]
    for x,y,z in pins:
        for xx in range(math.floor(x)-1,math.floor(x)+2):
            for zz in range(math.floor(z)-1,math.floor(z)+2):
                if x0<=xx<=x1 and z0<=zz<=z1 and changed[zz-z0,xx-x0]:raise RuntimeError(('Crossing changes a retained entrance datum',x,y,z))
    for dz,dx in ((0,1),(1,0),(1,1),(1,-1)):
        ax,bx=max(0,-dx),min(h.shape[1],h.shape[1]-dx);az,bz=0,h.shape[0]-dz
        m=mask[az:bz,ax:bx]&mask[az+dz:bz+dz,ax+dx:bx+dx]
        if np.any(m&(abs(target[az:bz,ax:bx]-target[az+dz:bz+dz,ax+dx:bx+dx])>1)):raise RuntimeError('Unwalkable crossing step')
    lo=(x0,55,z0);hi=(x1,118,z1);a,pal=volume(lo,hi);changes={};held=[]
    def put(x,y,z,new,owner):
        old=pal[int(a[y-lo[1],z-z0,x-x0])]
        if old==new:changes.pop((x,y,z),None);return
        if old.split('[')[0] not in PAVING|AIR|{'minecraft:light','minecraft:grass','minecraft:tall_grass','minecraft:fern'}:held.append([x,y,z,old,new]);return
        changes[x,y,z]=(old,new,owner)
    for pos,state in replacements.items():put(*pos,state,'r19/retire_road_obstructing_ballast')
    def finish(ix,iz):
        hh=int(target[iz,ix]);kind='line' if stripe[iz,ix] else 'road' if carriage[iz,ix] else 'walk'
        return ({'line':'minecraft:white_concrete','road':'minecraft:black_concrete','walk':'minecraft:smooth_stone'}[kind] if hh%2==0 else {'line':'minecraft:quartz_slab','road':'minecraft:polished_blackstone_slab','walk':'minecraft:smooth_stone_slab'}[kind]+'[type=bottom,waterlogged=false]')
    for iz,ix in np.argwhere(changed):
        x,z=int(ix+x0),int(iz+z0);base=(int(target[iz,ix])-1)//2;oldbase=(int(h[iz,ix])-1)//2
        for y in range(min(base,oldbase)-1,base+3):put(x,y,z,finish(ix,iz) if y==base else 'minecraft:stone' if y<base else 'minecraft:air','r19/graded_rail_street_crossing')
    for row in bad:
        if row['type']!='floor_height':continue
        x,y,z=row['pos'];put(x,y,z,finish(x-x0,z-z0),'r19/single_road_floor_gap')
    if held:raise RuntimeError(('Crossing meets retained fixtures',held[:12]))
    # Dry-run the exact proposed states against the independent native-rail
    # core definition before any world write.
    rail_intrusions=set()
    for rx,ry,rz in points:
        if ry<0 or not(x0-2<=rx<=x1+2 and z0-2<=rz<=z1+2):continue
        cx,cy,cz=round(rx),round(ry),round(rz)
        for x in range(cx-1,cx+2):
            for z in range(cz-1,cz+2):
                for y in range(cy+1,cy+5):
                    if not(lo[0]<=x<=hi[0] and lo[1]<=y<=hi[1] and lo[2]<=z<=hi[2]):continue
                    state=changes[x,y,z][1] if (x,y,z) in changes else pal[int(a[y-lo[1],z-z0,x-x0])]
                    if state.split('[')[0] not in AIR|{'minecraft:light'}:rail_intrusions.add((x,y,z,state))
    if rail_intrusions:raise RuntimeError(('Proposed road intrudes into native rail core',sorted(rail_intrusions)[:12]))
    for pos,(before,after,owner) in sorted(changes.items()):p.match((*pos,*pos),before,after,owner)
    paths=[]
    for index,(sx,sz,ex,ez,width) in enumerate(plan['segments']):
        n=max(abs(ex-sx),abs(ez-sz));run=[]
        for i in range(n+1):
            x=round(sx+(ex-sx)*i/max(1,n));z=round(sz+(ez-sz)*i/max(1,n))
            if x0<=x<=x1 and z0<=z<=z1 and mask[z-z0,x-x0]:run.append((x,z))
            elif run:break
        if not run or not any(changed[z-z0,x-x0] for x,z in run):continue
        points2=[[x+.5,int(target[z-z0,x-x0])/2,z+.5] for x,z in run[::2]]
        x,z=run[-1];points2.append([x+.5,int(target[z-z0,x-x0])/2,z+.5]);paths.append({'id':f'r19/current_rail_crossing/{index}','path':points2})
    p.meta.update(obstructing_supports=len(replacements),raised_road_columns=int(changed.sum()),native_rail_geometry_unchanged=True,native_anchors=anchors,retained_entrance_datums=True,walk_nodes=paths,native_core_intrusions=0,preferred_approach_grade=.10,maximum_quantized_adjacent_step=.5)
    p.apply('rail_street_crossings_v2') if apply else p.save_plan('rail_street_crossings_v2')
    np.savez_compressed(OUT/'rail_street_crossings_v2/surface_contract.npz',before=h,after=target,mask=mask,changed=changed,origin=[x0,z0])
    print('Road crossings',len(replacements),'old obstructions;',int(changed.sum()),'graded columns;',len(paths),'native route pairs')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
