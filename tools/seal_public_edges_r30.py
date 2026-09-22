"""Seal measured public-room exterior edges, preserving railway/lift ports."""
import argparse,json
from pathlib import Path
import regional_voxels as v
from query_blocks import read_box,AIR

WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/public_edges'

def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    rooms=[('hangar_station_east_north',192,-442,-433,-55,-45),('hangar_station_east_south',192,-442,-433,-35,-25),('pyramid_lower_east',127,-461,-453,263,290)]
    for name,x,foot,top,z0,z1 in rooms:
        b=read_box(WORLD,v.DIM,(x-2,foot-1,z0),(x+1,top+1,z1))
        for z in range(z0,z1+1):
            assert b[x,foot-1,z] in {'minecraft:smooth_stone','minecraft:light_gray_concrete'},(name,z,'support',b[x,foot-1,z])
            assert b[x,top+1,z] not in AIR,(name,z,'roof')
            for y in range(foot,top+1):
                old=b[x,y,z]
                if old not in AIR:continue
                frame=y in [foot,foot+1,top] or z in [z0,z1] or (z-z0)%6==0
                state='projectseele:nerv_structural_panel' if frame else 'projectseele:clear_glass'
                p.match((x,y,z,x,y,z),old,state,'r30/'+name)
        p.meta['rooms'].append({'id':name,'exterior_plane':[x,foot,z0,x,top,z1],'floor':foot,'evidence':'native collision floor edge + measured supported slab + continuous roof; outside is unsupported void','rail_port_preserved':[-43,-37] if name.startswith('hangar') else [291,297]})
        p.meta['walk_nodes'].extend([{'id':name+'/along','start':[x-1.5,foot,z0+1.5],'end':[x-1.5,foot,z1-1.5]}, {'id':name+'/return','start':[x-1.5,foot,z1-1.5],'end':[x-1.5,foot,z0+1.5]}])
    p.save_plan('public_room_enclosure')
    if apply:p.apply('public_room_enclosure')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
