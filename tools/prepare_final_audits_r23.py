"""Final affected-route checks plus the complete set of physical perimeter probes."""
from pathlib import Path
import argparse,json,math,shutil,numpy as np
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/validation'
def main(install=False):
 allcases=json.loads((OUT/'full_walk_cases.json').read_text(encoding='utf8'));latest={q['id']:q for q in json.loads((OUT/'native_full_walk_results.json').read_text())};latest.update({q['id']:q for q in json.loads((OUT/'native_recheck2_results.json').read_text())});affected={}
 cutoff=(OUT/'native_recheck2_results.json').stat().st_mtime
 for root in [ROOT/'artifacts/facility_r23']:
  for path in root.rglob('c.*.npz'):
   if path.parent.name!='delta' or not path.parent.parent.name.startswith('applied_') or path.stat().st_mtime<=cutoff:continue
   if (path.parent.parent/'ROLLED_BACK.json').exists() or 'promotion' in path.parts:continue
   cx,cz=map(int,path.stem.split('.')[1:]);d=np.load(path);offset=d['offsets'];
   if not len(offset):continue
   ys=offset.astype(np.int64)//256+int(d['minimum']);box=(cx*16-.35,float(ys.min())-2,cz*16-.35,cx*16+16.35,float(ys.max())+1,cz*16+16.35);old=affected.get((cx,cz));affected[cx,cz]=box if old is None else (box[0],min(old[1],box[1]),box[2],box[3],max(old[4],box[4]),box[5])
 def touches(case):
  pts=case.get('path',[case.get('start'),case.get('end')])
  for a,b in zip(pts,pts[1:]):
   lo=np.minimum(a,b);hi=np.maximum(a,b)
   for cx in range(math.floor((lo[0]-.4)/16),math.floor((hi[0]+.4)/16)+1):
    for cz in range(math.floor((lo[2]-.4)/16),math.floor((hi[2]+.4)/16)+1):
     box=affected.get((cx,cz))
     if box is not None and box[1]<=hi[1] and box[4]>=lo[1]:return True
  return False
 tests=[q for q in allcases if q['id'] not in latest or latest[q['id']]['status']!='pass' or touches(q)]
 (OUT/'final_walk_cases.json').write_text(json.dumps(tests,ensure_ascii=False),encoding='utf8')
 guards=json.loads((WORLD/'r23_guard_cases.json').read_text());old=[[108.5,-442,-30.5,-1,0],[103.5,-442,-53.5,-1,0],[97.5,-369,-52.5,-1,0],[112.5,-394,-255.5,1,0],[96.5,-394,-255.5,-1,0],[123.5,-442,223.5,1,0],[113.5,-442,223.5,-1,0],[30.5,-367,-276.5,0,1],[30.5,-367,-208.5,0,-1],[6446.5,127,-6217.5,-1,0],[6438.5,127,-6217.5,1,0],[6446.5,127,-6224.5,0,-1],[6446.5,127,-6215.5,0,1],[6286.5,127,-6217.5,-1,0],[6278.5,127,-6217.5,1,0],[6286.5,127,-6224.5,0,-1],[6286.5,127,-6215.5,0,1]]
 names={q['id'] for q in guards}
 for i,q in enumerate(old):
  name='r23/retained_guard/'+str(i)
  if name not in names:guards.append(dict(id=name,start=q[:3],direction=[q[3],0,q[4]]))
 # The five apparent gaps at the service landing sit behind its physical
 # interlocked door (Z=257). Test the public side, not a point already in
 # the shaft beyond the locked door.
 for x in range(10,15):
  name=f'r23/command_lift_closed_landing/{x}'
  if name not in names:guards.append(dict(id=name,start=[x+.5,-419,258.5],direction=[0,0,-1]))
 (OUT/'final_guard_cases.json').write_text(json.dumps(guards,ensure_ascii=False),encoding='utf8')
 if install:
  shutil.copy2(OUT/'final_walk_cases.json',WORLD/'r23_walk_cases.json');shutil.copy2(OUT/'final_guard_cases.json',WORLD/'r23_guard_cases.json')
 print('Final affected paths',len(tests),'of',len(allcases),'physical edge pushes',len(guards))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');main(ap.parse_args().install)
