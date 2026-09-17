"""Finish individually identified residual props without altering working systems."""
import argparse,copy,json
import numpy as np
import nbtlib
import regional_voxels as vox
from query_blocks import AIR,read_box,iter_block_entities
from finish_fixture_supports_r19 import route_segments,ROD

OUT=vox.ROOT/'artifacts/world_repair_r19/small_fixtures'

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();edits={};notes=[]
    def change(q,before,after,reason):
        if before==after:return
        assert q not in edits or edits[q]==(before,after,reason)
        edits[q]=(before,after,reason)
    def rods(lo,hi,reason,base=None):
        b=read_box(vox.WORLD,vox.DIM,lo,hi)
        if base:
            s=read_box(vox.WORLD,vox.DIM,base,base)[base]
            assert s.split('[')[0] not in AIR,('No structural bearing',base)
        for q,s in b.items():
            assert s.split('[')[0] in AIR,(q,s)
            change(q,s,ROD,reason)
    # These two narrow strips are from the same retired western launch pad.
    for x0,x1 in ((-68,-67),(-48,-47)):
        b=read_box(vox.WORLD,vox.DIM,(x0,-444,207),(x1,-444,214));assert set(b.values())=={'minecraft:polished_deepslate'}
        for q,s in b.items():change(q,s,'minecraft:air','retire_old_pad_edge')
    # Two obsolete pavement fragments stand above the current graded sidewalk.
    rows=json.loads((OUT.parent/'global_components/contact_classification.json').read_text())['groups']
    for r in rows:
        if r['lo'] not in ([-723,96,-54],[-717,96,-54]):continue
        b=read_box(vox.WORLD,vox.DIM,tuple(r['lo']),tuple(r['hi']))
        for q,s in b.items():
            assert s in r['states'];change(q,s,'minecraft:air','retire_superseded_high_pavement')
    for x in (-90,30,150):rods((x,102,17),(x,103,17),'roof_beacon_pole',(x,101,17))
    for x in (-31,-29):rods((x,-455,396),(x,-452,396),'entrance_light_hangers',(x,-451,396))
    rods((96,-427,284),(96,-427,284),'ceiling_sensor_bracket',(96,-426,284))
    rods((26,-384,360),(26,-382,360),'suspended_room_panel',(26,-381,360))
    # This is a live power socket. Give it a conduit from the measured cage
    # floor; its block entity, coordinate and charging behavior remain intact.
    rods((48,-442,-92),(48,-424,-92),'cage_power_conduit',(48,-443,-92))
    # The R07 return-stair repair removed a landing but left two railing cells.
    for q in ((6479,127,-6252),(6479,128,-6252),(87,-465,-24)):
        s=read_box(vox.WORLD,vox.DIM,q,q)[q]
        assert s.startswith('minecraft:iron_bars' if q[0]==6479 else 'minecraft:snow[')
        change(q,s,'minecraft:air','retired_stair_guard' if q[0]==6479 else 'underground_snow_remnant')
    # R08's fire equipment used the warehouse datum (68) on the quay (64).
    def move(lo,hi,delta,reason):
        b=read_box(vox.WORLD,vox.DIM,lo,hi);cells={q:s for q,s in b.items() if s.split('[')[0] not in AIR};moved=[]
        for q,s in cells.items():
            t=tuple(a+c for a,c in zip(q,delta));old=read_box(vox.WORLD,vox.DIM,t,t)[t]
            assert old.split('[')[0] in AIR,(reason,t,old)
            change(q,s,'minecraft:air',reason);change(t,old,s,reason);moved.append([q,t])
        for _,entity in iter_block_entities(vox.WORLD,vox.DIM,lo,hi):
            tag=copy.deepcopy(entity);q=tuple(int(tag[k])+d for k,d in zip(('x','y','z'),delta))
            for key,value in zip(('x','y','z'),q):tag[key]=nbtlib.Int(value)
            p.block_entities[q]=tag
        notes.append(dict(reason=reason,moved=moved))
    floor=read_box(vox.WORLD,vox.DIM,(1407,64,448),(1410,64,451));assert set(floor.values())=={'projectseele:nerv_floor_panel'}
    move((1407,69,448),(1410,72,452),(0,-4,0),'ground_fire_point_on_quay')
    # Keep the ship builder attribution, now on the high shore approach.
    floor=read_box(vox.WORLD,vox.DIM,(1396,68,558),(1396,68,558));assert floor[1396,68,558].split('[')[0] not in AIR
    move((1408,67,570),(1408,68,571),(-12,2,-12),'shore_approach_berth_sign')
    # Guard both body-space additions and removal of any named walking floor.
    starts,ends=route_segments()
    for q,(before,after,reason) in edits.items():
        q=np.asarray(q,float)
        lo=q+[-.31,-1.85,-.31] if after!='minecraft:air' else q+[-.31,.49,-.31]
        hi=q+[1.31,1,1.31] if after!='minecraft:air' else q+[1.31,1.02,1.31]
        low=np.zeros(len(starts));high=np.ones(len(starts));delta=ends-starts
        for ax in range(3):
            still=np.abs(delta[:,ax])<1e-9
            high[still&((starts[:,ax]<lo[ax])|(starts[:,ax]>hi[ax]))]=-1
            moving=~still;aa=(lo[ax]-starts[moving,ax])/delta[moving,ax];bb=(hi[ax]-starts[moving,ax])/delta[moving,ax]
            low[moving]=np.maximum(low[moving],np.minimum(aa,bb));high[moving]=np.minimum(high[moving],np.maximum(aa,bb))
        assert not np.any(low<=high),('Named route intersection',q,reason)
    for q,(before,after,reason) in edits.items():p.match((*q,*q),before,after,'r19/'+reason)
    p.meta.update(notes=notes,live_power_socket_preserved=True,named_routes_preserved=True)
    p.apply('individual_prop_corrections') if apply else p.save_plan('individual_prop_corrections')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
