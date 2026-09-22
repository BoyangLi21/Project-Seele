"""Survey complete named facility volumes, not only previously accepted path centre-lines.

Candidate floors, gaps and light sites are evidence, not an automatic build mask.
All block reads use the shared query_blocks-backed volume reader.
"""
from pathlib import Path
import argparse,json,gc
import numpy as np
from scipy.ndimage import label,find_objects,binary_dilation
from scipy.spatial import cKDTree
import scan_regional_completion as scan

ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=ROOT/'artifacts/facility_r30/survey'

def domains():
    boxes=[('pyramid',[-80,-474,235],[158,-354,425]),('command_rear',[16,-413,248],[42,-388,292]),
           ('hangars',[-64,-449,-302],[199,-344,12]),('hangar_station_link',[82,-449,-70],[203,-432,260]),
           ('dogma',[-45,-574,224],[120,-547,345]),('arrival',[-452,-481,701],[-246,-443,823]),
           ('science',[178,-481,382],[389,-432,706]),('logistics',[158,-480,61],[365,-430,283]),
           ('un_base',[6120,65,-6320],[6885,163,-5650]),('nerv_airport',[350,63,-177],[1350,123,86])]
    region=json.loads((WORLD/'regional_plan.json').read_text());transit=json.loads((WORLD/'native_transit_r26.json').read_text())
    for zone in region['zones']:
        if zone['kind'] not in ('district','airport','gateway'):continue
        x,X,z,Z=zone['bounds'];floor=zone['floor'];boxes.append((zone['id'],[x,floor-20,z],[X,floor+100,Z]))
    for station in transit['stations']:
        a,b=station['position1'],station['position2'];lo=[min(a[k],b[k])-3 for k in ('x','y','z')];hi=[max(a[k],b[k])+3 for k in ('x','y','z')]
        boxes.append(('station_'+str(station['id']),lo,hi))
    return boxes

