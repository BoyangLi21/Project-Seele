"""Remove isolated old-room trims beyond its ellipsoid and match the existing gallery finish."""
import argparse
import numpy as np
import regional_voxels as v
from scan_regional_completion import volume
from retire_r09_dogma_sphere import held
v.OUT=v.ROOT/'artifacts/world_refinement_r09'
def main(apply=False):
    lo=(-40,-631,240);hi=(102,-528,405);a,pal=volume(lo,hi);p=v.Painter();retired=0
    mask=np.array([s.split('[')[0] in ('minecraft:deepslate_bricks','minecraft:polished_basalt') for s in pal])[a]
    for iy,iz,ix in np.argwhere(mask):
        x,y,z=int(ix+lo[0]),int(iy+lo[1]),int(iz+lo[2])
        if held(x,y,z):continue
        assert z<265,(x,y,z)
        before=pal[a[iy,iz,ix]]
        p.match((x,y,z,x,y,z),before,'minecraft:stone','r09/retire_old_north_trim');retired+=1
    # R06 refined the top surface after R04; match its measured adjacent finish.
    adjacent=pal[a[-567-lo[1],280-lo[2],80-lo[0]]];assert adjacent=='minecraft:gray_concrete'
    for x in range(66,80):
        for z in range(269,282):
            before=pal[a[-567-lo[1],z-lo[2],x-lo[0]]]
            assert before in ('minecraft:polished_deepslate',adjacent)
            p.match((x,-567,z,x,-567,z),before,adjacent,'r09/match_existing_gallery_finish')
    p.meta.update(retired_trim_cells=retired,retained_old_material='Actual lift frame at x8..16, never the retired sphere',gallery_finish=adjacent)
    p.apply('dogma_finish') if apply else p.save_plan('dogma_finish')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
