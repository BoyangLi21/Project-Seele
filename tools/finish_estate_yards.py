"""Sparse service yards, shelters and lighting for the old apartment estate."""
import argparse,json
import numpy as np
import regional_voxels as vox
from quality_structures import Builder,OUT,CASES,walk
from quality_landscape import tree as organic_tree
from regional_architecture import *

def build():
    p=Builder();name='kirisato/yard';f=70
    for i,(x,z) in enumerate([(-2758,-1080),(-2680,-1036),(-2840,-1036)]):organic_tree(p,x,z,f,name,100+i)
    for x in (-2820,-2752,-2718):bench(p,x,-1050,f,name,'north')
    for x,z in [(-2888,-1128),(-2616,-1128),(-2888,-992),(-2616,-992),(-2812,-1048),(-2762,-1064),(-2672,-1048)]:
        p.fill(x,70,z,x,70,z,DARK,name)
        p.fill(x,71,z,x,75,z,'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]',name)
        p.fill(x,76,z,x,76,z+1,'minecraft:polished_blackstone_slab[type=bottom,waterlogged=false]',name)
        p.put(x,75,z+1,'minecraft:lantern[hanging=true,waterlogged=false]',name)
    # Shallow bicycle shelters sit clear of the apartment entrance walks.
    for x,z in [(-2856,-1028),(-2732,-1028)]:
        p.fill(x,70,z,x+14,70,z+5,FLOOR,name)
        p.fill(x-1,75,z-1,x+15,75,z+6,'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]',name)
        for xx in (x,x+14):
            for zz in (z,z+5):p.fill(xx,71,zz,xx,74,zz,'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]',name)
        for xx in range(x+3,x+13,3):p.fill(xx,71,z+4,xx,71,z+5,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]',name)
        walk(name+'/shelter/'+str(x),[x+2.5,71,z+1.5],[x+12.5,71,z+1.5])
    p.fill(-2636,70,-1051,-2623,70,-1039,FLOOR,name+'/waste')
    for x in (-2636,-2623):p.fill(x,71,-1051,x,72,-1039,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]',name)
    for z in (-1051,-1039):p.fill(-2636,71,z,-2623,72,z,'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]',name)
    p.fill(-2631,71,-1051,-2627,73,-1051,AIR,name)
    for x in (-2634,-2631,-2627):p.put(x,71,-1041,'minecraft:composter[level=0]',name)
    p.fill(-2626,71,-1051,-2624,73,-1051,WALL,name)
    p.sign(-2625,72,-1052,['資源回収','集積所','RECYCLING',''],name)
    walk(name+'/waste_entry',[-2629.5,71,-1053.5],[-2629.5,71,-1044.5])
    # Vehicular through traffic uses the existing southern block around S2.
    for x in (-1552,-1440):
        p.fill(x,105,756,x,108,756,WALL,'S2/road_wayfinding')
        p.sign(x,107,755,['S2 駅前','車道は南側へ','ROAD VIA SOUTH','歩行者入口'], 'S2/road_wayfinding')
    # Decorative vegetation cannot overwrite a verified road or house approach.
    a=np.load(OUT/'extension_road_surfaces.npz');ox,oz=map(int,a['origin']);mask=a['mask']
    for z in range(-1140,-980):
        for x in range(-2900,-2600):
            if mask[z-oz,x-ox]:p.protect((x,71,z,x,84,z),'verified_estate_road')
    vox.OUT=OUT;return p

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build()
    (OUT/'walk_cases_estate_yards.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf-8')
    p.apply('estate_yards') if args.apply else p.save_plan('estate_yards')
