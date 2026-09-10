"""Gate private installation on matching native-mesh, transition and floor evidence."""
import json,hashlib,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/staff_world_r15';FOLDER=ROOT/'artifacts/world_refinement_r14/pair_clinch15final'
p=OUT/'first_battle_r15.json';d=json.loads(p.read_text());sha=hashlib.sha256(p.read_bytes()).hexdigest();source=json.loads((FOLDER/'source.json').read_text());rows=json.loads((FOLDER.parent/'triangle_clinch15final.json').read_text());continuity={}
for role in ['eva','angel']:
 q=np.array([f['rotation_wxyz'] for f in d[role]['frames']]);q/=np.linalg.norm(q,axis=2,keepdims=True);angles=np.degrees(2*np.arccos(np.clip(np.abs((q[1:]*q[:-1]).sum(2)),0,1)));window=angles[481:561];i,j=np.unravel_index(window.argmax(),window.shape);continuity[role]={'max_joint_step_degrees':float(window.max()),'frame':int(i+482),'bone':d[role]['bones'][j]}
floor=min(float(np.load(FOLDER/(r['name']+'.npz'))[role][:,1].min()) for r in json.loads((FOLDER/'manifest.json').read_text()) for role in ['hero','angel'])
passed=source['clip']==sha and not d.get('surface_deformation_r14') and len(rows)==139 and not any(r['pairs'] for r in rows) and floor>=-.08 and max(r['max_joint_step_degrees'] for r in continuity.values())<35
report=dict(passed=passed,sha256=sha,triangle_samples=len(rows),overlap_samples=sum(r['pairs']>0 for r in rows),minimum_floor=floor,continuity=continuity)
(OUT/'clinch_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(0 if passed else 1)
