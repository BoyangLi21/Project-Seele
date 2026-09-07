"""Read back every designed road column, including physical headroom and height."""
import json,math,argparse
from collections import defaultdict,Counter
import numpy as np
from query_blocks import iter_selected_sections,AIR
from regional_voxels import WORLD,DIM,ROOT
OUT=ROOT/'artifacts/world_quality_r02'

def audit(source='road_surfaces.npz',report_name='road_actual_audit.json'):
    a=np.load(OUT/source);h=a['height2'];mask=a['mask'].copy();ox,oz=map(int,a['origin'])
    # A newly authored station replaces street space with platforms and ramps.
    # Those volumes have their own native collision/boarding cases.
    if source=='road_surfaces.npz' and (OUT/'estate_stations').exists() and list((OUT/'estate_stations').glob('applied_*/receipt.json')):
        for station in json.loads((OUT/'extension_plan.json').read_text(encoding='utf-8'))['transit']['platforms']:
            if not station.get('compact'):continue
            x,y,z=station['center'];half=station['length']//2+11;r=station['half_width']+1
            mask[z-r-oz:z+r-oz+1,x-half-ox:x+half-ox+1]=False
    points=defaultdict(list);selected=defaultdict(set)
    for iz,ix in zip(*np.nonzero(mask)):
        x,z=int(ix+ox),int(iz+oz);yy=(int(h[iz,ix])-1)//2;key=(x//16,z//16)
        points[key].append((x,z,yy,int(h[iz,ix])));selected[key].update(range((yy-1)//16,(yy+3)//16+1))
    palette=[];lookup={};sections={}
    for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected):
        mapping=[]
        for state in pal:
            if state not in lookup:lookup[state]=len(palette);palette.append(state)
            mapping.append(lookup[state])
        sections[cx,cz,sy]=np.asarray(mapping,dtype=np.uint16)[idx]
    def state(x,y,z):return palette[int(sections[x//16,z//16,y//16][((y&15)<<8)|((z&15)<<4)|(x&15)])]
    def top(s):
        if s in AIR or 'wall_sign' in s or '_button[' in s or s.startswith('minecraft:light['):return 0
        if '_slab[' in s:return .5 if 'type=bottom' in s else 1
        if s.split('[')[0] in ('minecraft:grass','minecraft:tall_grass','minecraft:fern','minecraft:dead_bush','minecraft:snow'):return 0
        return 1
    bad=[];counts=Counter();actual=np.full(h.shape,-32768,dtype=np.int16)
    for cells in points.values():
        for x,z,yy,expected in cells:
            base=state(x,yy,z);height=yy+top(base)
            if top(base)==0:height=yy-1+top(state(x,yy-1,z))
            actual[z-oz,x-ox]=round(height*2)
            error=None
            if abs(height-expected/2)>.01:error='floor_height'
            elif top(state(x,yy+1,z)) or top(state(x,yy+2,z)):error='head_obstruction'
            if error:
                counts[error]+=1;bad.append(dict(pos=[x,yy,z],expected=expected/2,actual=height,type=error,blocks=[base,state(x,yy+1,z),state(x,yy+2,z)]))
    jumps=[]
    for dz,dx in [(0,1),(1,0),(1,1),(1,-1)]:
        az,bz=max(0,-dz),min(h.shape[0],h.shape[0]-dz);ax,bx=max(0,-dx),min(h.shape[1],h.shape[1]-dx)
        m=mask[az:bz,ax:bx]&mask[az+dz:bz+dz,ax+dx:bx+dx]
        delta=abs(actual[az:bz,ax:bx]-actual[az+dz:bz+dz,ax+dx:bx+dx])
        for zz,xx in zip(*np.nonzero(m&(delta>1))):jumps.append([int(xx+ax+ox),int(zz+az+oz),dx,dz,int(delta[zz,xx])/2])
    report=dict(columns=int(mask.sum()),errors=dict(counts),height_jumps=len(jumps),bad=bad,jumps=jumps)
    (OUT/report_name).write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('bad','jumps')},ensure_ascii=False),flush=True)
    print(json.dumps(bad[:16],ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--extension',action='store_true');args=ap.parse_args()
    audit('extension_road_surfaces.npz','extension_road_actual_audit.json') if args.extension else audit()
