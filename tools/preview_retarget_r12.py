"""Bake actual private mesh poses for geometric inspection before scene choreography."""
from pathlib import Path
import json
import numpy as np
import retarget_human_r12 as human
import author_eva_rifle_stances_r06 as mesh

ROOT=human.eva.ROOT;OUT=ROOT/'artifacts/first_battle_refinement_r12/retarget_preview';OUT.mkdir(parents=True,exist_ok=True)
def main():
 parts=[n for n in mesh.MESH if n not in ['cannon','knife','lance','n2','entry_plug']];uv=np.vstack([np.array(human.eva.mesh['parts'][n]['vertices']).reshape(-1,8)[:,3:5] for n in parts]);records=[]
 for name,frame in [('heavy_pull',300),('grab_a',210),('punch2',53),('kick',60)]:
  source=human.Human(OUT.parent/'sources'/(name+'.npz'));actor=human.Retarget(source);human.battle.AXES.clear();p,root,metadata=actor.pose(frame);v=np.vstack([mesh.vertices(p,n) for n in parts]);floor=float(v[:,1].min()*5/16);np.savez_compressed(OUT/(name+'.npz'),vertices=v,uv=uv)
  records.append(dict(name=name,source_frame=frame,source=str(source.path),deformed_mesh_floor_blocks=floor,endpoint_error_blocks=metadata['errors']));print(records[-1])
 (OUT/'manifest.json').write_text(json.dumps(records,indent=2))
if __name__=='__main__':main()
