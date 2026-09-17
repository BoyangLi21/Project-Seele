"""Resolve measured orphan lamps and incomplete suspended architectural fixtures.

Road fixtures are moved off the complete road mask, rail envelope and every
registered pedestrian route. Ceiling suspension is attached to measured roofs.
"""
import argparse,json,math
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree
import regional_voxels as vox
from query_blocks import AIR,read_box

OUT=vox.ROOT/'artifacts/world_repair_r19/fixture_supports'
ROD='minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]'
FREE=AIR|{'minecraft:light','minecraft:grass','minecraft:fern','minecraft:tall_grass'}
GROUND={'minecraft:smooth_stone','minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:coarse_dirt','minecraft:polished_blackstone','minecraft:polished_basalt','minecraft:gray_concrete','minecraft:light_gray_concrete','projectseele:nerv_floor_panel'}
ROOF={'minecraft:black_concrete','minecraft:gray_concrete','minecraft:light_gray_concrete','minecraft:white_concrete','minecraft:iron_block','minecraft:iron_bars','minecraft:smooth_stone','projectseele:nerv_structural_panel','projectseele:nerv_floor_panel','projectseele:nerv_wall_panel'}

def route_segments():
    cases={c['id']:c for c in json.loads((vox.WORLD/'quality_walk_cases.json').read_text())}
    for folder in ('native_crossings_v2_pass','native_room_access_pass'):
        cases.update({c['id']:c for c in json.loads((OUT.parent/folder/'results.json').read_text())})
    pairs=[]
    for c in cases.values():
        path=c.get('path',[c.get('start'),c.get('end')]);pairs.extend(zip(path,path[1:]))
    return np.asarray([a for a,b in pairs]),np.asarray([b for a,b in pairs])

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();rows=json.loads((OUT.parent/'global_components/contact_classification.json').read_text())['groups']
    starts,ends=route_segments();slo=np.minimum(starts,ends);shi=np.maximum(starts,ends)
    rail=np.asarray([q for r in json.loads((OUT.parent/'rails/current_train_samples.json').read_text()) for q in r['points']]);tree=cKDTree(rail[:,[0,2]])
    roads=np.load(vox.ROOT/'artifacts/world_quality_r02/road_surfaces.npz');mask=roads['mask'];ox,oz=map(int,roads['origin'])
    def inroad(x,z):return 0<=z-oz<mask.shape[0] and 0<=x-ox<mask.shape[1] and bool(mask[z-oz,x-ox])
    def conflict(points):
        q=np.asarray(points,float);lo=q+[-.35,-1.9,-.35];hi=q+[1.35,1,1.35]
        near=np.all(shi>=lo.min(0),axis=1)&np.all(slo<=hi.max(0),axis=1)
        for a,b in zip(starts[near],ends[near]):
            delta=b-a;low=np.zeros(len(q));high=np.ones(len(q))
            for ax in range(3):
                if abs(delta[ax])<1e-9:high[(a[ax]<lo[:,ax])|(a[ax]>hi[:,ax])]=-1
                else:
                    aa=(lo[:,ax]-a[ax])/delta[ax];bb=(hi[:,ax]-a[ax])/delta[ax];low=np.maximum(low,np.minimum(aa,bb));high=np.minimum(high,np.maximum(aa,bb))
            if np.any(low<=high):return True
        for a,ids in zip(q,tree.query_ball_point(q[:,[0,2]]+.5,3.3)):
            if any(math.floor(rail[j,1])<=a[1]<=math.floor(rail[j,1])+7 for j in ids):return True
        return False
    mounted=[];lamps=[];held=[];retired=[];occupied=set();vertical_done=set()
    for r in rows:
        if r['kind']!='isolated_structure':continue
        names={s.split('[')[0] for s in r['states']};lo,hi=r['lo'],r['hi']
        islamp=lo[1]>60 and names<={'minecraft:sea_lantern','minecraft:smooth_stone_slab','minecraft:polished_basalt'}
        issuspended=names in ({'minecraft:polished_blackstone_slab'},{'projectseele:nerv_strip_light'})
        if not(islamp or issuspended):continue
        old=read_box(vox.WORLD,vox.DIM,tuple(lo),tuple(hi));cells={q:s for q,s in old.items() if s in r['states']}
        if len(cells)!=r['cells']:held.append(dict(bounds=[lo,hi],reason='Candidate changed after scan'));continue
        if islamp:
            x,y,z=lo;sourcefloor=y-(6 if 'minecraft:sea_lantern' in names else 7)
            if 'minecraft:polished_basalt' in names:sourcefloor=hi[1]-7
            radius=12;b=read_box(vox.WORLD,vox.DIM,(x-radius,sourcefloor-4,z-radius),(x+radius,hi[1]+4,z+radius));chosen=None
            offsets=sorted(((dx,dz) for dx in range(-radius,radius+1) for dz in range(-radius,radius+1)),key=lambda q:(q[0]**2+q[1]**2,q))
            for dx,dz in offsets:
                xx,zz=x+dx,z+dz
                if inroad(xx,zz) or (xx,zz) in occupied:continue
                if not any(inroad(xx+ax,zz+az) for ax,az in ((-1,0),(1,0),(0,-1),(0,1))):continue
                ys=[yy for yy in range(sourcefloor-3,sourcefloor+3) if b[xx,yy,zz].split('[')[0] in GROUND]
                if not ys:continue
                g=max(ys)
                if g+7>hi[1]+4:continue
                points=[(xx,yy,zz) for yy in range(g+1,g+7)]
                if any(b[q].split('[')[0] not in FREE and q not in cells for q in points):continue
                if conflict(points):continue
                # The arm projects toward the street but remains above clearance.
                dx0,dz0=x-xx,z-zz;facing=('east' if dx0>0 else 'west') if abs(dx0)>abs(dz0) else ('south' if dz0>0 else 'north')
                ax,az={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[facing]
                neighbour=(xx+ax,g+6,zz+az)
                if neighbour not in b or b[neighbour].split('[')[0] not in FREE:continue
                chosen=(xx,g,zz,points,facing);break
            if chosen is None:
                if names=={'minecraft:smooth_stone_slab'} and len(cells)==1:
                    for q,s in cells.items():p.match((*q,*q),s,'minecraft:air','r19/retire_cap_of_previously_removed_lamp')
                    retired.append(dict(bounds=[lo,hi],reason='Only nonfunctional old lamp cap remains over a transport junction'));continue
                held.append(dict(bounds=[lo,hi],reason='No clear roadside location within 12 blocks'));continue
            xx,g,zz,points,facing=chosen
            for q,s in cells.items():p.match((*q,*q),s,'minecraft:air','r19/retire_orphan_lamp_head')
            for q in points:
                state=ROD if q[1]<g+6 else f'projectseele:street_light_head[facing={facing}]'
                p.match((*q,*q),'minecraft:air' if q in cells else b[q],state,'r19/grounded_tokyo_style_street_light')
            occupied.add((xx,zz));lamps.append(dict(source=[lo,hi],base=[xx,g,zz],head=[xx,g+6,zz],facing=facing))
        else:
            # These are existing light banks / room ceiling baffles; never make
            # a ground post through a room to support an overhead fixture.
            if lo[1]!=hi[1]:
                x,_,z=lo
                if names=={'projectseele:nerv_strip_light'} and x in (4,14,46,56) and z in (-46,-26):
                    if (x,z) in vertical_done:continue
                    b=read_box(vox.WORLD,vox.DIM,(x,-443,z),(x,-351,z));assert b[x,-443,z] in {'projectseele:nerv_floor_panel','projectseele:nerv_structural_panel'}
                    qs=[q for q,s in b.items() if s.split('[')[0] in FREE]
                    assert all(s.split('[')[0] in FREE|{'projectseele:nerv_strip_light','projectseele:nerv_floor_panel','projectseele:nerv_structural_panel'} for s in b.values())
                    if conflict(qs):raise RuntimeError(('Guide-light support crosses a route',x,z))
                    for q in qs:p.match((*q,*q),b[q],ROD,'r19/grounded_interlane_guide_light_mast')
                    mounted.append(dict(bounds=[[x,-443,z],[x,-351,z]],rods=qs));vertical_done.add((x,z));continue
                held.append(dict(bounds=[lo,hi],reason='Not a horizontal ceiling fixture'));continue
            qsorted=sorted(cells);anchors=[qsorted[1] if len(qsorted)>4 else qsorted[0]]
            if len(qsorted)>2:anchors.append(qsorted[-2] if len(qsorted)>4 else qsorted[-1])
            b=read_box(vox.WORLD,vox.DIM,tuple(lo),(hi[0],hi[1]+5,hi[2]));supports=[];ok=True
            for x,y,z in anchors:
                roof=next((yy for yy in range(y+1,y+6) if b[x,yy,z].split('[')[0] in ROOF),None)
                if roof is None:ok=False;break
                qs=[(x,yy,z) for yy in range(y+1,roof)]
                if any(b[q].split('[')[0] not in FREE for q in qs) or qs and conflict(qs):ok=False;break
                supports.extend(qs)
            if not ok:held.append(dict(bounds=[lo,hi],reason='No unobstructed measured ceiling attachment'));continue
            for q in supports:p.match((*q,*q),b[q],ROD,'r19/ceiling_fixture_suspension')
            mounted.append(dict(bounds=[lo,hi],rods=supports))
    p.meta.update(road_lamps=lamps,ceiling_fixtures=mounted,retired_nonfunctional_caps=retired,held=held,road_mask_intersections=0,named_path_body_intersections=0,rail_envelope_intersections=0,
        references=['https://www.kensetsu.metro.tokyo.lg.jp/road/iji_syuzen','https://www.tokyo-airport-bldg.co.jp/files/news_release/1414_0310_1100.pdf'])
    p.apply('grounded_lights_and_baffles') if apply else p.save_plan('grounded_lights_and_baffles')
    print('Road lamps',len(lamps),'ceiling fixtures',len(mounted),'held',len(held),Counter(h['reason'] for h in held))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
