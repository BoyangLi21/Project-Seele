"""Select every recorded walk touching R29 edits, plus all newly joined paths."""
from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r29';WORLD=ROOT/'run/saves/SEELE_FIELD_R29_REVIEW'
def intersects(a,b,lo,hi):
    d=b-a;enter,leave=0.,1.
    for k in range(3):
        if abs(d[k])<1e-9:
            if a[k]<lo[k] or a[k]>hi[k]:return False
        else:
            x,y=(lo[k]-a[k])/d[k],(hi[k]-a[k])/d[k];enter=max(enter,min(x,y));leave=min(leave,max(x,y))
    return enter<=leave
def main():
    out=ART/'validation';out.mkdir(exist_ok=True)
    cases={q['id']:q for q in json.loads((WORLD/'quality_walk_cases.json').read_text())};extra=[];boxes=[]
    for name in ('upper_gallery','surface_cut','un_berths'):
        contract=ART/name/'contract.json'
        if contract.exists():extra+=json.loads(contract.read_text(encoding='utf8')).get('walk_nodes',[])
        for receipt in (ART/name).glob('*/applied_*'):
            if (receipt/'ROLLED_BACK.json').exists():continue
            for p in (receipt/'delta').glob('c.*.npz'):
                cx,cz=map(int,p.stem.split('.')[1:])
                with np.load(p) as d:
                    ids=d['offsets'].astype(int)+int(d['minimum'])*256
                    if not len(ids):continue
                    pts=np.c_[cx*16+(ids&15),ids//256,cz*16+((ids//16)&15)]
                    boxes.append((pts.min(0)-[2,3,2],pts.max(0)+[2,3,2]))
            tags=receipt/'block_entity_deltas.json'
            if tags.exists():
                for row in json.loads(tags.read_text()):
                    point=np.array(row['position']);boxes.append((point-[3,4,3],point+[3,2,3]))
    for x in (-12,30,72):
        start=[x+.5,-367,-204.5]
        extra.append(dict(id='r29/observation_map/'+str(x),path=[start,start],readingBoard=[x,-365,-201],readingWayfinding=True))
        extra.append(dict(id='r29/observation_map_approach/'+str(x),path=[[x+.5,-367,-213.5],start]))
    cases.update({q['id']:q for q in extra});selected={q['id'] for q in extra}
    for key,q in cases.items():
        points=q.get('path') or [q['start'],q['end']]
        if any(intersects(np.asarray(a),np.asarray(b),lo,hi) for a,b in zip(points,points[1:]) for lo,hi in boxes):selected.add(key)
    (out/'final_catalogue.json').write_text(json.dumps(list(cases.values()),ensure_ascii=False,indent=2),encoding='utf8')
    (out/'affected_cases.json').write_text(json.dumps([q for key,q in cases.items() if key in selected],ensure_ascii=False,indent=2),encoding='utf8')
    print('R29 affected native checks',len(selected),'combined catalogue',len(cases),flush=True)
if __name__=='__main__':main()
