"""Retire recorded former railway fabric outside current trains, walks and city plots."""
from pathlib import Path
from collections import defaultdict,Counter
import json,math,numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import iter_selected_sections,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/retired_transit'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    sources=[ROOT/'artifacts/world_rebuild_r20/transit/native_snapshot.json',ROOT/'artifacts/access_r22/native_before.json']
    old=[r for path in sources for r in json.loads(path.read_text())['curves'] if r['mode']=='TRAIN']
    native=json.loads((OUT.parent/'airport/native_final.json').read_text());active=[r for r in native['curves'] if r['mode']=='TRAIN']
    newpoints=np.asarray([q for r in active for q in r['points']]);newtree=cKDTree(newpoints[:,[0,2]])
    oldpoints=np.asarray([q for r in old for q in r['points']]);oldtree=cKDTree(oldpoints[:,[0,2]])
    selected=defaultdict(set)
    for xx,yy,zz in oldpoints[::2]:
        x,y,z=map(math.floor,(xx,yy,zz))
        for cx in range((x-6)//16,(x+6)//16+1):
            for cz in range((z-6)//16,(z+6)//16+1):selected[cx,cz].update(range((y-4)//16,(y+12)//16+1))
    routes=json.loads((WORLD/'quality_walk_cases.json').read_text());routes+=json.loads((OUT.parent/'reported/contract.json').read_text())['walk_nodes'];routes+=json.loads((OUT.parent/'airport/civil/contract.json').read_text())['walk_nodes']
    pedestrian=[]
    for r in routes:
        pts=r.get('path') or [r.get('start'),r.get('end')]
        if any(q is None for q in pts):continue
        for a,b in zip(pts,pts[1:]):
            a,b=np.asarray(a),np.asarray(b);pedestrian.extend(np.linspace(a,b,max(2,math.ceil(np.linalg.norm(a-b)))))
    walktree=cKDTree(np.asarray(pedestrian));plots=json.loads((ROOT/'artifacts/world_quality_r02/surface_layout.json').read_text())['kept_plots']
    road=np.load(ROOT/'artifacts/world_rebuild_r20/transit/civil/road_contract.npz');ox,oz=map(int,road['origin'])
    formation={'minecraft:light_gray_concrete','minecraft:gray_concrete','minecraft:gravel','minecraft:iron_bars','minecraft:polished_deepslate','minecraft:smooth_stone','minecraft:gray_stained_glass','minecraft:light_gray_stained_glass','minecraft:chain','minecraft:polished_blackstone_slab','minecraft:red_terracotta','minecraft:deepslate_bricks'}
    removed=[];kept=Counter();checked=0
    for cx,cz,sy,pal,indices in iter_selected_sections(WORLD,v.DIM,selected,skip_unfinished=True):
        ids=np.flatnonzero(np.asarray([s.split('[')[0] in formation for s in pal])[indices]);checked+=len(ids)
        if not len(ids):continue
        points=np.c_[cx*16+(ids&15),sy*16+(ids>>8),cz*16+((ids>>4)&15)]
        dist,oi=oldtree.query(points[:,[0,2]]+.5);nd,ni=newtree.query(points[:,[0,2]]+.5);wd,_=walktree.query(points+[.5,1,.5])
        for q,idx,d,i,n,j,w in zip(points,ids,dist,oi,nd,ni,wd):
            x,y,z=map(int,q)
            if d>5.5 or not oldpoints[i,1]-4<=y<=oldpoints[i,1]+11:continue
            if n<7.5:kept['current_alignment_or_support']+=1;continue
            if w<5:kept['registered_pedestrian_space']+=1;continue
            if -80<=x<=175 and -672<=y<=85 and -310<=z<=550:kept['headquarters_mechanics']+=1;continue
            if 350<=x<=1360 and 60<=y<=125 and -180<=z<=170:kept['airport_new_civil']+=1;continue
            rx,rz=x-ox,z-oz
            if y>=0 and 0<=rx<road['mask'].shape[1] and 0<=rz<road['mask'].shape[0] and road['mask'][rz,rx] and y<=road['height2'][rz,rx]/2+2:
                kept['ground_street']+=1;continue
            if any(b['bounds'][0]-2<=x<=b['bounds'][1]+2 and b['bounds'][2]-2<=z<=b['bounds'][3]+2 and b['floor']-1<=y<=b['floor']+b.get('storeys',1)*5+8 for b in plots):
                kept['retained_building_plot']+=1;continue
            # Old native stations remain public destinations only when a
            # current platform or registered walking path still claims them.
            state=pal[indices[idx]];removed.append((x,y,z,state))
    # Preserve fixed block-entity fixtures and their immediate backing cells.
    bychunk=defaultdict(list)
    for x,y,z,s in removed:bychunk[x//16,z//16].append((x,y,z,s))
    filtered=[]
    for (cx,cz),cells in bychunk.items():
        lo=(cx*16,min(q[1] for q in cells)-2,cz*16);hi=(cx*16+15,max(q[1] for q in cells)+2,cz*16+15)
        tags=list(iter_block_entities(WORLD,v.DIM,lo,hi))
        for x,y,z,s in cells:
            if any(abs(x-a[0])<=2 and abs(y-a[1])<=2 and abs(z-a[2])<=2 for a,t in tags):kept['existing_fixture']+=1;continue
            filtered.append((x,y,z,s));p.match((x,y,z,x,y,z),s,'minecraft:air','r28/recorded_retired_transit_fabric')
    p.meta.update(source_snapshots=[str(s) for s in sources],checked_formation_cells=checked,removed_cells=len(filtered),preserved_reasons=dict(kept),scope='Full recorded historical train alignments in surface and GeoFront; current rail/support buffers, current pedestrian paths, buildings, roads and mechanisms excluded')
    p.apply('retired_recorded_transit_fabric')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
    print('Historical transit fabric inspected',checked,'retired',len(filtered),'kept',dict(kept),flush=True)

if __name__=='__main__':main()
