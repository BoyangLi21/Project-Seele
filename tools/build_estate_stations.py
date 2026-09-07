"""A country halt and a compact tram interchange fitted between existing lots."""
import argparse,json
import regional_voxels as vox
from quality_structures import Builder,Station,OUT,CASES,load,walk,flat
from quality_circulation import Network
from regional_architecture import *

def compact_station(p,d):
    s=Station(p,d);r=s.y;h=s.half;name=s.owner
    s.fill(-h,r+1,-10,h,r+13,10,AIR)
    s.fill(-h,r-2,-10,h,r-1,10,DARK)
    s.fill(-h,r,-10,h,r,10,FLOOR)
    for v in (-10,10):
        s.fill(-h,r+1,v,h,r+2,v,WHITE)
        s.fill(-h,r+3,v,h,r+7,v,GLASS)
        s.fill(-h,r+8,v,h,r+9,v,DARK)
        for u in range(-h,h+1,14):s.fill(u,r+1,v,u,r+11,v,STEEL)
        s.fill(-3,r+1,v,3,r+5,v,AIR)
        s.fill(-3,r,v+(-1 if v<0 else 1),3,r,v+(-1 if v<0 else 1),'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
    s.fill(-h,r+11,-10,h,r+11,10,DARK)
    s.fill(-h,r+12,-3,h,r+12,3,WALL)
    s.fill(-h,r,-2,h,r+5,2,AIR)
    s.fill(-h,r-1,-2,h,r-1,2,'minecraft:black_concrete')
    for v in (-3,3):s.fill(-h,r,v,h,r,v,'minecraft:yellow_terracotta')
    s.boarding_edges()
    for u in range(-h+5,h-4,12):
        for v in (-6,6):s.fill(u,r+10,v,u+4,r+10,v,LIGHT)
    s.fill(-3,r+6,-9,3,r+6,9,FLOOR)
    for u in (-4,4):s.fill(u,r+7,-9,u,r+8,9,GLASS)
    for v in (-6,6):
        x,y,z=s.xyz(-9,r,v);stairs(p,x,z,y,6,'east',name+'/stair',3,'owned')
        for side in (v-2,v+2):
            for i in range(6):s.fill(-9+i,r+i+2,side,-9+i,r+i+3,side,GLASS)
        s.fill(-4,r+7,v-1,-4,r+10,v+1,AIR)
        walk(name+'/flight/'+str(v),s.pos(-10,r+1,v),s.pos(-3,r+7,v))
        walk(name+'/bypass/'+str(v),s.pos(-10,r+1,9 if v>0 else -9),s.pos(0,r+1,9 if v>0 else -9))
        walk(name+'/street_entry/'+str(v),s.pos(0,r,12 if v>0 else -12),s.pos(0,r+1,v))
    walk(name+'/crossing',s.pos(0,r+7,-6),s.pos(0,r+7,6))
    for u in (-h,h):
        for a,b in [(-10,-4),(4,10)]:s.fill(u,r+1,a,u,r+2,b,GLASS)
    x,y,z=s.xyz(5,r+7,-11);p.sign(x,y,z,['新箱根中央','S2 / 霧里団地','乗換 / TRANSFER',''],name)
    p.meta['landmarks'].append(dict(id=name,center=d['center'],half_width=11,style='compact_street_tram_stop'))

def build():
    p=Builder();data=load(OUT/'extension_plan.json')
    for d in data['transit']['platforms']:
        if d.get('compact'):compact_station(p,d)
        else:Station(p,d).run()
    net=Network(p)
    net.line((-1489,672),(-1489,688),110,'kirisato_transfer/existing_concourse',5,4,False)
    net.line((-1489,688),(-1496,688),110,'kirisato_transfer/turn',5,4,False)
    net.line((-1496,688),(-1496,694),110,'kirisato_transfer/low_landing',5,4,False)
    net.line((-1496,696),(-1496,748),111,'kirisato_transfer/overstreet_bridge',5,4,False)
    for x in (-1499,-1493):p.fill(x,112,698,x,113,734,GLASS,'kirisato_transfer/guard')
    net.finish();stairs(p,-1496,695,110,1,'south','kirisato_transfer/riser',5,'owned')
    walk('kirisato_transfer/riser',[-1495.5,111,693.5],[-1495.5,112,697.5])
    for z in (698,716,732):
        for x in (-1504,-1488):p.fill(x,105,z,x,110,z,'minecraft:polished_basalt[axis=y]','kirisato_transfer/piers')
        p.fill(-1504,110,z,-1488,110,z,STEEL,'kirisato_transfer/crossbeam')
        p.fill(-1498,109,z,-1494,109,z,LIGHT,'kirisato_transfer/lighting')
    # Connect the country station to the estate's south street.
    flat(p,(-2752,-984),(-2752,-976),70,7,4,'kirisato/arrival_walk',False)
    vox.OUT=OUT;return p

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build()
    (OUT/'walk_cases_estate_stations.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf-8')
    p.apply('estate_stations') if args.apply else p.save_plan('estate_stations')
