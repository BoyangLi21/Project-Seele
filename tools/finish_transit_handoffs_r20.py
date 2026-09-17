"""Restore bridge decks above the real train envelope and finish station entries."""
import json
from pathlib import Path
import regional_voxels as vox
from query_blocks import read_box
OUT=vox.ROOT/'artifacts/world_rebuild_r20/transit/civil'
def main():
    vox.OUT=OUT;p=vox.Painter();stations=json.loads((OUT/'viaduct_stations_and_streets/places.json').read_text(encoding='utf8'))['stations'];sweep=[]
    for s in stations:
        x,y,z=s['center'];h=s['half'];g=s['ground'];horizontal=s['horizontal'];o='r20/station_handoff/'+str(s['id'])
        def point(u,Y,v):return (x+u,Y,z+v) if horizontal else (x+v,Y,z+u)
        def fill(u,Y,v,U,YY,V,state):
            a=point(u,Y,v);b=point(U,YY,V);lo=tuple(min(c,d) for c,d in zip(a,b));hi=tuple(max(c,d) for c,d in zip(a,b));p.fill(*lo,*hi,state,o,'owned')
        u=h-24
        # Six whole blocks of clearance; the floor of the footbridge is above
        # that envelope and must survive the final rolling-stock sweep.
        fill(u+6,y+6,-13,u+10,y+6,13,'minecraft:smooth_stone')
        if g>=0:
            for sign in (-1,1):
                fill(-h,g-2,sign*16,h,g-1,sign*18,'minecraft:light_gray_concrete');fill(-h,g,sign*16,h,g,sign*18,'minecraft:smooth_stone');fill(-h+3,g+1,sign*16,h-3,g+4,sign*18,'minecraft:air')
    # West upper gallery turns into the east/west lift lobby; its old corner
    # column stood on the route, despite both branches being individually open.
    p.fill(92,-442,270,96,-438,274,'minecraft:air','r20/gallery/west_turn','owned')
    p.fill(92,-443,270,96,-443,274,'projectseele:nerv_floor_panel','r20/gallery/west_turn','owned')
    p.meta.update(restored_footbridges=len(stations),train_clear_height=6,station_forecourts_complete=True)
    p.save_plan('circulation_handoffs')
if __name__=='__main__':main()
