"""Saved-voxel floor and connected-route audits for the played regional world.

This uses query_blocks through the existing volume reader. Flood routes are
diagnostic candidates; only native player movement can certify their risers.
"""
from pathlib import Path
from collections import deque
import argparse,json,heapq
import numpy as np
from scipy.ndimage import label
import scan_regional_completion as scan
from regional_voxels import ROOT,WORLD

OUT=ROOT/'artifacts/world_quality_r03'
R02=ROOT/'artifacts/world_quality_r02'
OLD=ROOT/'artifacts/world_expansion_20260907'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))

def floors():
    rooms=load(R02/'circulation_repair/places.json')['rooms']
    rooms += [r for r in load(OLD/'geometry_all/places.json')['rooms'] if not r['id'].startswith('hq/')]
    from refine_world_quality_r03 import current_plots
    plots=[r for r in (load(R02/'surface_layout.json')['kept_plots'] if scan.WORLD!=WORLD else current_plots()) if 'storeys' in r]
    reports=[];holes=[];islands=[]
    for place in rooms+plots:
        x0,x1,z0,z1=place['bounds'];f=place['floor'];levels=place.get('storeys',1)
        a,pal=scan.volume((x0,f,z0),(x1,f+(levels-1)*5+3,z1))
        empty=np.asarray([s in scan.AIR for s in pal])[a]
        free=np.asarray([scan.passable(s) or '_door[' in s for s in pal])[a]
        for n in range(levels):
            y=n*5;mask=np.zeros(a.shape[1:],bool);mask[1:-1,1:-1]=True
            if levels>1:mask[2:11,1:10]=False
            gap=mask&empty[y]&free[y+1]&free[y+2]
            for zz,xx in zip(*np.nonzero(gap)):holes.append(dict(id=place['id'],pos=[x0+int(xx),f+y,z0+int(zz)]))
            walk=mask&~empty[y]&free[y+1]&free[y+2]
            groups,count=label(walk);sizes=np.bincount(groups.ravel());sizes[0]=0
            main=int(sizes.argmax())
            for k in range(1,count+1):
                if k==main or sizes[k]<9:continue
                zz,xx=np.argwhere(groups==k)[0];islands.append(dict(id=place['id'],floor=f+y,cells=int(sizes[k]),pos=[x0+int(xx),f+y+1,z0+int(zz)]))
            reports.append(dict(id=place['id'],floor=f+y,columns=int(mask.sum()),holes=int(gap.sum()),walk_cells=int(walk.sum())))
    result=dict(floors=len(reports),columns=sum(r['columns'] for r in reports),holes=holes,isolated_floor_areas=islands,details=reports)
    (OUT/'floor_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FLOORS',result['floors'],'columns',result['columns'],'holes',len(holes),'isolated candidates',len(islands),flush=True)
    print(json.dumps(dict(holes=holes[:12],islands=islands[:12]),ensure_ascii=False),flush=True)

def find_path(file,start,end):
    d=np.load(file);a=d['blocks'];pal=d['palette'];lo=d['bounds'][0]
    free=np.asarray([scan.passable(str(s)) for s in pal])[a]
    climb=np.asarray(['_stairs[' in s or 'escalator_step' in s for s in pal])[a]
    solid=np.asarray([not scan.passable(str(s)) and s.split('[')[0] not in ('minecraft:water','minecraft:lava') and not any(k in s for k in ('_door[','_fence','_bars','_pane')) for s in pal])[a]
    stand=np.zeros(a.shape,bool);stand[1:-1]=free[1:-1]&free[2:]&solid[:-2]
    def local(p):return (p[1]-int(lo[1]),p[2]-int(lo[2]),p[0]-int(lo[0]))
    begin,goal=local(start),local(end)
    if not stand[begin] or not stand[goal]:raise ValueError(('Not standing',start,end))
    frontier=[(0,0,begin)];cost={begin:0};parent={};h,d,w=a.shape
    while frontier:
        _,g,current=heapq.heappop(frontier)
        if current==goal:break
        if g>cost[current]:continue
        y,z,x=current
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            xx,zz=x+dx,z+dz
            if not 0<=xx<w or not 0<=zz<d:continue
            for dy in (0,-1,1):
                yy=y+dy;nxt=(yy,zz,xx)
                if not 1<=yy<h-1 or not stand[nxt]:continue
                if dy and not(climb[y-1,z,x] or climb[yy-1,zz,xx]):continue
                if dy>0 and not free[y+2,z,x]:continue
                if dy<0 and not free[yy+2,zz,xx]:continue
                ng=g+1+abs(dy)*.2
                if ng>=cost.get(nxt,1e20):continue
                cost[nxt]=ng;parent[nxt]=current
                heuristic=abs(yy-goal[0])+abs(zz-goal[1])+abs(xx-goal[2])
                heapq.heappush(frontier,(ng+heuristic,ng,nxt))
    else:raise ValueError(('Disconnected route',start,end))
    points=[goal]
    while points[-1]!=begin:points.append(parent[points[-1]])
    points.reverse();simple=[points[0]]
    for i in range(1,len(points)-1):
        prev,cur,nxt=points[i-1:i+2]
        if tuple(cur[j]-prev[j] for j in range(3))!=tuple(nxt[j]-cur[j] for j in range(3)):simple.append(cur)
    simple.append(points[-1])
    return [[int(x+lo[0])+.5,int(y+lo[1]),int(z+lo[2])+.5] for y,z,x in simple]

