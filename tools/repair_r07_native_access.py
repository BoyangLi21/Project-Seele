"""Repair the R07 collision failures using the measured native traces."""
import json
import regional_voxels as vox
from build_r07_installations import CASES,walk
OUT=vox.ROOT/'artifacts/world_expansion_r07';vox.OUT=OUT;p=vox.Painter()
AIR='minecraft:air';FLOOR='projectseele:nerv_floor_panel'
# The gantry crosses the tank wall above maximum LCL level, through a framed opening.
for x in (6425,6459):
    p.fill(x,127,-6219,x,130,-6216,AIR,'r07/gantry_pressure_wall_passage','owned')
    p.fill(x,131,-6220,x,131,-6215,'minecraft:iron_block','r07/gantry_pressure_wall_header','owned')
for cx,cz in [(6344,-6680),(6856,-6680),(6344,-5976),(6856,-5976)]:
    p.fill(cx+2,80,cz-3,cx+4,85,cz-2,AIR,'r07/defense_stair_approach_headroom','owned')
# Guard the actual crew-stair opening. The boarding walkway turns around it.
for x in (1438,1442):p.fill(x,67,544,x,67,547,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]','r07/fleet/crew_stair_guard')
f=OUT/'fleet_walk_cases.json';cases=json.loads(f.read_text(encoding='utf8'))
path=[[1421.5,65,546.5],[1436.5,67,546.5],[1436.5,67,540.5],[1444.5,67,540.5],[1444.5,67,546.5]]
for c in cases:
    if c['id']=='r07/fleet/SUPPORT-02/board':c['path']=path
    if c['id']=='r07/fleet/SUPPORT-02/board/return':c['path']=path[::-1]
f.write_text(json.dumps(cases,indent=2),encoding='utf8')
# The first shelter leaves through its broad south door, then joins the taxiway.
# Its east wall is part of the shelter, not a road opening.
p.fill(6609,74,-6558,6671,74,-6546,FLOOR,'r07/base/remove_crossing_marks_inside_shelter','owned')
f=OUT/'base_walk_cases.json';cases=json.loads(f.read_text(encoding='utf8'))
path=[[6640.5,75,-6560.5],[6640.5,75,-6540.5],[6720.5,75,-6540.5],[6720.5,75,-6551.5],[6784.5,75,-6551.5]]
for c in cases:
    if c['id']=='r07/base/taxi_cross_-6552':c['path']=path
    if c['id']=='r07/base/taxi_cross_-6552/return':c['path']=path[::-1]
f.write_text(json.dumps(cases,indent=2),encoding='utf8')
# One continuous ground-to-plug route, with no teleport between stair flights.
path=[[6402.5,77,-6132.5],[6402.5,77,-6138.5],[6420.5,77,-6138.5],[6420.5,77,-6244.5],[6480.5,77,-6244.5],[6480.5,77,-6248.5],[6476.5,77,-6248.5]]
for i in range(5):
    y=77+i*10
    path.extend([[6476.5,y,-6248.5],[6476.5,y+5,-6255.5],[6482.5,y+5,-6255.5],[6482.5,y+10,-6248.5]])
path.extend([[6480.5,127,-6249.5],[6462.5,127,-6249.5],[6462.5,127,-6217.5],[6442.5,127,-6217.5]])
walk('secret/continuous_staff_to_plug',path)
p.meta['walk_cases']=CASES;p.apply('native_access_repairs')
(OUT/'continuous_walk_cases.json').write_text(json.dumps(CASES,indent=2),encoding='utf8')
