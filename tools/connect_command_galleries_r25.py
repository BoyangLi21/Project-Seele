"""Eight explicitly requested, enclosed side-gallery connections at measured levels."""
import argparse,json,math
from collections import defaultdict
import numpy as np
import regional_voxels as v, scan_regional_completion as scan, plan_factory_r20 as f
from query_blocks import iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/command_links'
FLOOR='projectseele:nerv_floor_panel';STRUCT='projectseele:nerv_structural_panel';WALL='projectseele:nerv_wall_panel'

def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT
 f.LO=(-10,-439,251);f.HI=(82,-384,286);s=f.Scene();p=v.Painter();paths=[]
 # User Y values include the floor slab in three examples. Feet levels come
 # from the measured gallery and command approach, not rounded user heights.
 for side in ('west','east'):
  for i,(fy,ty,z) in enumerate([(-434,-429,267),(-420,-419,264),(-406,-409,259),(-392,-389,269)]):
   x0,x1=( -4,10) if side=='west' else (76,49 if i<2 else 31 if i==2 else 50)
   # The upper-command approach at -409 narrows to x=36; its east
   # connection meets the existing north lobby instead of its glazing.
   if side=='east' and i==2:z=259
   z0=276 if side=='west' else 283
   nodes=[(x0,fy,Z) for Z in range(z0,z-1,-1)]
   step=1 if x1>x0 else -1;length=abs(x1-x0)
   for n in range(1,length+1):
    rise=abs(ty-fy);dy=min(rise,max(0,n-(length-rise-2)))
    yy=fy+(1 if ty>fy else -1)*dy
    nodes.append((x0+n*step,yy,z))
   assert nodes[-1][1]==ty
   paths.append(dict(id=f'r25/{side}_command_{i}',side=side,start=[x0+.5,fy,z0+.5],end=[x1+.5,ty,z+.5],nodes=nodes))
 # Union each walk envelope before walls, so bends do not acquire internal
 # partitions. The four vertical levels remain separate shells.
 for route in paths:
  nodes=route['nodes'];floor={};axis={}
  for n,q in enumerate(nodes):
   prev=nodes[max(0,n-1)];nxt=nodes[min(len(nodes)-1,n+1)]
   dx=nxt[0]-prev[0];dz=nxt[2]-prev[2]
   for w in (-1,0,1):
    x,y,z=q;xx,zz=(x+w,z) if dz else (x,z+w)
    floor[xx,zz]=y;axis[xx,zz]=(dx,dz,nxt[1]-y,y-prev[1])
  shell={}
  for (x,z),y in floor.items():
   for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
    if (x+dx,z+dz) not in floor:shell.setdefault((x+dx,z+dz),y)
  for (x,z),y in {**shell,**floor}.items():
   s.fill((x,y-2,z,x,y-1,z),STRUCT);s.fill((x,y+3,z,x,y+3,z),STRUCT)
   for h in range(3):
    material='minecraft:air' if (x,z) in floor else 'projectseele:clear_glass' if h==1 else WALL
    s.fill((x,y+h,z,x,y+h,z),material)
  for (x,z),y in floor.items():
   dx,dz,up,down=axis[x,z];material=FLOOR
   if up or down:
    # The stair is in the lower of two adjacent floor cells, oriented
    # towards the upper tread. Full landing blocks occupy both ends.
    facing=('east' if dx>0 else 'west') if dx else ('south' if dz>0 else 'north')
    if up<0 or down<0:facing={'east':'west','west':'east','north':'south','south':'north'}[facing]
    material=f'minecraft:smooth_quartz_stairs[facing={facing},half=bottom,shape=straight,waterlogged=false]'
   s.fill((x,y-1,z,x,y-1,z),material)
  # End caps open only at the actual inherited gallery/lobby ports.
  for endpoint,neighbor in ((nodes[0],nodes[1]),(nodes[-1],nodes[-2])):
   x,y,z=endpoint;dx=int(np.sign(x-neighbor[0]));dz=int(np.sign(z-neighbor[2]))
   for w in (-1,0,1):
    X,Z=(x+dx+w,z+dz) if dz else (x+dx,z+dz+w)
    s.fill((X,y-1,Z,X,y-1,Z),FLOOR);s.fill((X,y,Z,X,y+2,Z),'minecraft:air')
  for q in nodes[3:-2:7]:s.fill((q[0],q[1]+3,q[2],q[0],q[1]+3,q[2]),'projectseele:nerv_strip_light')
 # Do not silently replace controls, storage contents, or one-way glazing.
 changes=s.before!=s.after
 for q,t in iter_block_entities(WORLD,v.DIM,f.LO,f.HI):
  if changes[q[1]-f.LO[1],q[2]-f.LO[2],q[0]-f.LO[0]]:raise RuntimeError(('Existing fixture in proposed connector',q,t.snbt()))
 count=s.delta(p,'r25/user_requested_command_gallery_connections')
 walk=[]
 for r in paths:
  path=[[x+.5,y,z+.5] for x,y,z in r['nodes']]
  # Sampling every tread exercises the real rise, in both directions.
  for reverse in (False,True):
   q=list(reversed(path)) if reverse else path
   walk.append(dict(id=r['id']+('/return' if reverse else '/out'),start=q[0],end=q[-1],path=q))
 p.meta.update(connections=paths,walk_nodes=walk,changed_cells=count,source='User R25 ports with measured floor levels')
 p.save_plan('eight_enclosed_links')
 if apply:p.apply('eight_enclosed_links')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Connections',len(paths),'cells',count)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
