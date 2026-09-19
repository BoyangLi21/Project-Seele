"""Measured small station shops, designed from the inspected 1990 Shinjuku references.

No historical photograph is used as a texture. Existing paired walks, benches,
stairs and station support columns remain. Every facade cell is measured first.
"""
from pathlib import Path
import argparse,json,math
import numpy as np,nbtlib
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,AIR

ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/shops'
SELECTED={('第三新东京中央','R1'):'青叶茶室',('新箱根中央','R1'):'箱根茶房',('雾里住宅区','R1'):'雾里茶室',('NERV 地面入口','S1'):'站前茶室'}

def main(apply=False):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();contract=[];held=[];walks=[]
    routes=json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));samples=[]
    for route in routes:
        pts=route.get('path',[route.get('start'),route.get('end')])
        if not pts or pts[0] is None:continue
        for a,b in zip(pts,pts[1:]):
            a,b=np.array(a),np.array(b)
            if a[1]<0 or b[1]<0:continue
            samples.extend(np.linspace(a,b,max(2,int(np.linalg.norm(a-b)*2)+1)))
    samples=np.array(samples);tree=cKDTree(samples[:,[0,2]])
    stations=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['stations']
    for station in stations:
        key=(station['station'],station['line'])
        if key not in SELECTED:continue
        x,_,z=station['center'];g=station['ground'];assert station['horizontal']
        # Those two stations have a reviewed cross-concourse route through
        # the centre. The shops occupy the next clear bay instead.
        if key[0] in ('雾里住宅区','新箱根中央'):x+=34
        b=read_box(WORLD,v.DIM,(x-8,g-1,z-18),(x+8,g+7,z-8));edit={};be={};localwalk=[]
        def at(u,Y,w):return (x+u,Y,z+w)
        def setcell(u,Y,w,state):edit[at(u,Y,w)]=state
        def fill(u,Y,w,U,V,W,state):
            for xx in range(u,U+1):
                for yy in range(Y,V+1):
                    for zz in range(w,W+1):setcell(xx,yy,zz,state)
        def prop(u,Y,w,kind,facing='south'):
            q=at(u,Y,w);setcell(u,Y,w,f'projectseele:period_fixture[facing={facing},kind={kind}]')
            be[q]=nbtlib.Compound({'id':nbtlib.String('projectseele:period_fixture'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2])})
        def board(u,Y,w,title,lines):
            q=at(u,Y,w);setcell(u,Y,w,'projectseele:station_departure_board[facing=south,wayfinding=true]')
            t=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2]),'Wayfinding':nbtlib.Byte(1),'Station':nbtlib.String(title),'Route':nbtlib.String('站内服务'),'PlatformCentre':nbtlib.Long(0)})
            for i,line in enumerate(lines):t['Row'+str(i)]=nbtlib.String(line)
            be[q]=t
        fill(-6,g,-16,5,g,-12,'minecraft:brown_terracotta')
        # Independent shop shell fits wholly inside the approved concourse.
        fill(-6,g+1,-16,5,g+4,-16,'minecraft:white_concrete')
        for u in (-6,1,5):fill(u,g+1,-15,u,g+4,-12,'minecraft:white_concrete')
        fill(-5,g+1,-12,0,g+3,-12,'projectseele:clear_glass')
        fill(-5,g+1,-12,0,g+1,-12,'minecraft:green_terracotta')
        fill(2,g+1,-12,4,g+3,-12,'projectseele:clear_glass')
        fill(-3,g+1,-12,-2,g+3,-12,'minecraft:air')
        fill(2,g+1,-12,3,g+3,-12,'minecraft:air')
        fill(-6,g+4,-12,5,g+4,-12,'minecraft:green_terracotta')
        fill(-7,g+5,-17,5,g+5,-11,'minecraft:smooth_quartz_slab[type=bottom,waterlogged=false]')
        for u in (-5,-1,3):setcell(u,g+4,-14,'projectseele:nerv_strip_light')
        prop(-5,g+1,-14,'cafe_table');prop(-5,g+1,-15,'cafe_stool');prop(-5,g+1,-13,'cafe_stool')
        prop(0,g+1,-15,'coffee_machine');prop(0,g+1,-14,'cafe_counter','west')
        prop(4,g+1,-15,'newspaper_rack');prop(4,g+1,-12,'cafe_counter')
        prop(-1,g+2,-15,'wall_clock')
        board(-3,g+3,-11,SELECTED[key],['茶 · 咖啡','站内休息','请勿占用通道'])
        board(3,g+3,-11,'书报小铺',['新闻 · 杂志','旅行资讯','站内服务'])
        for door in (-2.5,2.5):
            a=[x+door,g+1,z-9.5];c=[x+door,g+1,z-13.5]
            localwalk += [dict(id=f'r24/shop/{key[0]}/{door}/in',start=a,end=c),dict(id=f'r24/shop/{key[0]}/{door}/out',start=c,end=a)]
        failures=[]
        for q,new in edit.items():
            old=b[q]
            if old==new:continue
            if q[1]==g:
                if old!='minecraft:smooth_stone':failures.append((q,'floor not station deck',old))
            elif old not in AIR|{'minecraft:light'}:failures.append((q,'occupied cell',old))
            if new in AIR:continue
            for i in tree.query_ball_point([q[0]+.5,q[2]+.5],1):
                s=samples[i]
                if abs(s[0]-q[0]-.5)<.8 and abs(s[2]-q[2]-.5)<.8 and s[1]+1.85>q[1] and s[1]<q[1]+1:
                    failures.append((q,'registered route body',s.tolist()));break
        # Wider sign models are entirely above the two metre pedestrian body,
        # with a solid fascia immediately behind them and a canopy over them.
        if failures:
            held.append(dict(station=key,conflicts=failures));continue
        for q,new in edit.items():
            if b[q]!=new:p.match((*q,*q),b[q],new,'r24/original_period_station_shops')
        p.block_entities.update(be);walks.extend(localwalk)
        contract.append(dict(station=key,title=SELECTED[key],floor=g,box=[x-7,g,z-17,x+6,g+5,z-11],entry_points=[q['end'] for q in localwalk[::2]],cells=len(edit),new_fixtures=len(be)))
    p.meta.update(shops=contract,held=held,walk_nodes=walks,reference='1990 Nitto POLE LIGHT shop and JR bus stop photos by Cassiopeia sweet; original geometry and adapted station floor plan')
    p.save_plan('concourse_cafes_and_newsstands')
    if apply:p.apply('concourse_cafes_and_newsstands')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Shops',len(contract),'held',[(r['station'],r['conflicts'][:2]) for r in held])
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
