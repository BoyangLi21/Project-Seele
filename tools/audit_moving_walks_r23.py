"""Inventory every native escalator pair and remove only flat-run handrails."""
import argparse,json,time
from pathlib import Path
from collections import Counter
import numpy as np
import regional_voxels as v
from query_blocks import iter_matching_sections,read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/walkways'
def props(s):return dict(q.split('=') for q in s.split('[',1)[1][:-1].split(','))
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);snapshot=OUT/'native_cells.json';stats={};steps={};sides={}
 if snapshot.exists():
  data=json.loads(snapshot.read_text());stats=data['scan'];steps={tuple(r[:3]):r[3] for r in data['steps']};sides={tuple(r[:3]):r[3] for r in data['sides']}
 else:
  for cx,cz,sy,pal,indices in iter_matching_sections(WORLD,v.DIM,['mtr:escalator_step','mtr:escalator_side'],stats):
   match=np.array([s.startswith(('mtr:escalator_step','mtr:escalator_side')) for s in pal])[indices].reshape(16,16,16)
   for y,z,x in np.argwhere(match):
    q=(int(cx*16+x),int(sy*16+y),int(cz*16+z));s=pal[indices[(y*16+z)*16+x]];(steps if s.startswith('mtr:escalator_step') else sides)[q]=s
  snapshot.write_text(json.dumps(dict(scan=stats,steps=[[*q,s] for q,s in steps.items()],sides=[[*q,s] for q,s in sides.items()]),separators=(',',':')))
 parsed={q:props(s) for q,s in steps.items()};right={'north':(1,0),'south':(-1,0),'east':(0,1),'west':(0,-1)};ahead={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)};pairs=[];orphans=[];removed=[];v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
 for q,spec in parsed.items():
  dx,dz=right[spec['facing']];sign=1 if spec['side']=='left' else -1;other=(q[0]+dx*sign,q[1],q[2]+dz*sign);peer=parsed.get(other)
  if peer is None or peer['facing']!=spec['facing'] or peer['orientation']!=spec['orientation'] or peer['direction']!=spec['direction'] or peer['side']==spec['side']:orphans.append(dict(pos=q,state=steps[q],expected_peer=other,actual=steps.get(other)))
  elif spec['side']=='left':pairs.append((q,other))
 for q,s in sides.items():
  below=(q[0],q[1]-1,q[2]);spec=parsed.get(below)
  if spec is None:continue
  if spec['orientation'] in ('slope','transition_bottom','transition_top'):continue
  dx,dz=ahead[spec['facing']];near_incline=False
  for distance in range(-3,4):
   for dy in range(-3,4):
    neighbour=parsed.get((q[0]+dx*distance,q[1]-1+dy,q[2]+dz*distance))
    if neighbour and neighbour['facing']==spec['facing'] and neighbour['orientation'] in ('slope','transition_bottom','transition_top'):near_incline=True
  if not near_incline:p.match((*q,*q),s,'minecraft:air','r23/flat_walkway_without_handrails');removed.append(q)
 p.meta.update(full_save_scan=stats,native_step_cells=len(steps),paired_units=len(pairs),orphan_halves=orphans,flat_handrails_removed=len(removed),removed=removed)
 p.save_plan('flat_handrail_retirement')
 if apply:p.apply('flat_handrail_retirement')
 (OUT/'audit.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Full-save scan',stats,'steps',len(steps),'valid pairs',len(pairs),'orphan halves',len(orphans),'flat rails',len(removed),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
