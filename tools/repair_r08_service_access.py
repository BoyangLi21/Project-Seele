"""Finish the warehouse aisle and ensure open-container storage has real blocks."""
import json
import regional_voxels as v
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT;p=v.Painter()
p.fill(1268,69,339,1276,73,391,'minecraft:air','r08/warehouse/central_aisle','owned')
for x in (1308,1356):
    z=392;p.chest(x+2,69,z+4,[('minecraft:iron_ingot',64),('minecraft:leather',32)],'r08/container/storage')
    p.put(x+2,69,z+4,'minecraft:chest[facing=north,type=single,waterlogged=false]','r08/container/storage','owned')
p.apply('service_access')
path=OUT/'port_detail_walk_cases.json';cases=json.loads(path.read_text(encoding='utf8'))
for c in cases:
    if c['id'].startswith('r08/detail/port/warehouse'):
        c['path']=[[1272.5,69,396.5],[1272.5,69,342.5],[1288.5,69,342.5]]
        if c['id'].endswith('/return'):c['path'].reverse()
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
