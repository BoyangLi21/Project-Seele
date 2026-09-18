"""Validate and stage the pair in a separate private review pack."""
import json,shutil,hashlib
from pathlib import Path
import numpy as np
import fit_un_dorsal_r21 as dorsal
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/un_models_r21';PACK=ROOT/'run/resourcepacks/eva_un_r21_review';A=PACK/'assets/projectseele'
def main():
 for directory in ('mesh','geo','textures/entity','animations'):(A/directory).mkdir(parents=True,exist_ok=True)
 old=json.loads((ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/mesh/eva_prototype.mesh.json').read_text())['r13_dorsal_socket'];profiles_path=ROOT/'src/main/resources/assets/projectseele/motion/eva_dorsal_r13.json';profiles=json.loads(profiles_path.read_text());records=[]
 for unit,name in [('00','eva_prototype'),('01','eva_un01')]:
  local=OUT/('un'+unit);body=local/'body/assets/projectseele';runtime=local/'runtime/assets/projectseele';dorsal.fit(body,runtime,old,local/'dorsal.json',unit)
  mesh=json.loads((runtime/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((runtime/'geo/eva_prototype.geo.json').read_text());bone_names={b['name'] for b in geo['minecraft:geometry'][0]['bones']};norm_error=0;vertices=0
  for part_name,part in mesh['parts'].items():
   assert part_name in bone_names;v=np.asarray(part['vertices']).reshape(-1,8);assert len(v)%3==0 and np.isfinite(v).all();length=np.linalg.norm(v[:,5:],axis=1);assert np.min(length)>.99,part_name;norm_error=max(norm_error,float(np.max(abs(length-1))));vertices+=len(v)
  for part_name,spec in mesh['jointSkins'].items():
   influence=np.stack(list(spec['influences'].values()));assert influence.shape[1]==len(mesh['parts'][part_name]['vertices'])//8
   assert set(spec['influences'])<=bone_names and np.isfinite(influence).all() and influence.min()>=0 and np.max(abs(influence.sum(0)-1))<.0002
  assert vertices//3==mesh['triangleCount']
  geo['minecraft:geometry'][0]['description']['identifier']='geometry.'+name
  (A/'mesh'/(name+'.mesh.json')).write_text(json.dumps(mesh,separators=(',',':')));(A/'geo'/(name+'.geo.json')).write_text(json.dumps(geo,separators=(',',':')))
  for suffix in ('.png','_eyes.png'):shutil.copy2(runtime/'textures/entity'/('eva_prototype'+suffix),A/'textures/entity'/(name+suffix))
  shutil.copy2(runtime/'animations/eva_prototype.animation.json',A/'animations'/(name+'.animation.json'))
  frame=mesh['r13_dorsal_socket'];profiles['profiles'][name]={k:frame[k] for k in ('centre','outward','hinge','hinge_axis','open_angle_degrees')}
  records.append(dict(unit=unit,asset=name,triangles=mesh['triangleCount'],parts=len(mesh['parts']),bones=len(bone_names),maximum_normal_error=norm_error,authored_joint_parts=len(mesh['jointSkins']),eye=mesh['eye_socket_model'],dorsal=frame,sha256=hashlib.sha256((A/'mesh'/(name+'.mesh.json')).read_bytes()).hexdigest()))
 profiles_path.write_text(json.dumps(profiles,indent=2)+'\n')
 (PACK/'pack.mcmeta').write_text(json.dumps({'pack':{'pack_format':15,'description':'EVA UN pair R21 — private native review'}},ensure_ascii=False))
 (OUT/'staging.json').write_text(json.dumps(dict(stage='PRIVATE REVIEW; not installed in main model pack',records=records,pack=str(PACK)),indent=2))
 (ROOT/'run/saves/SEELE_R21_REVIEW/un_models_r21.json').write_text(json.dumps({'revision':'R21','purpose':'review commissioning','airframes':records},indent=2))
 print(json.dumps(records,indent=2))
if __name__=='__main__':main()
