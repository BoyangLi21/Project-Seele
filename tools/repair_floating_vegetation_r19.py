"""Replant isolated tree remnants clear of railways; retire detached leaf scraps."""
import argparse,json,math
from collections import Counter
import numpy as np
from scipy.ndimage import label
from scipy.spatial import cKDTree
import regional_voxels as vox
from query_blocks import AIR,read_box
from scan_regional_completion import volume

OUT=vox.ROOT/'artifacts/world_repair_r19/vegetation'
FREE=AIR|{'minecraft:grass','minecraft:fern','minecraft:tall_grass','minecraft:large_fern'}

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();report=json.loads((OUT.parent/'global_components/contact_classification.json').read_text());raw=json.loads((OUT.parent/'global_components/report.json').read_text())['candidates']
    groups=[r for r in report['groups'] if r['kind']=='isolated_vegetation'];rail=np.asarray([v for r in json.loads((OUT.parent/'rails/current_train_samples.json').read_text()) for v in r['points']]);index=cKDTree(rail[:,[0,2]])
    stations=json.loads((vox.ROOT/'artifacts/world_expansion_20260907/transit_plan.json').read_text())['platforms']
    stations+=json.loads((vox.ROOT/'artifacts/world_quality_r02/extension_plan.json').read_text())['transit']['platforms']
    stations+=json.loads((vox.ROOT/'artifacts/world_expansion_r07/port_transit_plan.json').read_text())['platforms']
    cases={c['id']:c for c in json.loads((vox.WORLD/'quality_walk_cases.json').read_text())}
    for folder in ('native_crossings_v2_pass','native_room_access_pass'):cases.update({c['id']:c for c in json.loads((OUT.parent/folder/'results.json').read_text())})
    segments=[]
    for c in cases.values():
        path=c.get('path',[c.get('start'),c.get('end')]);segments.extend(zip(path,path[1:]))
    starts=np.asarray([a for a,b in segments]);ends=np.asarray([b for a,b in segments]);seglo=np.minimum(starts,ends);seghi=np.maximum(starts,ends)
    def route_conflict(target):
        lo=target+[-.3,-1.8,-.3];hi=target+[1.3,1,1.3];near=np.all(seghi>=lo.min(0),axis=1)&np.all(seglo<=hi.max(0),axis=1)
        for a,b in zip(starts[near],ends[near]):
            delta=b-a;low=np.zeros(len(target));high=np.ones(len(target))
            for axis in range(3):
                if abs(delta[axis])<1e-9:high[(a[axis]<lo[:,axis])|(a[axis]>hi[:,axis])]=-1
                else:
                    aa=(lo[:,axis]-a[axis])/delta[axis];bb=(hi[:,axis]-a[axis])/delta[axis];low=np.maximum(low,np.minimum(aa,bb));high=np.minimum(high,np.maximum(aa,bb))
            if np.any(low<=high):return True
        return False
    occupied=set();relocated=[];retired=[];held=[]
    for number,group in enumerate(groups):
        lo,hi=group['lo'],group['hi'];b=read_box(vox.WORLD,vox.DIM,tuple(lo),tuple(hi));coords=[(x,y,z) for y in range(lo[1],hi[1]+1) for z in range(lo[2],hi[2]+1) for x in range(lo[0],hi[0]+1)]
        shape=(hi[1]-lo[1]+1,hi[2]-lo[2]+1,hi[0]-lo[0]+1);a=np.array([b[q].split('[')[0] not in AIR|{'minecraft:light','minecraft:water','projectseele:lcl'} for q in coords]).reshape(shape)
        labels,_=label(a,np.ones((3,3,3),bool));seed=np.asarray(raw[group['components'][0]]['seed'])-lo;which=labels[seed[1],seed[2],seed[0]]
        cells={coords[int(i)]:b[coords[int(i)]] for i in np.flatnonzero(labels.ravel()==which)};assert which and len(cells)==group['cells']
        logs=[q for q,s in cells.items() if s.split('[')[0].endswith('_log')]
        if not logs or len(cells)<=32:
            for q,s in cells.items():p.match((*q,*q),s,'minecraft:air','r19/detached_leaf_scraps')
            retired.append(dict(cells=len(cells),lo=lo,hi=hi));continue
        column=Counter((q[0],q[2]) for q in logs).most_common(1)[0][0];log_base=min(q[1] for q in logs if (q[0],q[2])==column)
        # Rail pruning sometimes removed the entire lower trunk. Infer the
        # root below the crown, not at its last surviving upper log, otherwise
        # moving that log to soil would bury the low leaves underground.
        leaf_base=min(q[1] for q,s in cells.items() if s.split('[')[0].endswith('_leaves'))
        root=(column[0],min(log_base,leaf_base-5),column[1]);tree=dict(cells);trunk=cells[(column[0],log_base,column[1])]
        for y in range(root[1],log_base):tree[column[0],y,column[1]]=trunk
        reach=82;low_y=max(-672,root[1]-30);high_y=min(319,log_base+24);vlo=(root[0]-reach,low_y,root[2]-reach);vhi=(root[0]+reach,high_y,root[2]+reach)
        data,palette=volume(vlo,vhi,allow_unknown=True);names=[s.split('[')[0] for s in palette];grass=np.array([n in {'minecraft:grass_block','minecraft:podzol','minecraft:moss_block'} for n in names])
        yy=np.arange(low_y,high_y+1)[:,None,None];ground=np.where(grass[data]&(yy<=log_base+8),yy,-9999).max(0);points=np.asarray(list(tree));selected=None
        for distance in (12,18,24,32,40,56,72):
            for angle in range(0,360,45):
                x=root[0]+round(distance*math.cos(math.radians(angle)));z=root[2]+round(distance*math.sin(math.radians(angle)));g=int(ground[z-vlo[2],x-vlo[0]])
                if g<low_y:continue
                offset=np.array([x-root[0],g+1-root[1],z-root[2]]);target=points+offset;tlo=target.min(0);thi=target.max(0)
                if np.any(tlo<vlo) or np.any(thi>vhi):continue
                if any(tuple(q) in occupied for q in target):continue
                if not all(names[int(data[q[1]-low_y,q[2]-vlo[2],q[0]-vlo[0]])] in FREE for q in target):continue
                # Keep canopies out of complete station/model envelopes.
                conflict=False
                for station in stations:
                    sx,sy,sz=station['center'];half=station['length']/2+14;r=20;dx,dz=(half,r) if station['heading'] in ('E','W') else (r,half)
                    if tlo[0]<=sx+dx and thi[0]>=sx-dx and tlo[2]<=sz+dz and thi[2]>=sz-dz and tlo[1]<=sy+20 and thi[1]>=sy:conflict=True;break
                if conflict:continue
                if route_conflict(target):continue
                # Examine every rail within the horizontal radius, including
                # multiple tracks at different heights; nearest-one is unsafe.
                for q,near in zip(target,index.query_ball_point(target[:,[0,2]]+.5,3.0)):
                    if any(math.floor(rail[j,1])+1<=q[1]<=math.floor(rail[j,1])+6 for j in near):conflict=True;break
                if conflict:continue
                # Roads and fixtures are already excluded by grass/air siting.
                # Require a substantial soil column below the chosen root.
                if g-2<low_y:continue
                if any(names[int(data[y-low_y,z-vlo[2],x-vlo[0]])] not in {'minecraft:grass_block','minecraft:dirt','minecraft:coarse_dirt','minecraft:stone','minecraft:podzol','minecraft:moss_block'} for y in (g,g-1,g-2)):continue
                selected=(offset,target,(x,g+1,z));break
            if selected is not None:break
        if selected is None:held.append(dict(root=root,cells=len(cells),reason='No measured free grass site within 72 m'));continue
        offset,target,newroot=selected
        for q,s in cells.items():p.match((*q,*q),s,'minecraft:air','r19/retire_floating_tree_remnant')
        for source,q in zip(points,target):
            q=tuple(map(int,q));old=palette[int(data[q[1]-low_y,q[2]-vlo[2],q[0]-vlo[0]])];p.match((*q,*q),old,tree[tuple(source)],'r19/replant_clear_of_rail');occupied.add(q)
        relocated.append(dict(source_root=root,new_root=newroot,cells=len(cells),replanted_cells=len(tree),reconstructed_trunk_cells=len(tree)-len(cells),offset=offset.tolist()))
    p.meta.update(relocations=relocated,retired_leaf_groups=retired,held=held,native_rail_clearance=True,station_envelopes_preserved=True,named_route_body_intersections=0)
    p.apply('grounded_railside_planting') if apply else p.save_plan('grounded_railside_planting')
    print('Relocated trees',len(relocated),'retired leaf groups',len(retired),'held',held,flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
