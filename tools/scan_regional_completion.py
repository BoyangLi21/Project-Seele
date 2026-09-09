"""Exact local circulation checks and evidence plans, independent of game rendering."""
from collections import deque
from pathlib import Path
import argparse,json
import numpy as np
from query_blocks import iter_selected_sections,AIR
from regional_voxels import WORLD,OUT,DIM


def passable(state):
    name=state.split('[')[0]
    return name in AIR or name=='minecraft:light' or name.endswith(('_button','_wall_sign','_sign','_torch')) or name=='minecraft:torch'


def volume(lo,hi,*,allow_unknown=False):
    selected={(cx,cz):set(range(lo[1]//16,hi[1]//16+1)) for cx in range(lo[0]//16,hi[0]//16+1) for cz in range(lo[2]//16,hi[2]//16+1)}
    palettes=[];lookup={};a=np.full((hi[1]-lo[1]+1,hi[2]-lo[2]+1,hi[0]-lo[0]+1),65535,dtype=np.uint16)
    for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected,skip_unfinished=allow_unknown):
        for state in pal:
            if state not in lookup:lookup[state]=len(palettes);palettes.append(state)
        mapping=np.asarray([lookup[s] for s in pal],dtype=np.uint16);v=mapping[idx].reshape(16,16,16)
        x0=max(lo[0],cx*16);x1=min(hi[0],cx*16+15)+1;z0=max(lo[2],cz*16);z1=min(hi[2],cz*16+15)+1;y0=max(lo[1],sy*16);y1=min(hi[1],sy*16+15)+1
        a[y0-lo[1]:y1-lo[1],z0-lo[2]:z1-lo[2],x0-lo[0]:x1-lo[0]]=v[y0-sy*16:y1-sy*16,z0-cz*16:z1-cz*16,x0-cx*16:x1-cx*16]
    if np.any(a==65535):
        if not allow_unknown:raise RuntimeError('Unmeasured local circulation volume')
        a[a==65535]=len(palettes);palettes.append('UNKNOWN')
    return a,palettes


def audit(name,lo,hi,start,targets):
    a,pal=volume(lo,hi);free=np.asarray([passable(s) for s in pal])[a]
    climb=np.asarray(['_stairs[' in s or 'escalator_step' in s for s in pal])[a]
    solid=np.asarray([not passable(s) and s.split('[')[0] not in ('minecraft:water','minecraft:lava') and not any(k in s for k in ('_door[','_fence','_bars','_pane')) for s in pal])[a]
    stand=np.zeros(a.shape,dtype=bool);stand[1:-1]=free[1:-1]&free[2:]&solid[:-2]
    start_index=(start[1]-lo[1],start[2]-lo[2],start[0]-lo[0]);seen=np.zeros(a.shape,dtype=bool);q=deque()
    if stand[start_index]:seen[start_index]=True;q.append(start_index)
    h,d,w=a.shape
    while q:
        y,z,x=q.popleft()
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            xx,zz=x+dx,z+dz
            if not 0<=xx<w or not 0<=zz<d:continue
            for dy in (0,-1,1):
                yy=y+dy
                if not 1<=yy<h-1 or seen[yy,zz,xx] or not stand[yy,zz,xx]:continue
                if dy and not(climb[y-1,z,x] or climb[yy-1,zz,xx]):continue
                if dy>0 and not free[y+2,z,x]:continue
                if dy<0 and not free[yy+2,zz,xx]:continue
                seen[yy,zz,xx]=True;q.append((yy,zz,xx))
    results=[]
    for key,(x,y,z) in targets.items():
        index=(y-lo[1],z-lo[2],x-lo[0]);ok=bool(seen[index]);near=[]
        if not ok:
            for dz in range(-2,3):
                for dx in range(-2,3):
                    if 0<=index[1]+dz<d and 0<=index[2]+dx<w and seen[index[0],index[1]+dz,index[2]+dx]:near.append([x+dx,y,z+dz])
        results.append(dict(id=key,pos=[x,y,z],connected=ok,near_connected=near[:3],feet=pal[a[index]],floor=pal[a[index[0]-1,index[1],index[2]]]))
    folder=OUT/'circulation';folder.mkdir(exist_ok=True)
    report=dict(id=name,bounds=[lo,hi],start=start,start_standable=bool(stand[start_index]),reachable_cells=int(seen.sum()),targets=results)
    (folder/(name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    np.savez_compressed(folder/(name+'.npz'),palette=np.asarray(pal),blocks=a,reachable=seen,bounds=[lo,hi])
    print(name,'reachable',int(seen.sum()),'PASS',sum(t['connected'] for t in results),'/',len(results),flush=True)
    for t in results:
        if not t['connected']:print('DISCONNECTED',t['id'],t['pos'],t['feet'],t['floor'],t['near_connected'],flush=True)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--part',default='all');args=parser.parse_args()
    places=json.loads((OUT/'geometry_all/places.json').read_text(encoding='utf-8'))
    if args.part in ('all','hq'):
        targets={r['id']:[r['entry'][0]+(-1 if r['id'].startswith('hq/west') else 1),r['entry'][1],r['entry'][2]] for r in places['rooms'] if r['id'].startswith('hq/')}
        targets.update(existing_west=[-24,-448,282],existing_east=[60,-448,290],hq_station=[30,-466,470],west_upper=[-29,-448,350],east_upper=[89,-448,350],public_lift_join=[123,-442,273],hangar_walkway=[118,-442,250])
        audit('hq',(-78,-469,250),(140,-430,477),(30,-461,418),targets)
    if args.part in ('all','arrival'):
        audit('arrival',(-408,-490,702),(-276,-447,810),(-360,-466,735),{'U1_platform':[-340,-466,776],'lobby_east_exit':[-314,-466,726]})
    if args.part in ('all','science'):
        targets={r['id']:[r['entry'][0]+1,r['entry'][1],r['entry'][2]] for r in places['rooms'] if r['id'].startswith('science/')}
        targets.update(sigma=[275,-466,633],sigma_lobby=[250,-466,681])
        audit('science',(185,-475,428),(380,-437,700),(310,-460,565),targets)
    if args.part in ('all','hangar'):
        audit('hangar_walk',(84,-470,-66),(200,-430,281),(123,-442,273),{'hangar_platform':[174,-442,-47],'moving_walkway':[118,-442,80]})
    if args.part in ('all','logistics'):
        targets={r['id']:[r['entry'][0]-1,r['entry'][1],r['entry'][2]] for r in places['rooms'] if r['id'].startswith('logistics/')}
        audit('logistics',(173,-475,85),(325,-446,279),(300,-460,180),targets)
    if args.part in ('all','airport'):
        for name,sx,gx,rz,sz in [('bay',740,650,1430,1190),('hakone',-1670,-1610,-20,-265)]:
            audit('airport_'+name,(sx-102,60,rz-383),(sx+102,104,rz-170),(sx,72,sz),{'terminal':[sx,81,rz-355],'gate_apron':[gx,81,rz-218]})


if __name__=='__main__':main()
