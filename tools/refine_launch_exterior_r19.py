"""Reference-led launch buttresses outside the wet cages and all three clear shafts."""
import argparse,json,math
import numpy as np
import regional_voxels as vox
from scan_regional_completion import volume
from query_blocks import AIR

OUT=vox.ROOT/'artifacts/world_repair_r19/launch_exterior'
LO=(-34,-470,-56);HI=(94,-354,-18)
EDGE='projectseele:nerv_machine_edge';FRAME='projectseele:nerv_structural_panel';GREEN='projectseele:nerv_machine_panel';HAZARD='projectseele:nerv_machine_hazard'

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();a,pal=volume(LO,HI);changes={};held=[]
    def old(x,y,z):return pal[int(a[y-LO[1],z-LO[2],x-LO[0]])]
    def put(x,y,z,state,owner):
        before=old(x,y,z);base=before.split('[')[0]
        if before==state:return
        allowed=base in AIR|{EDGE,FRAME,GREEN,'projectseele:nerv_floor_panel','projectseele:nerv_shaft_panel','minecraft:light_gray_concrete','minecraft:polished_basalt','minecraft:deepslate_brick_wall'}
        if not allowed:held.append(dict(pos=[x,y,z],state=before,desired=state));return
        changes[x,y,z]=(before,state,owner)
    # Each inter-lane structural web sits in the 11 m separation between the
    # 31 m shaft cores. It is outside Z=-55, the retained wet-cage boundary.
    for centre in (9,51):
        for y in range(-443,-368):
            front=-54+math.floor(32*(1-(y+443)/75))
            for x in range(centre-2,centre+3):
                for z in range(-54,front+1):
                    surface=x in (centre-2,centre+2) or z==front
                    material=GREEN if surface and (y+443)%12==0 else EDGE if surface else FRAME
                    put(x,y,z,material,'r19/launch_interlane_buttress')
        for x in range(centre-2,centre+3):
            for z in range(-54,-21):
                support=next((y for y in range(-444,-471,-1) if old(x,y,z).split('[')[0] not in AIR|{'minecraft:light','minecraft:water','projectseele:lcl'}),None)
                if support is None:raise RuntimeError(('Unmeasured buttress foundation',x,z))
                for y in range(support+1,-443):put(x,y,z,FRAME,'r19/buttress_foundation')
        put(centre,-443,-54,HAZARD,'r19/buttress_model_anchor')
    # Exterior facing is added only against an existing opaque structural
    # wall. Pressure-door barriers, openings, glass and the entire interior
    # remain unchanged. The visible rhythm follows the model reference.
    opaque={EDGE,FRAME,GREEN,'projectseele:nerv_shaft_panel','minecraft:polished_deepslate','minecraft:iron_block','minecraft:black_concrete'}
    for x in range(-32,94):
        for y in range(-443,-354):
            if old(x,y,-55).split('[')[0] not in opaque or old(x,y,-54).split('[')[0] not in AIR:continue
            put(x,y,-54,GREEN if (x+33)%21 in (0,1) or (y+443)%12==0 else EDGE,'r19/launch_outer_wall_panels')
    for centre in (9,51):put(centre,-443,-54,HAZARD,'r19/buttress_model_anchor')
    # Reject any newly occupied voxel intersecting an established walking
    # route. This is a geometric gate, not a replacement for native testing.
    collisions=[]
    for case in json.loads((vox.WORLD/'quality_walk_cases.json').read_text(encoding='utf8')):
        path=case.get('path',[case.get('start'),case.get('end')])
        for aa,bb in zip(path,path[1:]):
            if any(max(aa[i],bb[i])<LO[i] or min(aa[i],bb[i])>HI[i] for i in range(3)):continue
            for q in np.linspace(aa,bb,max(2,int(np.linalg.norm(np.asarray(bb)-aa)*4)+1)):
                for x in range(math.floor(q[0]-.31),math.floor(q[0]+.31)+1):
                    for z in range(math.floor(q[2]-.31),math.floor(q[2]+.31)+1):
                        for y in range(math.floor(q[1]+.02),math.floor(q[1]+1.8)+1):
                            if (x,y,z) in changes and changes[x,y,z][0].split('[')[0] in AIR:collisions.append((case['id'],x,y,z))
    if collisions:raise RuntimeError(('Proposed detail blocks a retained route',collisions[:12]))
    for pos,(before,after,owner) in sorted(changes.items()):p.match((*pos,*pos),before,after,owner)
    for cx in (-12,30,72):p.protect((cx-15,-443,-51,cx+15,-354,-21),'retained_31x31_launch_core')
    p.meta.update(reference='User video BV1fsRaBoE6i, SMALL WORLDS launch model: inter-lane buttresses, segmented pale metal walls, red service pipes',
        buttress_centres=[9,51],cage_boundary_z=-55,interior_untouched=True,canonical_routes_intersecting=0,held=held)
    p.apply('reference_facade') if apply else p.save_plan('reference_facade')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
