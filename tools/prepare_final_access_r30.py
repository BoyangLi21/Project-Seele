"""Select existing physical routes affected by the final fixtures and platform furniture."""
from pathlib import Path
import json,math
import numpy as np
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r30'
points=[]
for name in ['board_mounts','terminal_detail','global_repairs']:
    for receipt in (ART/name).glob('*/applied_*'):
        if (receipt/'ROLLED_BACK.json').exists():continue
        for f in (receipt/'delta').glob('c.*.npz'):
            cx,cz=map(int,f.stem.split('.')[1:])
            with np.load(f) as a:
                minimum=int(a['minimum']);o=a['offsets'].astype(np.int64)
                points.extend(np.c_[cx*16+(o&15)+.5,minimum+o//256+.5,cz*16+((o>>4)&15)+.5])
tree=cKDTree(points);chosen=[]
for case in json.loads((ART/'full_walk_cases.json').read_text()):
    route=case.get('path') or [case.get('start'),case.get('end')]
    if not all(p is not None for p in route):continue
    near=False
    for a,b in zip(route,route[1:]):
        a,b=np.asarray(a),np.asarray(b);samples=np.linspace(a,b,max(2,math.ceil(np.linalg.norm(b-a)) +1))
        if np.min(tree.query(samples)[0])<4:near=True;break
    if near:chosen.append(case)
(ART/'final_access_cases.json').write_text(json.dumps(chosen,ensure_ascii=False,indent=2),encoding='utf8')
print('Final fixture access routes',len(chosen),'changed cells',len(points))
