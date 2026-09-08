"""Finish measured station frontage, deck access and airfield taxi connections."""
import json
import regional_voxels as vox
from regional_architecture import stairs
from build_r07_installations import street,walk,CASES

OUT=vox.ROOT/'artifacts/world_expansion_r07';vox.OUT=OUT;p=vox.Painter()
FLOOR='projectseele:nerv_floor_panel';AIR='minecraft:air';GLASS='minecraft:gray_stained_glass';DARK='minecraft:gray_concrete'
# Restore the station facade; its public walkway belongs outside Z487.
p.fill(470,81,487,554,82,487,'minecraft:white_concrete','r07/P1/frontage','owned')
p.fill(470,83,487,554,86,487,GLASS,'r07/P1/frontage','owned')
for x in range(470,555,16):p.fill(x,81,487,x,86,487,'minecraft:polished_basalt[axis=y]','r07/P1/frontage','owned')
p.fill(508,81,487,516,86,487,AIR,'r07/P1/entry','owned')
for x in (506,518):p.fill(x,81,487,x,86,487,'minecraft:iron_block','r07/P1/entry','owned')
p.fill(446,80,490,516,80,490,FLOOR,'r07/P1/walk_edge','owned')
for x in (1180,1188):p.fill(x,71,490,x,71,501,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]','r07/P1/port_guard')
p.fill(1183,32,495,1185,66,497,'minecraft:polished_andesite','r07/P1/port_walk_pier')
# Service stairs actually reach each weapon deck at Y84.
for cx,cz in [(6344,-6680),(6856,-6680),(6344,-5976),(6856,-5976)]:
    o=f'r07/defense_access/{cx}/{cz}'
    p.fill(cx-5,79,cz-3,cx+5,79,cz-1,FLOOR,o,'owned')
    stairs(p,cx-3,cz+4,74,5,'north',o,3,'owned')
    stairs(p,cx+3,cz-1,79,4,'south',o,3,'owned')
    path=[[cx-2.5,75,cz+5.5],[cx-2.5,80,cz-1.5],[cx+3.5,80,cz-2.5],[cx+3.5,84,cz+4.5]]
    walk(o,path)
# Taxi every shelter directly to the parallel taxiway, at the same runway datum.
for z in (-6544,-6456,-6192):street(p,6640,z,6720,z,74,'base/shelter_taxi_'+str(z),15)
p.fill(6652,74,-6152,6676,74,-6128,'minecraft:green_terracotta','r07/base/helipad')
for x in (6660,6668):p.fill(x,74,-6146,x,74,-6134,'minecraft:white_concrete','r07/base/helipad')
p.fill(6660,74,-6140,6668,74,-6140,'minecraft:white_concrete','r07/base/helipad')
# The short aft compartments keep bunks inside the hollow hull, not embedded in its stern.
for oldz,newz in [(439,435),(553,550)]:
    for x in (1439,1448):
        p.fill(x,62,oldz-1,x,62,oldz,'minecraft:red_terracotta','r07/fleet/aft_bunks','owned')
        p.bed(x,62,newz,'r07/fleet/aft_bunks',color='light_gray')
p.fill(1444,65,437,1444,65,437,'minecraft:gray_concrete','r07/fleet/aft_light','owned')
p.put(1444,65,435,'projectseele:nerv_strip_light','r07/fleet/aft_light')
for name,bow in [('ESCORT-01',338),('SUPPORT-02',462)]:walk('fleet/'+name+'/upper_bridge',[[1447.5,69,bow+72.5],[1447.5,76,bow+62.5]])
p.meta['walk_cases']=CASES;p.apply('access_details');(OUT/'access_walk_cases.json').write_text(json.dumps(CASES,indent=2))
