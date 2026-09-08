"""Enclosure and leftover-soil audit of named staff links, retaining existing room ports."""
import json,gzip
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation,label
import scan_regional_completion as scan
from regional_voxels import ROOT,WORLD
from quality_structures import Station

OUT=ROOT/'artifacts/world_motion_r06/staff_corridors';OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
SOURCES=[ROOT/'artifacts/world_quality_r02'/n for n in ['circulation_repair','airport_architecture','structures_stations']]
SOURCES.append(ROOT/'artifacts/world_expansion_20260907/geometry_all')
AREAS={'hq_lower':((-80,-473,238),(145,-430,480)),
       'hangar_link':((-66,-493,-160),(182,-350,283)),
       'science_logistics':((163,-489,68),(392,-435,705)),
       'arrival':((-414,-492,699),(-267,-444,825)),
       'bay_airport':((630,68,1040),(850,102,1248)),
       'hakone_airport':((-1780,68,-410),(-1560,102,-190))}

def main():
    ops=[];protected=[]
    for folder in SOURCES:
        if not (folder/'ops.json.gz').exists():continue
        with gzip.open(folder/'ops.json.gz','rt',encoding='utf-8') as stream:ops+=json.load(stream)
        if (folder/'protected.json').exists():protected+=load(folder/'protected.json')
    protected+=load(ROOT/'artifacts/world_motion_r04/pyramid/protected.json')
    floors={(tuple(o['box'][i] for i in (0,2,3,5)),o['box'][1]) for o in ops if o['state']=='minecraft:smooth_stone' and o['box'][1]==o['box'][4]}
    corridors={};rooms=[]
    for op in ops:
        if op['state']!='minecraft:air':continue
        b=op['box'];w=b[3]-b[0]+1;d=b[5]-b[2]+1;h=b[4]-b[1]+1
        if 2<=h<=6 and min(w,d)<=11 and max(w,d)>=4 and (tuple(b[i] for i in (0,2,3,5)),b[1]-1) in floors:
            if b[1]<0 or op['owner'].startswith('airport/') and b[1]<78:corridors[tuple(b)]=op['owner']
        if h>=7 and min(w,d)>=7 and ((b[0]-1,b[2]-1,b[3]+1,b[5]+1),b[1]-1) in floors:rooms.append(tuple(b))
        # Individual stair headroom and door cuts are authored ports too.
        if h<=6 and min(w,d)<=11:rooms.append(tuple(b))
    for family in ('world_quality_r03','world_motion_r04'):
        for path in (ROOT/'artifacts'/family).glob('*/ops.json.gz'):
            with gzip.open(path,'rt',encoding='utf-8') as stream:
                for op in json.load(stream):
                    if op['state']=='minecraft:air':rooms.append(tuple(op['box']))
    platforms=[p for p in load(ROOT/'artifacts/world_expansion_20260907/transit_plan.json')['platforms'] if p.get('mode')!='AIRPLANE']
    platforms+=load(ROOT/'artifacts/world_quality_r02/extension_plan.json')['transit']['platforms']
    for data in platforms:
        s=Station(None,data);a=s.xyz(-s.half,s.y+1,-15);b=s.xyz(s.half,s.y+13,15);rooms.append((*a,*b))
    rooms.append((-46,-443,-142,110,-354,-56))
    cases=load(WORLD/'quality_walk_cases.json');reports=[]
    for name,(lo,hi) in AREAS.items():
        lo=np.array(lo);hi=np.array(hi);blocks,pal=scan.volume(lo,hi);space=np.zeros(blocks.shape,bool);context=np.zeros_like(space);held=np.zeros_like(space);ports=np.zeros_like(space)
        def put(mask,box):
            a=np.maximum(lo,box[:3]);b=np.minimum(hi,box[3:]);
            if np.any(a>b):return
            mask[a[1]-lo[1]:b[1]-lo[1]+1,a[2]-lo[2]:b[2]-lo[2]+1,a[0]-lo[0]:b[0]-lo[0]+1]=True
        for box in corridors:put(space,box)
        for box in rooms:put(context,box)
        for p in protected:put(held,p['box'])
        for case in cases:
            path=case.get('path',[case.get('start'),case.get('end')])
            if any(v is None for v in path):continue
            for a,b in zip(path,path[1:]):
                a=np.array(a);b=np.array(b)
                if np.any(np.maximum(a,b)<lo) or np.any(np.minimum(a,b)>hi):continue
                steps=min(2000,max(1,int(np.linalg.norm(b-a)*2)))
                for t in np.linspace(0,1,steps+1):
                    x,y,z=np.floor(a+(b-a)*t).astype(int);put(ports,(x,y,z,x,y+2,z))
        horizontal=np.zeros((3,3,3),bool);horizontal[1]=True;expanded=binary_dilation(space,structure=horizontal)
        walls=expanded&~space;floor=np.roll(expanded,-1,axis=0)&~expanded;ceil=np.roll(expanded,1,axis=0)&~expanded
        empty=np.array([s.split('[')[0] in scan.AIR for s in pal])[blocks]
        valid=~held&~ports&~context
        # Crop boundaries remain unknown, not artificial end walls.
        valid[:2]=False;valid[-2:]=False;valid[:,:2]=False;valid[:,-2:]=False;valid[:,:,:2]=False;valid[:,:,-2:]=False
        masks={k:v&empty&valid for k,v in [('floor',floor),('wall',walls),('ceiling',ceil)]}
        natural=np.array([s.split('[')[0] in {'minecraft:stone','minecraft:dirt','minecraft:gravel','minecraft:sand','minecraft:grass_block'} for s in pal])[blocks]
        masks['soil']=space&natural&~held
        result=dict(area=name,bounds=[lo.tolist(),hi.tolist()],counts={k:int(v.sum()) for k,v in masks.items()},components={})
        for k,v in masks.items():
            groups,count=label(v);components=[]
            for i in range(1,count+1):
                y,z,x=np.nonzero(groups==i);points=np.column_stack((x+lo[0],y+lo[1],z+lo[2]));components.append(dict(cells=len(x),min=points.min(0).tolist(),max=points.max(0).tolist()))
            result['components'][k]=sorted(components,key=lambda c:-c['cells'])
        np.savez_compressed(OUT/(name+'.npz'),blocks=blocks,palette=np.array(pal),lo=lo,hi=hi,space=space,context=context,held=held,ports=ports,**masks)
        reports.append(result);print(name,result['counts'],flush=True)
    (OUT/'report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')

if __name__=='__main__':main()
