"""Resolve measured corridor intersections and the two audited rail conflicts."""
from dataclasses import replace
from pathlib import Path
import json,os
import numpy as np
from regional_voxels import Painter,WORLD,OUT,ROOT,DIM
from regional_architecture import *
from build_regional_underground import corridor
from query_blocks import iter_selected_sections
from relocate_regional_eva import selected_boxes,runs

p=Painter()


def lane(x0,z0,x1,z1,floor,name,width=5,head=4):
    r=width//2
    ax,bx=(x0-r,x0+r) if x0==x1 else (min(x0,x1),max(x0,x1))
    az,bz=(z0-r,z0+r) if z0==z1 else (min(z0,z1),max(z0,z1))
    p.fill(ax,floor,az,bx,floor,bz,FLOOR,name,'owned')
    p.fill(ax,floor+1,az,bx,floor+head,bz,AIR,name,'owned')


# Restore the discarded long foldback's changes inside the existing EVA sector.
before=sorted((OUT/'geometry_all').glob('applied_*/before'))[-1]
fixture=ROOT/'.Codex/world-expansion/pre-regional-geometry';region=fixture/'dimensions/projectseele/geofront/region';region.mkdir(parents=True,exist_ok=True)
for file in before.glob('*.mca'):
    dest=region/file.name
    if not dest.exists():os.link(file,dest)
box=(-5,-489,-43,111,-437,-37)
for cx,cz,sy,pal,idx in iter_selected_sections(fixture,DIM,selected_boxes([box])):
    a=np.asarray(pal)[idx].reshape(16,16,16)
    for yy in range(16):
        y=sy*16+yy
        if not box[1]<=y<=box[4]:continue
        for zz in range(16):
            z=cz*16+zz
            if not box[2]<=z<=box[5]:continue
            xs=[x for x in range(cx*16,cx*16+16) if box[0]<=x<=box[3]]
            runs(p,xs,[a[yy,zz,x-cx*16] for x in xs],y,z,'rail/retire_old_U2_foldback')

# Retire the old high airport approach only within its own narrow rail footprint.
old=json.loads((OUT/'transit1/track_samples.json').read_text(encoding='utf-8'))
for rail in old:
    if rail['id']!='S1_section_1':continue
    for xx,yy,zz in rail['points']:
        x,y,z=map(round,(xx,yy,zz))
        if z<=100:
            p.fill(x-3,81,z-3,x+3,max(81,y+6),z+3,AIR,'rail/retire_high_airport_approach','owned')
            if y<81:p.fill(x-3,y-2,z-3,x+3,min(79,y+6),z+3,'minecraft:stone','rail/retire_old_airport_tunnel','owned')
            material='minecraft:black_concrete' if abs(z+20)<=18 or abs(z-40)<=18 else 'minecraft:gray_concrete'
            p.fill(x-3,80,z-3,x+3,80,z+3,material,'airport/reclose_old_rail_cut','owned')

# New graph uses an early rail descent and a 24 m hangar foldback.
samples=json.loads((OUT/'transit2/track_samples.json').read_text(encoding='utf-8'))
for rail in samples:
    if rail['id'] not in ('S1_section_1_descent','S1_section_1_underpass','U2_turnback'):continue
    for x,y,z in {tuple(map(round,a)) for a in rail['points']}:
        p.fill(x-3,y-3,z-3,x+3,y-1,z+3,DARK,'rail/corrected_native_route','owned')
        p.fill(x-2,y,z-2,x+2,y+5,z+2,AIR,'rail/corrected_native_route','owned')

# Remove the upper storey's temporary foundation infill from both circulation spines.
for floor in (-462,-449):
    for x in (-29,89):lane(x,271,x,425 if floor==-462 else 400,floor,'hq/continuous_wing')
    for i in range(4):
        z=276+i*32
        lane(-35,z,-29,z,floor,'hq/west_room_threshold',3)
        lane(89,z,95,z,floor,'hq/east_room_threshold',3)
for x in (-29,89):
    stairs(p,x,380,-462,13,'north','hq/continuous_wing_stair',5,'owned')
    lane(x,365,x,367,-449,'hq/stair_landing',5)
    p.fill(x-2,-448,403,x+2,-447,403,GLASS,'hq/upper_gallery_end','owned')
for x in (-26,82):lane(x-1,289,x+1,289,-449,'hq/existing_TV_room_port',5)
lane(-29,425,89,425,-462,'hq/lobby_distribution')
lane(30,442,30,447,-466,'hq/pyramid_base_approach',9,5)
for x in range(26,35):p.put(x,-466,447,'minecraft:polished_deepslate_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]','hq/base_edge_step','owned')

