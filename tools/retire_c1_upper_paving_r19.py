"""Remove obsolete cantilevered pavement above the repaired C1 road grade."""
import argparse,json,math
import numpy as np
from scipy.spatial import cKDTree
import regional_voxels as vox
from query_blocks import read_box,AIR,iter_block_entities
from finish_fixture_supports_r19 import route_segments

OUT=vox.ROOT/'artifacts/world_repair_r19/c1_upper_paving'

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();base=np.load(vox.ROOT/'artifacts/world_quality_r02/road_surfaces.npz');h=base['height2'].copy();mask=base['mask'];ox,oz=map(int,base['origin'])
    for name in ('C1_street_grade','rail_street_crossings_v2'):
        d=np.load(OUT.parent/'roads'/name/'surface_contract.npz');px,pz=map(int,d['origin']);a=d['after'];v=h[pz-oz:pz-oz+a.shape[0],px-ox:px-ox+a.shape[1]];v[d['mask']]=a[d['mask']]
    lo=(-650,88,672);hi=(-590,98,688);b=read_box(vox.WORLD,vox.DIM,lo,hi);starts,ends=route_segments();removed=[];held=[]
    points=np.asarray([q for r in json.loads((OUT.parent/'rails/current_train_samples.json').read_text()) for q in r['points']]);tree=cKDTree(points[:,[0,2]])
    pavement={'minecraft:black_concrete','minecraft:white_concrete','minecraft:polished_blackstone','minecraft:polished_blackstone_slab','minecraft:smooth_stone','minecraft:smooth_stone_slab','minecraft:quartz_slab'}
    for q,s in b.items():
        x,y,z=q;floor=(int(h[z-oz,x-ox])-1)//2
        if not mask[z-oz,x-ox] or y<=floor+2 or s.split('[')[0] not in pavement:continue
        if any(b.get((x,yy,z),'UNKNOWN').split('[')[0] not in AIR|{'minecraft:light'} for yy in range(y+1,hi[1]+1)):held.append(dict(pos=q,reason='Supports an upper object'));continue
        # A current rail bed may legitimately sit over a lower road.
        ids=tree.query_ball_point([x+.5,z+.5],2.2)
        if any(abs(points[j,1]-(y+1))<1.6 for j in ids):held.append(dict(pos=q,reason='Current native rail support'));continue
        low=np.asarray(q)+[-.31,.49,-.31];high=np.asarray(q)+[1.31,1.02,1.31]
        possible=np.all(np.maximum(starts,ends)>=low,axis=1)&np.all(np.minimum(starts,ends)<=high,axis=1)
        assert not np.any(possible),('Named upper-level route',q)
        assert not list(iter_block_entities(vox.WORLD,vox.DIM,q,q))
        p.match((*q,*q),s,'minecraft:air','r19/retire_old_high_C1_pavement');removed.append(dict(pos=q,current_road_floor=floor,old=s))
    assert removed
    p.meta.update(removed=removed,held=held,reason='Final rendered side-view showed old pavement at Y93/94 over the commissioned Y87/88 grade; its ends were still attached to the bank',current_floor_unchanged=True,named_floor_routes_untouched=True,native_rail_beds_preserved=True)
    p.apply('old_high_road_layer') if apply else p.save_plan('old_high_road_layer')
    print('Retired high paving',len(removed),'held',held[:6])

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
