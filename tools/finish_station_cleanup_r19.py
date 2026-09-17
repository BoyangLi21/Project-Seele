"""Correct S2 seats that were classified before the extension catalogue was loaded."""
import argparse,json,re
import regional_voxels as vox
from query_blocks import read_box

def main(apply=False):
    vox.OUT=vox.ROOT/'artifacts/world_repair_r19/stations';p=vox.Painter()
    platforms=json.loads((vox.ROOT/'artifacts/world_quality_r02/extension_plan.json').read_text(encoding='utf8'))['transit']['platforms']
    for station in platforms:
        x,y,z=station['center'];half=station['length']//2+20
        horizontal=station['heading'] in ('E','W');dx,dz=(half,25) if horizontal else (25,half)
        for pos,state in read_box(vox.WORLD,vox.DIM,(x-dx,y-1,z-dz),(x+dx,y+13,z+dz)).items():
            if state.startswith('projectseele:residential_chair['):
                p.match((*pos,*pos),state,state.replace(':residential_chair[',':station_seat['),'r19/S2_station_seating')
    p.meta.update(reason='S2 extension platform seats use public-station furniture',platforms=[s['id'] for s in platforms])
    p.apply('S2_seat_correction') if apply else p.save_plan('S2_seat_correction')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
