"""Restore confirmed R23 frame-retirement cuts; inventory the full passenger deck."""
from pathlib import Path
import argparse,json,math,collections,numpy as np
import regional_voxels as v
from query_blocks import read_box,AIR

ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/station_decks'
def main(apply=False):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    source=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))
    native=json.loads((WORLD/'native_transit_r23.json').read_text(encoding='utf8'))
    rail=set()
    for curve in native['curves']:
        if curve['mode']!='TRAIN' or curve['points'][0][1]<0:continue
        for x,y,z in curve['points']:
            X,Y,Z=math.floor(x+1e-6),math.floor(y+1e-6),math.floor(z+1e-6)
            for dx in (-1,0,1):
                for dz in (-1,0,1):
                    for dy in range(-1,6):rail.add((X+dx,Y+dy,Z+dz))
    transfer=set()
    for route in source['transfer_links']:
        if route['id'].endswith('/return'):continue
        axisx=abs(route['path'][0][0]-route['path'][-1][0])>abs(route['path'][0][2]-route['path'][-1][2])
        for X,Y,Z in route['path']:
            X,Y,Z=map(math.floor,(X,Y,Z))
            for dx in ([0] if axisx else range(-4,5)):
                for dz in (range(-4,5) if axisx else [0]):
                    for yy in range(Y-3,Y+5):transfer.add((X+dx,yy,Z+dz))
    repaired=[];unexpected=[];grid=[];routes=[]
    for station in source['stations']:
        x,y,z=station['center'];h=station['half'];g=station['ground'];rise=y-g;u0=-h+5;hor=station['horizontal'];dx,dz=(h+2,19) if hor else (19,h+2)
        b=read_box(WORLD,v.DIM,(x-dx,y-3,z-dz),(x+dx,y+4,z+dz))
        at=lambda u,Y,w:(x+u,Y,z+w) if hor else (x+w,Y,z+u)
        plats=[q for q in native['platforms'] if q['id'] in station['platform_ids']]
        edge=int(round(max(abs(((q['position1']['z']+q['position2']['z'])/2-z) if hor else ((q['position1']['x']+q['position2']['x'])/2-x)) for q in plats)))+2
        for side in (-1,1):
            up,down=(-15,-11) if side<0 else (10,14);low,high=min(up,down),max(up,down)+1
            for u in range(-h+1,h):
                for absolute_w in range(edge+1,17):
                    w=side*absolute_w;q=at(u,y,w)
                    if u0-1<=u<=u0+rise and low<=w<=high:continue
                    if q in rail or q in transfer:continue
                    if any(b.get(at(u,Y,w),'').startswith('mtr:escalator_step') for Y in range(y-2,y+1)):continue
                    grid.append(dict(id=f"r24/deck/{station['platform_ids'][0]}/{u}/{w}",feet=[q[0]+.5,y+1,q[2]+.5]))
                    if b[q] not in AIR:continue
                    if abs(w)!=15:
                        unexpected.append(dict(station=station['station'],line=station['line'],pos=q,state=b[q]));continue
                    for Y in range(y-2,y+1):
                        qq=at(u,Y,w);old=b[qq]
                        if old not in AIR:continue
                        new='minecraft:smooth_stone' if Y==y else 'minecraft:light_gray_concrete'
                        p.match((*qq,*qq),old,new,'r24/restore_deck_through_retired_frame_strip');repaired.append(dict(pos=qq,station=station['station'],line=station['line'],before=old,after=new))
            # Traverse every repaired strip beyond the documented stairwell.
            a=at(u0+rise+7,y+1,side*15);bpos=at(h-3,y+1,side*15)
            key=f"r24/deck_strip/{station['platform_ids'][0]}/{side}"
            routes += [dict(id=key,start=[a[0]+.5,a[1],a[2]+.5],end=[bpos[0]+.5,bpos[1],bpos[2]+.5])]
    p.meta.update(repaired=repaired,unexpected_floor_gaps=unexpected,passenger_deck_points=grid,walk_nodes=routes,
                  root_cause='R23 old-frame deletion crossed the new platform deck at lateral offset +/-15; source generator now preserves its three deck layers.')
    p.save_plan('restore_retired_frame_deck_strips')
    if apply:
        assert not unexpected,('Inspect other floor openings before application',unexpected[:12]);p.apply('restore_retired_frame_deck_strips')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
    print('Restore cells',len(repaired),'full passenger deck probes',len(grid),'other gaps',len(unexpected))
    if unexpected:print(unexpected[:16])
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
