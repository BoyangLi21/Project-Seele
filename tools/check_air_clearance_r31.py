"""Read actual runtime triangles and check the revised face-down transport envelope."""
from pathlib import Path
import hashlib,json,math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/facility_r31/transport'
PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/mesh'
REVIEW=ROOT/'run/resourcepacks/eva_un_r31_review/assets/projectseele/mesh'
plane_path=ROOT/'src/main/resources/assets/projectseele/mesh/tv_facilities_r16.json'
plane=np.asarray(json.loads(plane_path.read_text())['parts']['un_transport_body']).reshape(-1,6)
keel=float(plane[:,1].min()+112)
records=[]
for name in ('eva_unit00','eva_unit01','eva_unit02','eva_prototype','eva_un01'):
    path=(REVIEW if name in ('eva_prototype','eva_un01') else PACK)/(name+'.mesh.json')
    blob=path.read_bytes();mesh=json.loads(blob);points=[]
    for part,q in mesh['parts'].items():
        if part in ('cannon','knife','lance','shield','n2'):continue
        a=np.asarray(q['vertices']).reshape(-1,8)
        points.append((a[:,:3]+q['pivot'])*[-1,1,1]*5/16)
    points=np.concatenate(points);high=(-math.inf,None);low=math.inf
    for degrees in np.linspace(0,90,181):
        phase=math.radians(degrees);angle=-phase
        ys=(points[:,1]-34)*math.cos(angle)-points[:,2]*math.sin(angle)+34+54*math.sin(phase)-8*math.sin(2*phase)
        maximum=float(ys.max());low=min(low,float(ys.min()))
        if maximum>high[0]:high=(maximum,float(degrees))
    record={'model':name,'mesh_sha256':hashlib.sha256(blob).hexdigest(),'triangleVertices':len(points),
            'highest':high[0],'angleOfHighest':high[1],'keelMinimum':keel,
            'clearanceToConservativeKeelPlane':keel-high[0],'lowestAboveInitialGround':low}
    assert record['clearanceToConservativeKeelPlane']>0,record
    records.append(record)
assert np.allclose([0,math.sin(-math.pi/2),-math.cos(-math.pi/2)],[0,-1,0],atol=1e-12)
report={'sampledDegrees':181,'orientation':'prone: physical root X=-phase; local face -Z points world -Y at phase 90; dorsal +Z points up',
        'note':'Actual neutral runtime triangles; full keel plane is conservative. This does not substitute for native articulated/body/capsule/cradle visual review.',
        'models':records,'aircraft_mesh_sha256':hashlib.sha256(plane_path.read_bytes()).hexdigest()}
(OUT/'rotation_clearance.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'orientation':report['orientation'],'minimum_keel_clearance':min(r['clearanceToConservativeKeelPlane'] for r in records)}))
