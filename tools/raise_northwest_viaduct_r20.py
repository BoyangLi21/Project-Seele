"""Match the five corrected native C1 grades and retain real pier support."""
import json,math
from collections import defaultdict
from scipy.spatial import cKDTree
import numpy as np
import regional_voxels as v
from build_transit_civil_r20 import ff,AIR,DECK
OUT=v.ROOT/'artifacts/world_rebuild_r20/transit/grade_finish'
def main():
    OUT.mkdir(exist_ok=True);v.OUT=OUT;p=v.Painter();before=json.loads((OUT.parent/'built7/native_commission.json').read_text(encoding='utf8'));after=json.loads((OUT.parent/'built10/native_commission.json').read_text(encoding='utf8'));removed=set(after['removed']);added=set(after['added']);old=[r for r in before['curves'] if r['id'] in removed];new=[r for r in after['curves'] if r['id'] in added];assert len(old)==len(new)==5
    retire=defaultdict(set);deck=defaultdict(set);core=defaultdict(set)
    for rails,target in [(old,retire),(new,deck)]:
        for r in rails:
            for xx,yy,zz in r['points']:
                x,y,z=math.floor(xx),math.floor(yy),math.floor(zz)
                for dx in range(-3,4):
                    for dz in range(-3,4):target[x+dx,z+dz].add(y)
                if target is deck:
                    for dx in range(-1,2):
                        for dz in range(-1,2):core[x+dx,z+dz].add(y)
    for (x,z),ys in retire.items():
        for y in ys:
            for state in ('minecraft:light_gray_concrete','minecraft:gravel'):p.match((x,y-3,z,x,y-1,z),state,AIR,'r20/retire_low_c1_formation')
    for (x,z),ys in deck.items():
        for y in ys:ff(p,(x,y-3,z,x,y-1,z),DECK,'r20/c1_road_clearance_deck')
    a=np.asarray([q for r in old for q in r['points']]);b=np.asarray([q for r in new for q in r['points']]);ta=cKDTree(a[:,[0,2]]);tb=cKDTree(b[:,[0,2]]);upgraded=[]
    for x,y,z in json.loads((OUT.parent/'civil/viaduct_stations_and_streets/places.json').read_text())['piers']:
        dist,_=ta.query([x+.5,z+.5])
        if dist>2.5:continue
        _,i=tb.query([x+.5,z+.5]);Y=math.floor(b[i,1])
        if Y>y:ff(p,(x-1,y-4,z-1,x+1,Y-4,z+1),DECK,'r20/c1_raised_pier');upgraded.append(dict(x=x,z=z,before_y=y,after_y=Y))
    for (x,z),ys in core.items():
        for y in ys:ff(p,(x,y,z,x,y+5,z),AIR,'r20/c1_native_body');ff(p,(x,y-1,z,x,y-1,z),'minecraft:gravel','r20/c1_ballast')
    p.meta.update(raised_curves=list(added),upgraded_piers=upgraded,station_and_platform_datums_unchanged=True,minimum_required_road_clearance=6);p.save_plan('six_metre_road_clearance')
if __name__=='__main__':main()
