"""Two requested shafts with enclosed, measured landings and one cabin each."""
import json,argparse
import numpy as np
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f
import repair_facility_r21 as halls
from query_blocks import iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/lifts'
AIR='minecraft:air';STRUCT=f.STRUCT;FLOOR=f.FLOOR;GLASS='projectseele:clear_glass'
def build(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;p=v.Painter();specs=[];walks=[]
 for name,x,z,floors,exit in [('east',73,253,[-448,-434,-420,-406,-392],'south'),('observation',-29,-278,[-394,-367],'north')]:
  f.LO=halls.LO=(x-6,min(floors)-3,z-13);f.HI=halls.HI=(x+10,max(floors)+7,z+32);s=halls.Facility()
  # Keep the existing crane portal at x=-35..-32, z=-285..-280.
  if name=='observation':s.protect((-35 if f.LO[0]<=-35 else f.LO[0],f.LO[1],-285,-32,f.HI[1],-280))
  s.fill((x-3,min(floors)-2,z-3,x+3,max(floors)+5,z+3),STRUCT)
  s.fill((x-2,min(floors)-1,z-2,x+2,max(floors)+4,z+2),AIR)
  for y in floors:
   if exit=='south':
    s.hall(name+str(y),[(x-4,x+5,z+3,z+29)],y-1,5,
           [(x-1,y,z+3,x+1,y+2,z+3),(x+1,y,z+29,x+4,y+2,z+29)])
    s.fill((x-1,y,z+3,x+1,y+2,z+4),AIR)
    path=[[x+.5,y,z+6.5],[76.5,y,278.5],[76.5,y,283.5]]
    if y==-448:path=[[x+.5,y,z+6.5],[76.5,y,278.5]]
   else:
    s.hall(name+str(y),[(x-2,x+7,z-11,z-3),(x+4,x+8,z-8,z+11)],y-1,5,
           [(x-1,y,z-3,x+1,y+2,z-3),(x+5,y,z+11,x+7,y+2,z+11)])
    s.fill((x-1,y,z-4,x+1,y+2,z-3),AIR)
    path=[[x+.5,y,z-6.5],[x+6.5,y,z-6.5],[x+6.5,y,z+8.5]]
    if y==-367:path=[[x+.5,y,z-6.5],[x+6.5,y,z-6.5],[x+10.5,y,z-6.5],[x+10.5,y,z-3.5]]
   for reverse in (False,True):
    q=list(reversed(path)) if reverse else path
    walks.append(dict(id=f'r25/lift/{name}/{y}/'+str(reverse),start=q[0],end=q[-1],path=q))
  # Native capture is exactly five by five by six. The fixed shaft remains
  # separate; no decorative strip is allowed through the travelling volume.
  s.fill((x-2,min(floors)-1,z-2,x+2,max(floors)+4,z+2),AIR)
  y=floors[0];s.fill((x-2,y-1,z-2,x+2,y-1,z+2),'minecraft:polished_deepslate')
  s.fill((x-2,y+4,z-2,x+2,y+4,z+2),'minecraft:smooth_quartz')
  for X in range(x-2,x+3):
   for Z in range(z-2,z+3):
    if abs(X-x)==2 or abs(Z-z)==2:s.fill((X,y,Z,X,y+3,Z),'minecraft:iron_block')
  side=1 if exit=='south' else -1;s.fill((x-1,y,z+side*2,x+1,y+2,z+side*2),'minecraft:light_gray_stained_glass')
  changed=s.before!=s.after
  for q,t in iter_block_entities(WORLD,v.DIM,f.LO,f.HI):
   if changed[q[1]-f.LO[1],q[2]-f.LO[2],q[0]-f.LO[0]]:raise RuntimeError(('Existing mechanism in new shaft',q,t.snbt()))
  count=s.delta(p,'r25/'+name+'_native_lift_civil');specs.append(dict(id=name,centre=[x,z],feet_levels=floors,exit=exit,cells=count))
 p.meta.update(lifts=specs,walk_nodes=walks,terminal_dogma_stop=False)
 p.save_plan('new_native_lift_shafts')
 if apply:
  p.apply('new_native_lift_shafts')
  (WORLD/'facility_lifts_r25.json').write_text(json.dumps(dict(installed=True,lifts=specs),ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');build(ap.parse_args().apply)
