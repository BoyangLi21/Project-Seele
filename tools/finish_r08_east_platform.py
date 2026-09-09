"""Replace the measured suspended earth fill under the east platform with a steel substructure."""
import json
import numpy as np
import regional_voxels as v
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT;p=v.Painter();d=np.load(OUT/'facilities/east_platform_before.npz');a=d['blocks'];pal=d['palette'];lo=d['lo']
natural={s for s in pal if s.split('[')[0] in ('minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand')}
for state in natural:p.match((136,-449,263,159,-445,400),str(state),'minecraft:air','r08/east_platform/retire_earth')
# The walking deck at Y-444 is untouched. The top box section and transverse webs carry it.
p.fill(136,-446,263,159,-445,400,'minecraft:gray_concrete','r08/east_platform/underside','new')
for x in (137,158):p.fill(x,-448,263,x,-447,400,'minecraft:polished_deepslate','r08/east_platform/longitudinal','new')
for z in range(267,401,20):p.fill(136,-448,z,159,-447,z,'minecraft:polished_deepslate','r08/east_platform/cross_web','new')
cases=json.loads((v.WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));columns=[]
for z in (270,298,326,354,382,398):
    x=158;blocked=[]
    for case in cases:
        pts=case.get('path',[case.get('start'),case.get('end')])
        if any(q is None for q in pts):continue
        for q,r in zip(pts,pts[1:]):
            if min(q[0],r[0])-2<=x<=max(q[0],r[0])+2 and min(q[2],r[2])-2<=z<=max(q[2],r[2])+2 and max(q[1],r[1])+3>=-465 and min(q[1],r[1])<=-448:blocked.append(case['id'])
    if blocked:continue
    p.fill(x,-465,z,x+1,-449,z+1,'minecraft:polished_deepslate','r08/east_platform/column','new');columns.append([x,z])
p.meta.update(retired_earth_cells=int(np.array([s in natural for s in pal])[a].sum()),walking_deck_preserved_y=-444,columns=columns)
p.apply('east_platform_structure')
cases=[dict(id='r08/structure/east_platform_maintenance',path=[[150.5,-465,270.5],[150.5,-465,390.5]])]
cases.append(dict(id=cases[0]['id']+'/return',path=cases[0]['path'][::-1]))
(OUT/'structure_walk_cases.json').write_text(json.dumps(cases,indent=2),encoding='utf8')
