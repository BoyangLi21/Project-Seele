"""Validate and atomically install the reviewed private R13 airframes.

Only the original UN geometry is mirrored to public resources. Captured motion,
canonical third-party geometry and the user's TV reference frames remain local.
"""
from pathlib import Path
import json,hashlib,subprocess,msvcrt
from contextlib import ExitStack
import numpy as np
from scipy.spatial import ConvexHull

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/dorsal_tv_r13';CAND=OUT/'candidate/assets/projectseele';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
EXPECTED={'eva_unit00':(11028,45),'eva_unit01':(11666,45),'eva_unit02':(11262,45),'eva_prototype':(94054,48)}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,content):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.r13.tmp');temp.write_bytes(content);temp.replace(path)

def main():
    audit=json.loads((OUT/'cover_ray_audit.json').read_text());assert len(audit)==4 and all(row['passed'] for row in audit)
    checkpoint=json.loads((OUT/'checkpoint.json').read_text(encoding='utf-8'));backup=Path(checkpoint['backup']);protected=json.loads((ROOT/'artifacts/first_battle_refinement_r12/completion.json').read_text(encoding='utf-8'))['protected_files']
    for name,sha in protected.items():assert digest(ROOT/name)==sha,('protected user resource changed',name)
    assert not subprocess.check_output(['git','diff','--name-only','--','src/main/resources/assets/projectseele/mesh/eva_prototype.mesh.json','src/main/resources/assets/projectseele/geo/eva_prototype.geo.json'],cwd=ROOT,text=True).strip(),'Preserve unexpected prototype edits before installation'
    profiles=json.loads((ROOT/'src/main/resources/assets/projectseele/motion/eva_dorsal_r13.json').read_text())['profiles'];models={};geometries={}
    for model,expected in EXPECTED.items():
        mesh=json.loads((CAND/'mesh'/(model+'.mesh.json')).read_text());geo=json.loads((CAND/'geo'/(model+'.geo.json')).read_text());bones={b['name']:b for b in geo['minecraft:geometry'][0]['bones']};assert len(bones)==len(geo['minecraft:geometry'][0]['bones']);count=0
        for name,part in mesh['parts'].items():
            values=np.array(part['vertices']);assert name in bones and values.size>0 and values.size%24==0 and np.isfinite(values).all();assert np.max(np.abs(np.array(part['pivot'])-bones[name]['pivot']))<.001;count+=values.size//24
        for name in bones:
            visited=set();current=name
            while current is not None:
                assert current in bones and current not in visited;visited.add(current);current=bones[current].get('parent')
        assert (count,len(mesh['parts']))==expected,(model,count,len(mesh['parts']))
        assert all(n in bones for n in ['dorsal_cover','dorsal_liner','torso_upper','head'])
        for key in ['centre','outward','hinge','hinge_axis']:assert np.max(np.abs(np.array(mesh['r13_dorsal_socket'][key])-profiles[model][key]))<1e-5
        for relative in ['animations/'+model+'.animation.json','textures/entity/'+model+'.png']:assert (PACK/relative).is_file()
        models[model]=mesh;geometries[model]=geo
    body_path=ROOT/'run/projectseele-local-maps/eva_body_r11.json';body=json.loads((backup/'run/projectseele-local-maps/eva_body_r11.json').read_text());motion_hash=hashlib.sha256(json.dumps(body['motion'],sort_keys=True).encode()).hexdigest()
    for variant in range(3):body['rigs'][str(variant)]=geometries[f'eva_unit0{variant}']['minecraft:geometry'][0]['bones']
    body['rig']=body['rigs']['1'];mesh=models['eva_unit01']
    for name in body.get('support',{}):
        names=[name]+(['dorsal_cover'] if name=='torso_upper' else []);arrays=[]
        for n in names:
            if n not in mesh['parts']:continue
            p=mesh['parts'][n];a=np.array(p['vertices']).reshape(-1,8);arrays.append((a[:,:3]+p['pivot'])*[-1,1,1])
        if arrays:
            points=np.unique(np.vstack(arrays).round(6),axis=0);body['support'][name]=points[ConvexHull(points).vertices].tolist()
    assert hashlib.sha256(json.dumps(body['motion'],sort_keys=True).encode()).hexdigest()==motion_hash
    with ExitStack() as locks:
        for world in ['SEELE_TV_WORLD_PREVIEW_20260906','SEELE_MECHANICS_REVIEW_R11','SEELE_R11_CANONICAL_ACCEPTANCE','SEELE_FIRST_BATTLE_REVIEW_R10']:
            path=ROOT/'run/saves'/world/'session.lock'
            if path.is_file():handle=locks.enter_context(path.open('r+b'));msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        changes=[]
        for model in EXPECTED:
            for category in ['mesh','geo']:
                relative=Path(category)/(model+'.'+category+'.json');content=(CAND/relative).read_bytes();destination=PACK/relative;write(destination,content);changes.append(dict(path=str(destination),sha256=digest(destination)))
                if model=='eva_prototype':write(ROOT/'src/main/resources/assets/projectseele'/relative,json.dumps(geometries[model],indent=2).encode('utf-8') if category=='geo' else content)
        write(body_path,json.dumps(body,separators=(',',':')).encode('utf-8'))
    for name,sha in protected.items():assert digest(ROOT/name)==sha
    report=dict(status='installed',geometry=changes,shared_body_sha256=digest(body_path),motion_payload_unchanged_sha256=motion_hash,first_battle_r12_sha256=digest(ROOT/'run/projectseele-local-maps/first_battle_r12.json'),public_resources='Original UN geometry only; numeric measured profiles and source code',main_world_edits=0)
    (OUT/'installation.json').write_text(json.dumps(report,indent=2));print('R13 private models and shared rig installed; no world blocks changed')
if __name__=='__main__':main()
