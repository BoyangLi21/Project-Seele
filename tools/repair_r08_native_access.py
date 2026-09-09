"""Resolve native walking failures: boarding height, dock lamp, and real deck/shelter routes."""
import json,math
import regional_voxels as v
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT;p=v.Painter()
for cx,start in ((1444,1423),(1494,1475)):
    end=cx-8;z=420
    for x in range(start,end+1):
        h=round((64+4*min(1,(x-start)/(cx-10-start)))*2)/2;yy=math.floor(h)
        p.fill(x,64,z-2,x,72,z+2,'minecraft:air','r08/access/gangway_clear','owned')
        p.fill(x,63,z-2,x,yy,z+2,'minecraft:gray_concrete','r08/access/gangway_floor','owned')
        if h%1:p.fill(x,yy+1,z-2,x,yy+1,z+2,'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]','r08/access/half_step','owned')
    for zz in (417,423):
        p.match((cx-10,69,zz,cx-8,72,zz),'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]','minecraft:air','r08/access/rail_return')
for z in (376,568):
    p.match((1471,65,z,1471,72,z),'minecraft:gray_concrete','minecraft:air','r08/access/lamp_retire')
    p.match((1469,73,z,1473,73,z),'projectseele:nerv_strip_light','minecraft:air','r08/access/lamp_retire')
    p.fill(1466,65,z,1466,72,z,'minecraft:gray_concrete','r08/access/edge_lamp','owned');p.fill(1464,73,z,1468,73,z,'projectseele:nerv_strip_light','r08/access/edge_lamp','owned')
p.apply('native_access')
path=OUT/'port_walk_cases.json';cases=json.loads(path.read_text(encoding='utf8'))
for c in cases:
    if '/aft_deck' in c['id']:
        cx=1444 if 'ship_01' in c['id'] else 1494
        c['path']=[[cx-7.5,69,420.5],[cx-5.5,69,420.5],[cx-5.5,69,403.5],[cx-7.5,69,403.5],[cx-7.5,69,402.5]]
        if c['id'].endswith('/return'):c['path'].reverse()
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
path=OUT/'base_detail_walk_cases.json';cases=json.loads(path.read_text(encoding='utf8'))
for c in cases:
    if '/air_shelter_' in c['id']:
        z=int(c['id'].split('/air_shelter_')[1].split('/')[0]);c['path']=[[6616.5,75,z+59.5],[6624.5,75,z+59.5],[6624.5,75,z+50.5],[6616.5,75,z+50.5],[6616.5,75,z+16.5],[6629.5,75,z+16.5]]
        if c['id'].endswith('/return'):c['path'].reverse()
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
