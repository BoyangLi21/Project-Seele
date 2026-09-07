"""Remove tunnel shells left above the final graded terrain, preserving actual roads and buildings."""
import argparse,json,math
from collections import defaultdict
import numpy as np
import regional_voxels as vox
from regional_voxels import WORLD,DIM
from query_blocks import iter_selected_sections
from quality_structures import Builder,OUT,OLD,load

def run(apply=False):
    a=np.load(OUT/'surface_levels_extension_before.npz');base=a['height'];ox,oz=map(int,a['origin'])
    target=np.load(OUT/'extension_terrain_target.npz')['height'];h=np.load(OUT/'extension_road_surfaces.npz')['height2']
    plan=load(OUT/'extension_plan.json');retire=set();keep=set();seen=set();changes=[];number=0
    def shell(x,z,r,y,dx,dz,light):
        out={(xx,yy,zz) for xx in range(x-r-3,x+r+4) for zz in range(z-r-3,z+r+4) for yy in (y+6,y+7)}
        for side in (-r-3,r+3):
            xx,zz=x-dz*side,z+dx*side
            out.update((xx,yy,zz) for yy in range(y+1,y+6))
        if light:out.add((x,y+6,z))
        return out
    for road in plan['roads']:
        r=road['width']//2
        for a,b in zip(road['points'],road['points'][1:]):
            n=max(abs(a[0]-b[0]),abs(a[2]-b[2]));dx=int(np.sign(b[0]-a[0]));dz=int(np.sign(b[2]-a[2]))
            for i in range(n+1):
                x=round(a[0]+(b[0]-a[0])*i/max(1,n));z=round(a[2]+(b[2]-a[2])*i/max(1,n));number+=1
                if (x,z) in seen:continue
                seen.add((x,z));y=(int(h[z-oz,x-ox])-1)//2;old=int(base[z-oz,x-ox]);new=int(target[z-oz,x-ox])
                cells=shell(x,z,r,y,dx,dz,(number-1)%12==0)
                if new>=y+6:keep.update(cells)
                elif old>y+8:retire.update(cells);changes.append(dict(road=road['id'],x=x,z=z,old_ground=old,final_ground=new,road_floor=y))
    retire-=keep
    protected=[]
    for b in plan['estate']['blocks']+load(OUT/'surface_layout.json')['kept_plots']:
        x0,x1,z0,z1=b['bounds'];f=b.get('floor',70);protected.append((x0,f,z0,x1,f+b.get('storeys',3)*5+8,z1))
    for d in load(OLD/'transit_plan.json')['platforms']+plan['transit']['platforms']:
        x,y,z=d['center'];half=d['length']//2+10;r=d.get('half_width',15)
        protected.append((x-half,y-3,z-r-1,x+half,y+15,z+r+1) if d['heading'] in ('E','W') else (x-r-1,y-3,z-half,x+r+1,y+15,z+half))
    for box in [(460,32,1035,1220,118,1530),(-2180,32,-415,-1420,118,95)]:protected.append(box)
    retire={p for p in retire if not any(x0<=p[0]<=x1 and y0<=p[1]<=y1 and z0<=p[2]<=z1 for x0,y0,z0,x1,y1,z1 in protected)}
    selected=defaultdict(set)
    for x,y,z in retire:selected[x//16,z//16].add(y//16)
    measured={(cx,cz,sy):(pal,idx.reshape(16,16,16)) for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected)}
    vox.OUT=OUT;p=Builder();removed=[]
    for x,y,z in sorted(retire):
        pal,indices=measured[x//16,z//16,y//16];state=pal[indices[y&15,z&15,x&15]]
        if state in ('minecraft:light_gray_concrete','minecraft:sea_lantern'):
            p.put(x,y,z,'minecraft:air','remove_exposed_tunnel_shell');removed.append([x,y,z,state])
    report=dict(changed_centres=changes,removed=removed)
    (OUT/'exposed_road_tunnels.json').write_text(json.dumps(report),encoding='utf-8')
    print('Exposed tunnel centres',len(changes),'matching shell cells',len(removed),'roads',sorted({c['road'] for c in changes}),flush=True)
    p.apply('exposed_road_tunnel_cleanup') if apply else p.save_plan('exposed_road_tunnel_cleanup')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();run(args.apply)
