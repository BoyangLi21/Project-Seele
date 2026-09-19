"""Measured period fixtures in the already authorised station envelopes.

Do not alter tracks, boarding doors, stairs, existing furniture, or any route.
The model's full height, a real backing/floor, and its front approach are checked.
"""
from pathlib import Path
import argparse,json,math,nbtlib,numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,AIR

ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/stations'
FLOORS={'minecraft:smooth_stone','minecraft:light_gray_concrete','minecraft:polished_andesite','minecraft:stone_bricks','projectseele:nerv_floor_panel','projectseele:nerv_structural_panel'}
BACKING={'minecraft:light_gray_concrete','minecraft:green_concrete','minecraft:orange_concrete','projectseele:nerv_machine_panel','projectseele:nerv_structural_panel','projectseele:nerv_wall_panel'}
def main(apply=False):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    records=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['stations']
    paths=json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'))
    samples=[]
    for route in paths:
        pts=route.get('path',[route.get('start'),route.get('end')])
        if not pts or pts[0] is None:continue
        for a,b in zip(pts,pts[1:]):
            a,b=np.asarray(a),np.asarray(b)
            if a[1]<0 or b[1]<0:continue
            samples.extend(np.linspace(a,b,max(2,int(np.linalg.norm(b-a)*2)+1)))
    samples=np.asarray(samples);tree=cKDTree(samples[:,[0,2]])
    steps=json.loads((ROOT/'artifacts/facility_r23/walkways/native_cells.json').read_text())['steps'];steps=np.asarray([q[:3] for q in steps if q[1]>=0],float);step_tree=cKDTree(steps[:,[0,2]])
    placed=[];held=[];walks=[];occupied=set()
    geometry={q['name']:q for q in json.loads((ROOT/'artifacts/facility_r24/props/geometry.json').read_text())}
    for r in records:
        x,y,z=r['center'];h=r['half'];g=r['ground'];hor=r['horizontal'];dx,dz=(h+3,21) if hor else (21,h+3)
        blocks=read_box(WORLD,v.DIM,(x-dx,g-1,z-dz),(x+dx,y+12,z+dz))
        def at(u,Y,w):return (x+u,Y,z+w) if hor else (x+w,Y,z+u)
        def place(kind,u,Y,w,side,title='',lines=()):
            pos=at(u,Y,w);face=('south' if side<0 else 'north') if hor else ('east' if side<0 else 'west')
            toward=(0,0,-side) if hor else (-side,0,0);height=geometry[kind]['hi'][1];cells=[(pos[0],pos[1]+dy,pos[2]) for dy in range(math.ceil(height))]
            reason=None
            if any(q in occupied or blocks.get(q,'UNKNOWN') not in AIR|{'minecraft:light'} for q in cells):reason='occupied full model envelope'
            mounting=kind in ('wall_clock','utility_box','pipe_run')
            support=tuple(pos[i]-toward[i] for i in range(3)) if mounting else (pos[0],pos[1]-1,pos[2])
            if blocks.get(support,'').split('[')[0] not in (BACKING if mounting else FLOORS):reason='missing approved backing/floor'
            nearby=tree.query_ball_point([pos[0]+.5,pos[2]+.5],1.5)
            for index in nearby:
                q=samples[index]
                if abs(q[0]-(pos[0]+.5))<.85 and abs(q[2]-(pos[2]+.5))<.85 and q[1]+1.85>pos[1] and q[1]<pos[1]+height:reason='registered pedestrian body clearance';break
            for index in step_tree.query_ball_point([pos[0]+.5,pos[2]+.5],1.5):
                q=steps[index]
                if q[1]-.5<=pos[1]<=q[1]+3.5:reason='full paired escalator clearance';break
            if not mounting:
                front=tuple(pos[i]+toward[i] for i in range(3))
                if blocks.get((front[0],Y-1,front[2]),'').split('[')[0] not in FLOORS or any(blocks.get((front[0],Y+dy,front[2]),'UNKNOWN') not in AIR|{'minecraft:light'} for dy in (0,1)):
                    reason='front standing space is not clear and supported'
            if reason:
                held.append(dict(station=r['station'],line=r['line'],kind=kind,pos=pos,reason=reason));return False
            state=f'projectseele:period_fixture[facing={face},kind={kind}]'
            p.match((*pos,*pos),blocks[pos],state,'r24/period_station_fixtures');occupied.update(cells)
            tag=nbtlib.Compound({'id':nbtlib.String('projectseele:period_fixture'),'x':nbtlib.Int(pos[0]),'y':nbtlib.Int(pos[1]),'z':nbtlib.Int(pos[2])})
            if title:tag['Title']=nbtlib.String(title)
            if lines:tag['Lines']=nbtlib.List[nbtlib.String]([nbtlib.String(q) for q in lines])
            p.block_entities[pos]=tag;placed.append(dict(station=r['station'],line=r['line'],kind=kind,position=pos,facing=face,model_height=height,support=support,title=title,lines=lines))
            if not mounting:
                # Side approaches stay in the existing aisle. The fixture
                # front is usable, but it is not treated as a through-route.
                a=[front[0]+.5,Y,front[2]+.5];aa=[a[0]+(2 if hor else 0),Y,a[2]+(0 if hor else 2)]
                walks.extend([dict(id=f'r24/fixture/{len(placed)}/approach',start=aa,end=a),dict(id=f'r24/fixture/{len(placed)}/return',start=a,end=aa)])
            return True
        displaced={('新箱根中央','R1'):1,('新箱根中央','S1'):-1,('湾岸防卫区','R1'):-1,('湾岸防卫区','S1'):1}
        for side in (-1,1):
            offset=20 if displaced.get((r['station'],r['line']))==side else 0
            for clock_u in (offset-4,offset+4,offset+10):
                if place('wall_clock',clock_u,y+3,side*16,side):break
            for u in (-28,-24,-32):
                if place('public_phone',u,y+1,side*16,side):break
            for u in (28,24,32,36):
                if place('notice_board',u,y+1,side*16,side,r['station'],[r['line']+' 线乘车指引','每分钟一班','时刻以实时牌为准','站台门开启后乘车','出口与换乘看导向牌']):break
            # These are measured existing station columns, not inferred new
            # walls. Keep service fittings at least twelve metres apart.
            previous=-10000
            for u in range(-h+8,h-7):
                if u-previous<12:continue
                if not all(blocks.get(at(u,Y,side*17),'').split('[')[0] in BACKING for Y in range(g+1,g+7)):continue
                if place('utility_box',u,g+2,side*16,side):
                    previous=u
                    for Y in range(g+3,min(g+7,y)):place('pipe_run',u,Y,side*16,side)
            for u in (8,12,-8):
                if place('drinking_fountain',u,g+1,side*14,side):break
    p.meta.update(placed=placed,held_candidates=held,walk_nodes=walks,station_groups=len(records),native_paired_steps_preserved=True)
    p.save_plan('supported_period_station_details')
    if apply:p.apply('supported_period_station_details')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
    from collections import Counter
    print('Period station fixtures',dict(Counter(q['kind'] for q in placed)),'held candidates',len(held),'new approaches',len(walks))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
