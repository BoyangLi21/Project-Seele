"""Validate and stage the repaired private pair; do not modify the main pack yet."""
from pathlib import Path
import hashlib,json,re,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23/models';PACK=ROOT/'run/resourcepacks/eva_access_r22_review'
def main():
 rows=[];files=[]
 for serial in ('00','01'):
  source=OUT/('un'+serial)/'runtime';a=source/'assets/projectseele';meshfile=a/'mesh/eva_prototype.mesh.json';m=json.loads(meshfile.read_text());g=json.loads((a/'geo/eva_prototype.geo.json').read_text());bones={b['name'] for b in g['minecraft:geometry'][0]['bones']};violations=[]
  for name,p in m['parts'].items():
   data=np.asarray(p['vertices']).reshape(-1,8);assert np.isfinite(data).all() and name in bones;norms=np.linalg.norm(data[:,5:8],axis=1);assert (norms>.97).all() and (norms<1.03).all(),(serial,name,norms.min(),norms.max())
   if name in m.get('jointSkins',{}):
    weights=m['jointSkins'][name]['influences'];assert all(k in bones and len(w)==len(data) for k,w in weights.items());assert np.allclose(sum(np.asarray(w) for w in weights.values()),1,atol=1e-5)
   if name.startswith(('forearm','arm_','r21_join_forearm')):
    points=(data[:,:3]+p['pivot'])*[-1,1,1];bad=(points[:,1]<85)&(abs(points[:,0])<26)
    if bad.any():violations.append([name,int(bad.sum())])
  assert not violations,violations
  eye=m['r23_optical_frame'];assert eye['lens'][0]==0 and eye['axis']==[0.,0.,-1.]
  rows.append(dict(unit=serial,triangles=m['triangleCount'],parts=len(m['parts']),rig_bones=len(bones),all_normals_finite=True,weights_normalized=True,no_forearm_vertices_in_knee_zone=True,optic_origin=eye['lens'],sha256=hashlib.sha256(meshfile.read_bytes()).hexdigest()))
  for path in source.rglob('*'):
   if not path.is_file():continue
   rel=path.relative_to(source);rel=Path(str(rel).replace('eva_prototype','eva_un01')) if serial=='01' else rel;dest=PACK/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
   if serial=='01' and dest.name.endswith('.geo.json'):
    geo=json.loads(dest.read_text());geo['minecraft:geometry'][0]['description']['identifier']='geometry.eva_un01';dest.write_text(json.dumps(geo,separators=(',',':')))
   files.append(dict(path=str(rel),sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
 p=ROOT/'src/main/java/com/projectseele/client/render/LocalVisualAssetFingerprint.java';s=p.read_text();line='private static final Map<String,MeshContract> R23_CONTRACTS=Map.of("eva_prototype",new MeshContract(%d,64,false),"eva_un01",new MeshContract(%d,64,false));'%(rows[0]['triangles'],rows[1]['triangles']);s=re.sub(r'private static final Map<String,MeshContract> R23_CONTRACTS=.*?;',line,s);p.write_text(s)
 (OUT/'mesh_verification.json').write_text(json.dumps(rows,indent=2));(OUT/'staged_files.json').write_text(json.dumps(files,indent=2));print('Verified/staged',rows,flush=True)
if __name__=='__main__':main()