def main(only):
    OUT.mkdir(parents=True,exist_ok=True);scan.WORLD=WORLD
    shapes=json.loads((WORLD/'native_collision_shapes.json').read_text());cases=json.loads((WORLD/'quality_walk_cases.json').read_text());route=[]
    for c in cases:
        points=c.get('path') or [c.get('start'),c.get('end')]
        if not all(p is not None for p in points):continue
        for a,b in zip(points,points[1:]):
            a,b=np.asarray(a,float),np.asarray(b,float)
            if abs(b[1]-a[1])>4 and np.linalg.norm((b-a)[[0,2]])<2:continue
            route.extend(np.linspace(a,b,max(2,int(np.linalg.norm(b-a)/2)+1)))
    route=np.asarray(route);index=[]
    for name,lo,hi in domains():
        if only and name not in only:continue
        path=OUT/(name+'.json')
        a,pal=scan.volume(lo,hi,allow_unknown=True);known=[];free=[];floor=[];artificial=[]
        for state in pal:
            shape=shapes.get(state);base=state.split('[')[0]
            known.append(shape is not None or base in scan.AIR or base=='minecraft:light')
            collision=shape or []
            free.append(known[-1] and not any(b[0]<.8 and b[3]>.2 and b[2]<.8 and b[5]>.2 and b[1]<.999 and b[4]>0 for b in collision))
            floor.append(shape is not None and any(b[0]<=.2 and b[3]>=.8 and b[2]<=.2 and b[5]>=.8 and abs(b[4]-1)<1e-5 for b in collision)
                         and not any(k in base for k in ['chair','bench','stool','fence','bars','wall','leaves']))
            artificial.append(base.startswith(('projectseele:','mtr:','another_furniture:')) or any(k in base for k in ['concrete','terracotta','iron_block','smooth_stone','stone_brick','polished','glass']))
        f=np.asarray(free)[a];solid=np.asarray(floor)[a];manmade=np.asarray(artificial)[a]
        walk=np.zeros_like(f);walk[1:-1]=solid[:-2]&f[1:-1]&f[2:]
        # A top floor or outdoor terrain has no ceiling. Record that distinction.
        covered=np.zeros_like(walk)
        for dy in range(3,13):covered[:-dy]|=walk[:-dy]&solid[dy:]
        inside=walk&covered
        sample=route[np.all(route>=np.asarray(lo)+2,axis=1)&np.all(route<=np.asarray(hi)-2,axis=1)]
        near_route=np.zeros_like(walk)
        for p in sample:
            x,y,z=np.floor(p).astype(int)-lo
            near_route[max(0,y-1):y+2,max(0,z-4):z+5,max(0,x-4):x+5]=True
        permitted_floor=walk&((inside&manmade[np.maximum(0,np.arange(a.shape[0])-1),:,:])|near_route)
        gap=[]
        # Edge points retain their outward direction and full old states for later review.
        for dz,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
            neighbour=np.roll(f,(-dz,-dx),(1,2));drop=permitted_floor&neighbour&np.roll(neighbour,-1,0)
            for dy in range(1,5):drop&=np.roll(neighbour,dy,0)
            drop[:5]=False;drop[-3:]=False;drop[:,:3]=False;drop[:,-3:]=False;drop[:,:,:3]=False;drop[:,:,-3:]=False
            for y,z,x in np.argwhere(drop):gap.append({'floor':[int(x+lo[0]),int(y+lo[1]),int(z+lo[2])],'outward':[dx,dz],'support':pal[a[y-1,z,x]]})
        ceiling_sites=[];held_ceiling=0
        # A thin surface fixture hangs from an existing solid roof; roof geometry stays intact.
        for y,z,x in np.argwhere(inside&permitted_floor):
            X,Y,Z=x+lo[0],y+lo[1],z+lo[2]
            if X%6 or Z%6:continue
            for dy in range(3,9):
                if y+dy>=a.shape[0]:break
                if solid[y+dy,z,x]:
                    if all(f[y+k,z,x] for k in range(2,dy)) and pal[a[y+dy-1,z,x]] in scan.AIR:
                        ceiling_sites.append([int(X),int(Y+dy-1),int(Z),int(Y)])
                    break
            else:held_ceiling+=1
        # Group same-floor risks; graphs do not confer permission to construct across unknown air.
        risk=np.zeros_like(walk)
        for row in gap:
            x,y,z=np.asarray(row['floor'])-lo;risk[y,z,x]=True
        labels,count=label(binary_dilation(risk,iterations=1));clusters=[]
        for box in find_objects(labels):
            ys,zs,xs=box;pts=np.argwhere(risk[box])+[ys.start,zs.start,xs.start]
            if not len(pts):continue
            world=pts[:,[2,0,1]]+lo;clusters.append({'lo':world.min(0).tolist(),'hi':world.max(0).tolist(),'cells':len(pts)})
        report={'id':name,'bounds':[lo,hi],'measured_cells':int(a.size),'unknown_states':[s for s,k in zip(pal,known) if not k],
                'potential_floor_cells':int(walk.sum()),'covered_floor_cells':int(inside.sum()),'fall_edges':gap,'fall_clusters':sorted(clusters,key=lambda q:-q['cells']),
                'ceiling_sites':ceiling_sites,'ceiling_candidates':len(ceiling_sites),'scope':'Whole named volume, native saved collision shapes; possible floors and edges require semantic review before mutation.'}
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');index.append({k:v for k,v in report.items() if k not in ('fall_edges','ceiling_sites','fall_clusters')})
        print(name,'floor',report['potential_floor_cells'],'covered',report['covered_floor_cells'],'edge candidates',len(gap),'ceiling sites',len(ceiling_sites),'unknown states',len(report['unknown_states']),flush=True)
        del a,f,solid,manmade,walk,inside,near_route,permitted_floor,risk,labels;gc.collect()
    (OUT/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--only',nargs='*');main(ap.parse_args().only)
