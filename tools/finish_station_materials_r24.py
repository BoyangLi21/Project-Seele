"""Replace only measured, authorised station walking-deck smooth stone surfaces."""
from pathlib import Path
import json,argparse
import regional_voxels as v
from query_blocks import read_box
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/materials'
def main(apply=False):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();changes=[]
    records=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['stations']
    for station in records:
        # Four initially inspected stations; expand only after actual views.
        if station['station'] not in ('第三新东京中央','NERV 地面入口','雾里住宅区','新箱根中央'):continue
        x,y,z=station['center'];g=station['ground'];h=station['half'];hor=station['horizontal'];dx,dz=(h+1,18) if hor else (18,h+1)
        for Y in (g,y):
            b=read_box(WORLD,v.DIM,(x-dx,Y,z-dz),(x+dx,Y,z+dz));count=0
            for q,state in b.items():
                if state!='minecraft:smooth_stone':continue
                p.match((*q,*q),state,'projectseele:period_station_floor','r24/measured_station_material_finish');count+=1
            changes.append(dict(station=station['station'],line=station['line'],height=Y,cells=count))
    p.meta.update(surfaces=changes,collision_unchanged_full_cube=True,stairs_and_tactile_blocks_unchanged=True)
    p.save_plan('period_station_floor_finish')
    if apply:p.apply('period_station_floor_finish')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('New floor material cells',sum(c['cells'] for c in changes))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
