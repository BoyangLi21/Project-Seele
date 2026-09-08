"""Add working MTR ticket machines and suspended clocks in measured station pockets."""
import argparse,json
import numpy as np
import nbtlib
from scipy.spatial import cKDTree
import regional_voxels as vox
from quality_structures import Station
from scan_regional_completion import volume,AIR

OUT=vox.ROOT/'artifacts/world_motion_r06/station_fittings'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
def main(apply=False):
    cases=load(vox.ROOT/'artifacts/world_motion_r06/all_walk_cases.json');points=[]
    for case in cases:
        path=case.get('path',[case.get('start'),case.get('end')])
        for aa,bb in zip(path,path[1:]):
            a=np.array(aa);b=np.array(bb);points.extend(a+(b-a)*np.linspace(0,1,max(2,int(np.linalg.norm(b-a))+1))[:,None])
    paths=cKDTree(points);vox.OUT=OUT;p=vox.Painter();placed=[];new_cases=[]
    data=[d for d in load(vox.ROOT/'artifacts/world_expansion_20260907/transit_plan.json')['platforms'] if d.get('mode')!='AIRPLANE']
    data+=load(vox.ROOT/'artifacts/world_quality_r02/extension_plan.json')['transit']['platforms']
    for d in data:
        s=Station(p,d);f=s.y;h=s.half;side=10 if d.get('compact') else 15;owner='r06/'+s.owner+'/ticket_bank'
        a=s.xyz(-h,f,-side);b=s.xyz(h,f+12,side);lo=np.minimum(a,b);hi=np.maximum(a,b);blocks,pal=volume(lo,hi)
        def state(pos):
            x,y,z=map(int,np.array(pos)-lo);return pal[blocks[y,z,x]]
        bank=None
        for u in [h-14,h-20,-h+14,-h+22]:
            for sign in (-1,1):
                v=sign*(side-1);positions=[s.xyz(u+k,f+dy,v) for k in (0,1) for dy in (1,2)]
                approach=[s.xyz(u+k,f+1,v-sign*n) for k in (0,1) for n in (1,2,3)]
                if any(state(pos)!='minecraft:air' for pos in positions+approach):continue
                if any(state(s.xyz(u+k,f,v)).split('[')[0] in AIR for k in (0,1)):continue
                if min(paths.query(np.array(positions)[::2]+[.5,0,.5])[0])<1.05:continue
                bank=(u,v,sign);break
            if bank:break
        if bank is None:raise RuntimeError('No measured station ticket pocket '+s.owner)
        # MTR's south state is the unrotated model, whose screen faces north.
        u,v,sign=bank;facing=('south' if sign>0 else 'north') if s.horizontal else ('east' if sign>0 else 'west')
        for k in (0,1):
            for dy,half in ((1,'lower'),(2,'upper')):
                pos=s.xyz(u+k,f+dy,v);p.match((*pos,*pos),'minecraft:air',f'mtr:ticket_machine[facing={facing},half={half}]',owner)
        clock=s.xyz(u,f+5,v-sign)
        if state(clock)!='minecraft:air':raise RuntimeError(('Clock clearance',clock))
        p.match((*clock,*clock),'minecraft:air',f'mtr:clock[facing={str(not s.horizontal).lower()}]',owner+'/clock')
        x,y,z=clock;p.block_entities[clock]=nbtlib.Compound({'id':nbtlib.String('mtr:clock'),'x':nbtlib.Int(x),'y':nbtlib.Int(y),'z':nbtlib.Int(z)})
        for y in range(f+6,f+11):
            pos=s.xyz(u,y,v-sign)
            if state(pos)=='minecraft:air':p.match((*pos,*pos),'minecraft:air','minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]',owner+'/clock_hanger')
        a=np.array(s.xyz(u,f+1,v-sign*3),float)+[.5,0,.5];b=np.array(s.xyz(u,f+1,v-sign),float)+[.5,0,.5]
        new_cases.extend([dict(id=owner+suffix,start=x.tolist(),end=y.tolist()) for suffix,x,y in [('',a,b),('/return',b,a)]])
        placed.append(dict(station=d['id'],tickets=[s.xyz(u+k,f+1,v) for k in (0,1)],clock=clock,facing=facing))
    p.meta.update(stations=placed,ticket_machines=len(placed)*2,clocks=len(placed),route_clearance='All original and R06 native route centre lines remain clear')
    p.apply('fittings') if apply else p.save_plan('fittings')
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'walk_cases.json').write_text(json.dumps(new_cases,indent=2))
    print('Fitted',len(placed),'stations',flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
