"""Geometric lid closure and open-channel checks on staged candidate surfaces."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/dorsal_tv_r13'

def hits(triangles,origins,direction):
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2];e1=b-a;e2=c-a;p=np.cross(direction,e2);det=(e1*p).sum(1);safe=abs(det)>1e-7;inverse=np.where(safe,1/np.where(safe,det,1),0);result=[]
    for origin in origins:
        delta=origin-a;u=(delta*p).sum(1)*inverse;q=np.cross(delta,e1);v=(q*direction).sum(1)*inverse;t=(q*e2).sum(1)*inverse;result.append(bool((safe&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)&(t>=0)&(t<54)).any()))
    return np.array(result)

def main():
    report=[]
    for row in json.loads((OUT/'candidate_manifest.json').read_text()):
        model=row['model'];data=json.loads((OUT/'candidate/assets/projectseele/mesh'/(model+'.mesh.json')).read_text());part=data['parts']['dorsal_cover'];triangles=np.array(part['vertices']).reshape(-1,3,8)[:,:,:3]+part['pivot'];C=np.array(row['centre']);N=np.array(row['outward']);Y=np.array(row['hinge_axis']);H=np.array(row['hinge']);grid=np.linspace(-3.6,3.6,29);disk=np.array([[x,y] for x in grid for y in grid if x*x+y*y<=3.6**2]);origins=C+N*18+disk[:,0,None]*[1,0,0]+disk[:,1,None]*Y
        closed=hits(triangles,origins,-N);opened=hits(H+R.from_rotvec(Y*np.deg2rad(row['open_angle_degrees'])).apply((triangles-H).reshape(-1,3)).reshape(triangles.shape),origins,-N)
        entry=json.loads((ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/mesh/entry_plug_unit01.mesh.json').read_text());p=entry['parts']['entry_plug'];v=np.array(p['vertices']).reshape(-1,8);v[:,:3]+=p['pivot'];radius=float(np.linalg.norm(v[:,:2],axis=1).max()*.2)
        record=dict(model=model,rays=len(disk),closed_covered=int(closed.sum()),open_obstructed=int(opened.sum()),missed_closed=disk[~closed].round(4).tolist(),visible_plug_radius_blocks=radius,minimum_bore_radius_blocks=3.49*5/16,passed=bool(closed.all() and not opened.any() and radius<3.49*5/16));report.append(record);print(model,record['passed'],record['closed_covered'],record['open_obstructed'])
    (OUT/'cover_ray_audit.json').write_text(json.dumps(report,indent=2));assert all(row['passed'] for row in report),'Candidate is not ready for installation'
if __name__=='__main__':main()
