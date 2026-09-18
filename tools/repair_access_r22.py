"""Measured station shortcut, through-door and complete reachable platform edges."""
import argparse,json,math
from pathlib import Path
import nbtlib,numpy as np
from scipy.ndimage import label,binary_dilation
import regional_voxels as v
import scan_regional_completion as scan
import repair_facility_r21 as f21
import plan_factory_r20 as factory
from query_blocks import iter_block_entities
ROOT=v.ROOT;OUT=ROOT/'artifacts/access_r22/map';MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_R22_REVIEW'
FLOOR=factory.FLOOR;STRUCT=factory.STRUCT;GLASS='projectseele:clear_glass';AIR='minecraft:air'

def scene(lo,hi):
 f21.LO=factory.LO=lo;f21.HI=factory.HI=hi
 s=f21.Facility();s.protected|=np.array([q.startswith(('projectseele:nerv_pyramid_panel','projectseele:one_way_glass')) for q in s.palette])[s.before]
 for p,t in iter_block_entities(scan.WORLD,v.DIM,lo,hi):
  if str(t['id']).startswith('movingelevators:'):
   x,y,z=p;s.protect((max(lo[0],x-8),lo[1],max(lo[2],z-8),min(hi[0],x+8),hi[1],min(hi[2],z+8)))
 return s

def edges(s,lo,hi,routes):
 shapes={v.canonical_state(k):value for k,value in json.loads((MAIN/'native_collision_shapes.json').read_text()).items()}
 def shape(state):
  if state in shapes:return shapes[state]
  if state.split('[')[0] in ('minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:light'):return []
  return [[0,0,0,1,1,1]]
 sh=[shape(state) for state in s.palette]
 empty=np.array([not b for b in sh]);support=np.array([any(b[4]>.99 and b[0]<=.4 and b[3]>=.6 and b[2]<=.4 and b[5]>=.6 for b in bs) for bs in sh])
 a=s.after;walk=np.zeros(a.shape,bool);walk[1:-1]=support[a[:-2]]&empty[a[1:-1]]&empty[a[2:]]
 connection=np.zeros((3,3,3),bool);connection[:,1,1]=True
 for z,x in [(0,1),(2,1),(1,0),(1,2)]:connection[:,z,x]=True
 labels,n=label(walk,structure=connection);ids=set()
 for r in routes:
  pts=r.get('path',[r.get('start'),r.get('end')]);pts=[p for p in pts if p]
  for start,end in zip(pts,pts[1:]):
   length=max(abs(end[i]-start[i]) for i in range(3))
   for t in np.linspace(0,1,max(2,math.ceil(length)+1)):
    p=np.floor(np.array(start)*(1-t)+np.array(end)*t).astype(int);x,y,z=p-lo
    if 1<=y<a.shape[0]-1 and 1<=z<a.shape[1]-1 and 1<=x<a.shape[2]-1:
     ids.update(int(q) for q in labels[max(0,y-1):y+2,max(0,z-2):z+3,max(0,x-2):x+3].ravel() if q)
 reachable=np.isin(labels,list(ids));risks=[];guards=set();unknown=0
 for y,z,x in np.argwhere(reachable):
  if y<4 or y>=a.shape[0]-3 or z<2 or x<2 or z>=a.shape[1]-2 or x>=a.shape[2]-2:unknown+=1;continue
  if s.protected[y,z,x]:continue
  for dz,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
   nz,nx=z+dz,x+dx
   if walk[y-1:y+2,nz,nx].any():continue
   # A wall, a handrail, or an immediate lower tread is a real boundary.
   if not empty[a[y,nz,nx]] or not empty[a[y+1,nz,nx]]:continue
   if support[a[y-3:y,nz,nx]].any():continue
   box=(slice(y-1,y+2),nz,nx)
   if s.protected[box].any() or not empty[a[box]].all():continue
   pt=(int(nx+lo[0]),int(y+lo[1]),int(nz+lo[2]));guards.add(pt);risks.append({'from':[int(x+lo[0]),int(y+lo[1]),int(z+lo[2])],'unguarded_edge':pt})
 for x,y,z in sorted(guards):
  s.fill((x,y-1,z,x,y-1,z),STRUCT);s.fill((x,y,z,x,y+1,z),GLASS)
 return dict(reachable_floor_cells=int(reachable.sum()),components=len(ids),edge_guards=len(guards),cut_boundary_cells=unknown,risks=risks)

