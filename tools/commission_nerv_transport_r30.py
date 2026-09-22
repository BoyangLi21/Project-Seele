"""Mark a measured vacant airport apron and register the NERV heavy-airlift stand."""
import json,argparse
import regional_voxels as v
from query_blocks import read_box,AIR

WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/nerv_transport'
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();x,z=1200,20
    b=read_box(WORLD,v.DIM,(x-74,72,z-61),(x+74,130,z+61))
    assert all(s in AIR for (X,Y,Z),s in b.items() if Y>=73),'Aircraft envelope occupied'
    native=json.loads((WORLD/'native_transit_r26.json').read_text())
    assert not any(1126<=q[0]<=1274 and q[1]<150 and -41<=q[2]<=81 for c in native['curves'] if c['mode']=='AIRPLANE' for q in c['points']),'Native aircraft corridor overlap'
    paint={}
    for dx in range(-69,70):
        for dz in [-58,58]:paint[x+dx,72,z+dz]='minecraft:yellow_concrete'
    for dz in range(-58,59):
        for dx in [-69,69]:paint[x+dx,72,z+dz]='minecraft:yellow_concrete'
    for dx in range(-15,16):
        for dz in range(-18,19):
            if abs(dx) in [12,13,14] or abs(dz)<=2:paint[x+dx,72,z+dz]='minecraft:white_concrete'
    for dx in [-71,71]:
        for dz in [-60,0,60]:paint[x+dx,72,z+dz]='minecraft:sea_lantern'
    for q,state in paint.items():
        old=b[q];assert old=='minecraft:gray_concrete',(q,old)
        p.match((*q,*q),old,state,'r30/nerv_heavy_airlift_stand')
    p.meta['landmarks']=[{'id':'nerv_heavy_airlift_stand','aircraft_origin':[1200.5,84,20.5],'ground_y':73,'measured_airframe_bounds':[[-69,-11,-56],[69,19,58]],'native_route_overlap':False}]
    p.save_plan('nerv_airlift_stand')
    if apply:
        p.apply('nerv_airlift_stand');(WORLD/'nerv_transport_r30.json').write_text(json.dumps({'revision':30,'stand':[1200.5,84,20.5],'ground_y':73,'commissioned':True,'authority':'User requested NERV airport transport department; measured vacant apron with native air routes excluded'},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
