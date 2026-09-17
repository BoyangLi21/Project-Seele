"""Remove measured obstructions from owned lift sweeps, retaining the real cabins."""
import argparse,json
from collections import Counter
import nbtlib
import regional_voxels as vox
from query_blocks import read_box,iter_block_entities,AIR

OUT=vox.ROOT/'artifacts/world_rebuild_r20/lifts'

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();groups=[];records=[]
    raw=nbtlib.load(vox.WORLD/'dimensions/projectseele/geofront/data/capabilities.dat')['data']['movingelevators:elevator_groups']
    for key,value in raw.items():
        g=value['group'];assert not int(g['isMoving']),('Park native car before offline repair',key)
        x,z=map(int,key.split(';'));floors=list(map(int,g['floors']));state=read_box(vox.WORLD,vox.DIM,(x,min(floors),z),(x,min(floors),z))[(x,min(floors),z)]
        groups.append({'key':key,'floors':floors,'sizes':[int(g[k]) for k in ('cageSizeX','cageSizeY','cageSizeZ')],'controller_state':state})
    for g in groups:
        if g['key']=='97;-15':continue  # Explicitly retired with its observation corridor.
        sx,sy,sz=g['sizes'];valid={'minecraft:polished_deepslate','projectseele:nerv_structural_panel'}
        if sx>7:valid.add('minecraft:smooth_stone')
        x,z=map(int,g['key'].split(';'));face=g['controller_state'].split('facing=')[1].split(']')[0];dx,dz={'east':(1,0),'west':(-1,0),'south':(0,1),'north':(0,-1)}[face]
        cx=x+dx*(sx//2+1);cz=z+dz*(sz//2+1);rows=[]
        for y in g['floors']:
            lo=(cx-sx//2,y-1,cz-sz//2);hi=(cx+sx//2,y+sy-2,cz+sz//2);cells=read_box(vox.WORLD,vox.DIM,lo,hi);floor=dict(Counter(s for q,s in cells.items() if q[1]==lo[1]))
            rows.append({'group':g['key'],'center':[cx,y,cz],'floor_y':y,'bounds':[lo,hi],'floor':floor})
        cars=[r for r in rows if sum(r['floor'].values())==sx*sz and set(r['floor'])<=valid]
        assert len(cars)==1,('No unique complete cabin floor',g['key'],cars)
        car=cars[0];cx,_,cz=car['center'];carlo,carhi=car['bounds'];lo=(cx-sx//2,min(g['floors'])-1,cz-sz//2);hi=(cx+sx//2,max(g['floors'])+sy-2,cz+sz//2)
        b=read_box(vox.WORLD,vox.DIM,lo,hi);be=dict(iter_block_entities(vox.WORLD,vox.DIM,lo,hi));removed=Counter();held=[]
        for q,s in b.items():
            if all(carlo[i]<=q[i]<=carhi[i] for i in range(3)) or s.split('[')[0] in AIR:continue
            if q in be:held.append({'pos':q,'id':str(be[q]['id'])});continue
            p.match((*q,*q),s,'minecraft:air','r20/restore_owned_lift_travel_space');removed[s]+=1
        # The inherited command car had no roof inside the native capture box.
        # Complete that box; do not extend it into a different landing.
        roof_added=0
        if g['key']=='9;253':
            for x in range(carlo[0],carhi[0]+1):
                for z in range(carlo[2],carhi[2]+1):
                    q=(x,carhi[1],z);s=b[q]
                    if s.split('[')[0] in AIR:p.match((*q,*q),s,'minecraft:smooth_quartz','r20/complete_captured_command_cabin_roof');roof_added+=1
        records.append({'group':g['key'],'sweep':[lo,hi],'retained_cabin':car,'obstructions':dict(removed),'held_block_entities':held,'roof_added':roof_added})
    assert not any(r['held_block_entities'] for r in records),records
    p.meta.update(lifts=records,dynamic_sweeps_excluded_from_future_floor_filling=True)
    name='clear_owned_lift_sweeps'+('_review' if vox.WORLD.name=='SEELE_R20_REVIEW' else '')
    p.apply(name) if apply else p.save_plan(name)
    if vox.WORLD.name!='SEELE_R20_REVIEW':(OUT/'sweep_masks.json').write_text(json.dumps(records,indent=2))
    print([(r['group'],sum(r['obstructions'].values()),r['roof_added']) for r in records])

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
