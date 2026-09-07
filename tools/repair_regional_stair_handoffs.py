"""Restore stair ends trimmed by corridor caps, preserving the measured floor datum."""
import json
from regional_voxels import Painter,OUT
from regional_architecture import *
p=Painter()
for x in (-29,89):
    p.fill(x-3,-462,365,x+3,-462,382,FLOOR,'hq/lower_stair_bypass','owned')
    p.fill(x-3,-461,365,x+3,-458,382,AIR,'hq/lower_stair_bypass','owned')
    stairs(p,x,380,-462,13,'north','hq/continuous_stair',3,'owned')
    p.fill(x-2,-449,365,x+2,-449,367,FLOOR,'hq/stair_top','owned')
    p.fill(x-2,-448,365,x+2,-445,367,AIR,'hq/stair_top','owned')
for x in range(26,35):p.put(x,-466,451,'minecraft:polished_deepslate_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]','hq/station_step','owned')
for sx,gx,rz in [(740,650,1430),(-1670,-1610,-20)]:
    stairs(p,sx,rz-299,71,9,'north','airport/terminal_stair_restore',5,'owned')
    stairs(p,gx,rz-234,71,9,'south','airport/gate_stair_restore',5,'owned')
transit=json.loads((OUT/'transit_plan.json').read_text(encoding='utf-8'))
for platform in transit['platforms']:
    if platform.get('mode')=='AIRPLANE' or platform['heading'] not in ('N','S'):continue
    x,y,z=platform['center']
    stairs(p,x-12,z,y,6,'east','station/reopen_native_stair',3,'owned')
    stairs(p,x+12,z,y,6,'west','station/reopen_native_stair',3,'owned')
p.apply('stair_handoffs')
