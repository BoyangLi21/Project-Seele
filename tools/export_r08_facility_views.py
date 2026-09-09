"""Full envelopes and clearly separated drawing cuts, all read from the current save."""
from pathlib import Path
import sys,json,msvcrt,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.Codex/3d-sections'))
import export_sections as g
OUT=ROOT/'artifacts/world_refinement_r08/facilities';g.OUT=OUT
g.SHAPES['projectseele:lcl[level=0]']=[[0,0,0,1,1,1]]
old=g.rgb
def colour(s):
    if s.startswith('projectseele:lcl'):return (190,130,49)
    if 'black_concrete' in s:return (25,28,29)
    if 'blackstone' in s:return (49,54,56)
    if 'nerv_wall' in s:return (177,181,171)
    if 'nerv_floor' in s:return (163,174,170)
    if 'nerv_strip_light' in s:return (216,229,192)
    return old(s)
g.rgb=colour
def reset():
    for x in (g.VERTS,g.FACES,g.MATS,g.COLORS,g.CODES,g.COUNTS):x.clear()
def save(a,p,lo,mask,name):
    reset();g.mesh(a,p,lo,np.broadcast_to(mask,a.shape).copy(),name);g.save(name)
def main():
    lock=(g.WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    lo=(-94,-467,203);hi=(154,-286,451);a,p=g.volume(lo,hi);x,y,z=g.coordinates(lo,hi)
    save(a,p,lo,y>=-467,'pyramid_exterior')
    save(a,p,lo,(x<=30)&(y>=-467),'pyramid_x_section')
    save(a,p,lo,(z<=327)&(y>=-467),'pyramid_z_section')
    # Include the complete double roof and the start of each black launch riser.
    lo=(-55,-467,-151);hi=(162,-320,14);a,p=g.volume(lo,hi);x,y,z=g.coordinates(lo,hi)
    save(a,p,lo,y>=-467,'hangar_exterior')
    mask=np.ones(a.shape,bool)
    for cx in (-12,30,72):mask&=~((x>cx)&(x<=cx+19)&(z>=-137)&(z<=-19)&(y>-443))
    mask&=~((y>=-355)&(z<-55));mask&=~((x>111)&(z<-55)&(y>-442))
    save(a,p,lo,mask,'hangar_bay_section')
    save(a,p,lo,(z<=-95)&(y>=-447),'hangar_cross_section')
    lo=(-39,-610,242);hi=(100,-528,405);a,p=g.volume(lo,hi);x,y,z=g.coordinates(lo,hi)
    # Bedrock/geologic host below the salt lake is excluded, never room walls.
    save(a,p,lo,y>=-603,'dogma_exterior')
    save(a,p,lo,(y>=-603)&(y<=-533)&(x<95)&((z>=268)|((x>=6)&(x<=18))),'dogma_entrance_section')
    save(a,p,lo,(x<=30)&(y>=-603),'dogma_longitudinal_section')
    reset()
    for lo,hi in [((-55,-467,-151),(162,25,14)),((-94,-467,203),(154,-286,451)),((86,-471,-68),(201,-430,551))]:
        a,p=g.volume(lo,hi);x,y,z=g.coordinates(lo,hi);keep=np.ones(a.shape,bool)
        # View-only exclusion of geologic host, and overlap already included above.
        natural=np.array([s.split('[')[0] in ('minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:sand','minecraft:gravel') for s in p]);keep&=~natural[a]
        if lo[0]==86:keep&=~(((z<=14)&(x<=162))|((z>=203)&(z<=451)&(x<=154)))
        g.mesh(a,p,lo,keep,'layout_part_'+str(lo))
    g.save('hq_to_launch_exterior')
    (OUT/'source.json').write_text(json.dumps(dict(world=str(g.WORLD),dimension=g.DIM,level_sha256=hashlib.sha256((g.WORLD/'level.dat').read_bytes()).hexdigest(),equal_xyz_scale=True,world_mutated=False,geometry='Saved block collision shapes; moving entities shown only in native photos',cuts=dict(pyramid_x='X<=30, west half retained',pyramid_z='Z<=327, north half retained',hangar='exterior top cropped at Y-320; cutaway roofs and selected side walls omitted only in drawings',dogma='geologic host below Y-603 omitted; alternate pressure-wall and longitudinal cuts')),ensure_ascii=False,indent=2),encoding='utf8')
    msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()
if __name__=='__main__':main()
