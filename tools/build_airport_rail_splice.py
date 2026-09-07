"""Seal the retired side-entry tunnel and line the validated smooth approach."""
import json,argparse,math
import regional_voxels as vox
from quality_structures import Builder,OUT,OLD,load
from regional_architecture import AIR,DARK,WALL,LIGHT

def build():
    p=Builder();old=load(OLD/'transit2/track_samples.json');ids={r['id'] for r in load(OUT/'airport_rail_splice.json')['additions']}
    new=[r for r in load(OUT/'airport_rail_splice_prototype/track_samples.json') if r['id'] in ids]
    if len(new)!=5:raise RuntimeError('Native splice geometry incomplete')
    # Retain the completed platform building and all other existing train bodies.
    station=(-1728,62,-280,-1612,79,-250);p.protect(station,'retained_airport_station')
    for rail in old:
        if rail['id']=='S1_section_1_underpass' or rail['mode']!='TRAIN':continue
        for point in rail['points'][::2]:
            x,y,z=math.floor(point[0]),round(point[1]),math.floor(point[2])
            if -1840<=x<=-1680 and -300<=z<=150 and y>=0:p.protect((x-2,y,z-2,x+2,y+5,z+2),'retained_train_body')
    obsolete=next(r for r in old if r['id']=='S1_section_1_underpass')
    for point in obsolete['points']:
        x,y,z=math.floor(point[0]),round(point[1]),math.floor(point[2]);p.fill(x-4,y-3,z-4,x+4,y+7,z+4,'minecraft:stone','S1/retire_side_entry')
    clear=[];lights=[]
    for rail in new:
        for i,point in enumerate(rail['points']):
            x,y,z=math.floor(point[0]),round(point[1]),math.floor(point[2])
            p.fill(x-4,y-3,z-4,x+4,y+7,z+4,WALL,'S1/smooth_tunnel_shell')
            p.fill(x-3,y-2,z-3,x+3,y-1,z+3,DARK,'S1/smooth_tunnel_bed')
            clear.append((x-3,y,z-3,x+3,y+5,z+3))
            if i%16==0:lights.append((x,y+6,z))
    for box in clear:p.fill(*box,AIR,'S1/smooth_vehicle_space')
    for x,y,z in lights:p.put(x,y,z,LIGHT,'S1/tunnel_light')
    p.meta['rail_replacement']=dict(retired='S1_section_1_underpass',added=sorted(ids),minimum_curve_radius=40,platform_route_ids_preserved=True)
    vox.OUT=OUT;return p

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build()
    p.apply('airport_rail_splice') if args.apply else p.save_plan('airport_rail_splice')
