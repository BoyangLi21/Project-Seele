"""Check full stair pairs and exposed passenger floor edges in current station volumes."""
from pathlib import Path
import json
from collections import Counter
import numpy as np
import scan_regional_completion as scan
from audit_moving_walks_r23 import props
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/stations'
def main():
 scan.WORLD=WORLD;records=json.loads((OUT/'contract.json').read_text(encoding='utf8'))['stations'];results=[];right={'north':(1,0),'south':(-1,0),'east':(0,1),'west':(0,-1)}
 for r in records:
  cx,y,cz=r['center'];h=r['half'];g=r['ground'];horizontal=next(x for x in json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['stations'] if x['station']==r['station'] and x['line']==r['line'])['horizontal'];dx,dz=(h+2,19) if horizontal else (19,h+2);lo=(cx-dx,g-3,cz-dz);hi=(cx+dx,y+14,cz+dz);a,pal=scan.volume(lo,hi);steps={};side=[]
  matched=np.array([s.startswith('mtr:escalator_') for s in pal])[a]
  for yy,zz,xx in np.argwhere(matched):
   q=(int(xx+lo[0]),int(yy+lo[1]),int(zz+lo[2]));state=pal[a[yy,zz,xx]]
   if state.startswith('mtr:escalator_step'):steps[q]=state
   else:side.append(q)
  orphans=[];obstacles=[]
  def state(q):return pal[a[q[1]-lo[1],q[2]-lo[2],q[0]-lo[0]]]
  for q,raw in steps.items():
   p=props(raw);rx,rz=right[p['facing']];k=1 if p['side']=='left' else -1;peer=(q[0]+rx*k,q[1],q[2]+rz*k);other=props(steps[peer]) if peer in steps else None
   if other is None or other['side']==p['side'] or any(other[f]!=p[f] for f in ('facing','direction','orientation')):orphans.append(dict(pos=q,expected=peer,actual=state(peer)))
   for height in (2,3):
    s=state((q[0],q[1]+height,q[2]))
    if s.split('[')[0] not in ('minecraft:air','minecraft:light','minecraft:cave_air') and not s.startswith('mtr:escalator_side'):obstacles.append(dict(pos=q,overhead_height=height,state=s))
  results.append(dict(station=r['station'],line=r['line'],step_cells=len(steps),orphan_halves=orphans,overhead_conflicts=obstacles))
 report=dict(stations=results,orphan_halves=sum(len(r['orphan_halves']) for r in results),overhead_conflicts=sum(len(r['overhead_conflicts']) for r in results));(OUT/'assembly_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('Station assemblies',len(results),'orphans',report['orphan_halves'],'overhead conflicts',report['overhead_conflicts'])
 for r in results:
  if r['orphan_halves'] or r['overhead_conflicts']:print(r['station'],r['line'],r['orphan_halves'][:4],r['overhead_conflicts'][:6])
if __name__=='__main__':main()
