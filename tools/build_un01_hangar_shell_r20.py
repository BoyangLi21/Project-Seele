"""Prepare an independent UN-01 bay while the airframe model is deferred."""
import json,copy
from pathlib import Path
import numpy as np
import nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
from build_transit_civil_r20 import grouped,ff
OUT=v.ROOT/'artifacts/world_rebuild_r20/un01_hangar';DX=-160
def main():
    OUT.mkdir(parents=True,exist_ok=True);v.OUT=OUT;p=v.Painter();source=read_box(v.WORLD,v.DIM,(6384,73,-6288),(6500,161,-6135));target=read_box(v.WORLD,v.DIM,(6224,77,-6288),(6340,161,-6135))
    unexpected={s for (x,y,z),s in target.items() if s.split('[')[0] not in AIR and not v.natural(s) and not(s=='minecraft:gray_concrete' and x in (6332,6333) and y<=78) and not(s=='minecraft:polished_deepslate' and x==6331 and y<=80)};assert not unexpected,unexpected
    owner='r20/un01_hangar/shell'
    p.grade(6216,-6296,6350,-6104,76,owner+'/site',20)
    ff(p,(6224,77,-6288,6340,161,-6135),'minecraft:air',owner+'/retire_old_service_curb')
    rows={}
    for (x,y,z),s in source.items():
        if s.split('[')[0] not in AIR:rows.setdefault((y,z,s),[]).append(x+DX)
    for (y,z,state),xs in rows.items():
        xs.sort();start=end=xs[0]
        for x in xs[1:]:
            if x==end+1:end=x
            else:ff(p,(start,y,z,end,y,z),state,owner);start=end=x
        ff(p,(start,y,z,end,y,z),state,owner)
    for pos,tag in iter_block_entities(v.WORLD,v.DIM,(6384,73,-6288),(6500,161,-6135)):
        t=copy.deepcopy(tag);q=(pos[0]+DX,pos[1],pos[2]);t['x']=nbtlib.Int(q[0]);p.block_entities[q]=t
    # A generous front apron joins the already built military campus.
    ff(p,(6218,73,-6134,6384,75,-6108),'projectseele:nerv_structural_panel',owner)
    ff(p,(6218,76,-6134,6384,76,-6108),'projectseele:nerv_floor_panel',owner)
    for z in (-6133,-6109):
        ff(p,(6218,77,z,6383,77,z),'minecraft:light_gray_concrete',owner)
        for x in range(6226,6380,18):ff(p,(x,78,z,x,82,z),'projectseele:nerv_machine_edge',owner);p.put(x,83,z,'projectseele:nerv_strip_light',owner)
    ff(p,(6352,73,-6302,6364,75,-6105),'minecraft:stone',owner+'/service_road')
    ff(p,(6352,76,-6302,6364,76,-6105),'minecraft:black_concrete',owner+'/service_road')
    ff(p,(6352,77,-6302,6364,83,-6105),'minecraft:air',owner+'/service_road')
    for z in range(-6298,-6110,12):ff(p,(6358,76,z,6358,76,z+5),'minecraft:white_concrete',owner+'/service_road')
    # Two safe grade transitions meet the existing lower campus elevation.
    for x in range(6219,6384):
        p.put(x,76,-6107,'minecraft:smooth_quartz_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]',owner)
        p.put(x,75,-6106,'minecraft:smooth_quartz_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]',owner)
    # Continuous runway beams and substantial portals support the reused
    # mechanical hoist. The airframe itself is not spawned in this phase.
    for z in (-6264,-6150):
        for x in (6258,6306):ff(p,(x-1,76,z-1,x+1,157,z+1),'projectseele:nerv_structural_panel',owner)
        ff(p,(6257,154,z-1,6307,157,z+1),'projectseele:nerv_machine_edge',owner)
    for x in (6278,6286):ff(p,(x,151,-6264,x,153,-6150),'projectseele:nerv_machine_edge',owner)
    # UN lettering is supported on the facade and kept outside the gate sweep.
    glyphs={'U':['10001','10001','10001','10001','01110'],'N':['10001','11001','10101','10011','10001']}
    for char,base in [('U',6228),('N',6240)]:
        for row,line in enumerate(glyphs[char]):
            for col,c in enumerate(line):
                if c=='1':ff(p,(base+col*2,147-row*2,-6135,base+col*2+1,148-row*2,-6135),'minecraft:white_concrete',owner)
    for x,text in [(6234,'排空 LCL'),(6238,'舱门开关'),(6246,'注入 LCL')]:
        p.sign(x,80,-6141,['EVA-UN-01',text,'独立试验舱','联合国'],owner,'south')
    config=dict(installed=False,home=[6282.5,77,-6205.5],door=[6282.5,77,-6135.5],wet_min=[6266,77,-6226],wet_max=[6298,120,-6137],buttons=[[6234,78,-6141],[6238,78,-6141],[6246,78,-6141]],model_status='deferred_to_user_ChatGPT_Pro',spawn_airframe=False)
    (OUT/'facility.json').write_text(json.dumps(config,indent=2));p.meta.update(facility=config,source='Existing commissioned UN bay architecture, copied to an independently surveyed site',source_bounds=[[6384,73,-6288],[6500,161,-6135]],offset=[DX,0,0],walk_nodes=[dict(id='r20/un01/front_apron',start=[6270.5,77,-6120.5],end=[6378.5,77,-6120.5])]);p.save_plan('reserved_hangar_shell')
if __name__=='__main__':main()
