"""Measure the real dock envelope against the current save before native driving."""
from pathlib import Path
import json
import numpy as np
import query_blocks as q
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=ROOT/'artifacts/facility_r30'

def main():
    body=json.loads((ROOT/'run/projectseele-local-maps/eva_body_r30_review.json').read_text());rows=[]
    for serial,cx in ((0,6442.5),(1,6282.5)):
        cells=q.read_box(WORLD,'projectseele:geofront',(int(cx)-19,77,-6225),(int(cx)+19,141,-6185))
        solids={p:s for p,s in cells.items() if s not in q.AIR and not s.startswith(('projectseele:lcl[','minecraft:water['))}
        positions=np.asarray(list(solids));hits=set();hulls=np.asarray(body['carrier_hulls'][str(3+serial)])
        # Native carrier yaw 0 rotates the Geo model 180 degrees about Y.
        lo=hulls[:,:3].copy();hi=hulls[:,3:].copy();lo[:,[0,2]]=-hulls[:,[3,5]];hi[:,[0,2]]=-hulls[:,[0,2]]
        path=[(77+u*1.6,-6205.5) for u in np.linspace(0,1,17)]+[(78.6,z) for z in np.arange(-6205.5,-6190,.25)]
        for y,z in path:
            a=lo+[cx,y,z]+.025;b=hi+[cx,y,z]-.025
            for low,high in zip(a,b):
                mask=((positions+1>low)&(positions<high)).all(1)
                hits.update(map(tuple,positions[mask].tolist()))
        rows.append({'unit':serial,'native_yaw':0,'carrier_hulls':len(hulls),'path_samples':len(path),'solid_cells_measured':len(solids),'overlapping_cells':[{'pos':p,'state':solids[p]} for p in sorted(hits)],'passed':not hits})
    (OUT/'un_dock_envelope_readback.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2));assert all(r['passed'] for r in rows)

if __name__=='__main__':main()
