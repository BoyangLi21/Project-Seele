"""Check both ends of the remaining inclined MTR groups without deleting working stairs."""
from pathlib import Path
import json
import numpy as np
from scipy.ndimage import label,find_objects
import scan_regional_completion as scan
from query_blocks import AIR
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R26_REVIEW'

def main():
 scan.WORLD=WORLD;lo=(-90,-474,230);hi=(155,-345,430);a,p=scan.volume(lo,hi)
 mask=np.array([s.startswith('mtr:escalator_step') for s in p])[a];lab,n=label(mask,structure=np.ones((3,3,3),bool));sh=json.loads((WORLD/'native_collision_shapes.json').read_text())
 def accessible(x,y,z):
  if not(0<=x<a.shape[2] and 0<y<a.shape[0]-2 and 0<=z<a.shape[1]):return False
  state=p[a[y-1,z,x]]
  if any(k in state for k in ('escalator','wall[','bars','fence','water','lcl')):return False
  return any(b[4]>=.9 for b in sh.get(state,[] if state.split('[')[0] in AIR else [[0,0,0,1,1,1]])) and all(p[a[y+j,z,x]].split('[')[0] in AIR|{'minecraft:light'} for j in (0,1))
 records=[]
 for i,b in enumerate(find_objects(lab),1):
  if b[0].stop-b[0].start<3:continue
  pts=np.argwhere(lab[b]==i)+np.array([b[0].start,b[1].start,b[2].start]);ends=[]
  for Y in (pts[:,0].min(),pts[:,0].max()):
   contacts=set()
   for y,z,x in pts[pts[:,0]==Y]:
    for dz,dx in ((0,1),(0,-1),(1,0),(-1,0)):
     for distance in (1,2,3):
      for dy in (0,1,2):
       if accessible(x+dx*distance,y+dy,z+dz*distance):contacts.add(tuple(map(int,(x+dx*distance+lo[0],y+dy+lo[1],z+dz*distance+lo[2]))))
   ends.append(sorted(contacts))
  xyz=pts[:,[2,0,1]]+lo;records.append(dict(id=i,cells=len(pts),min=xyz.min(0).tolist(),max=xyz.max(0).tolist(),bottom_contacts=ends[0],top_contacts=ends[1]))
 out=ROOT/'artifacts/facility_r26/survey/old_inclined_endpoints.json';out.write_text(json.dumps(records,indent=2))
 print('Inclined groups',len(records),'unconnected ends',[(r['id'],r['min'],r['max'],len(r['bottom_contacts']),len(r['top_contacts'])) for r in records if not all((r['bottom_contacts'],r['top_contacts']))])
if __name__=='__main__':main()
