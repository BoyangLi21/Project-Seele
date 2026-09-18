"""Retire custom slow belts; install complete original MTR pairs with crossing landings."""
import argparse,gzip,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
import regional_voxels as v
from query_blocks import iter_selected_sections,AIR as AIR_STATES,read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/access_r22/walkways'
AIR='minecraft:air';PASS=AIR_STATES|{'minecraft:light'};FLOOR='projectseele:nerv_floor_panel';STRUCT='projectseele:nerv_structural_panel';GLASS='projectseele:clear_glass'

def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();original={};selected=defaultdict(set)
 for name in ('paired_indoor_walkways','high_ceiling_galleries'):
  rows=json.loads(gzip.decompress((ROOT/'artifacts/world_repair_r21/global_walkways'/name/'ops.json.gz').read_bytes()))
  for r in rows:
   if not r['state'].startswith('projectseele:nerv_moving_walk'):continue
   x,y,z,X,Y,Z=r['box']
   for yy in range(y,Y+1):
    for zz in range(z,Z+1):
     for xx in range(x,X+1):original[xx,yy,zz]=r['extra'][0]
   for cx in range((x-4)//16,(X+4)//16+1):
    for cz in range((z-4)//16,(Z+4)//16+1):selected[cx,cz].update(range((y-1)//16,(Y+6)//16+1))
 cells={};custom={}
 for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,v.DIM,selected):
  a=idx.reshape(16,16,16)
  for yy in range(16):
   for zz in range(16):
    for xx in range(16):
     q=(cx*16+xx,sy*16+yy,cz*16+zz);state=pal[a[yy,zz,xx]];cells[q]=state
     if state.startswith('projectseele:nerv_moving_walk'):custom[q]=state
 changes={};records=[];seen=set();holds=[]
 def get(q):return changes.get(q,cells.get(q,'UNKNOWN'))
 def put(q,state):
  if q not in cells:raise ValueError(('Unmeasured walkway cell',q))
  changes[q]=v.canonical_state(state)
 # All custom floor strips go, even where a full original MTR pair will not fit.
 for q in custom:put(q,original.get(q,FLOOR))
 rows=json.loads((ROOT/'artifacts/world_repair_r21/global_corridor_sections.json').read_text())['segments']
 routes=json.loads((WORLD/'quality_walk_cases.json').read_text());junctions=[]
 for r in routes:
  pts=r.get('path',[r.get('start'),r.get('end')]);junctions.extend(q for q in pts if q)
 for r in sorted(rows,key=lambda r:-r['length']):
  x,y,z=map(int,r['start']);X,Y,Z=map(int,r['end']);axis=r['axis'];f=y-1
  def at(n,dy,w):return (x+n,f+dy,z+w) if axis=='x' else (x+w,f+dy,z+n)
  if not any(at(n,0,w) in custom for n in range(r['length']) for w in (-2,-1,1,2)):continue
  breaks=set(range(0,5))|set(range(r['length']-5,r['length']))
  for n in range(r['length']):
   if n%36<6:breaks.add(n)
  for jx,jy,jz in junctions:
   u=jx-x if axis=='x' else jz-z;w=jz-z if axis=='x' else jx-x
   if abs(jy-y)<.6 and abs(w)<3 and 4<u<r['length']-4:
    # Only transverse branches are crossings; dense centreline samples are not.
    if any(abs((q[2]-z) if axis=='x' else (q[0]-x))>4 and abs(q[1]-y)<.6 and abs(((q[0]-x) if axis=='x' else (q[2]-z))-u)<2 for q in junctions):breaks.update(range(math.floor(u)-3,math.ceil(u)+4))
  active=[]
  for n in range(5,r['length']-5):
   if n in breaks:continue
   base=at(n,0,0)
   if base in seen:continue
   # A protected interior or a real machine is not sacrificed for a belt.
   if 6<=base[0]<=52 and -445<=f<=-388 and 262<=base[2]<=365:continue
   allowed=True;widen=[]
   for w in (-2,-1,1,2):
    q=at(n,1,w);head=get(q).split('[')[0]
    if head not in PASS:
     if abs(w)!=2 or head not in {'projectseele:nerv_wall_panel',GLASS,'minecraft:light_gray_stained_glass','minecraft:gray_stained_glass'}:allowed=False;break
     outer=w+int(math.copysign(1,w))
     if any(get(at(n,h,outer)).split('[')[0] not in PASS|{'projectseele:nerv_wall_panel',GLASS,'minecraft:light_gray_stained_glass','minecraft:gray_stained_glass'} for h in (1,2,3)):allowed=False;break
     if any(at(n,h,outer) not in cells for h in (0,1,2,3,4)):allowed=False;break
     widen.append((w,outer))
    if any(get(at(n,h,w)).split('[')[0] not in PASS|{'projectseele:nerv_wall_panel',GLASS,'minecraft:light_gray_stained_glass','minecraft:gray_stained_glass'} for h in (1,2,3)):allowed=False;break
   if not allowed:holds.append({'route':r['id'],'at':base,'result':'plain walkable floor; native full-width assembly needs a separate room change'});continue
   for w,outer in widen:
    for h in (1,2,3):put(at(n,h,w),AIR);put(at(n,h,outer),GLASS if h>1 else 'projectseele:nerv_wall_panel')
    put(at(n,0,outer),STRUCT);put(at(n,4,w),STRUCT);put(at(n,4,outer),STRUCT)
   active.append(n);seen.add(base)
  # Do not leave one-block mechanical fragments between doors.
  runs=[]
  for n in active:
   if not runs or n!=runs[-1][-1]+1:runs.append([n])
   else:runs[-1].append(n)
  installed=0
  for run in runs:
   if len(run)<6:continue
   for n in run:
    orientation='landing_bottom' if n==run[0] else 'landing_top' if n==run[-1] else 'flat'
    facing='east' if axis=='x' else 'north'
    for w0,direction in [(-2,True),(1,False)]:
     for lane,side in [(0,'left'),(1,'right')]:
      w=w0+lane
      for dy,state in [(-1,STRUCT),(0,f'mtr:escalator_step[direction={str(direction).lower()},facing={facing},orientation={orientation},side={side},status=true]'),(1,f'mtr:escalator_side[facing={facing},orientation={orientation},side={side}]')]:put(at(n,dy,w),state)
      installed+=1
   records.append({'route':r['id'],'start':at(run[0],0,-2),'end':at(run[-1],0,2),'length':len(run),'axis':axis,'paired':True})
 for q,state in changes.items():
  if state!=cells[q]:p.match((*q,*q),cells[q],state,'r22/original_mtr_walkway')
 p.meta.update(retired_custom_cells=len(custom),native_runs=records,held_cross_sections=holds,ordinary_central_lane=True,measured_changes=len(p.ops))
 p.save_plan('original_mtr_walkways')
 if apply:p.apply('original_mtr_walkways')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Custom retired',len(custom),'native paired runs',len(records),'held sections',len(holds),'changes',len(p.ops))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
