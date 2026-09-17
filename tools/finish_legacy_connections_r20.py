"""Repair the retained route interfaces exposed by the whole-catalogue native walk."""
import json
from pathlib import Path
import regional_voxels as v
from query_blocks import read_box,AIR
from build_transit_civil_r20 import ff
OUT=v.ROOT/'artifacts/world_rebuild_r20/legacy_connections';REVIEW=v.ROOT/'run/saves/SEELE_R20_REVIEW'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.OUT=OUT;p=v.Painter();owner='r20/retained_route_ports';changes=[]
    def box(b,s):ff(p,b,s,owner)
    # Existing east staff-room doors remain destinations at both old floors.
    # Door openings are framed between columns, not filled by new supports.
    for z in (276,308,340):
        for feet in (-448,-461):
            box((92,feet,z-1,94,feet+3,z+1),'minecraft:air')
            box((92,feet-1,z-1,94,feet-1,z+1),'projectseele:nerv_floor_panel')
            box((92,feet+4,z-2,94,feet+4,z+2),'projectseele:nerv_machine_edge')
        for dz in (-3,3):box((93,-467,z+dz,94,-450,z+dz),'projectseele:nerv_structural_panel')
    # The existing B40 concourse enters the completed west upper junction.
    box((88,-442,272,94,-439,274),'minecraft:air');box((88,-443,272,94,-443,274),'projectseele:nerv_floor_panel')
    # A lateral port joins the moved third-cage gallery to the new service hall.
    box((89,-394,-265,91,-391,-263),'minecraft:air');box((89,-395,-265,91,-395,-263),'projectseele:nerv_floor_panel')
    box((89,-390,-266,91,-390,-262),'projectseele:nerv_machine_edge')
    # The upper observation room is one step above the retained lift landing.
    box((92,-370,-57,94,-370,-57),'minecraft:air')
    box((92,-371,-57,94,-371,-57),'projectseele:nerv_floor_panel')
    box((92,-370,-58,94,-370,-58),'minecraft:smooth_quartz_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]')
    # Restore only the pre-existing science footbridge floor accidentally cut
    # by the first rail-envelope pass. Native trains stay one full metre below.
    lo,hi=(192,-461,474),(200,-461,500);old=read_box(v.WORLD,v.DIM,lo,hi);now=read_box(REVIEW,v.DIM,lo,hi)
    for q,s in old.items():
        if s.split('[')[0] not in AIR and now[q].split('[')[0] in AIR:
            p.match((*q,*q),now[q],s,owner+'/science_bridge_floor');changes.append(q)
    # P1's original port ramp meets the new station undercroft at its centre.
    # Replace the centre pier with a supported portal around that entrance.
    box((1182,71,486,1186,76,488),'minecraft:air')
    for x in (1180,1187):box((x,68,486,x+1,92,488),'minecraft:light_gray_concrete')
    box((1180,77,486,1188,78,488),'projectseele:nerv_machine_edge')
    # The older airport approach road predates the main road mask. Restore
    # its exact paving under the offending pier and move support off-road.
    lo,hi=(223,80,992),(225,91,994);old=read_box(v.WORLD,v.DIM,lo,hi);now=read_box(REVIEW,v.DIM,lo,hi)
    for q,s in now.items():
        if s=='minecraft:light_gray_concrete':p.match((*q,*q),s,old[q],owner+'/airport_road_pier')
    footing=read_box(REVIEW,v.DIM,(223,78,1006),(225,93,1008))
    assert all(footing[x,81,z].split('[')[0] in ('minecraft:dirt','minecraft:grass_block','minecraft:stone') for x in range(223,226) for z in range(1006,1009))
    assert all(footing[x,y,z].split('[')[0] in AIR|{'minecraft:light','minecraft:grass'} for x in range(223,226) for z in range(1006,1009) for y in range(82,94))
    box((223,79,1006,225,91,1008),'minecraft:light_gray_concrete')
    box((223,92,992,225,93,1008),'projectseele:nerv_machine_edge')
    p.meta.update(restored_science_floor=changes,east_room_ports=6,new_cage_gallery_port=True,port_station_portal=True,airport_pier_moved_from=[224,94,993],airport_pier_moved_to=[224,94,1007],elevator_car_volume_untouched=True)
    p.save_plan('retained_destinations');print('Legacy connection plan',len(p.ops))

if __name__=='__main__':main()
