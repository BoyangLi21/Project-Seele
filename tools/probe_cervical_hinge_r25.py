"""Independent triangle SAT for candidate cervical hinge positions, no world writes."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import build_eva_body_r05 as rig
ROOT=rig.ROOT;OUT=ROOT/'artifacts/facility_r25/head_probe'
def intersections(a,b):
 lowA=a.min(1);highA=a.max(1);lowB=b.min(1);highB=b.max(1)
 ii,jj=np.where((highA[:,None]>=lowB[None]-1e-7).all(2)&(highB[None]>=lowA[:,None]-1e-7).all(2))
 if not len(ii):return 0
 A=a[ii];B=b[jj];ea=[A[:,1]-A[:,0],A[:,2]-A[:,1],A[:,0]-A[:,2]];eb=[B[:,1]-B[:,0],B[:,2]-B[:,1],B[:,0]-B[:,2]]
 na=np.cross(ea[0],ea[1]);nb=np.cross(eb[0],eb[1]);axes=[na,nb]+[np.cross(x,y) for x in ea for y in eb]+[np.cross(na,e) for e in ea]+[np.cross(nb,e) for e in eb]
 keep=np.ones(len(ii),bool)
 for axis in axes:
  p=np.einsum('nvi,ni->nv',A,axis);q=np.einsum('nvi,ni->nv',B,axis)
  keep&=~((p.max(1)<q.min(1)-1e-6)|(q.max(1)<p.min(1)-1e-6))
 return len(np.unique(ii[keep]))
def main():
 OUT.mkdir(parents=True,exist_ok=True);m=json.loads((ROOT/'artifacts/facility_r25/crouch/eva_body_r25.json').read_text())['motion'];mesh=json.loads((rig.PACK/'mesh/eva_unit01.mesh.json').read_text())
 def vertices(name):
  p=mesh['parts'][name];return (np.asarray(p['vertices']).reshape(-1,3,mesh['stride'])[:,:,:3]+p['pivot'])*[-1,1,1]
 head=vertices('head');cover=vertices('dorsal_cover');base=rig.P['head'].copy();rows=[]
 def posed(v,mat):return v@mat[:3,:3].T+mat[:3,3]
 for offset in (0,4,8,12,16,20,24):
  rig.P['head']=base+[0,offset,offset];counts=[]
  for pitch in (-30,-20,-10,0,10,16,25,35):
   p=rig.decode(m['clips']['rifle_stance']['frames'][-1],m['bones']);p.setq('head',R.from_matrix(p.parent('head')[:3,:3]).inv()*R.from_euler('x',-pitch,degrees=True))
   n=intersections(posed(head,p.matrix('head')),posed(cover,p.matrix('torso_upper')));counts.append(n);rows.append(dict(offset_model=offset,pitch=pitch,head_triangles=n))
  print(offset,counts,flush=True)
 rig.P['head']=base
 (OUT/'hinge_grid.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
if __name__=='__main__':main()
