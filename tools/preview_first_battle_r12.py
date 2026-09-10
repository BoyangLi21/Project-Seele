"""Bake both evaluated private meshes from a candidate movie, independent of renderer guesses."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_first_battle_r10 as b
import author_eva_rifle_stances_r06 as mesh

ROOT=b.ROOT;OUT=ROOT/'artifacts/first_battle_refinement_r12';PREVIEW=OUT/'paired_preview';PREVIEW.mkdir(exist_ok=True)
def angel_pose(frame,names):
 p=b.ANGEL.pose()
 for n,q in zip(names,frame['rotation_wxyz']):w,x,y,z=q;p.setq(n,R.from_quat([-x,-y,z,w]))
 for n,v in frame.get('bone_position_xyz',{}).items():p.setp(n,np.array(v)*[-1,1,1])
 p.setp('root',np.array(frame['root_m'])*112*[-1,1,1]);return p
def main():
 data=json.loads((OUT/'candidate_v1.json').read_text());parts=[n for n in mesh.MESH if n not in ['cannon','knife','lance','n2','entry_plug']];hero_uv=np.vstack([np.array(b.eva.mesh['parts'][n]['vertices']).reshape(-1,8)[:,3:5] for n in parts]);a=json.loads((b.eva.PACK/'mesh/sachiel.mesh.json').read_text());av=np.array(a['parts']['root']['vertices']).reshape(-1,8);_,inverse=np.unique(np.round(av[:,:3]*[-1,1,1],6),axis=0,return_inverse=True)
 records=[]
 for name,time in [('tear',4),('grip',7),('kick',9.2),('pounce',10.85),('pin',11.9),('strike',12.75),('strike2',14.15),('rib',16.05),('wrap',18.35)]:
  i=round(time*30);h=b.eva.decode(data['eva']['frames'][i],data['eva']['bones']);p=angel_pose(data['angel']['frames'][i],data['angel']['bones']);hero=np.vstack([mesh.vertices(h,n) for n in parts])*b.HEROMIRROR*5/16+data['eva']['root_blocks'][i];enemy=p.skin()[inverse]*5/16+data['angel']['root_blocks'][i]
  np.savez_compressed(PREVIEW/(name+'.npz'),hero=hero,hero_uv=hero_uv,angel=enemy,angel_uv=av[:,3:5]);records.append(dict(name=name,time=time,hero_bounds=[hero.min(0).tolist(),hero.max(0).tolist()],angel_bounds=[enemy.min(0).tolist(),enemy.max(0).tolist()]))
 (PREVIEW/'manifest.json').write_text(json.dumps(records,indent=2));print('Actual paired mesh poses baked')
if __name__=='__main__':main()
