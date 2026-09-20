"""Measured repairs to the reported shaft, pyramid galleries and science connection."""
from pathlib import Path
import json,numpy as np
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f,repair_facility_r21 as h
from query_blocks import iter_block_entities,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/reported'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;records=[];walks=[]
    def scene(lo,hi):f.LO=h.LO=lo;f.HI=h.HI=hi;return h.Facility()
    def finish(s,name):
        if list((OUT/name).glob('applied_*')):
            records.append(dict(id=name,already_applied=True));walks.extend(s.walks);return
        p=v.Painter();changed=s.before!=s.after
        for q,t in iter_block_entities(WORLD,v.DIM,h.LO,h.HI):
            if changed[q[1]-h.LO[1],q[2]-h.LO[2],q[0]-h.LO[0]]:
                if str(t['id']) not in ('projectseele:station_departure_board','projectseele:nerv_direction_panel','minecraft:sign'):raise RuntimeError(('Fixture conflict',q,str(t['id'])))
                for dx,dy,dz in ((0,0,0),(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                    x,y,z=q[0]+dx,q[1]+dy,q[2]+dz
                    if all(h.LO[i]<=v<=h.HI[i] for i,v in enumerate((x,y,z))):
                        old=s.palette[s.before[y-h.LO[1],z-h.LO[2],x-h.LO[0]]]
                        if old not in AIR:s.fill((x,y,z,x,y,z),old)
        count=s.delta(p,'r28/'+name);p.meta.update(walk_nodes=s.walks,sections=s.contract)
        result=p.apply(name);records.append(dict(id=name,cells=count,sections=s.contract));walks.extend(s.walks)
    s=scene((-32,-413,-57),(115,80,-16))
    # The old enclosure started at -370, leaving the lower 41 metres open.
    # Preserve the three measured rail approach mouths and observer entrance.
    for y in range(-412,80):
        s.fill((-31,y,-55,114,y,-55),'minecraft:black_concrete')
        for cx in (-12,30,72):
            if -410<=y<=-349:s.fill((cx-16,y,-55,cx+16,y,-55),'minecraft:air')
        if -369<=y<=-364:s.fill((89,y,-55,112,y,-55),'minecraft:air')
        s.fill((-31,y,-17,114,y,-17),'minecraft:black_concrete')
        for x in (-31,114):s.fill((x,y,-54,x,y,-18),'minecraft:black_concrete')
    # Shorten only the lower inter-bay partitions, leaving every shaft core
    # and its original width above the launch hall unchanged.
    for x in (5,13,47,55):s.fill((x,-410,-53,x,-350,-33),'minecraft:air')
    for x,X in ((6,12),(48,54)):
        s.fill((x,-412,-55,X,-411,-18),f.STRUCT)
        s.fill((x,-349,-55,X,-348,-18),f.EDGE)
    finish(s,'sealed_lower_launch_envelope_short_partitions')
    s=scene((66,-452,266),(82,-357,286));floors=[]
    for y in (-448,-434,-420,-406,-392,-378,-364):
        old=s.palette[s.before[y-1-h.LO[1],275-h.LO[2],74-h.LO[0]]]
        if old not in (f.FLOOR,f.STRUCT):continue
        floors.append(y)
        s.fill((73,y-2,271,78,y-2,281),f.STRUCT)
        s.fill((73,y-1,271,78,y-1,281),f.FLOOR)
        s.fill((73,y,272,73,y+4,280),f.WALL)
        s.fill((73,y+1,272,73,y+3,280),'projectseele:clear_glass')
        s.fill((73,y+5,271,78,y+5,281),f.STRUCT)
        s.path('east_gallery_sealed_'+str(y),[[75.5,y,270.5],[75.5,y,282.5]])
    finish(s,'complete_east_gallery_sections');records[-1]['floors']=floors
    s=scene((83,-470,392),(213,-450,546))
    s.hall('science_hq_bridge',[(86,201,395,403)],-462,6,
           [(86,-461,397,86,-458,401),(194,-461,403,199,-458,403)])
    # Preserve the existing MTR paired lanes inside the new full-width shell.
    for iy,iz,ix in np.argwhere(np.array([q.startswith('mtr:escalator_step') for q in s.palette])[s.before]):
        x,y,z=int(ix+h.LO[0]),int(iy+h.LO[1]),int(iz+h.LO[2])
        if 87<=x<=188 and 396<=z<=402:s.fill((x,y,z,x,y,z),s.palette[s.before[iy,iz,ix]])
    # A separate lower personnel gallery completes the existing descending
    # stair. No live native rail runs in this nine-wide corridor.
    s.hall('science_lower_gallery',[(192,200,410,542),(198,211,525,529)],-467,5,
           [(195,-466,410,197,-463,410),(203,-466,529,209,-463,529)])
    # Upper return connection and a supported stair from the lower gallery.
    s.hall('science_south_upper_return',[(200,211,538,542)],-461,5,
           [(200,-460,539,200,-457,541),(203,-460,538,209,-457,538)])
    for z in range(530,538):
        floor=-467+min(6,z-529)
        s.fill((202,floor-1,z,211,floor,z),f.STRUCT)
        s.fill((203,floor+1,z,210,floor+4,z),'minecraft:air')
        s.fill((202,floor+5,z,211,floor+5,z),f.STRUCT)
        for x in (202,211):s.fill((x,floor+1,z,x,floor+4,z),f.WALL)
        if z<=535:s.fill((203,floor,z,210,floor,z),'minecraft:smooth_quartz_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]')
        else:s.fill((203,floor,z,210,floor,z),f.FLOOR)
    # Connect the top landing through the old east wall, with a complete deck.
    s.fill((199,-461,539,210,-461,541),f.FLOOR)
    s.fill((199,-460,539,210,-457,541),'minecraft:air')
    for x,direction in ((194,True),(197,False)):
        for z in range(416,520):
            for lane in (0,1):
                orient='landing_bottom' if z==416 else 'landing_top' if z==519 else 'flat'
                side='left' if lane==0 else 'right'
                s.fill((x+lane,-467,z,x+lane,-467,z),f'mtr:escalator_step[direction={str(direction).lower()},facing=north,orientation={orient},side={side},status=true]')
    s.path('science_bridge_complete',[[89.5,-461,399.5],[190.5,-461,399.5],[196.5,-461,399.5]])
    s.path('science_lower_complete',[[196.5,-466,411.5],[196.5,-466,527.5],[206.5,-466,527.5],[206.5,-466,529.5],[206.5,-460,536.5],[206.5,-460,540.5],[196.5,-460,540.5]])
    finish(s,'science_dual_level_enclosed_circulation')
    (OUT/'contract.json').write_text(json.dumps(dict(repairs=records,walk_nodes=walks),ensure_ascii=False,indent=2),encoding='utf8')
    print('Reported repairs',[(r['id'],r.get('cells','retained receipt')) for r in records],flush=True)

if __name__=='__main__':main()
