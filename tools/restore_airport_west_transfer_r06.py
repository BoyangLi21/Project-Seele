"""Reconnect the original west subway to the rebuilt airport platform's lower floor."""
import argparse,json
import numpy as np
import regional_voxels as vox
from scan_regional_completion import volume

OUT=vox.ROOT/'artifacts/world_motion_r06/airport_west_transfer';OUT.mkdir(parents=True,exist_ok=True)
LO=(646,64,1175);HI=(699,80,1186)
def main(apply=False):
    if any((OUT/'connection').glob('applied_*')):
        raise RuntimeError('This measured repair already has a receipt; retain its original before snapshot')
    blocks,pal=volume(LO,HI);np.savez_compressed(OUT/'before.npz',blocks=blocks,palette=np.array(pal),lo=LO,hi=HI)
    changes={}
    def old(x,y,z):return pal[blocks[y-LO[1],z-LO[2],x-LO[0]]]
    def fill(x0,y0,z0,x1,y1,z1,state):
        for y in range(y0,y1+1):
            for z in range(z0,z1+1):
                for x in range(x0,x1+1):changes[x,y,z]=state
    floor='projectseele:nerv_floor_panel';wall='projectseele:nerv_wall_panel'
    # The original tunnel ends six blocks above the new platform. Its west
    # junction also crosses the wall of the retained north/south subway.
    fill(653,72,1178,653,75,1182,'minecraft:air')
    fill(654,71,1177,681,71,1183,floor)
    for z in (1176,1184):
        fill(654,71,z,681,75,z,wall)
        fill(654,73,z,681,73,z,'projectseele:nerv_wall_datum')
    fill(654,76,1176,681,76,1184,'minecraft:polished_deepslate')
    for x in range(657,680,8):fill(x,76,1179,x+2,76,1181,'projectseele:nerv_strip_light')
    # A proper stair run lands on the existing Y65 deck; the upper tunnel
    # never becomes an unguarded drop into the platform.
    for x in range(682,688):
        f=71-(x-682)
        fill(x,65,1178,x,f-1,1182,wall)
        fill(x,f,1178,x,f,1182,'minecraft:polished_andesite_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]')
        fill(x,f+1,1178,x,f+4,1182,'minecraft:air')
        for z in (1177,1183):
            fill(x,65,z,x,f,z,wall)
            fill(x,f+1,z,x,f+1,z,'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]')
    for x in range(690,693):
        chair=old(x,66,1180)
        if not chair.startswith('another_furniture:dark_oak_chair[') or old(x,66,1176)!='minecraft:air':raise RuntimeError('Airport seat precondition')
        changes[x,66,1180]='minecraft:air';changes[x,66,1176]=chair
    vox.OUT=OUT;p=vox.Painter()
    for pos,state in sorted(changes.items()):
        before=old(*pos)
        if before==state:continue
        if any(t in before for t in ('mtr:','movingelevators:','_sign[','chest','door[')):
            raise RuntimeError(('Protected apparatus',pos,before))
        p.match((*pos,*pos),before,state,'r06/airport/west_transfer')
    p.meta.update(cause='R02 platform rebuilt at Y65 while original transfer remained at Y71',
                  entrance=[650.5,72,1180.5],exit=[698.5,66,1180.5],stair_width=5,relocated_chairs=3)
    p.apply('connection') if apply else p.save_plan('connection')
    route=[[650.5,72,1180.5],[680.5,72,1180.5],[688.5,66,1180.5],[698.5,66,1180.5]]
    cases=[dict(id='r06/airport/west_transfer'+suffix,path=path) for suffix,path in [('',route),('/return',route[::-1])]]
    (OUT/'walk_cases.json').write_text(json.dumps(cases,indent=2))
    if apply:
        after,palette=volume(LO,HI)
        for (x,y,z),state in changes.items():
            if palette[after[y-LO[1],z-LO[2],x-LO[0]]]!=vox.canonical_state(state):raise RuntimeError(('Readback',x,y,z))
        print('Airport transfer readback verified',len(p.ops),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
