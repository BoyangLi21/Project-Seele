"""Portable apron stairs aligned to measured native A320 door geometry."""
import argparse,copy,itertools,json,math,msvcrt,shutil
from datetime import datetime
from pathlib import Path
from regional_voxels import WORLD,ROOT
from quality_structures import OUT,OLD,load

def transform(p,model):
    x,y,z=p;angle=model['yaw'];c,s=math.cos(angle),math.sin(angle)
    if abs(model['pitch'])>.0001:raise RuntimeError('Aircraft must be measured at a level gate')
    return [model['x']+x*c+z*s,model['y']+y,model['z']+z*c-x*s]

def plan():
    gates=[]
    for name in ('bay','hakone'):
        source=WORLD/f'quality_aircraft_geometry_{name}.json'
        if source.exists():
            model=load(source);provenance='measured native stopped vehicle'
            if abs(model['head'][1]-model['y'])>.1:
                rail=next(r for r in load(OLD/'transit_plan.json')['rails'] if r['id']==f'F1_{name}_gate')
                x,y,z=rail['to'];model['head']=[x+.5,y,z+.5]
                provenance='measured native body; terminal head corrected from finite platform endpoint'
        elif name=='bay':
            model=copy.deepcopy(load(WORLD/'quality_aircraft_geometry_hakone.json'))
            offset=model['x']-model['head'][0]
            model.update(x=670.5-offset,y=80,z=1240.5,head=[670.5,80,1240.5],yaw=-math.pi/2,pitch=0)
            provenance='predicted mirror of measured car at opposite gate; live boarding still required'
        else:raise RuntimeError('Native aircraft geometry has not been measured')
        doors=[]
        for box in model['doorways']:
            corners=[transform(p,model) for p in itertools.product((box[0],box[3]),(box[1],box[4]),(box[2],box[5]))]
            doors.append(dict(lo=[min(p[i] for p in corners) for i in range(3)],hi=[max(p[i] for p in corners) for i in range(3)]))
        door=min(doors,key=lambda d:d['lo'][2]);centre=(door['lo'][0]+door['hi'][0])/2
        if abs(door['lo'][1]-83)>.001 or not .85<door['hi'][0]-door['lo'][0]<1.15:raise RuntimeError('Unexpected native boarding doorway')
        x=math.floor(centre);z=math.floor(door['lo'][2]);states={}
        # Four half-height steps and a flush landing. They retract as one set
        # before taxiing, so no stationary support remains in the swept wing area.
        for i in range(6):
            zz=z-5+i;h2=min(166,163+i);y=(h2-1)//2
            for xx in range(x-1,x+2):
                for yy in range(81,y):states[xx,yy,zz]='minecraft:gray_concrete'
                states[xx,y,zz]='minecraft:quartz_slab[type=bottom,waterlogged=false]' if h2%2 else 'minecraft:smooth_quartz'
            for xx in (x-2,x+2):
                for yy in range(81,y+1):states[xx,yy,zz]='minecraft:light_gray_concrete'
                states[xx,y+1,zz]='minecraft:gray_stained_glass'
        for xx in range(x-1,x+2):states[xx,82,z]='mtr:platform[door_type=none,facing=south,side=0]'
        gate=dict(id=name,head=model['head'],stairs=[[*p,state] for p,state in sorted(states.items())],
                  entry=[centre,81,z-5.5],landing=[centre,83,z+.5],door=[centre,83,(door['lo'][2]+door['hi'][2])/2],
                  direction='south',native_door=door,survey_source=provenance)
        gates.append(gate)
    result=dict(version=1,gates=gates)
    destination=OUT/'aircraft_boarding_plan.json';destination.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Native boarding plan',[(g['id'],g['head'],g['entry'],g['door'],len(g['stairs'])) for g in gates],flush=True)
    return result

def install(result):
    # Installing this controller plan never places stairs offline. The runtime
    # owns only these listed air cells and checks each before deployment.
    from query_blocks import read_box,AIR
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        # Use the project's shared reader; no second region decoder is permitted.
        for gate in result['gates']:
            positions=[tuple(cell[:3]) for cell in gate['stairs']]
            lo=tuple(min(p[i] for p in positions) for i in range(3));hi=tuple(max(p[i] for p in positions) for i in range(3))
            actual=read_box(WORLD,'projectseele:geofront',lo,hi)
            bad=[(p,actual.get(p)) for p in positions if actual.get(p) not in AIR]
            if bad:raise RuntimeError(f'Boarding volume is not empty: {bad[:10]}')
        dest=WORLD/'regional_boarding_gates.json'
        if dest.exists():
            before=OUT/('boarding_plan_before_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.json');shutil.copy2(dest,before)
        text=json.dumps(result,indent=2);dest.write_text(text,encoding='utf-8')
        if dest.read_text(encoding='utf-8')!=text:raise RuntimeError('Boarding plan readback mismatch')
    print('Installed measured native boarding configuration',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');args=ap.parse_args();result=plan()
    if args.install:install(result)
