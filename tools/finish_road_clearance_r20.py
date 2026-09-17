"""Move viaduct piers off streets and grade the raised S2 station forecourt."""
import json,math
from pathlib import Path
import numpy as np
import regional_voxels as v
from scan_world_components_r19 import SOIL
from query_blocks import read_box,AIR
from build_transit_civil_r20 import arrays,ff,grouped
OUT=v.ROOT/'artifacts/world_rebuild_r20/road_actual';REVIEW=v.ROOT/'run/saves/SEELE_R20_REVIEW'
def main():
    v.OUT=OUT;p=v.Painter();report=json.loads((OUT/'road_actual_audit.json').read_text());old=arrays(OUT.parent/'transit/civil/road_contract.npz');terrain=arrays(v.ROOT/'artifacts/world_quality_r02/terrain_target.npz');h=old['height2'].copy();mask=old['mask'];ox,oz=map(int,old['origin']);nz,nx=mask.shape;piers=json.loads((OUT.parent/'transit/civil/viaduct_stations_and_streets/places.json').read_text())['piers'];moved=[]
    upgrades=json.loads((OUT.parent/'transit/grade_finish/six_metre_road_clearance/places.json').read_text())['upgraded_piers'];height_override={(r['x'],r['z']):r['after_y'] for r in upgrades};piers=[[x,height_override.get((x,z),y),z] for x,y,z in piers]
    bad=[r for r in report['bad'] if any('light_gray_concrete' in a for a in r['blocks'][1:])];matched=set()
    def road(x,z):return 0<=x-ox<nx and 0<=z-oz<nz and bool(mask[z-oz,x-ox])
    for row in bad:
        x,y,z=row['pos'];near=[q for q in piers if abs(q[0]-x)<=1 and abs(q[2]-z)<=1];assert len(near)==1,(row,near);matched.add(tuple(near[0]))
    for x,y,z in sorted(matched):
        g=int(terrain['height'][z-oz,x-ox]);data=read_box(REVIEW,v.DIM,(x-27,32,z-27),(x+27,y,z+27));chosen=None
        for distance in range(4,25):
            offsets=sorted([(dx,dz) for dx in range(-distance,distance+1) for dz in range(-distance,distance+1) if max(abs(dx),abs(dz))==distance],key=lambda q:q[0]*q[0]+q[1]*q[1])
            for dx,dz in offsets:
                X,Z=x+dx,z+dz
                if any(road(X+a,Z+b) for a in range(-2,3) for b in range(-2,3)):continue
                ground=max((yy for yy in range(32,y-4) if data[X,yy,Z].split('[')[0] in SOIL),default=31)
                if ground>=y-5:continue
                if any(data[xx,yy,zz].split('[')[0] not in AIR|{'minecraft:light','minecraft:grass','minecraft:tall_grass','minecraft:fern'} for xx in range(X-1,X+2) for zz in range(Z-1,Z+2) for yy in range(ground+1,y-3)):continue
                chosen=(X,ground,Z);break
            if chosen:break
        assert chosen,('No off-street pier pocket',x,y,z)
        # Remove the old post above the local finished ground. Restore each
        # street's own paving, keeping its exact half-block height contract.
        for xx in range(x-1,x+2):
            for zz in range(z-1,z+2):
                fy=(int(h[zz-oz,xx-ox])-1)//2 if road(xx,zz) else g
                for yy in range(fy+1,y-3):p.match((xx,yy,zz,xx,yy,zz),'minecraft:light_gray_concrete','minecraft:air','r20/road/remove_pier_from_clearance')
                if road(xx,zz):
                    value=int(h[zz-oz,xx-ox]);kind=2 if old['stripe'][zz-oz,xx-ox] else 1 if old['carriage'][zz-oz,xx-ox] else 0
                    state=['minecraft:smooth_stone','minecraft:black_concrete','minecraft:white_concrete'][kind]
                    if value%2:state=['minecraft:smooth_stone_slab','minecraft:polished_blackstone_slab','minecraft:quartz_slab'][kind]+'[type=bottom,waterlogged=false]'
                    ff(p,(xx,fy,zz,xx,fy,zz),state,'r20/road/paving_under_viaduct')
        X,G,Z=chosen;ff(p,(X-1,G-2,Z-1,X+1,y-4,Z+1),'minecraft:light_gray_concrete','r20/road/off_street_pier')
        steps=max(abs(X-x),abs(Z-z))
        for t in range(steps+1):
            xx=round(x+(X-x)*t/max(1,steps));zz=round(z+(Z-z)*t/max(1,steps));ff(p,(xx-1,y-4,zz-1,xx+1,y-3,zz+1),'projectseele:nerv_machine_edge','r20/road/cantilever_headstock')
        moved.append(dict(before=[x,y,z],after=[X,y,Z],ground=G))
    # This existing S2 station uses a 105m plinth, one metre above the city
    # street. Two half-height rises finish every edge of the forecourt.
    x0,x1,z0,z1=-1538,-1454,730,766
    for z in range(z0-1,z1+2):
        for x in range(x0-1,x1+2):
            inside=x0<=x<=x1 and z0<=z<=z1
            if not inside:
                ff(p,(x,105,z,x,105,z),'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]','r20/road/graded_station_kerb')
            if road(x,z):h[z-oz,x-ox]=212 if inside else 211
    np.savez_compressed(OUT/'road_contract_final.npz',height2=h,mask=mask,carriage=old['carriage'],stripe=old['stripe'],origin=old['origin'])
    p.meta.update(moved_piers=moved,station_forecourt_datums={'road_feet':105,'edge_feet':105.5,'station_feet':106},road_floor_changes_limited_to_station_plinth=True)
    p.save_plan('clear_roadways_and_station_kerbs');print('Off-street piers',len(moved),flush=True)
if __name__=='__main__':main()
