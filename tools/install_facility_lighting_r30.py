"""Mount lights only against surveyed static ceilings, outside rail/lift envelopes."""
from pathlib import Path
from collections import Counter
import argparse,json
import numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
import scan_regional_completion as scan
from query_blocks import read_box,iter_selected_sections,AIR

ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';ART=ROOT/'artifacts/facility_r30';OUT=ART/'lighting'
SHAFTS=[(12,253,-575,90),(130,273,-455,95),(66,302,-470,-355),(-29,-278,-400,-355),(93,-52,-450,-350)]

def static_ceiling(state):
    name=state.split('[')[0]
    return name in {'minecraft:stone','minecraft:iron_block','minecraft:glass','minecraft:smooth_stone','minecraft:deepslate','minecraft:bedrock'} or (
        name.startswith('minecraft:') and any(k in name for k in ['concrete','terracotta','_planks','stone_bricks','stained_glass'])) or (
        name.startswith('projectseele:nerv_') and any(k in name for k in ['panel','paving','edge','light','datum']))

def main(apply):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;scan.WORLD=WORLD;p=v.Painter();sites={};held=[]
    native=json.loads((WORLD/'native_transit_r26.json').read_text());rail=np.array([q for c in native['curves'] if c['mode']=='TRAIN' for q in c['points']]);tree=cKDTree(rail[:,[0,2]])
    for report in sorted((ART/'survey').glob('*.json')):
        if report.name=='index.json':continue
        d=json.loads(report.read_text());lo,hi=d['bounds'];blocks,palette=scan.volume(lo,hi,allow_unknown=True)
        def state_at(q):
            x,y,z=q
            if not (lo[0]<=x<=hi[0] and lo[1]<=y<=hi[1] and lo[2]<=z<=hi[2]):return 'UNKNOWN'
            return palette[blocks[y-lo[1],z-lo[2],x-lo[0]]]
        for x,y,z,floor in d['ceiling_sites']:
            q=(x,y,z)
            if q in sites:continue
            old=state_at(q);roof=state_at((x,y+1,z))
            if old not in AIR or not static_ceiling(roof):continue
            if 'strip_light' in roof or 'froglight' in roof:continue
            if any(abs(x-X)<=4 and abs(z-Z)<=4 and a<=y<=b for X,Z,a,b in SHAFTS):held.append({'pos':q,'reason':'lift motion envelope'});continue
            near=tree.query_ball_point([x,z],3.8)
            if near and any(rail[i,1]-.2<=y<=rail[i,1]+6.1 for i in near):held.append({'pos':q,'reason':'train swept envelope'});continue
            controlled=6<=x<=52 and 272<=z<=365 and -445<=floor<=-406
            state='projectseele:nerv_ceiling_light[hanging=true,lit='+('false' if controlled else 'true')+']'
            sites[q]={'pos':q,'old':old,'roof':roof,'floor':floor,'controlled':controlled,'zone':d['id'],'state':state}
            p.match((*q,*q),old,state,'r30/static_ceiling_luminaire')
    # The command hall is a tall atrium: roof fixtures alone cannot illuminate its lower platforms.
    room=read_box(WORLD,v.DIM,(8,-431,264),(51,-403,310))
    for y in [-429,-424,-423,-413,-409,-406]:
        for x in range(10,51,6):
            for z in range(274,310,6):
                q=(x,y,z);old=room.get(q)
                if q in sites or old not in AIR or room.get((x,y+1,z)) not in AIR:continue
                if not static_ceiling(room.get((x,y-1,z),'UNKNOWN')):continue
                state='projectseele:nerv_ceiling_light[hanging=false,lit=false]'
                sites[q]={'pos':q,'old':old,'floor':y,'controlled':True,'zone':'command_platforms','state':state}
                p.match((*q,*q),old,state,'r30/command_platform_recessed_luminaire')
    # Low guide lights serve documented routes under tall roofs (not natural caves).
    wanted=set()
    for case in json.loads((WORLD/'quality_walk_cases.json').read_text()):
        path=case.get('path') or [case.get('start'),case.get('end')]
        if not all(q is not None for q in path):continue
        for a,b in zip(path,path[1:]):
            a,b=np.asarray(a,float),np.asarray(b,float)
            if max(a[1],b[1])>=-300 or abs(a[1]-b[1])>1:continue
            for q in np.linspace(a,b,max(2,int(np.linalg.norm(b-a)/7)+1)):
                if abs(q[1]-round(q[1]))<.05:wanted.add(tuple(map(int,np.floor(q))))
    selected={};queries={}
    for x,y,z in wanted:
        for Y in [y-1,y,y+1]:
            selected.setdefault((x//16,z//16),set()).add(Y//16);queries.setdefault((x//16,z//16,Y//16),set()).add((x,Y,z))
    measured={}
    for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,v.DIM,selected,skip_unfinished=True):
        for q in queries.get((cx,cz,sy),()):
            x,y,z=q;measured[q]=pal[idx[(y-sy*16)*256+(z&15)*16+(x&15)]]
    constant=np.array([q for q,r in sites.items() if not r['controlled']]);light_tree=cKDTree(constant);buckets=set()
    for q in sorted(wanted):
        x,y,z=q;bucket=(x//6,y//3,z//6)
        if q in sites or bucket in buckets or (6<=x<=52 and 272<=z<=365 and -445<=y<=-406):continue
        old=measured.get(q);support=measured.get((x,y-1,z),'UNKNOWN')
        if old not in AIR or measured.get((x,y+1,z)) not in AIR or not static_ceiling(support) or 'glass' in support:continue
        if light_tree.query(q)[0]<6:continue
        if any(abs(x-X)<=4 and abs(z-Z)<=4 and a<=y<=b for X,Z,a,b in SHAFTS):continue
        near=tree.query_ball_point([x,z],3.8)
        if near and any(rail[i,1]-.2<=y<=rail[i,1]+6.1 for i in near):continue
        state='projectseele:nerv_ceiling_light[hanging=false,lit=true]';buckets.add(bucket)
        sites[q]={'pos':q,'old':old,'floor':y,'controlled':False,'zone':'tall_roof_route_guides','state':state}
        p.match((*q,*q),old,state,'r30/public_route_recessed_guide')
    lever=(26,-405,275);support=(26,-406,275);measured=read_box(WORLD,v.DIM,(26,-406,275),(26,-405,275))
    assert measured[lever] in AIR and measured[support]=='minecraft:stone',measured
    p.match((*lever,*lever),measured[lever],'minecraft:lever[face=floor,facing=south,powered=false]','r30/commander_lighting_lever')
    counts=Counter(row['zone'] for row in sites.values());p.meta.update(lights=len(sites),zones=dict(counts),command_lever=list(lever),command_lamps=[list(q) for q,r in sites.items() if r['controlled']],held=held,fixture_contract='2/16-high fixture backed by a measured static ceiling; clear of all current rail gauges and named moving shafts; original roof and floor states retained')
    p.save_plan('facility_interior_lighting');(OUT/'sites.json').write_text(json.dumps(list(sites.values()),ensure_ascii=False,indent=2),encoding='utf8')
    print('R30 light sites',len(sites),'command circuit',len(p.meta['command_lamps']),'held',len(held),dict(counts),flush=True)
    if apply:
        p.apply('facility_interior_lighting')
        (WORLD/'facility_lighting_r30.json').write_text(json.dumps({'revision':'R30','command_lever':list(lever),'command_lamps':p.meta['command_lamps'],'constant_lamps':[list(q) for q,r in sites.items() if not r['controlled']]},indent=2),encoding='utf8')
        states=set(json.loads((WORLD/'regional_states.json').read_text()));states.update(row['state'] for row in sites.values());states.update(['minecraft:lever[face=floor,facing=south,powered=false]','minecraft:lever[face=floor,facing=south,powered=true]']);(WORLD/'regional_states.json').write_text(json.dumps(sorted(states),indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
