"""Carry the lower personnel gallery beneath the actual U2 railway sweep."""
from pathlib import Path
import json,math
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f,repair_facility_r21 as h
from query_blocks import iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/science_underpass'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT
    f.LO=h.LO=(190,-477,450);f.HI=h.HI=(213,-460,518);s=h.Facility();p=v.Painter()
    s.fill((192,-474,453,200,-462,515),'minecraft:air')
    profile=[]
    for z in range(452,516):
        floor=-467-max(0,min(6,z-452))+max(0,min(6,z-508))
        profile.append([z,floor]);s.fill((192,floor-1,z,200,floor,z),f.STRUCT)
        s.fill((193,floor+1,z,199,floor+4,z),'minecraft:air');s.fill((192,floor+5,z,200,floor+5,z),f.STRUCT)
        for x in (192,200):s.fill((x,floor+1,z,x,floor+4,z),f.WALL)
        state='minecraft:smooth_quartz_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]' if 453<=z<=458 else 'minecraft:smooth_quartz_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]' if 509<=z<=514 else f.FLOOR
        s.fill((193,floor+(1 if 453<=z<=458 else 0),z,199,floor+(1 if 453<=z<=458 else 0),z),state)
        if 464<=z<=500:
            for x,direction in ((194,True),(197,False)):
                for lane in (0,1):
                    orient='landing_bottom' if z==464 else 'landing_top' if z==500 else 'flat';side='left' if lane==0 else 'right'
                    s.fill((x+lane,floor,z,x+lane,floor,z),f'mtr:escalator_step[direction={str(direction).lower()},facing=north,orientation={orient},side={side},status=true]')
        if z%8==0:s.fill((196,floor+4,z,196,floor+4,z),f.LIGHT)
    # The two preserved U2 curves cross above this ceiling, at rail Y=-467.
    # Restore their full lower body/gauge volume after enclosing the subway.
    native=json.loads((WORLD/'native_transit_r28.json').read_text());crossings=[]
    for curve in native['curves']:
        if curve['mode']!='TRAIN':continue
        for xx,yy,zz in curve['points']:
            x,y,z=math.floor(xx),math.floor(yy),math.floor(zz)
            if 189<=x<=212 and 460<=z<=505 and y==-467:
                lo=(max(190,x-2),y,max(450,z-2));hi=(min(213,x+2),y+5,min(518,z+2))
                s.fill((*lo,*hi),'minecraft:air')
                s.fill((lo[0],y-1,lo[2],hi[0],y-1,hi[2]),f.STRUCT);crossings.append([x,y,z])
    assert crossings
    changed=s.before!=s.after
    for q,t in iter_block_entities(WORLD,v.DIM,h.LO,h.HI):
        if changed[q[1]-h.LO[1],q[2]-h.LO[2],q[0]-h.LO[0]]:raise RuntimeError(('Existing fixture',q,str(t['id'])))
    s.delta(p,'r28/grade_separated_science_underpass')
    pts=[[196.5,-466,411.5],[196.5,-466,451.5],[196.5,-472,459.5],[196.5,-472,507.5],[196.5,-466,515.5],[196.5,-466,527.5],[206.5,-466,527.5],[206.5,-466,529.5],[206.5,-460,536.5],[206.5,-460,540.5],[196.5,-460,540.5]]
    walks=[dict(id='r21/science_lower_complete',path=pts),dict(id='r21/science_lower_complete/return',path=pts[::-1])]
    p.meta.update(profile=profile,rail_crossing_samples=len(crossings),walk_nodes=walks);p.apply('science_walk_below_live_rail')
    (OUT/'contract.json').write_text(json.dumps(p.meta,indent=2))
    dest=OUT.parent/'reported/contract.json';data=json.loads(dest.read_text());replace={r['id']:r for r in walks};data['walk_nodes']=[replace.get(r['id'],r) for r in data['walk_nodes']];dest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print('Science underpass below',len(crossings),'native rail samples',flush=True)

if __name__=='__main__':main()
