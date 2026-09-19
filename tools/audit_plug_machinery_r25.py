"""Native capsule OBB versus actual rendered carrier/cage triangles, all 3 airframes."""
from pathlib import Path
import json,argparse
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r25/plug_clearance'
def overlap(triangles,centre,half):
 t=triangles-centre
 keep=(t.min(axis=1)<=half+1e-7).all(1)&(t.max(axis=1)>=-half-1e-7).all(1)
 t=t[keep]
 if not len(t):return 0
 e=[t[:,1]-t[:,0],t[:,2]-t[:,1],t[:,0]-t[:,2]]
 axes=[np.cross(e[0],e[1])]+[np.cross(edge,axis) for edge in e for axis in np.eye(3)]
 hit=np.ones(len(t),bool)
 for axis in axes:
  r=abs(axis)@half;projection=np.einsum('nvi,ni->nv',t,axis)
  hit&=~((projection.min(1)>r+1e-7)|(projection.max(1)<-r-1e-7))
 return int(hit.sum())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mesh',type=Path,default=ROOT/'src/main/resources/assets/projectseele/mesh/tv_facilities_r16.json');ap.add_argument('--label',default='baseline');a=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 source=ROOT/'run/saves/SEELE_R25_REVIEW/r25_plug_route_witness.json';poses=json.loads(source.read_text());(OUT/'native_poses.json').write_bytes(source.read_bytes())
 parts=json.loads(a.mesh.read_text())['parts'];meshes={name:np.array(parts[name],float).reshape(-1,3,6)[:,:,:3] for name in ('carrier_spine','cage_frame')};rows=[]
 for unit in poses:
  for sample in unit['poses']:
   rotation=R.from_quat(sample['quaternion_xyzw']).as_matrix();origin=np.asarray(sample['translation'])
   for part,tri in meshes.items():
    local=(tri-origin)@rotation;n=overlap(local,np.array([0.,0.,5.]),np.array([1.2,1.2,5.15]))
    if n:rows.append(dict(variant=unit['variant'],progress=sample['progress'],part=part,triangles=n))
 report=dict(mesh=str(a.mesh),source='401 exact production insertion poses per native NERV unit; oriented capsule safety hull against rendered triangles',sampled_poses=sum(len(u['poses']) for u in poses),conflicting_samples=len(rows),conflicts=rows,passed=not rows)
 (OUT/(a.label+'.json')).write_text(json.dumps(report,indent=2),encoding='utf8')
 from collections import Counter
 print(a.label,report['sampled_poses'],'poses;',len(rows),'conflicts',dict(Counter((r['variant'],r['part']) for r in rows)),flush=True)
if __name__=='__main__':main()
