"""Supported Chinese station-name plates and flush perimeter drainage covers."""
from pathlib import Path
import argparse,json,nbtlib
import regional_voxels as v
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/station_civil_details'
def main(apply=False):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();plates=[];drains=[];held=[]
    source=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['stations']
    for station in source:
        x,y,z=station['center'];g=station['ground'];h=station['half'];hor=station['horizontal'];dx,dz=(h+2,19) if hor else (19,h+2)
        blocks=read_box(WORLD,v.DIM,(x-dx,g,z-dz),(x+dx,y+8,z+dz))
        def at(u,Y,w):return (x+u,Y,z+w) if hor else (x+w,Y,z+u)
        for side in (-1,1):
            face=('south' if side<0 else 'north') if hor else ('east' if side<0 else 'west')
            used=[]
            for u in range(-h+2,h,16):
                if u<-h+26 or u>h-25 or used and u-used[-1]<40:continue
                q=at(u,y+4,side*16);support=at(u,y+4,side*17)
                if blocks[support]!='minecraft:light_gray_concrete':held.append(dict(pos=q,reason='not an existing station column'));continue
                if any(blocks[at(u+du,y+4,side*16)] not in AIR|{'minecraft:light'} for du in (-1,0,1)):held.append(dict(pos=q,reason='sign model envelope occupied'));continue
                p.match((*q,*q),blocks[q],f'projectseele:period_fixture[facing={face},kind=shop_sign]','r24/supported_station_name_plate')
                p.block_entities[q]=nbtlib.Compound({'id':nbtlib.String('projectseele:period_fixture'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2]),'Title':nbtlib.String(station['station']),'Lines':nbtlib.List[nbtlib.String]([nbtlib.String(station['line']+' 线 · 出口与换乘请循导向')])})
                plates.append(dict(station=station['station'],line=station['line'],pos=q,support=support,facing=face));used.append(u)
            for u in range(-h+8,h-7,16):
                q=at(u,g,side*18);old=blocks[q]
                if old not in ('minecraft:smooth_stone','projectseele:period_station_floor'):continue
                p.match((*q,*q),old,'projectseele:station_drain','r24/flush_concourse_drain');drains.append(dict(station=station['station'],pos=q))
    p.meta.update(station_name_plates=plates,flush_drains=drains,held=held,overhead_sign_base_above_passenger_floor=3.0,stairs_and_boarding_aisles_unchanged=True)
    p.save_plan('station_names_and_drainage')
    if apply:p.apply('station_names_and_drainage')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Supported station-name plates',len(plates),'flush drainage',len(drains),'held',len(held))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
