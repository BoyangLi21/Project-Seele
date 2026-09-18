"""Give long pyramid galleries a coherent five-metre clear width and paired native walks."""
from pathlib import Path
from collections import defaultdict
import argparse,json,math,numpy as np
from scipy.ndimage import binary_dilation
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f
from query_blocks import read_box,AIR,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/gallery_width'
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;f.LO=(-10,-438,266);f.HI=(83,-358,382);s=f.Scene();p=v.Painter();routes=json.loads((ROOT/'artifacts/facility_r23/validation/full_walk_cases.json').read_text(encoding='utf8'));by_floor=defaultdict(list)
 for y in (-434,-420,-406,-392):
  by_floor[y]+=[dict(name='west',axis='z',a=-6,b=-2,start=274,end=371),dict(name='east',axis='z',a=73,b=77,start=282,end=371),dict(name='rear',axis='x',a=370,b=374,start=-5,end=76)]
 for y in (-378,-364):by_floor[y]+=[dict(name='upper_west',axis='z',a=9,b=13,start=295,end=344),dict(name='upper_south',axis='x',a=366,b=370,start=-1,end=69)]
 # Retire this round's boards and their own rods before remounting on the
 # final gallery walls. Earlier station departure boards are not removed.
 retired=[];nav=json.loads((ROOT/'artifacts/facility_r23/navigation/junctions.json').read_text(encoding='utf8'))
 for row in nav['boards']:
  for q in [row['position']]+row['suspension']:
   q=tuple(q);old=read_box(WORLD,v.DIM,q,q)[q]
   if not (old.startswith(('projectseele:station_departure_board','projectseele:nerv_direction_panel')) or old.startswith('minecraft:iron_bars')):continue
   if all(f.LO[i]<=q[i]<=f.HI[i] for i in range(3)):s.fill((*q,*q),'minecraft:air')
   else:p.match((*q,*q),old,'minecraft:air','r23/remount_after_corridor_width')
   retired.append(q)
 known={'minecraft:air','minecraft:cave_air','minecraft:light','minecraft:smooth_stone','minecraft:gray_concrete','minecraft:light_gray_concrete','minecraft:polished_deepslate','minecraft:smooth_stone_slab','minecraft:gray_stained_glass','minecraft:light_gray_stained_glass','minecraft:iron_bars','minecraft:polished_blackstone_slab','minecraft:sea_lantern','minecraft:white_concrete','projectseele:nerv_floor_panel','projectseele:nerv_wall_panel','projectseele:nerv_wall_datum','projectseele:nerv_structural_panel','projectseele:nerv_strip_light','projectseele:clear_glass','projectseele:nerv_direction_panel','projectseele:station_departure_board'}
 known|={'minecraft:smooth_quartz','minecraft:black_concrete','projectseele:nerv_hazard_paving'}
 allowed=np.array([q.split('[')[0] in known or q.startswith('mtr:escalator_') for q in s.palette]);unknown=[];belts=[];ports_report=[]
 def put(q,value):
  iy,iz,ix=q[1]-f.LO[1],q[2]-f.LO[2],q[0]-f.LO[0];old=s.palette[s.after[iy,iz,ix]]
  if old.split('[')[0] not in known and not old.startswith('mtr:escalator_'):unknown.append(dict(pos=q,state=old));return
  s.fill((*q,*q),value)
 for y,bands in by_floor.items():
  footprint=np.zeros((f.HI[2]-f.LO[2]+1,f.HI[0]-f.LO[0]+1),bool)
  for b in bands:
   for n in range(b['start'],b['end']+1):
    for w in range(b['a'],b['b']+1):
     x,z=(n,w) if b['axis']=='x' else (w,n);footprint[z-f.LO[2],x-f.LO[0]]=True
  envelope=binary_dilation(footprint,structure=np.array([[0,1,0],[1,1,1],[0,1,0]],bool));shell=envelope&~footprint;ports=set()
  for route in routes:
   path=route.get('path',[route.get('start'),route.get('end')])
   for aa,bb in zip(path,path[1:]):
    if max(aa[1],bb[1])<y-.6 or min(aa[1],bb[1])>y+.6:continue
    aa,bb=np.asarray(aa),np.asarray(bb);length=np.linalg.norm(bb-aa)
    if np.any(np.maximum(aa,bb)<np.array(f.LO)-2) or np.any(np.minimum(aa,bb)>np.array(f.HI)+2):continue
    for q in np.linspace(aa,bb,max(2,int(length*2)+1)):
     if abs(q[1]-y)>.6:continue
     x,z=math.floor(q[0]),math.floor(q[2])
     for dx in (-1,0,1):
      for dz in (-1,0,1):
       X,Z=x+dx-f.LO[0],z+dz-f.LO[2]
       if 0<=Z<shell.shape[0] and 0<=X<shell.shape[1] and shell[Z,X]:ports.add((x+dx,z+dz))
  for zz,xx in np.argwhere(envelope):
   x,z=int(xx+f.LO[0]),int(zz+f.LO[2]);rim=bool(shell[zz,xx]);opening=(x,z) in ports
   for Y,material in [(y-2,'projectseele:nerv_structural_panel'),(y-1,'projectseele:nerv_floor_panel'),(y+4,'projectseele:nerv_structural_panel')]:put((x,Y,z),material)
   for h in range(4):
    material='minecraft:air' if not rim or opening else 'projectseele:nerv_wall_datum' if h==1 else 'projectseele:clear_glass' if h==2 else 'projectseele:nerv_wall_panel';put((x,y+h,z),material)
  ports_report.append(dict(floor_y=y,ports=sorted(ports)))
  for b in bands:
   # Every real crossing and room/stair entrance has a stationary landing.
   breaks=set(range(b['start'],b['start']+5))|set(range(b['end']-4,b['end']+1))
   for x,z in ports:
    n=x if b['axis']=='x' else z;w=z if b['axis']=='x' else x
    if b['a']-1<=w<=b['b']+1:breaks.update(range(n-3,n+4))
   for n in range(b['start'],b['end']+1):
    if (n-b['start'])%36<5:breaks.add(n)
   runs=[]
   for n in range(b['start']+5,b['end']-4):
    if n in breaks:continue
    if not runs or n!=runs[-1][-1]+1:runs.append([n])
    else:runs[-1].append(n)
   for run in runs:
    if len(run)<7:continue
    for n in run:
     for origin,forward in ((b['a'],True),(b['b']-1,False)):
      for lane,side in ((0,'left'),(1,'right')):
       x,z=(n,origin+lane) if b['axis']=='x' else (origin+lane,n);orient='landing_bottom' if n==run[0] else 'landing_top' if n==run[-1] else 'flat';face='east' if b['axis']=='x' else 'north';put((x,y-1,z),f'mtr:escalator_step[direction={str(forward).lower()},facing={face},orientation={orient},side={side},status=true]')
    belts.append(dict(gallery=b['name'],feet=y,axis=b['axis'],from_n=run[0],to_n=run[-1],lanes=[b['a'],b['b']-1]))
   # Fitted ceiling luminaires replace freestanding floor decorations.
   for n in range(b['start']+6,b['end']-4,12):
    w=(b['a']+b['b'])//2;x,z=(n,w) if b['axis']=='x' else (w,n);put((x,y+4,z),'projectseele:nerv_strip_light')
 # Preserve all fixtures with explicit semantics until individually reviewed.
 unique={tuple(q['pos']):q for q in unknown};p.meta.update(galleries=sum(map(len,by_floor.values())),clear_width=5,native_paired_runs=belts,ports=ports_report,retired_own_sign_cells=retired,unexpected_materials=list(unique.values()))
 if unique:
  (OUT/'held.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');raise RuntimeError(('Unexpected gallery fixture',list(unique.values())[:8]))
 count=s.delta(p,'r23/five_metre_galleries_and_original_mtr_walks');p.meta['changed_cells']=count;p.save_plan('coherent_pyramid_galleries')
 if apply:p.apply('coherent_pyramid_galleries')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Galleries',p.meta['galleries'],'native paired runs',len(belts),'changed',count)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
