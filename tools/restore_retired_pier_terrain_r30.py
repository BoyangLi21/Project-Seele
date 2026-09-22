"""Restore terrain through the recorded R07 P1 pier footprints outside today's routes.

The older cleanup only inspected a shallow band around the retired track and
omitted polished-andesite foundations descending to Y32.
"""
from pathlib import Path
from collections import defaultdict
import argparse,json,math
import numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,AIR,iter_block_entities

ROOT=v.ROOT;BASE=ROOT/'run/saves/SEELE_R30_WORLD';WORLD=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=ROOT/'artifacts/facility_r30/retired_pier_terrain'
EARTH={'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:coarse_dirt','minecraft:sand','minecraft:gravel','minecraft:clay','minecraft:podzol','minecraft:rooted_dirt'}
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();old=json.loads((ROOT/'artifacts/world_expansion_r07/port_native_transit/track_samples.json').read_text());boxes={}
    for r in old:
        for q in r['points']:
            x,y,z=map(round,q)
            if x%24==0 and z==472:boxes[x,z]=(x-1,z-2,x+1,z+2)
            if z%24==0 and x==576:boxes[x,z]=(x-2,z-1,x+2,z+1)
    native=json.loads((BASE/'native_transit_r26.json').read_text());active=np.asarray([q for c in native['curves'] if c['mode']=='TRAIN' for q in c['points'] if q[1]>32]);rail=cKDTree(active[:,[0,2]])
    paths=[]
    for c in json.loads((BASE/'quality_walk_cases.json').read_text()):
        ps=c.get('path') or [c.get('start'),c.get('end')]
        if not all(q is not None for q in ps):continue
        for a,b in zip(ps,ps[1:]):
            a,b=np.array(a),np.array(b)
            if min(a[1],b[1])>32:paths.extend(np.linspace(a,b,max(2,math.ceil(np.linalg.norm(a-b)/2)+1)))
    walk=cKDTree(np.asarray(paths)[:,[0,2]]);decisions=[];changed=0
    for (cx,cz),(x0,z0,x1,z1) in sorted(boxes.items()):
        if rail.query([cx,cz])[0]<12 or walk.query([cx,cz])[0]<7:continue
        if any(min(s['position1']['x'],s['position2']['x'])-4<=cx<=max(s['position1']['x'],s['position2']['x'])+4 and min(s['position1']['z'],s['position2']['z'])-4<=cz<=max(s['position1']['z'],s['position2']['z'])+4 for s in native['stations']):continue
        lo=(x0-12,32,z0-12);hi=(x1+12,130,z1+12);b=read_box(WORLD,v.DIM,lo,hi)
        if list(iter_block_entities(WORLD,v.DIM,(x0,32,z0),(x1,130,z1))):continue
        natural=[];water=[]
        for x in range(lo[0],hi[0]+1):
            for z in range(lo[2],hi[2]+1):
                if x0-2<=x<=x1+2 and z0-2<=z<=z1+2:continue
                earth=[y for y in range(32,131) if b.get((x,y,z),'UNKNOWN').split('[')[0] in EARTH]
                if not earth:continue
                top=max(earth);above=b.get((x,top+1,z),'UNKNOWN').split('[')[0]
                if above not in AIR|{'minecraft:water','minecraft:grass','minecraft:fern','minecraft:tall_grass','minecraft:snow'}:continue
                natural.append([x,top,z]);wet=[y for y in range(top+1,131) if b.get((x,y,z),'').startswith('minecraft:water')]
                if wet:water.append(max(wet))
        if len(natural)<24:continue
        ground=np.asarray(natural);tree=cKDTree(ground[:,[0,2]]);waterline=int(np.median(water)) if water else -999
        count=0;tops=[]
        for x in range(x0,x1+1):
            for z in range(z0,z1+1):
                distances,ids=tree.query([x,z],k=min(24,len(ground)));near=ground[ids];weights=1/np.maximum(1,distances)
                A=np.c_[near[:,0]-x,near[:,2]-z,np.ones(len(near))];h=np.linalg.lstsq(A*weights[:,None],near[:,1]*weights,rcond=None)[0][2];top=int(np.clip(round(h),near[:,1].min(),near[:,1].max()));tops.append(top)
                for y in range(32,131):
                    q=x,y,z;oldstate=b[q]
                    if oldstate!='minecraft:polished_andesite':continue
                    new='minecraft:stone' if y<top-2 else 'minecraft:dirt' if y<top else ('minecraft:gravel' if waterline>=top else 'minecraft:grass_block[snowy=false]') if y==top else 'minecraft:water[level=0]' if y<=waterline else 'minecraft:air'
                    p.match((*q,*q),oldstate,new,'r30/retired_P1_pier_terrain');count+=1
        if count:decisions.append({'centre':[cx,cz],'footprint':[x0,z0,x1,z1],'changed':count,'restored_height_range':[min(tops),max(tops)],'current_rail_distance':float(rail.query([cx,cz])[0]),'source':'tools/build_r07_port_transit.py explicit P1 piers/depot_piers'});changed+=count
    p.meta.update(restored_piers=decisions,changed_cells=changed,current_stations_walks_and_rails_preserved=True);p.save_plan('retired_pier_terrain');print('Restored pier footprints',len(decisions),'cells',changed,flush=True)
    if apply:p.apply('retired_pier_terrain')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
