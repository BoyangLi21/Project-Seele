#!/usr/bin/env python3
"""Build one reversible TV-inspired interior trial in a copy of R28."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import csv
import hashlib
import json
from pathlib import Path
import shutil
import time
from functools import lru_cache

import nbtlib
import numpy as np

from query_blocks import AIR, read_box, iter_block_entities, dimension_dir
from apply_s20_approved_semantic_repairs import Change, rewrite_region, atomic_replace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'run/saves/SEELE_S20_RECOVERY_R28'
TARGET = ROOT/'run/saves/SEELE_PYRAMID_TV_PREVIEW_20260905'
OUT = ROOT/'artifacts/pyramid_tv_interior_20260905'
DIM = 'projectseele:geofront'
LO, HI = (-30,-466,260), (86,-436,329)
PACKET = 'PYRAMID-TV-INTERIOR-20260905'
FREE = AIR | {'minecraft:light'}
FLOOR = 'minecraft:polished_andesite'
EDGE = 'minecraft:polished_deepslate'
WALL = 'minecraft:light_gray_concrete'
DARK = 'minecraft:cyan_terracotta'
RED = 'minecraft:red_terracotta'
ROOF = 'minecraft:smooth_stone'


def bare(state): return state.split('[')[0]


def plan():
    before = read_box(SOURCE,DIM,LO,HI)
    protected = {p for p,_ in iter_block_entities(SOURCE,DIM,LO,HI)}
    desired, reasons, additions, doors = {}, {}, {}, []
    branch = ({(26,y,z) for z in range(266,269) for y in range(-448,-445)}
              | {(50,y,z) for z in range(277,280) for y in range(-448,-445)})

    def get(pos): return desired.get(pos,before.get(pos,'UNKNOWN'))

    def put(x,y,z,state,why,keep=False):
        pos=(x,y,z); original=before.get(pos,'UNKNOWN')
        if pos in protected: raise RuntimeError(f'protected block entity {pos}')
        if original=='UNKNOWN': raise RuntimeError(f'unmeasured cell {pos}')
        if bare(original) not in FREE and original!=state and pos not in branch:
            if keep: return
            raise RuntimeError(f'authored obstacle {pos}: {original} -> {state} ({why})')
        desired[pos]=state; reasons[pos]=why

    def box(x0,y0,z0,x1,y1,z1,state,why,keep=False):
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):
                for z in range(z0,z1+1): put(x,y,z,state,why,keep)

    def room(x0,z0,x1,z1,floor,roof,label):
        for x in range(x0,x1+1):
            for z in range(z0,z1+1):
                edge=x in (x0,x1) or z in (z0,z1)
                put(x,floor,z,EDGE if edge else FLOOR,label+'/floor')
                put(x,roof,z,ROOF,label+'/ceiling')
                if edge:
                    for y in range(floor+1,roof):
                        material=EDGE if y==floor+1 else RED if y==roof-1 else WALL
                        if x in (x0,x1) and (z-z0)%7==0: material=EDGE
                        put(x,y,z,material,label+'/wall')
        # Repeated transverse structure and restrained recessed light strips.
        for z in range(z0+3,z1-1,7):
            box(x0+1,roof-1,z,x1-1,roof-1,z,EDGE,label+'/beam')
            for x in range(x0+3,x1-2):
                put(x,roof,z+1,'minecraft:sea_lantern',label+'/recessed-light')
                put(x,roof-1,z+1,'minecraft:iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]',label+'/light-baffle')
        # Four continuous bearing piers reach the measured pyramid bottom slab.
        for x in (x0,x1):
            for z in (z0,z1):
                box(x,-465,z,x,floor-1,z,EDGE,label+'/bearing-pier',True)

    room(-26,265,-6,275,-449,-442,'west-duty')
    room(-26,278,-6,298,-449,-442,'west-briefing')
    room(58,284,82,298,-449,-442,'east-comms')
    room(8,288,48,324,-462,-451,'lower-data-service')

    # Corridor floor cells form a union: overlapping branches never leave an internal wall.
    upper=set()
    def corridor(x0,z0,x1,z1):
        upper.update((x,z) for x in range(x0,x1+1) for z in range(z0,z1+1))
    corridor(-3,266,26,268)
    corridor(-3,267,1,303)
    corridor(-7,269,-3,271)
    corridor(-7,287,-3,289)
    corridor(53,279,57,303)
    corridor(49,277,57,279)
    corridor(57,289,59,291)
    for x,z in upper:
        put(x,-449,z,FLOOR,'upper-circulation/floor',True)
        box(x,-448,z,x,-444,z,'minecraft:air','upper-circulation/clearance',True)
        put(x,-443,z,ROOF,'upper-circulation/ceiling',True)
    perimeter={(x+dx,z+dz) for x,z in upper for dx,dz in [(1,0),(-1,0),(0,1),(0,-1)]} - upper
    for x,z in perimeter:
        # Connection to the surveyed existing landing is open, not a glass panel repurposed as a door.
        if x==27 and 266<=z<=268: continue
        if x==48 and 277<=z<=279: continue
        if any(x0<x<x1 and z0<z<z1 for x0,z0,x1,z1 in
               [(-26,265,-6,275),(-26,278,-6,298),(58,284,82,298)]): continue
        box(x,-449,z,x,-443,z,WALL,'upper-circulation/bulkhead',True)
        put(x,-444,z,RED,'upper-circulation/identification-band',True)
        put(x,-448,z,DARK,'upper-circulation/protective-base',True)
        if (z in (265,269) and x%7==0) or (x in (-4,2,52,58) and z%7==0):
            box(x,-448,z,x,-443,z,EDGE,'upper-circulation/structural-rib',True)
    for x,z in upper:
        if (x%7==0 and z==268) or (z%7==0 and x in (-1,55)):
            put(x,-443,z,'minecraft:sea_lantern','upper-circulation/light',True)
        if (x%7==0 and 266<=z<=268 and -3<=x<=25) or (z%7==0 and x in (-3,-2,-1,0,1,53,54,55,56,57)):
            put(x,-444,z,EDGE,'upper-circulation/overhead-rib',True)
    for x in (4,11,18):
        box(x,-447,269,x+1,-446,269,DARK,'upper-circulation/service-panel',True)
        put(x,-447,268,'minecraft:stone_button[face=wall,facing=north,powered=false]','upper-circulation/service-panel-control')

    # The branch is at the escalator landing, never through its machinery or guardrail.
    for x,y,z in branch: put(x,y,z,'minecraft:air','existing-personnel-corridor/new-framed-branch')

    def stair(west):
        x0,x1=(-16,3) if west else (53,74)
        first=range(-13,-10) if west else range(67,70)
        second=range(-5,-2) if west else range(59,62)
        label='west-stair' if west else 'east-stair'
        room(x0,300,x1,318,-462,-442,label)
        # The top and bottom landings have separate doors, never a ladder or a floating threshold.
        box(x0+1,-449,301,x1-1,-449,303,FLOOR,label+'/upper-landing')
        box(x0+1,-448,301,x1-1,-444,303,'minecraft:air',label+'/upper-landing-clearance')
        middle0=min(min(first),min(second)); middle1=max(max(first),max(second))
        box(middle0,-456,311,middle1,-456,314,FLOOR,label+'/middle-landing')
        for i in range(7):
            for x in first:
                put(x,-449-i,304+i,'minecraft:polished_andesite_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]',label+'/flight-one')
                put(x,-450-i,304+i,EDGE,label+'/stringer-one')
            if i<6:
                for x in second:
                    put(x,-456-i,310-i,'minecraft:polished_andesite_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]',label+'/flight-two')
                    put(x,-457-i,310-i,EDGE,label+'/stringer-two')
            for x in (min(first)-1,max(first)+1):
                put(x,-448-i,304+i,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]',label+'/first-guardrail')
            if i<6:
                for x in (min(second)-1,max(second)+1):
                    put(x,-455-i,310-i,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]',label+'/second-guardrail')
        box(x0,-457,313,x1,-457,313,EDGE,label+'/landing-support-beam')
        # Service pipe risers and landings lit at both elevations.
        for z in (304,312):
            box(x0+1,-461,z,x0+1,-444,z,'minecraft:polished_basalt[axis=y]',label+'/pipe-riser')
        for y in (-446,-450,-459):
            put(x1-1,y,316,'minecraft:sea_lantern',label+'/landing-light')
    stair(True); stair(False)

    # Reopen the planned interfaces after constructing the stair enclosures.
    box(-2,-448,299,1,-445,303,'minecraft:air','west-stair/upper-interface')
    box(54,-448,299,57,-445,303,'minecraft:air','east-stair/upper-interface')
    for x0,x1 in [(2,9),(47,54)]:
        box(x0,-462,301,x1,-462,303,FLOOR,'lower-circulation/floor')
        box(x0,-461,301,x1,-458,303,'minecraft:air','lower-circulation/clearance')
        box(x0,-457,301,x1,-457,303,ROOF,'lower-circulation/ceiling')
        for z in (300,304): box(x0,-462,z,x1,-457,z,WALL,'lower-circulation/wall')

    def portal(x,y,z,axis,label):
        # Open framed apertures keep the primary circulation three blocks wide.
        for w in (-1,0,1):
            xx,zz=(x+w,z) if axis=='x' else (x,z+w)
            box(xx,y,zz,xx,y+3,zz,'minecraft:air',label+'/aperture')
            put(xx,y+4,zz,RED,label+'/header')
        doors.append({'name':label,'feet':[x,y,z],'axis':axis,'clear_width':3,'clear_height':4})
    portal(-6,-448,270,'z','DUTY')
    portal(-6,-448,288,'z','BRIEFING')
    portal(58,-448,290,'z','COMMS')
    portal(8,-461,302,'z','DATA-WEST')
    portal(48,-461,302,'z','DATA-EAST')

    # West briefing: recessed board, a central table, and circulation behind the seats.
    box(-24,-447,279,-9,-445,279,EDGE,'briefing/board-frame')
    box(-23,-447,278,-10,-446,278,DARK,'briefing/sector-board-back')
    box(-23,-447,279,-10,-446,279,'minecraft:gray_stained_glass','briefing/board')
    for x in (-21,-16,-11): put(x,-446,278,RED,'briefing/sector-marker')
    box(-21,-448,284,-12,-448,293,'minecraft:smooth_stone_slab[type=top,waterlogged=false]','briefing/table')
    for x in (-20,-13):
        for z in (285,292): put(x,-448,z,DARK,'briefing/table-pedestal')
    for z in (285,288,291):
        put(-23,-448,z,'minecraft:polished_deepslate_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]','briefing/west-seat')
        put(-10,-448,z,'minecraft:polished_deepslate_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]','briefing/east-seat')
    for x in range(-24,-8,3):
        box(x,-448,266,x+1,-446,266,'minecraft:iron_block','duty/lockers')
        put(x,-447,267,'minecraft:stone_button[face=wall,facing=south,powered=false]','duty/locker-handle')
    box(-24,-448,273,-12,-448,273,'minecraft:polished_deepslate_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]','duty/bench')

    # East signal-analysis workstations: low console planes and dense rear equipment.
    for x in (63,69,75):
        for z in (288,294):
            box(x,-448,z,x+2,-448,z,EDGE,'comms/console-body')
            for xx in range(x,x+3):
                put(xx,-447,z,'minecraft:polished_blackstone_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]','comms/console-face')
                put(xx,-448,z+1,'minecraft:stone_button[face=wall,facing=south,powered=false]','comms/control')
            put(x+1,-448,z+2,'minecraft:polished_deepslate_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]','comms/seat')
    for x in range(61,81,4):
        box(x,-448,285,x+1,-444,285,DARK,'comms/rack')
        put(x,-445,284,'minecraft:redstone_lamp[lit=false]','comms/status-panel')

    # Lower service deck: four large shrouded data/cooling modules, exposed lower manifolds.
    for x in (15,35):
        for z in (293,313):
            box(x-3,-462,z-3,x+3,-462,z+3,EDGE,'service/module-plinth')
            box(x-2,-461,z-2,x+2,-455,z+2,DARK,'service/module-body')
            box(x-2,-456,z-2,x+2,-454,z+2,WALL,'service/module-shroud')
            box(x-3,-456,z-3,x+3,-456,z+3,RED,'service/shroud-band')
            for xx in (x-2,x,x+2):
                box(xx,-461,z-3,xx,-458,z-3,'minecraft:polished_basalt[axis=y]','service/exposed-manifold')
            put(x,-459,z-4,'minecraft:lever[face=floor,facing=north,powered=false]','service/local-isolator')
    for z in range(292,322):
        put(27,-463,z,'minecraft:polished_basalt[axis=z]','service/cable-trench')
        put(28,-463,z,'minecraft:dark_prismarine','service/cooling-trench')
        for x in (27,28):
            put(x,-462,z,'minecraft:iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]','service/flush-grating')
    for x in (11,45):
        box(x,-465,289,x,-451,289,EDGE,'service/structural-column')
        box(x,-465,323,x,-451,323,EDGE,'service/structural-column')

    def sign(x,y,z,facing,lines):
        put(x,y,z,f'minecraft:birch_wall_sign[facing={facing},waterlogged=false]','wayfinding/sign')
        text=nbtlib.Compound({'color':nbtlib.String('black'),'has_glowing_text':nbtlib.Byte(0),
            'messages':nbtlib.List[nbtlib.String]([nbtlib.String(json.dumps({'text':v},ensure_ascii=False)) for v in lines])})
        additions[(x,y,z)]=nbtlib.Compound({'id':nbtlib.String('minecraft:sign'),
            'x':nbtlib.Int(x),'y':nbtlib.Int(y),'z':nbtlib.Int(z),'front_text':text,'back_text':text,
            'is_waxed':nbtlib.Byte(1)})
    sign(-3,-445,273,'east',['NERV / A','DUTY','值班准备','TO COMMAND >'])
    sign(-3,-445,291,'east',['NERV / A','BRIEFING','作战简报','STAIRS SOUTH'])
    sign(57,-445,294,'west',['NERV / B','COMMS','通信支援','DATA DECK v'])
    sign(9,-458,305,'east',['TECH / 01','DATA SERVICE','数据链路维护','< WEST STAIR'])
    sign(47,-458,305,'west',['TECH / 01','DATA SERVICE','数据链路维护','EAST STAIR >'])
    changes=[Change(PACKET,*pos,before[pos],state,'user_authorized_preview',reasons[pos])
             for pos,state in sorted(desired.items()) if before[pos]!=state]
    return before,desired,changes,additions,doors


def validate_routes(before,desired):
    def state(p): return desired.get(p,before.get(p,'UNKNOWN'))
    def free(s):
        return bare(s) in FREE or any(k in s for k in ['wall_sign','_button','lever'])
    @lru_cache(None)
    def walk(p):
        x,y,z=p
        return free(state(p)) and free(state((x,y+1,z))) and not free(state((x,y-1,z))) and state((x,y-1,z))!='UNKNOWN'
    start=(28,-448,267)
    targets={'duty':(-16,-448,270),'briefing':(-24,-448,282),'communications':(60,-448,290),
             'west_mid_landing':(-8,-455,312),'east_mid_landing':(64,-455,312),
             'lower_service':(28,-461,302),'east_existing_corridor':(48,-448,276)}
    if not walk(start): raise RuntimeError(f'Entry not walkable: {start}')
    queue=deque([start]);dist={start:0}
    while queue:
        p=queue.popleft();x,y,z=p
        for dx,dz in [(1,0),(-1,0),(0,1),(0,-1)]:
            for dy in (0,1,-1):
                q=(x+dx,y+dy,z+dz)
                if q in dist or not all(LO[i]<=q[i]<=HI[i] for i in range(3)) or not walk(q):continue
                if dy==1 and 'stairs' not in state((q[0],q[1]-1,q[2])) and 'stairs' not in state((x,y-1,z)):continue
                dist[q]=dist[p]+1;queue.append(q)
    missing={n:p for n,p in targets.items() if p not in dist}
    if missing: raise RuntimeError(f'Disconnected routes: {missing}; reachable={len(dist)}')
    return {n:{'feet':list(p),'steps_from_entry':dist[p]} for n,p in targets.items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-preview',action='store_true')
    parser.add_argument('--revise-preview',action='store_true')
    args=parser.parse_args()
    before,desired,changes,additions,doors=plan()
    routes=validate_routes(before,desired)
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'forward.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['x','y','z','before','after','reason'])
        writer.writerows((c.x,c.y,c.z,c.before,c.after,c.reason) for c in changes)
    with (OUT/'inverse.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['x','y','z','before','after','reason'])
        writer.writerows((c.x,c.y,c.z,c.after,c.before,'undo/'+c.reason) for c in changes)
    manifest={'packet':PACKET,'source':str(SOURCE),'preview':str(TARGET),'writes':len(changes),
              'bounds':[LO,HI],'rooms':['west duty','west briefing','east communications','lower data service'],
              'entry':[28,-448,267],'east_branch':[50,-448,278],
              'doors':doors,'new_signs':[list(p) for p in additions],
              'validated_routes':routes,
              'reasons':dict(Counter(c.reason for c in changes)),
              'authority':'2026-09-05 user requested a TV-style pyramid interior trial; original R28 is read-only'}
    regions={(c.x>>9,c.z>>9) for c in changes}
    manifest['source_region_sha256']={f'r.{rx}.{rz}.mca':hashlib.sha256((dimension_dir(SOURCE,DIM)/'region'/f'r.{rx}.{rz}.mca').read_bytes()).hexdigest() for rx,rz in regions}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.apply_preview:
        if TARGET.resolve()==SOURCE.resolve(): raise RuntimeError('Refusing to write the source')
        marker=TARGET/'.projectseele_pyramid_tv_preview.json'
        if TARGET.exists():
            old=json.loads(marker.read_text(encoding='utf-8'))
            if not args.revise_preview or old.get('packet')!=PACKET or old.get('handed_off',False):
                raise RuntimeError('Existing preview is not an editable trial owned by this packet')
            iteration=OUT/'iterations'/time.strftime('%Y%m%d_%H%M%S');iteration.mkdir(parents=True)
            for name,h in old['source_region_sha256'].items():
                backup=OUT/'region_before'/name
                if hashlib.sha256(backup.read_bytes()).hexdigest()!=h: raise RuntimeError('Baseline backup changed')
                path=dimension_dir(TARGET,DIM)/'region'/name
                if not path.resolve().is_relative_to(TARGET.resolve()): raise RuntimeError('Invalid preview path')
                shutil.copy2(path,iteration/name)
                shutil.copy2(backup,path)
        else:
            shutil.copytree(SOURCE,TARGET)
            level=nbtlib.load(TARGET/'level.dat')
            level['Data']['LevelName']=nbtlib.String('SEELE - TV Pyramid Interior Preview')
            level.save()
        marker.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        (TARGET/'.projectseele_spatial_preview_read_only.json').write_text('{"purpose":"pyramid TV interior trial; disable runtime builders"}',encoding='utf-8')
        grouped=defaultdict(lambda:defaultdict(list))
        for c in changes: grouped[(c.x>>9,c.z>>9)][(c.x>>4,c.z>>4)].append(c)
        backups=OUT/'region_before';backups.mkdir(exist_ok=True)
        for (rx,rz),chunk_changes in grouped.items():
            path=dimension_dir(TARGET,DIM)/'region'/f'r.{rx}.{rz}.mca'
            if not (backups/path.name).exists(): shutil.copy2(path,backups/path.name)
            atomic_replace(path,rewrite_region(path,chunk_changes,block_entity_additions=additions))
        actual=read_box(TARGET,DIM,LO,HI)
        mismatch=[(c.x,c.y,c.z) for c in changes if actual.get((c.x,c.y,c.z))!=c.after]
        if mismatch: raise RuntimeError(f'read-back mismatch: {mismatch[:10]}')
        read_entities=dict(iter_block_entities(TARGET,DIM,LO,HI))
        if any(read_entities.get(p)!=entry for p,entry in additions.items()): raise RuntimeError('Sign NBT read-back mismatch')
        if any(hashlib.sha256((dimension_dir(SOURCE,DIM)/'region'/name).read_bytes()).hexdigest()!=h for name,h in manifest['source_region_sha256'].items()): raise RuntimeError('Source region changed during preview creation')
        (OUT/'applied.json').write_text(json.dumps({'writes':len(changes),'readback':'PASS','source_unchanged':True}),encoding='utf-8')
    print(json.dumps({'writes':len(changes),'regions':len({(c.x>>9,c.z>>9) for c in changes}),
                      'preview_written':args.apply_preview,'output':str(OUT)}))


if __name__=='__main__':main()
