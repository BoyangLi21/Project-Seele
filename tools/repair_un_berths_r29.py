"""Recess the boarding-gantry lip beyond both physical UN silhouettes and restore edge rails."""
from pathlib import Path
import json
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R29_REVIEW';OUT=ROOT/'artifacts/facility_r29/un_berths'
def main():
    v.WORLD=WORLD;v.OUT=OUT;OUT.mkdir(parents=True,exist_ok=True);p=v.Painter();walks=[]
    for cx in (6282,6442):
        lo=(cx-11,126,-6216);hi=(cx+11,127,-6214);before=read_box(WORLD,v.DIM,lo,hi)
        assert not list(iter_block_entities(WORLD,v.DIM,lo,hi))
        for x in range(cx-10,cx+11):
            for z in (-6215,-6214):
                for y in (126,127):
                    old=before[x,y,z];assert old=='minecraft:air' or old=='projectseele:nerv_floor_panel' or old.startswith('minecraft:iron_bars'),((x,y,z),old)
                    p.match((x,y,z,x,y,z),old,'minecraft:air','r29/un_gantry_lip_setback')
        # The docking notch stays open; its existing two side guards remain.
        for x in range(cx-11,cx+12):
            if abs(x-cx)<3:continue
            below=before[x,126,-6216];assert below!='minecraft:air',(x,below)
            state='minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]'
            p.put(x,127,-6216,state,'r29/un_gantry_edge_guard','owned')
        for x in (cx-11,cx+11):
            for z in (-6215,-6214):p.put(x,127,z,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]','r29/un_gantry_edge_guard','owned')
        for sign in (-1,1):
            pts=[[cx+sign*13+.5,127,-6218.5],[cx+sign*4+.5,127,-6218.5],[cx+sign*4+.5,127,-6217.5]]
            walks.extend([dict(id=f'r29/un_berth/{cx}/{sign}',path=pts),dict(id=f'r29/un_berth/{cx}/{sign}/return',path=pts[::-1])])
    p.meta.update(walk_nodes=walks,kept_dock_feet_z=-6217.5,setback_front_z=-6216,reason='Native occupied return found the old gantry lip within the vehicle envelope; keep safe docking positions and move the unused lip back two metres.')
    p.apply('un_boarding_lip_and_guards');(OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
