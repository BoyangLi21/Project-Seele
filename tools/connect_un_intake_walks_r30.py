"""Restore the measured transverse apron route and remove obsolete step lips."""
import argparse
import regional_voxels as v
from query_blocks import read_box
WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/un_intake_ports'
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();b=read_box(WORLD,v.DIM,(6255,76,-6123),(6311,79,-6107))
    bars='minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]'
    for z in range(-6123,-6117):
        q=(6309,77,z);assert b[q]==bars and b[6310,76,z]=='projectseele:nerv_floor_panel',(q,b[q]);p.match((*q,*q),bars,'minecraft:air','r30/intake_east_pedestrian_port')
    for x in range(6256,6309):
        q=(x,77,-6109)
        # Keep the existing marker's full column and both perimeter rail bases.
        if x!=6262 and b[q]=='minecraft:light_gray_concrete':p.match((*q,*q),b[q],'minecraft:air','r30/obsolete_apron_step_lip')
        q=(x,76,-6107)
        if 'smooth_quartz_stairs' in b[q]:p.match((*q,*q),b[q],'minecraft:light_gray_concrete','r30/level_intake_walk')
    p.meta['walk_nodes']=[{'id':'r30/intake_transverse_east_return','path':[[6378.5,77,-6120.5],[6270.5,77,-6120.5]]}]
    p.save_plan('intake_pedestrian_ports')
    if apply:p.apply('intake_pedestrian_ports')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
