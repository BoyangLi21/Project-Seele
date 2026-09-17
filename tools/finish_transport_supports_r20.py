"""Support every station sign and connect the new interchange bridge levels."""
import json,math
from pathlib import Path
from collections import defaultdict
import regional_voxels as v
from build_transit_civil_r20 import ff,FLOOR,DECK,AIR,GLASS,STEEL
OUT=v.ROOT/'artifacts/world_rebuild_r20/transit/civil'
def main():
    v.OUT=OUT;p=v.Painter();places=json.loads((OUT/'viaduct_stations_and_streets/places.json').read_text(encoding='utf8'));walks=[]
    for s in places['stations']:
        x,y,z=s['center'];h=s['half'];horizontal=s['horizontal'];owner='r20/station_sign_frame/'+str(s['id'])
        for side in (-1,1):
            xx,zz=(x-h+2,z+side*15) if horizontal else (x+side*15,z-h+2)
            ff(p,(xx,y+1,zz,xx,y+10,zz),STEEL,owner)
    # The shared stations use the same newly placed overbridge, so transfers
    # do not end in the gap between independently rebuilt platform canopies.
    for name,x,y,z0,z1 in [('tokyo',-78,100,-200,-136),('hakone',-1438,124,640,672),('nerv',56,-461,490,522)]:
        owner='r20/interchange/'+name;ff(p,(x-2,y,z0,x+2,y,z1),FLOOR,owner);ff(p,(x-2,y+1,z0,x+2,y+4,z1),AIR,owner)
        for xx in (x-3,x+3):ff(p,(xx,y+1,z0,xx,y+2,z1),GLASS,owner);ff(p,(xx,y+3,z0,xx,y+4,z1),STEEL,owner)
        ff(p,(x-3,y+5,z0,x+3,y+5,z1),DECK,owner)
        walks.extend([dict(id=owner,start=[x+.5,y+1,z0+.5],end=[x+.5,y+1,z1+.5]),dict(id=owner+'/return',start=[x+.5,y+1,z1+.5],end=[x+.5,y+1,z0+.5])])
    old=json.loads((OUT.parent/'built3/native_commission.json').read_text(encoding='utf8'));new=json.loads((OUT.parent/'built7/native_commission.json').read_text(encoding='utf8'));oldids={r['id'] for r in old['curves']}
    # P1 now has actual two-way running tracks, with separate short throats.
    # Also restore the full A1 turnback formation cleared with the old shed.
    curves=[r for r in new['curves'] if r['mode']=='TRAIN' and (r['id'] not in oldids or any(850<q[0]<880 and abs(q[2]-1190)<2 for q in r['points']))]
    deck=defaultdict(set);core=defaultdict(set)
    for r in curves:
        for xx,yy,zz in r['points']:
            x,y,z=math.floor(xx),math.floor(yy),math.floor(zz)
            for dx in range(-3,4):
                for dz in range(-3,4):deck[x+dx,z+dz].add(y)
            for dx in range(-1,2):
                for dz in range(-1,2):core[x+dx,z+dz].add(y)
    for (x,z),ys in deck.items():
        for y in ys:ff(p,(x,y-3,z,x,y-1,z),DECK,'r20/complete_native_formation')
    for (x,z),ys in core.items():
        for y in ys:ff(p,(x,y,z,x,y+5,z),AIR,'r20/complete_native_body');ff(p,(x,y-1,z,x,y-1,z),'minecraft:gravel','r20/complete_native_ballast')
    # Portal girders distribute both P1 decks onto its existing centre piers.
    for x in range(600,1130,48):ff(p,(x-1,90,465,x+1,90,479),STEEL,'r20/port_double_track_girder')
    ff(p,(910,94,1188,911,95,1192),STEEL,'r20/airport_turnback_stop')
    ff(p,(907,91,1187,912,93,1193),DECK,'r20/airport_turnback_stop_support')
    for x in (-12,30,72):ff(p,(x,-415,-36,x,-412,-36),STEEL,'r20/launch_dock_locator_support')
    p.meta.update(walk_nodes=walks,station_signs_supported=50,interchanges=3,native_formations_repaired=[r['id'] for r in curves]);p.save_plan('supported_signs_and_interchanges')
if __name__=='__main__':main()
