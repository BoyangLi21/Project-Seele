"""Unify ceiling finishes and furnish surveyed observation and station bays."""
import json
import regional_voxels as v
from query_blocks import read_box,AIR
from build_transit_civil_r20 import ff
OUT=v.ROOT/'artifacts/world_rebuild_r20/visual_finish';REVIEW=v.ROOT/'run/saves/SEELE_R20_REVIEW'
def main():
    OUT.mkdir(parents=True,exist_ok=True);v.OUT=OUT;p=v.Painter();counts={};owner='r20/finish'
    masks=json.loads((OUT.parent/'lifts/sweep_masks.json').read_text())
    def reserved(q):return any(all(r['sweep'][0][i]<=q[i]<=r['sweep'][1][i] for i in range(3)) for r in masks)
    remap={'minecraft:iron_block':'projectseele:nerv_machine_edge','minecraft:sea_lantern':'projectseele:nerv_strip_light','minecraft:deepslate_bricks':'projectseele:nerv_structural_panel','minecraft:polished_deepslate':'projectseele:nerv_structural_panel'}
    for lo,hi in [((-35,-373,-282),(95,-349,-214)),((85,-462,243),(128,-437,350))]:
        for q,before in read_box(REVIEW,v.DIM,lo,hi).items():
            if before in remap and not reserved(q):p.match((*q,*q),before,remap[before],owner+'/palette');counts[before]=counts.get(before,0)+1
    # Two facing banks leave the central observation aisle and lift turn clear.
    furniture=[]
    for z in (-75,-66,-39,-27):
        for x,face,cx,chairface in [(98,'west',96,'east'),(108,'east',110,'west')]:
            for dz in (0,1):furniture.append(((x,-369,z+dz),'projectseele:nerv_workstation[facing='+face+']'))
            furniture.append(((cx,-369,z),'projectseele:nerv_office_chair[facing='+chairface+']'))
    # Repeated small seating bays suit long Japanese-style platforms. Stairs
    # remain in the end bays, and the continuous +/-8 aisles stay untouched.
    stations=json.loads((OUT.parent/'transit/civil/continuous_platform_aisles/places.json').read_text(encoding='utf8'))['stations'];benches=0
    for s in stations:
        if s['half']<50:continue
        x,y,z=s['center'];horizontal=s['horizontal'];colour={'C1':'green','R1':'orange','A1':'blue','S1':'purple','S2':'green','P1':'blue'}.get(s['line'],'gray')
        for sign in (-1,1):
            face=('south' if sign<0 else 'north') if horizontal else ('east' if sign<0 else 'west')
            for u in (-22,-21,-20,-19,14,15,16,17):
                q=(x+u,y+1,z+sign*13) if horizontal else (x+sign*13,y+1,z+u)
                furniture.append((q,'projectseele:station_seat[facing='+face+']'));benches+=1
            a=(x-s['half'],y+9,z+sign*15) if horizontal else (x+sign*15,y+9,z-s['half'])
            b=(x+s['half'],y+9,z+sign*15) if horizontal else (x+sign*15,y+9,z+s['half'])
            ff(p,(*a,*b),'minecraft:'+colour+'_terracotta',owner+'/canopy_line_colour')
    for q,state in furniture:
        before=read_box(REVIEW,v.DIM,q,q)[q];assert before.split('[')[0] in AIR|{'minecraft:light'},(q,before)
        p.match((*q,*q),before,state,owner+'/furniture')
    p.meta.update(recoloured=counts,observation_furniture=24,new_station_seats=benches,main_command_room_untouched=True,cabin_sweeps_preserved=True)
    p.save_plan('coherent_finishes_and_furniture')
if __name__=='__main__':main()
