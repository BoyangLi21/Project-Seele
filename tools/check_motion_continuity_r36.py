"""Catch IK flips in every authored phrase; this is not an aesthetic grade."""
from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'artifacts/combat_direction_r36'
def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--profiles',type=Path,default=BASE/'profiles');ap.add_argument('--output',type=Path,default=BASE/'continuity.json');args=ap.parse_args()
 rows=[]
 for path in args.profiles.glob('*.json'):
  data=json.loads(path.read_text());names=data['bones'];indices=[i for i,n in enumerate(names) if n.startswith(('arm_','forearm_','leg_','shin_'))]
  for name,c in data['clips'].items():
   if 'intent' not in c:continue
   q=np.array([f['rotation_wxyz'] for f in c['frames']]);q/=np.linalg.norm(q,axis=-1,keepdims=True)
   angle=np.degrees(2*np.arccos(np.clip(np.abs((q[:-1]*q[1:]).sum(-1)),0,1)));values=angle[:,indices]
   frame,bone=np.unravel_index(np.argmax(values),values.shape);maximum=float(values[frame,bone]);per60=maximum*(len(q)-1)/(c['duration_seconds']*60)
   rows.append(dict(rig=data['rig_key'],clip=name,bone=names[indices[bone]],phase=float(frame/(len(q)-1)),maximum_degrees=maximum,degrees_per_60hz=per60))
 failures=[r for r in rows if r['degrees_per_60hz']>45 or not np.isfinite(r['degrees_per_60hz'])]
 report=dict(phrases=len(rows),passed=not failures,failures=failures,rows=rows,scope='Discrete joint-flip check only; artistic timing and mesh contact need native inspection.')
 args.output.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
 if failures:raise SystemExit(2)
if __name__=='__main__':main()
