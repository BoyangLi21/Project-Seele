"""Replace orphan gallery fragments with a two-level circulation junction.

The retained command stair/lift landing and the east station link are explicit
destinations. Moving cabin prisms, including empty space, are never infilled.
"""
import json
import numpy as np
import regional_voxels as vox
from refine_architecture_r14 import Measured,PANEL,WALL,FLOOR,LIGHT

OUT=vox.ROOT/'artifacts/world_rebuild_r20/galleries'
GLASS='projectseele:clear_glass';AIR='minecraft:air'
def main():
    OUT.mkdir(parents=True,exist_ok=True);vox.OUT=OUT;p=vox.Painter();walks=[];ports=[]
    masks=json.loads((OUT.parent/'lifts/sweep_masks.json').read_text())
    def protected(pos):return any(all(a<=v<=b for a,v,b in zip(r['sweep'][0],pos,r['sweep'][1])) for r in masks)
    def flush(m):
        for pos,state in sorted(m.writes.items()):
            if not protected(pos) and state!=m.old(pos):p.match((*pos,*pos),m.old(pos),state,m.owners[pos])
    def path(name,a,b):walks.extend([dict(id='r20/gallery/'+name,start=a,end=b),dict(id='r20/gallery/'+name+'/return',start=b,end=a)])
    m=Measured(p,(78,-470,240),(140,-431,351));o='r20/east_transfer_junction'
    def box(b,s,owner=o):m.box(b[:3],b[3:],s,owner)
    def hallway(x0,x1,z0,z1,f,axis):
        box((x0,f-1,z0,x1,f+6,z1),PANEL);box((x0+1,f+1,z0+1,x1-1,f+5,z1-1),AIR);box((x0+1,f,z0+1,x1-1,f,z1-1),FLOOR)
        if axis=='x':
            for z in (z0,z1):box((x0+1,f+2,z,x1-1,f+4,z),GLASS)
            for x in range(x0+4,x1,10):box((x,f+6,z0+2,x+1,f+6,z1-2),LIGHT)
        else:
            for x in (x0,x1):box((x,f+2,z0+1,x,f+4,z1-1),GLASS)
            for z in range(z0+4,z1,10):box((x0+2,f+6,z,x1-2,f+6,z+1),LIGHT)
    # The former flat escalator sides have no middle treads. Their old slot
    # becomes an enclosed upper gallery, using the existing stair for height.
    hallway(88,128,243,251,-443,'x')
    hallway(89,97,249,273,-443,'z')
    hallway(93,126,270,276,-443,'x')
    hallway(119,127,249,274,-443,'z')
    # Lower route retains its floor and reaches the named staff rooms.
    hallway(86,116,251,261,-449,'x')
    hallway(85,93,257,350,-449,'z')
    # Overlapping shells are opened only at the intended same-level junctions.
    for b in [(90,-442,247,96,-438,252),(94,-442,271,124,-438,275),(120,-442,247,126,-438,272),
              (87,-448,255,92,-444,264),(89,-448,253,114,-444,259),
              (87,-448,345,92,-444,350),(92,-448,282,96,-445,288)]:box(b,AIR)
    # Existing six-riser stair: clear all of its headroom after both decks.
    for i in range(6):
        z=254-i;y=-448+i
        box((110,y,z,114,-437,z),AIR)
        box((110,-449,z,114,y-1,z),PANEL)
        box((110,y,z,114,y,z),'minecraft:smooth_quartz_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]')
    box((110,-443,247,114,-443,248),FLOOR);box((110,-442,247,114,-437,249),AIR)
    box((110,-437,247,114,-437,254),PANEL)
    # The north gallery connects directly to the existing long station path.
    box((120,-442,240,126,-438,244),AIR);box((120,-443,240,126,-443,244),FLOOR)
    # Cab sweep at X=127..133 is protected. Finish only its west threshold.
    box((123,-442,271,126,-439,275),AIR);box((123,-443,271,126,-443,275),FLOOR)
    # Real columns and edge beams tie both galleries into the lower structure.
    for x,z in [(86,250),(86,261),(119,244),(119,261),(126,244)]:box((x,-469,z,x+1,-450,z+1),PANEL)
    for z in range(276,346,16):
        for x in (85,93):box((x,-467,z,x,-450,z+1),PANEL)
    # The lower room's west entry remains open into the circulation spine.
    box((84,-448,281,88,-445,289),AIR);box((84,-449,281,88,-449,289),FLOOR)
    # Wall bays replace the former floating trim. The route stays 5m clear.
    for z in (277,301,325):
        m.put((92,-448,z),'projectseele:nerv_storage_panel[facing=west]',o+'/service_bay')
    path('lower_spine',[89.5,-448,269.5],[89.5,-448,344.5]);path('lower_branch',[89.5,-448,256.5],[112.5,-448,256.5]);path('six_risers',[112.5,-448,255.5],[112.5,-442,247.5]);path('upper_cross',[94.5,-442,247.5],[123.5,-442,247.5]);path('surface_lift',[123.5,-442,247.5],[123.5,-442,273.5]);path('west_upper',[93.5,-442,247.5],[93.5,-442,272.5]);path('lift_upper_cross',[94.5,-442,273.5],[126.5,-442,273.5]);path('lower_room',[84.5,-448,285.5],[89.5,-448,285.5])
    flush(m)
    # Convert the short orphan north of the command stair into a proper
    # lift/stair vestibule. Command seating and stairs from Z=262 stay intact.
    m=Measured(p,(8,-427,245),(35,-409,261));o='r20/command_north_vestibule'
    def box(b,s):m.box(b[:3],b[3:],s,o)
    box((16,-421,249,32,-413,261),PANEL);box((17,-419,250,31,-414,260),AIR);box((17,-420,250,31,-420,260),FLOOR)
    # One rise matches the original command stair apron at walking Y=-418.
    box((26,-419,250,31,-419,261),FLOOR)
    for z in range(255,261):box((25,-419,z,25,-419,z),'minecraft:smooth_quartz_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]')
    box((26,-418,258,30,-414,261),AIR)
    box((15,-419,256,17,-415,260),AIR);box((15,-420,256,17,-420,260),FLOOR)
    for x in (18,28):box((x,-417,249,x+2,-415,249),GLASS)
    for x in (19,27):box((x,-413,253,x+1,-413,258),LIGHT)
    for x in (16,32):box((x,-424,250,x,-422,260),PANEL)
    # The old gallery end now has a grounded equipment alcove, accessed from
    # the lift foyer, rather than an exposed bridge pointing into the void.
    for x in range(18,23):m.put((x,-419,250),'projectseele:nerv_storage_panel[facing=south]',o+'/alcove')
    path('command_lift_to_stair',[12.5,-419,258.5],[23.5,-419,258.5]);path('command_single_rise',[23.5,-419,258.5],[28.5,-418,258.5]);path('command_stair_apron',[28.5,-418,258.5],[28.5,-418,261.5]);flush(m)
    p.meta.update(walk_nodes=walks,cabin_sweeps_preserved=[r['group'] for r in masks],main_command_room_unchanged='All command seating and stair volumes Z>=262',retired='Flat escalator remnants without intermediate treads; obsolete north bridge end',destinations=['Command rear lift','Command stairs','Public surface lift','EVA station gallery','East staff rooms'])
    p.save_plan('connected_gallery_junctions');print('Gallery repair',len(p.ops),'exact changes',len(walks),'walk cases',flush=True)
if __name__=='__main__':main()
