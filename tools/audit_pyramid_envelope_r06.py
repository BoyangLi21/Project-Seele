"""Compare the actual save with the enclosure of explicitly authored R04 spaces."""
from pathlib import Path
import gzip,json
import numpy as np
from scipy.ndimage import binary_dilation,label
import scan_regional_completion as scan

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/world_motion_r06';OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'artifacts/world_motion_r04/pyramid'
LO=np.array([-80,-472,238]);HI=np.array([143,-346,442])
load=lambda p:json.loads(p.read_text(encoding='utf-8'))

def put(mask,box):
    a=np.maximum(np.array(box[:3],int),LO);b=np.minimum(np.array(box[3:],int),HI)
    if np.any(a>b):return
    mask[a[1]-LO[1]:b[1]-LO[1]+1,a[2]-LO[2]:b[2]-LO[2]+1,a[0]-LO[0]:b[0]-LO[0]+1]=True

def coords(mask):
    y,z,x=np.nonzero(mask)
    return np.column_stack((x+LO[0],y+LO[1],z+LO[2]))

def main():
    blocks,palette=scan.volume(LO,HI)
    spaces=np.zeros(blocks.shape,bool);rooms=load(SOURCE/'places.json')['rooms'];corridors=[]
    for room in rooms:
        x0,x1,z0,z1=room['bounds'];f=room['floor']
        put(spaces,(x0+1,f+1,z0+1,x1-1,f+8,z1-1))
        x,y,z=room['entry']
        if x in (x0,x1):put(spaces,(x,y,z-1,x,y+2,z+1))
        else:put(spaces,(x-1,y,z,x+1,y+2,z))
    with gzip.open(SOURCE/'ops.json.gz','rt',encoding='utf-8') as stream:ops=json.load(stream)
    floors={(o['owner'],tuple(o['box'][i] for i in (0,2,3,5)),o['box'][1]) for o in ops
            if o['box'][1]==o['box'][4] and o['state']=='minecraft:smooth_stone'}
    seen=set()
    for op in ops:
        b=op['box'];key=(op['owner'],tuple(b[i] for i in (0,2,3,5)),b[1]-1)
        if op['state']!='minecraft:air' or key not in floors or tuple(b) in seen:continue
        seen.add(tuple(b));put(spaces,b);corridors.append(dict(id=op['owner'],box=b))
    put(spaces,(62,-448,350,72,-357,368))
    # Original equipment, existing rooms and working lifts are retained verbatim.
    held=np.zeros(blocks.shape,bool)
    for p in load(SOURCE/'protected.json'):put(held,p['box'])
    # Named, authored walk routes define existing ports. Air at a crop edge does not.
    ports=np.zeros(blocks.shape,bool);cases=load(scan.WORLD/'quality_walk_cases.json')
    for case in cases:
        path=case.get('path',[case.get('start'),case.get('end')])
        if not path or any(p is None for p in path):continue
        for a,b in zip(path,path[1:]):
            a=np.array(a,float);b=np.array(b,float)
            if np.any(np.maximum(a,b)<LO) or np.any(np.minimum(a,b)>HI):continue
            steps=max(1,int(np.linalg.norm(b-a)*2))
            if steps>2000:continue
            for t in np.linspace(0,1,steps+1):
                v=a+(b-a)*t;x,y,z=np.floor(v).astype(int)
                put(ports,(x,y,z,x,y+2,z))
    horizontal=np.zeros((3,3,3),bool);horizontal[1,:,:]=True
    expanded=binary_dilation(spaces,structure=horizontal)
    walls=expanded&~spaces
    floor=np.roll(expanded,-1,axis=0)&~(spaces|walls);floor[-1]=False
    ceiling=np.roll(expanded,1,axis=0)&~(spaces|walls);ceiling[0]=False
    empty=np.array([s.split('[')[0] in scan.AIR or s.startswith('minecraft:light[') for s in palette])[blocks]
    natural=np.array([s.split('[')[0] in {'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:bedrock','minecraft:deepslate'} for s in palette])[blocks]
    report=dict(world=str(scan.WORLD),bounds=[LO.tolist(),HI.tolist()],rooms=len(rooms),corridors=corridors,issues={})
    masks={}
    for name,mask in [('floor',floor),('wall',walls),('ceiling',ceiling)]:
        candidates=mask&empty&~held&~ports;masks[name]=candidates;groups,count=label(candidates);components=[]
        for i in range(1,count+1):
            pts=coords(groups==i)
            components.append(dict(cells=len(pts),min=pts.min(axis=0).tolist(),max=pts.max(axis=0).tolist()))
        report['issues'][name]=dict(cells=int(candidates.sum()),components=components)
    fragments=spaces&natural&~held
    report['issues']['natural_interior']=dict(cells=int(fragments.sum()),positions=coords(fragments).tolist())
    np.savez_compressed(OUT/'pyramid_envelope.npz',blocks=blocks,palette=np.array(palette),spaces=spaces,held=held,ports=ports,
                        floor=masks['floor'],wall=masks['wall'],ceiling=masks['ceiling'],fragments=fragments,lo=LO,hi=HI)
    (OUT/'pyramid_envelope.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Authored rooms',len(rooms),'corridors',len(corridors),'space cells',int(spaces.sum()),flush=True)
    print({k:v['cells'] for k,v in report['issues'].items()},flush=True)

if __name__=='__main__':main()