# The arrival corridor joins the north platform edge without crossing live rails.
p.fill(-313,-466,774,-305,-460,788,AIR,'arrival/retire_track_crossing','owned')
p.fill(-313,-467,774,-305,-467,782,FLOOR,'arrival/restore_platform','owned')
p.fill(-313,-467,783,-305,-467,787,AIR,'arrival/restore_track_trench','owned')
lane(-360,726,-309,726,-467,'arrival/lobby_spine')
lane(-309,726,-309,771,-467,'arrival/platform_spine')
lane(-309,771,-342,771,-467,'arrival/platform_threshold',3)

# Programmed research rooms can be partly embedded in native hills: clear their measured footprints.
for i,(label,purpose) in enumerate([('同期解析室','ANALYSIS'),('隔離診察室','MEDICAL'),('資料保管庫','ARCHIVE')]):
    q=Painter();z=440+i*55
    furnished_room(q,(334,372,z,z+45),-467,'science/'+str(i),label,purpose,exit_side='west')
    for op in q.ops:p.fill(*op.box,op.state,op.owner,'owned')
    p.block_entities.update(q.block_entities)
lane(328,447,328,608,-467,'science/east_spine')
for z in (462,517,572):lane(322,z,335,z,-467,'science/lab_threshold',3)
lane(322,565,328,565,-467,'science/east_platform_join',5)
lane(275,443,275,552,-467,'science/sigma_spine')
lane(275,552,291,552,-467,'science/west_join')
lane(291,552,291,565,-467,'science/west_join')
lane(291,565,297,565,-467,'science/west_platform_join')
# Human route passes above both U1 and U2; native track envelopes stay unobstructed.
p.fill(192,-466,410,200,-460,552,AIR,'science/retire_at_grade_west_walk','owned')
lane(196,406,196,540,-461,'science/rail_overbridge',7)
for x in (192,200):p.fill(x,-460,406,x,-459,540,GLASS,'science/overbridge_railings','owned')
lane(89,399,196,399,-462,'science/HQ_bridge',5)
lane(196,399,196,405,-462,'science/HQ_bridge',5)
stairs(p,196,405,-462,1,'south','science/bridge_step',5,'owned')
stairs(p,196,546,-467,6,'north','science/bridge_return_stair',5,'owned')
lane(196,547,196,552,-467,'science/bridge_return')
lane(196,552,275,552,-467,'science/reception_spine')

lane(259,100,259,267,-467,'logistics/continuous_gallery')
for z in (116,182,246):lane(247,z,259,z,-467,'logistics/room_threshold',3)
lane(259,180,288,180,-467,'logistics/platform_join')

# Complete station/terminal underpasses across the railway deck and terminal wall.
for sx,gx,rz,sz in [(740,650,1430,1190),(-1670,-1610,-20,-265)]:
    lane(sx,rz-298,sx,sz,71,'airport/terminal_underpass',5)
    lane(min(sx,gx),rz-250,max(sx,gx),rz-250,71,'airport/gate_underpass',5)
    lane(gx,rz-250,gx,rz-235,71,'airport/gate_underpass',5)

# Offset stair flights keep all longitudinal interchange passages open.
transit=json.loads((OUT/'transit_plan.json').read_text(encoding='utf-8'))
for platform in transit['platforms']:
    if platform.get('mode')=='AIRPLANE' or platform['heading'] not in ('E','W'):continue
    x,y,z=platform['center'];owner='station/offset_stair/'+platform['id']
    for start,heading,sgn in [(z-12,'south',1),(z+12,'north',-1)]:
        p.fill(x-1,y+1,min(start,start+sgn*5),x+1,y+5,max(start,start+sgn*5),AIR,owner,'owned')
        stairs(p,x+12,start,y,6,heading,owner,3,'owned')
        lane(x+12,start+sgn*6,x+12,z,y+6,owner,3)
    lane(x,z,x+12,z,y+6,owner,5)

# Reopen only measured obstruction cells in the native vehicle bodies after the new pedestrian bridges.
bad=json.loads((OUT/'transit_clearance.json').read_text(encoding='utf-8'))
bad_ids={r['id'] for r in bad['results'] if r['obstructed_cells'] and r['id'] not in ('U2_turnback','F1_hakone_landing','S1_section_1')}
for rail in samples:
    if rail['id'] not in bad_ids or rail['mode']!='TRAIN':continue
    for x,y,z in {tuple(map(round,a)) for a in rail['points']}:
        p.fill(x-1,y+1,z-1,x+1,y+4,z+1,AIR,'rail/verified_clearance_port','owned')

p.apply('connection_completion')
