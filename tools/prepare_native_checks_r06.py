"""Select affected real-player collision routes and retain the full route catalog."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from regional_voxels import ROOT,WORLD

OUT=ROOT/'artifacts/world_motion_r06'
def main():
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    original=load(ROOT/'artifacts/world_motion_r04/final_cases.json')
    additions=load(OUT/'airport_west_transfer/walk_cases.json');all_cases=original+additions
    (OUT/'all_walk_cases.json').write_text(json.dumps(all_cases,ensure_ascii=False,indent=2),encoding='utf-8')
    points=[]
    for path in [OUT/'pyramid_envelope.npz']+list((OUT/'staff_corridors').glob('*.npz')):
        d=np.load(path);mask=d['floor']|d['wall']|d['ceiling'];lo=d['lo']
        y,z,x=np.nonzero(mask);points.extend(np.column_stack((x+lo[0],y+lo[1],z+lo[2])).tolist())
    tree=cKDTree(points);chosen=[]
    for row in original:
        ident=row['id'];path=row.get('path',[row.get('start'),row.get('end')]);select=False
        if ident.startswith(('r04/pyramid','r03/continuous','r03/platform_length','station/','airport/')):select=True
        if not select:
            for aa,bb in zip(path,path[1:]):
                a=np.array(aa);b=np.array(bb);length=np.linalg.norm(b-a)
                samples=a+(b-a)*np.linspace(0,1,max(2,int(length)+1))[:,None]+[0,.8,0]
                if np.any(tree.query(samples,distance_upper_bound=4)[0]<4):select=True;break
        if select:chosen.append(row)
    chosen+=additions
    (OUT/'native_cases.json').write_text(json.dumps(chosen,ensure_ascii=False,indent=2),encoding='utf-8')
    (WORLD/'quality_walk_cases.json').write_text(json.dumps(chosen,ensure_ascii=False,indent=2),encoding='utf-8')
    states=set(load(WORLD/'regional_states.json'))
    for path in OUT.glob('**/states.json'):states.update(load(path))
    (WORLD/'regional_states.json').write_text(json.dumps(sorted(states)),encoding='utf-8')
    print('Affected native routes',len(chosen),'retained catalog',len(all_cases),'states',len(states),flush=True)
if __name__=='__main__':main()