def routes():
    cases=[]
    specs=[('pyramid_to_launch','pyramid_to_cage_wait',[30,-461,418],[93,-442,-47]),
           ('pyramid_to_launch','pyramid_to_U2_platform',[30,-461,418],[150,-442,-30]),
           ('hangar_middle','hangar_to_observation_lift',[93,-394,-46],[94,-394,-20])]
    specs += [('hangar_middle',f'cage_gallery_{x}',[93,-394,-46],[x,-394,-73]) for x in (-12,30,72)]
    specs += [('launch_gallery',f'launch_control_{x}',[88,-418,-15],[x,-418,-15]) for x in (-12,30,72)]
    for grid,key,start,end in specs:
        path=find_path(OUT/'circulation'/f'{grid}.npz',start,end)
        if key.startswith('pyramid_to_'):
            # This transfer must enter the north-facing flight from its foot,
            # not step sideways onto the tall edge of its first stair block.
            a=next(i for i,p in enumerate(path) if p==[87.5,-448,254.5])
            b=next(i for i,p in enumerate(path) if p==[114.5,-442,243.5])
            path[a:b+1]=[[89.5,-448,258.5],[112.5,-448,258.5],[112.5,-448,255.5],[112.5,-442,247.5],[114.5,-442,243.5]]
        if key=='pyramid_to_cage_wait' and list((OUT/'access_repairs_details').glob('applied_*/receipt.json')):
            i=path.index([131.5,-442,-47.5])
            path[i:]=[[131.5,-442,-47.5],[114.5,-442,-47.5],[114.5,-442,-49.5],[101.5,-442,-49.5],[101.5,-442,-43.5],[93.5,-442,-43.5],[93.5,-442,-46.5]]
        cases += [dict(id='r03/continuous/'+key,path=path),dict(id='r03/continuous/'+key+'/return',path=path[::-1])]
        print(key,'waypoints',len(path),flush=True)
    (OUT/'continuous_cases.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
    return cases

def prepare(full=False):
    cases=routes()
    for x in (28,48):
        for reverse in (False,True):
            a=[x+.5,-448,283.5];b=[x+.5,-448,278.5]
            cases.append(dict(id=f'r03/retained_door/{x}'+('/return' if reverse else ''),start=b if reverse else a,end=a if reverse else b,useDoor=True,door=[x,-448,282]))
    # The retained MTR retrofit leaves the ordinary stair at Z=273.5;
    # Z=274.5 lies on an escalator handrail, not the pedestrian centre.
    a=[48.5,-448,273.5];b=[58.5,-442,273.5]
    cases.extend([dict(id='r03/retained_B40_stair',start=a,end=b),dict(id='r03/retained_B40_stair/return',start=b,end=a)])
    for name,end in [('dogma_front',[30,-566,300]),('dogma_west',[-2,-566,279]),('dogma_perimeter',[30,-566,332]),('dogma_quarantine',[60,-566,310])]:
        path=find_path(OUT/'circulation/dogma.npz',[12,-566,258],end)
        cases.extend([dict(id='r03/'+name,path=path),dict(id='r03/'+name+'/return',path=path[::-1])])
    if full:
        seen=set()
        for filename in ('native_full01.json','native_extension01.json','native_final_crossings.json'):
            for case in load(R02/filename):
                if case['id'] in seen:continue
                seen.add(case['id']);cases.append({k:v for k,v in case.items() if k in ('id','start','end','button','door')})
        from refine_world_quality_r03 import current_plots
        from quality_structures import Station
        for b in current_plots():
            if 'storeys' not in b:continue
            x=b['entry'][0];f=b['floor'];z=b['bounds'][3]
            a=[x+.5,f+1,z+4.5];end=[x+.5,f+1,z-.5]
            for reverse in (False,True):cases.append(dict(id='r03/entry/'+b['id']+('/return' if reverse else ''),start=end if reverse else a,end=a if reverse else end,door=[x,f+1,z],useDoor=True))
        platforms=[d for d in load(OLD/'transit_plan.json')['platforms'] if d.get('mode')!='AIRPLANE']+load(R02/'extension_plan.json')['transit']['platforms']
        for d in platforms:
            if d.get('compact'):continue
            s=Station(None,d)
            for v in (-5,5):
                a=s.pos(-s.half+2,s.y+1,v);b=s.pos(s.half-2,s.y+1,v)
                for reverse in (False,True):cases.append(dict(id='r03/platform_length/'+d['id']+'/'+str(v)+('/return' if reverse else ''),start=b if reverse else a,end=a if reverse else b))
        for sx,z0 in [(740,1050),(-1670,-400)]:
            for z in (z0+26,z0+67):
                for side in (-1,1):
                    a=[sx+.5,81,z+.5];b=[sx+side*88+.5,81,z+.5]
                    for reverse in (False,True):cases.append(dict(id=f'r03/airport_lounge/{sx}/{z}/{side}'+('/return' if reverse else ''),start=b if reverse else a,end=a if reverse else b))
            for side in (-1,1):
                for index in range(3):
                    x=sx+side*(27+index*24)
                    path=[[sx+.5,81,z0+26.5],[x+.5,81,z0+26.5],[x+.5,81,z0+17.5]]
                    cases.append(dict(id=f'r03/checkin/{sx}/{side}/{index}',path=path))
    (WORLD/'quality_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False),encoding='utf-8')
    (OUT/('native_cases_full.json' if full else 'native_cases_routes.json')).write_text(json.dumps(cases,ensure_ascii=False),encoding='utf-8')
    print('Prepared',len(cases),'native cases')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['floors','routes','prepare']);ap.add_argument('--baseline',action='store_true');ap.add_argument('--full',action='store_true');args=ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.baseline:scan.WORLD=Path(load(OUT/'source_manifest.json')['backup'])
    if args.mode=='floors':floors()
    elif args.mode=='routes':routes()
    else:prepare(args.full)