def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);scan.WORLD=MAIN;v.WORLD=REVIEW;v.OUT=OUT;p=v.Painter();walks=[];reports=[];contracts=[]
 routes=json.loads((MAIN/'quality_walk_cases.json').read_text())
 lo=(-72,-480,234);hi=(15,-435,422);s=scene(lo,hi)
 s.protect((-8,-474,278,15,-435,366))
 # The northern end of the low west gallery opens into the already-connected
 # duty lounge. Its second doorway at z=275 makes an actual short circulation loop.
 s.fill((-35,-463,268,-27,-462,271),STRUCT);s.fill((-35,-462,268,-27,-462,271),FLOOR)
 s.fill((-35,-461,268,-27,-458,271),AIR)
 s.path('west_lounge_through',[[ -28.5,-461,277.5],[-28.5,-461,269.5],[-39.5,-461,269.5],[-39.5,-461,275.5],[-28.5,-461,275.5]])
 # Finish the upper stair landing east of the retained flight, opening only
 # its two real approaches. All of the reported drop is now inside a room.
 s.hall('upper_south_landing',[(-10,-3,373,389)],-449,6,
        [(-10,-448,374,-10,-444,377),(-10,-448,381,-10,-444,385)])
 s.path('south_safe_landing',[[-14.5,-448,375.5],[-6.5,-448,375.5],[-6.5,-448,385.5],[-10.5,-448,383.5]])
 local=routes+s.walks;report=edges(s,lo,hi,local);report['region']='pyramid_west_and_south';reports.append(report)
 count=s.delta(p,'r22/through_access_and_all_reachable_edges');walks+=s.walks;contracts+=s.contract
 # Direct, legible gateway--station approach. Retire the exact detour envelope;
 # platform, native tracks, lift shaft and its north approach remain intact.
 lo=(-374,-480,708);hi=(-280,-456,796);s=scene(lo,hi)
 s.fill((-313,-469,728,-304,-460,769),AIR)
 s.fill((-335,-469,764,-304,-460,769),AIR)
 s.hall('arrival_direct',[(-341,-329,724,778)],-467,7,
        [(-341,-466,724,-337,-462,729),(-338,-466,778,-332,-462,778)])
 # Link to the existing north approach at y=-466, not the lift's moving doors.
 s.fill((-356,-468,724,-337,-468,729),STRUCT);s.fill((-356,-467,724,-337,-467,729),FLOOR);s.fill((-356,-466,724,-333,-462,729),AIR)
 s.belt('arrival_to_platform',-339,736,34,-467,axis='z',direction=False)
 s.belt('arrival_to_lift',-332,736,34,-467,axis='z',direction=True)
 s.path('gateway_shortcut',[[-359.5,-466,726.5],[-335.5,-466,726.5],[-335.5,-466,739.5],[-335.5,-466,777.5],[-330.5,-466,777.5]])
 reports.append(dict(region='gateway_station',retired_bounds=[-313,-469,728,-304,-460,769],**edges(s,lo,hi,[r for r in routes if not r['id'].startswith('nerv/arrival_platform_corridor')]+s.walks)))
 count+=s.delta(p,'r22/direct_gateway_station');walks+=s.walks;contracts+=s.contract
 for row in walks:row['id']=row['id'].replace('r21/','r22/',1)
 p.meta.update(walk_nodes=walks,sections=contracts,edge_audits=reports,changed_cells=count,retired_route_ids=['nerv/arrival_platform_corridor'])
 plan=p.save_plan('direct_station_and_safe_platforms')
 if apply:p.apply('direct_station_and_safe_platforms')
 (OUT/'access_contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
 print('R22 access',count,'cells;',sum(r['edge_guards'] for r in reports),'full-width edge guards; plan',plan)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
