"""Check native evaluated bridge undersides against every retained road datum."""
from pathlib import Path
import argparse,json,numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23/transit'
def main(snapshot=None):
 path=Path(snapshot) if snapshot else OUT/'built/native_final.json';s=json.loads(path.read_text(encoding='utf8'));d=np.load(ROOT/'artifacts/world_rebuild_r20/road_actual/road_contract_final.npz');mask=d['mask'];height=d['height2'];ox,oz=map(int,d['origin']);bad=[];minclear=1e9;steep=[];count=0;tested=0
 for r in s['curves']:
  if r['mode']!='TRAIN' or r['points'][0][1]<0:continue
  count+=1;points=np.asarray(r['points']);q=np.floor(points).astype(int);delta=np.diff(points,axis=0);grade=np.abs(delta[:,1])/np.maximum(.01,np.linalg.norm(delta[:,[0,2]],axis=1));peak=float(grade.max(initial=0))
  if peak>.085:steep.append(dict(id=r['id'],maximum=peak))
  local=[]
  for dx in range(-3,4):
   for dz in range(-3,4):
    x,z=q[:,0]+dx-ox,q[:,2]+dz-oz;known=(x>=0)&(x<mask.shape[1])&(z>=0)&(z<mask.shape[0]);idx=np.flatnonzero(known);idx=idx[mask[z[idx],x[idx]]]
    if not len(idx):continue
    feet=height[z[idx],x[idx]]/2;clear=q[idx,1]-3-feet;minclear=min(minclear,float(clear.min()));tested+=len(idx);wrong=np.flatnonzero(clear<6)
    for j in wrong[:3]:local.append(dict(pos=[int(x[idx[j]]+ox),float(feet[j]),int(z[idx[j]]+oz)],clearance=float(clear[j])))
  if local:bad.append(dict(id=r['id'],first=r['points'][0],last=r['points'][-1],minimum=min(row['clearance'] for row in local),examples=local[:4]))
 report=dict(snapshot=str(path),surface_rails=count,road_samples=tested,minimum_bridge_clearance=minclear,bad=bad,steep=steep,passed=not bad and not steep);(OUT/'road_clearance_audit.json').write_text(json.dumps(report,indent=2));print('Bridge-road audit',count,'rails',tested,'samples','min clear',minclear,'bad',len(bad),'steep',len(steep));print(json.dumps(bad[:8],indent=2));print(steep)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--snapshot');main(ap.parse_args().snapshot)
