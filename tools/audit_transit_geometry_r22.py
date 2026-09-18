"""Three-dimensional train envelope checks on the engine's evaluated curves."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/access_r22/transit'
def main():
 s=json.loads((OUT/(sys.argv[1] if len(sys.argv)>1 else 'built3')/'native_commission.json').read_text());rails=[r for r in s['curves'] if r['mode']=='TRAIN' and r['points'][0][1]>0];collisions=[];grades=[]
 for i,a in enumerate(rails):
  p=np.asarray(a['points']);d=np.diff(p,axis=0);horizontal=np.linalg.norm(d[:,[0,2]],axis=1);grade=np.abs(d[:,1])/np.maximum(horizontal,.01);maximum=float(grade.max(initial=0))
  if maximum>.085:grades.append(dict(rail=a['id'],maximum_grade=maximum))
  for b in rails[i+1:]:
   ag=a['geometry'];bg=b['geometry'];endsA=[ag['position1'],ag['position2']];endsB=[bg['position1'],bg['position2']]
   if any(x==y for x in endsA for y in endsB):continue
   q=np.asarray(b['points'])
   if np.any(p[:,[0,2]].max(0)+4<q[:,[0,2]].min(0)) or np.any(q[:,[0,2]].max(0)+4<p[:,[0,2]].min(0)):continue
   near=cKDTree(q[:,[0,2]]).query_ball_point(p[:,[0,2]],r=3.2)
   for pi,js in enumerate(near):
    if not js:continue
    delta=np.abs(q[js,1]-p[pi,1]);j=int(np.argmin(delta))
    if delta[j]<7.5:
     collisions.append(dict(a=a['id'],b=b['id'],point_a=p[pi].tolist(),point_b=q[js[j]].tolist(),vertical_gap=float(delta[j])));break
 result=dict(surface_rails=len(rails),crossing_conflicts=collisions,steep_segments=grades,passed=not collisions)
 (OUT/'geometry_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
