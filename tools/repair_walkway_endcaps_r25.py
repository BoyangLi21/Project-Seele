"""Flat MTR landing blocks lack a top face; use paired flat treads on flat runs."""
import json,argparse
import numpy as np
import regional_voxels as v
from query_blocks import iter_matching_sections
from audit_moving_walks_r23 import props
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/walkways'
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);steps={};stats={};cache=OUT/'measured_steps.json'
 if cache.exists():
  data=json.loads(cache.read_text());steps={tuple(r[:3]):r[3] for r in data['steps']};stats=data['scan']
 else:
  for cx,cz,sy,pal,indices in iter_matching_sections(WORLD,v.DIM,['mtr:escalator_step'],stats):
   mask=np.array([s.startswith('mtr:escalator_step') for s in pal])[indices]
   for raw in np.flatnonzero(mask):
    i=int(raw);steps[cx*16+(i&15),sy*16+(i>>8),cz*16+((i>>4)&15)]=pal[indices[i]]
  cache.write_text(json.dumps({'steps':[[*q,s] for q,s in steps.items()],'scan':stats},separators=(',',':')))
 spec={q:props(s) for q,s in steps.items()};p=v.Painter();v.WORLD=WORLD;v.OUT=OUT;fixed=[];held=[]
 for q,t in spec.items():
  if t['orientation'] not in ('landing_bottom','landing_top'):continue
  dx,dz={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[t['facing']]
  incline=False
  for n in range(-3,4):
   for dy in range(-3,4):
    k=spec.get((q[0]+dx*n,q[1]+dy,q[2]+dz*n))
    if k and k['facing']==t['facing'] and k['orientation'] in ('slope','transition_bottom','transition_top'):incline=True
  if incline:held.append(q);continue
  rx,rz={'north':(1,0),'south':(-1,0),'east':(0,1),'west':(0,-1)}[t['facing']];direction=1 if t['side']=='left' else -1;peer=spec.get((q[0]+rx*direction,q[1],q[2]+rz*direction))
  if not peer or any(peer[k]!=t[k] for k in ('facing','orientation','direction')) or peer['side']==t['side']:raise RuntimeError(('Incomplete end pair',q,t,peer))
  new=steps[q].replace('orientation='+t['orientation'],'orientation=flat');p.match((*q,*q),steps[q],new,'r25/flat_belt_complete_top_surface');fixed.append(q)
 p.meta.update(scan=stats,native_steps=len(steps),fixed_cells=fixed,sloped_landings_retained=len(held),source='Pinned MTR landing model omits top; flat model supplies tread surface')
 p.save_plan('opaque_flat_endcaps')
 if apply:p.apply('opaque_flat_endcaps')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Fixed flat endcap cells',len(fixed),'preserved slope landing cells',len(held),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
