"""Finish proven rail formations outside the actual launch-shaft exclusions."""
import json,math
from pathlib import Path
from collections import defaultdict
import numpy as np
import regional_voxels as v
from query_blocks import read_box,AIR
from build_transit_civil_r20 import arrays,ff,DECK
from scan_world_components_r19 import SOIL
OUT=v.ROOT/'artifacts/world_rebuild_r20/transit/final_envelopes';REVIEW=v.ROOT/'run/saves/SEELE_R20_REVIEW'
def main():
    OUT.mkdir(parents=True,exist_ok=True);v.OUT=OUT;p=v.Painter();s=json.loads((OUT.parent/'built11/native_commission.json').read_text(encoding='utf8'));audit=json.loads((OUT.parent/'physical10/transit_clearance.json').read_text());bad={r['id']:r for r in audit['results'] if r['obstructed_cells'] or r['unsupported_center_cells']};roads=arrays(OUT.parent.parent/'road_actual/road_contract_final.npz');mask=roads['mask'];ox,oz=map(int,roads['origin']);formed=[];pruned=[];piers=[]
    def reserved(x,z):return any(abs(x-cx)<=23 and -60<=z<=-12 for cx in (-12,30,72))
    for rail in s['curves']:
        if rail['mode']!='TRAIN' or rail['id'] not in bad:continue
        detail=bad[rail['id']];deck=defaultdict(set)
        if detail['unsupported_center_cells']:
            for xx,yy,zz in rail['points']:
                x,y,z=math.floor(xx),math.floor(yy),math.floor(zz)
                assert not reserved(x,z),('Rail enters real launch exclusion',rail['id'],x,z)
                for dx in range(-3,4):
                    for dz in range(-3,4):deck[x+dx,z+dz].add(y)
            for (x,z),ys in deck.items():
                assert not reserved(x,z)
                for y in ys:ff(p,(x,y-3,z,x,y-1,z),DECK,'r20/supported_surface_rail')
            for i in range(10,len(rail['points']),48):
                xx,yy,zz=rail['points'][i];x,y,z=math.floor(xx),math.floor(yy),math.floor(zz)
                if any(abs(x-X)<20 and abs(z-Z)<20 for X,Y,Z in piers):continue
                if any(0<=z+dz-oz<mask.shape[0] and 0<=x+dx-ox<mask.shape[1] and mask[z+dz-oz,x+dx-ox] for dx in range(-2,3) for dz in range(-2,3)):continue
                footing=SOIL|{'minecraft:gray_concrete','minecraft:light_gray_concrete','minecraft:smooth_stone','projectseele:nerv_floor_panel'}
                b=read_box(REVIEW,v.DIM,(x-1,40,z-1),(x+1,y-4,z+1));g=max((Y for Y in range(43,y-4) if b[x,Y,z].split('[')[0] in footing and all(b[x,q,z].split('[')[0] in footing for q in range(Y-3,Y+1))),default=39)
                if g<40 or any(b[X,Y,Z].split('[')[0] not in AIR|{'minecraft:light','minecraft:grass','minecraft:fern','minecraft:tall_grass'} for X in range(x-1,x+2) for Z in range(z-1,z+2) for Y in range(g+1,y-3)):continue
                ff(p,(x-1,g-2,z-1,x+1,y-4,z+1),DECK,'r20/rail_natural_footing');piers.append((x,y,z))
            formed.append(rail['id'])
        if detail['obstructed_cells']:
            # Only natural vegetation/soil in the independently measured
            # rolling-stock envelope is trimmed; buildings are never guessed.
            selected={}
            for xx,yy,zz in rail['points']:
                x,y,z=map(round,(xx,yy,zz))
                for dx in (-1,0,1):
                    for dz in (-1,0,1):
                        for dy in range(1,6):selected[x+dx,y+dy,z+dz]=None
            lo=tuple(min(q[i] for q in selected) for i in range(3));hi=tuple(max(q[i] for q in selected) for i in range(3));b=read_box(REVIEW,v.DIM,lo,hi);removed=0
            for q in selected:
                state=b[q]
                if state.split('[')[0] in AIR|{'minecraft:light'}:continue
                assert v.natural(state),('Engineered rail obstruction requires a new design',q,state)
                p.match((*q,*q),state,'minecraft:air','r20/rail_natural_clearance');removed+=1
            pruned.append(dict(rail=rail['id'],cells=removed))
    # The eastward landing threshold is displaced into the clear part of the
    # Hakone runway. White arrows lead to its actual native touchdown point.
    ff(p,(-2160,80,22,-1881,80,58),'minecraft:black_concrete','r20/hakone_displaced_threshold')
    for x in range(-2130,-1895,40):
        ff(p,(x,80,39,x+18,80,41),'minecraft:white_concrete','r20/runway_arrow')
        for d in range(8):
            for sign in (-1,1):ff(p,(x+18-d,80,40+sign*d,x+19-d,80,40+sign*d),'minecraft:white_concrete','r20/runway_arrow')
    ff(p,(-1881,80,22,-1879,80,58),'minecraft:white_concrete','r20/runway_threshold_bar')
    p.meta.update(supported_formations=formed,piers=piers,pruned_native_corridors=pruned,actual_launch_shafts_excluded=True,runway_marking_reference='https://www.faa.gov/air_traffic/publications/aim_html/chap2_section_3.html');p.save_plan('final_static_clearance')
if __name__=='__main__':main()
