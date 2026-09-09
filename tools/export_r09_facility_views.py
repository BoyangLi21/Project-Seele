"""Updated measured pyramid/Dogma views; geological host is omitted from the drawings."""
import json,msvcrt,shutil,hashlib
import numpy as np
import export_r08_facility_views as previous
g=previous.g
OUT=g.ROOT/'artifacts/world_refinement_r09/facilities';OUT.mkdir(parents=True,exist_ok=True);g.OUT=OUT
old=g.rgb
def colour(state):
    if state.startswith(('projectseele:nerv_pyramid_panel','projectseele:one_way_glass')):return (29,31,32)
    if state.startswith('projectseele:nerv_pyramid_marking'):return (167,34,39)
    return old(state)
g.rgb=colour

def main():
    with (g.WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        lo=(-94,-467,203);hi=(165,-286,451);a,p=g.volume(lo,hi);x,y,z=g.coordinates(lo,hi)
        previous.save(a,p,lo,y>=-467,'pyramid_exterior')
        previous.save(a,p,lo,(x<=30)&(y>=-467),'pyramid_x_section')
        previous.save(a,p,lo,(z<=327)&(y>=-467),'pyramid_z_section')
        lo=(-39,-610,242);hi=(100,-528,405);a,p=g.volume(lo,hi);x,y,z=g.coordinates(lo,hi)
        host=np.array([s.split('[')[0] in ('minecraft:stone','minecraft:deepslate','minecraft:bedrock','minecraft:dirt') for s in p])[a]
        base=(y>=-603)&~host
        previous.save(a,p,lo,base,'dogma_exterior')
        previous.save(a,p,lo,base&(y<=-533)&(x<95)&((z>=268)|((x>=6)&(x<=18))),'dogma_entrance_section')
        previous.save(a,p,lo,base&(x<=30),'dogma_longitudinal_section')
        shutil.copy2(g.ROOT/'artifacts/world_refinement_r08/facilities/lilith_pose.json',OUT/'lilith_pose.json')
        (OUT/'source.json').write_text(json.dumps(dict(world=str(g.WORLD),dimension=g.DIM,level_sha256=hashlib.sha256((g.WORLD/'level.dat').read_bytes()).hexdigest(),equal_xyz_scale=True,world_mutated=False,geometry='Actual saved block collision geometry; one-way panes shown in their exterior opaque state',cuts=dict(pyramid_x='X<=30',pyramid_z='Z<=327',dogma='Geologic host omitted; marked cutaways remove selected pressure walls only in the drawing'),lilith_pose='Saved R08 pose; native R09 photo verifies unchanged placement'),indent=2),encoding='utf8')
if __name__=='__main__':main()
