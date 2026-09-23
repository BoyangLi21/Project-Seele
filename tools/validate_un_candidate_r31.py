"""Structural checks for the isolated UN candidates, without installing or launching them."""
from pathlib import Path
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r31/models';records=[]
for unit in ('00','01'):
    root=ART/('un'+unit);asset=root/'runtime/assets/projectseele';baseline=root/'baseline/assets/projectseele';p=asset/'mesh/eva_prototype.mesh.json';m=json.loads(p.read_text());old=json.loads((baseline/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((asset/'geo/eva_prototype.geo.json').read_text());bones={b['name'] for b in geo['minecraft:geometry'][0]['bones']}
    assert (asset/'geo/eva_prototype.geo.json').read_bytes()==(baseline/'geo/eva_prototype.geo.json').read_bytes()
    assert (asset/'animations/eva_prototype.animation.json').read_bytes()==(baseline/'animations/eva_prototype.animation.json').read_bytes()
    for key in ('r13_dorsal_socket','r30_optical_frame','eye_socket_model','r30_hands','r30_thrusters'):
        if key in old:assert m[key]==old[key],key
    triangles=0;weighted=0
    for n,q in m['parts'].items():
        a=np.asarray(q['vertices']).reshape(-1,8);assert n in bones and len(a)%3==0 and np.isfinite(a).all();triangles+=len(a)//3
        assert np.allclose(np.linalg.norm(a[:,5:8],axis=1),1,atol=3e-4),n
        assert a[:,3:5].min()>=-1e-5 and a[:,3:5].max()<=1.00001
        if n in m['jointSkins']:
            w=m['jointSkins'][n]['influences'];assert set(w)<=bones;v=np.asarray(list(w.values()));assert v.shape[1]==len(a) and np.isfinite(v).all() and v.min()>=-1e-7 and v.max()<=1.000001 and np.allclose(v.sum(0),1,atol=1e-6);weighted+=len(a)//3
    assert triangles==m['triangleCount']
    records.append({'unit':unit,'meshSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'triangles':triangles,'weightedTriangles':weighted,'parts':len(m['parts']),'bones':len(bones),'rigAndAnimationExact':True,'opticsHandsDorsalFlightContractExact':True,'rgbaPbrMapsUnchanged':all((asset/'textures/entity'/('eva_prototype'+s+'.png')).read_bytes()==(baseline/'textures/entity'/('eva_prototype'+s+'.png')).read_bytes() for s in ('','_mr','_s','_n','_eyes'))})
(ART/'candidate_validation.json').write_text(json.dumps({'status':'structural checks passed; not a native-game acceptance','models':records},indent=2));print(json.dumps(records,indent=2),flush=True)
