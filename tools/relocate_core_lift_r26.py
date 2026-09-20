"""Recess the east lift within the measured pyramid and serve all eight room floors."""
from pathlib import Path
import copy,json,math,msvcrt
import numpy as np,nbtlib
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f,repair_facility_r21 as h
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R26_REVIEW';ART=ROOT/'artifacts/facility_r26';OUT=ART/'core_lift'
FLOORS=[-461,-448,-434,-420,-406,-392,-378,-364];CENTRE=(66,302)

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    original=Path(json.loads((ROOT/'artifacts/facility_r25/baseline.json').read_text())['backup'])/'world'
    lo=(69,-450,249);hi=(90,-385,284);now=read_box(WORLD,v.DIM,lo,hi);before=read_box(original,v.DIM,lo,hi)
    keep=set();links=json.loads((ROOT/'artifacts/facility_r25/command_links/contract.json').read_text())['walk_nodes']
    for row in links:
        if 'east_command' not in row['id'] or 'return' in row['id']:continue
        for xx,yy,zz in row['path']:
            x,y,z=math.floor(xx),math.floor(yy),math.floor(zz)
            for X in range(x-2,x+3):
                for Z in range(z-2,z+3):
                    for Y in range(y-2,y+5):keep.add((X,Y,Z))
    oldtags=dict(iter_block_entities(original,v.DIM,lo,hi))
    for q,old in now.items():
        # Retain the old ring gallery east of X=85; retire only the lift's
        # footprint and its former branch, not unrelated room fixtures.
        if q[0]>=85 and q[1]>-443:continue
        if q in keep:continue
        if old!=before[q]:
            p.match((*q,*q),old,before[q],'r26/retire_exterior_east_lift_and_blind_approach')
            if q in oldtags:p.block_entities[q]=copy.deepcopy(oldtags[q])
    # The retained west-turning links no longer have an opening toward the old shaft.
    for y,z in [(-434,265),(-420,262),(-406,257),(-392,267)]:
        for x in range(69,79):
            for Y in range(y,y+4):
                q=(x,Y,z);old=now[q]
                p.match((*q,*q),old,f.WALL if Y in (y,y+3) else 'projectseele:clear_glass','r26/closed_former_lift_branch')
    f.LO=h.LO=(61,-464,296);f.HI=h.HI=(90,-357,372);s=h.Facility();x,z=CENTRE;walks=[]
    s.fill((x-3,FLOORS[0]-2,z-3,x+3,FLOORS[-1]+5,z+3),f.STRUCT)
    for y in FLOORS:
        if y<=-448:
            rects=[(x-2,x+2,z+3,z+9),(x-2,85,z+5,z+9)];ports=[(85,y,308,85,y+2,310)];end=[89.5,y,309.5]
            path=[[66.5,y,308.5],[66.5,y,309.5],end]
        elif y<=-392:
            rects=[(x-2,x+2,z+3,z+9),(x-2,74,z+5,z+9)];ports=[(74,y,308,74,y+2,310)];end=[76.5,y,309.5]
            path=[[66.5,y,308.5],[66.5,y,309.5],end]
        else:
            rects=[(x-2,x+2,z+3,365)];ports=[(65,y,365,67,y+2,365)];end=[66.5,y,367.5]
            path=[[66.5,y,308.5],end]
        ports.append((x-1,y,z+3,x+1,y+2,z+4))
        s.hall('r26/core_lift/'+str(y),rects,y-1,5,ports)
        for rev in (False,True):walks.append(dict(id='r26/core_lift/'+str(y)+('/return' if rev else ''),path=path[::-1] if rev else path))
    s.fill((x-2,FLOORS[0]-1,z-2,x+2,FLOORS[-1]+4,z+2),'minecraft:air')
    y=FLOORS[0];s.fill((x-2,y-1,z-2,x+2,y-1,z+2),'minecraft:polished_deepslate');s.fill((x-2,y+4,z-2,x+2,y+4,z+2),'minecraft:smooth_quartz')
    for X in range(x-2,x+3):
        for Z in range(z-2,z+3):
            if abs(X-x)==2 or abs(Z-z)==2:s.fill((X,y,Z,X,y+3,Z),'minecraft:iron_block')
    s.fill((x-1,y,z+2,x+1,y+2,z+2),'minecraft:light_gray_stained_glass')
    changed=s.before!=s.after
    for q,t in iter_block_entities(WORLD,v.DIM,h.LO,h.HI):
        assert not changed[q[1]-h.LO[1],q[2]-h.LO[2],q[0]-h.LO[0]],('Existing fixture in new core',q,str(t.get('id')))
    s.delta(p,'r26/internal_eight_floor_core');p.meta.update(centre=CENTRE,feet_levels=FLOORS,walk_nodes=walks,retired_group='70;253',new_group='63;302')
    # Every part of the new shaft must remain under the original sloping skin.
    for Y in range(FLOORS[0]-2,FLOORS[-1]+6):
        radius=math.floor(120*(1-(Y+466)/172)+.5)
        assert max(abs(x-3-30),abs(x+3-30),abs(z-3-327),abs(z+3-327))<radius
    p.apply('internal_lift_and_retired_exterior_shaft')
    cap=WORLD/'dimensions/projectseele/geofront/data/capabilities.dat'
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        data=nbtlib.load(cap);groups=data['data']['movingelevators:elevator_groups'];assert '70;253' in groups
        (OUT/'capabilities_before.dat').write_bytes(cap.read_bytes());del groups['70;253'];data.save(cap)
    marker=dict(installed=True,centre=CENTRE,feet_levels=FLOORS,exit='south',retired_group='70;253')
    (WORLD/'facility_lifts_r26.json').write_text(json.dumps(marker,indent=2),encoding='utf8');(OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
    print('Internal eight-floor lift ready',CENTRE,FLOORS)
if __name__=='__main__':main()
