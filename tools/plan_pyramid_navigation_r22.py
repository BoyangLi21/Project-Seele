"""Route signs use measured 3D walkable floors plus named lift landings."""
import argparse,heapq,json,math
from pathlib import Path
import numpy as np,nbtlib
from scipy import sparse
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
import regional_voxels as v
import scan_regional_completion as scan
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/access_r22/navigation'
LO=(-76,-474,235);HI=(157,-356,474)
def main(apply=False,output=None):
 global OUT
 if output is not None:OUT=Path(output)
 OUT.mkdir(parents=True,exist_ok=True);scan.WORLD=WORLD;v.WORLD=WORLD;v.OUT=OUT
 a,pal=scan.volume(LO,HI);measured=a.copy();door_ports=[]
 # Registered moving doors are real controlled connections. A static snapshot
 # of their closed barrier must not make the entire command suite disappear
 # from the navigation graph. No arbitrary glass or barrier is opened here.
 marker=WORLD/'.projectseele_command_sliding_doors_r01.json';air=pal.index('minecraft:air')
 if marker.exists():
  for door in json.loads(marker.read_text()).get('doors',[]):
   included=[]
   for x,y,z in door.get('aperture',[]):
    if all(LO[i]<=q<=HI[i] for i,q in enumerate((x,y,z))):
     current=pal[a[y-LO[1],z-LO[2],x-LO[0]]]
     if current in ('minecraft:barrier','minecraft:air'):a[y-LO[1],z-LO[2],x-LO[0]]=air;included.append((x,y,z))
   if included:door_ports.append(dict(id=door['id'],aperture=included,buttons=door.get('buttons',[])))
 shapes={v.canonical_state(k):s for k,s in json.loads((WORLD/'native_collision_shapes.json').read_text()).items()}
 def shape(s):
  if s in shapes:return shapes[s]
  if s.split('[')[0] in AIR|{'minecraft:light'}:return []
  if s.startswith('mtr:escalator_step') and 'orientation=flat' in s:return [[0,0,0,1,.9375,1]]
  return [[0,0,0,1,1,1]]
 sh=[shape(s) for s in pal]
 def overlaps(b,height):return b[3]>.205 and b[0]<.795 and b[5]>.205 and b[2]<.795 and b[4]>.01 and b[1]<height
 free=np.array([not any(overlaps(b,1) for b in bs) for bs in sh]);head=np.array([not any(overlaps(b,.79) for b in bs) for bs in sh]);floor=np.array([any(.9<=b[4]<=1.001 and b[0]<=.5<=b[3] and b[2]<=.5<=b[5] for b in bs) for bs in sh]);stairs=np.array(['stairs' in s or 'escalator_step' in s for s in pal])
 floor&=np.array([not any(t in s for t in ('_wall[','_fence[','_bars[','_sign[','station_departure_board','nerv_direction_panel','escalator_side')) for s in pal])
 walk=np.zeros(a.shape,bool);walk[1:-1]=floor[a[:-2]]&free[a[1:-1]]&head[a[2:]]
 # Bedrock, ceilings and roofs are not assigned a use; only graph-connected,
 # measured public route nodes will become sign sites.
 index=np.full(a.shape,-1,np.int32);index[walk]=np.arange(walk.sum(),dtype=np.int32);coords=np.argwhere(walk);n=len(coords);tree=cKDTree(coords[:,[2,0,1]]+np.array(LO))
 def nearest(point,radius=6):
  candidates=tree.query_ball_point(point,radius);same=[i for i in candidates if abs(coords[i,0]+LO[1]-point[1])<.55]
  if not same:return None
  return min(same,key=lambda i:sum((coords[i,[2,0,1]]+LO-np.array(point))**2))
 rows=[];cols=[];weights=[]
 for dy in (-1,0,1):
  for dz,dx in ((0,1),(0,-1),(1,0),(-1,0)):
   aa=tuple(slice(max(0,-d),min(size,size-d)) for size,d in zip(a.shape,(dy,dz,dx)));bb=tuple(slice(max(0,d),min(size,size+d)) for size,d in zip(a.shape,(dy,dz,dx)))
   keep=walk[aa]&walk[bb]
   if dy:
    support_stair=np.zeros(a.shape,bool);support_stair[1:]=stairs[a[:-1]];keep&=support_stair[aa]|support_stair[bb]
   rows.extend(index[aa][keep]);cols.extend(index[bb][keep]);weights.extend([math.sqrt(1+dy*dy)]*int(keep.sum()))
 landings=[]
 for y in (-448,-423,-419,-409):
  i=nearest((12,y,258),7)
  if i is not None:landings.append((y,i))
 for (y,i),(Y,j) in zip(landings,landings[1:]):rows.extend([i,j]);cols.extend([j,i]);weights.extend([24+abs(Y-y)/.85]*2)
 graph=sparse.coo_matrix((weights,(rows,cols)),shape=(n,n)).tocsr()
 # Door 18 is the documented public entrance to the command hall. The old
 # target was inside the glazed operator island beside Misato, not its entry.
 goals=[('指挥室入口',(28,-406,269)),('机库',(118,-442,240)),('总部火车站',(30,-466,451))];gids=[nearest(g,8) for _,g in goals]
 if any(i is None for i in gids):raise RuntimeError(('Missing measured destination floor',list(zip(goals,gids))))
 distances,predecessors=dijkstra(graph,directed=True,indices=gids,return_predecessors=True)
 reachable=np.zeros(a.shape,bool);reachable[tuple(coords[np.isfinite(distances).all(axis=0)].T)]=True
 np.savez_compressed(OUT/'measured_public_space.npz',blocks=measured,palette=np.asarray(pal),reachable=reachable,lo=LO,hi=HI)
 sites=[]
 for y in (-461,-448):
  for x in (-30,89):
   for z in (270,276,308,340,372,399):sites.append((x,y,z))
 sites += [(30,-461,425),(-30,-461,425),(89,-461,425),(-7,-448,375),(72,-448,375),(110,-448,255),(118,-442,244),(30,-466,446)]
 for y in (-434,-420,-406,-392):
  for x in (-5,76):
   for z in (283,315,346,371):sites.append((x,y,z))
  sites.append((30,y,371))
 for y in (-378,-364):sites += [(10,y,300),(10,y,329),(10,y,344),(-1,y,367),(34,y,367),(68,y,367)]
 p=v.Painter();placed=[];held=[];used=[];covered=[]
 def block(q):
  x,y,z=q
  if not all(LO[i]<=q[i]<=HI[i] for i in range(3)):return 'UNKNOWN'
  return pal[measured[y-LO[1],z-LO[2],x-LO[0]]]
 backing={'projectseele:nerv_wall_panel','projectseele:nerv_structural_panel','projectseele:nerv_floor_panel','projectseele:nerv_machine_panel','projectseele:nerv_shaft_panel','projectseele:clear_glass','minecraft:gray_stained_glass','minecraft:light_gray_stained_glass','minecraft:gray_concrete','minecraft:light_gray_concrete','minecraft:smooth_stone','minecraft:smooth_quartz'}
 backing|={'projectseele:nerv_wall_datum','minecraft:polished_deepslate','projectseele:nerv_hazard_paving'}
 empty=AIR|{'minecraft:light','minecraft:oak_wall_sign','projectseele:station_departure_board','projectseele:nerv_direction_panel'}
 def protected(q):return 6<=q[0]<=52 and -445<=q[1]<=-388 and 262<=q[2]<=365
 def clear_ray(a,b):
  for t in np.linspace(.05,.95,max(3,int(np.linalg.norm(np.array(a)-b)*4))):
   if block(tuple(np.floor(np.array(a)*(1-t)+np.array(b)*t).astype(int))).split('[')[0] not in empty:return False
  return True
 for requested in sites:
  at=nearest(requested,5)
  if at is None or not np.isfinite(distances[:,at]).all():held.append(dict(site=requested,reason='missing connected floor',reachable=[] if at is None else np.isfinite(distances[:,at]).tolist()));continue
  site=tuple(map(int,coords[at,[2,0,1]]+LO));choice=None;support=[];compact=False
  shared=next((i for i,r in enumerate(placed) if r['site'][1]==site[1] and np.linalg.norm(np.array(r['site'])-site)<5 and clear_ray(np.array(site)+[.5,1.62,.5],np.array(r['position'])+[.5,.7,.5])),None)
  if shared is not None:covered.append(dict(site=site,board=shared));continue
  for radius in range(2,8):
   if choice:break
   for face,nx,nz in [('north',0,-1),('south',0,1),('west',-1,0),('east',1,0)]:
    for shift in (0,-1,1,-2,2):
     q=(site[0]-nx*radius+(shift if nz else 0),site[1]+2,site[2]-nz*radius+(shift if nx else 0))
     if any(sum((q[k]-old[k])**2 for k in range(3))<36 for old in used):continue
     front=[(q[0]+(u if nz else 0),q[1]+h,q[2]+(u if nx else 0)) for u in (-1,0,1) for h in (0,1)];back=[(x-nx,y,z-nz) for x,y,z in front]
     if any(protected(t) for t in front):continue
     if not all(block(t).split('[')[0] in empty for t in front):continue
     if not all(block(t).split('[')[0] in backing for t in back):continue
     # A stair can put a person's head higher than the nearby level floor.
     # Reserve the whole model footprint against every measured walking level.
     if any(walk[Y-LO[1],Z-LO[2],X-LO[0]] for X,_,Z in front for Y in range(max(LO[1],q[1]-1),min(HI[1],q[1]+1)+1)):continue
     read=nearest((q[0]+nx*2,site[1],q[2]+nz*2),1.5)
     if read is None or not np.isfinite(distances[:,read]).all() or not clear_ray(np.array(coords[read,[2,0,1]]+LO)+[.5,1.62,.5],np.array(q)+[.5,.5,.5]):continue
     choice=q,face,nx,nz;break
    if choice:break
  # A one-block panel can fit a real narrow-corridor wall without extending
  # invisibly into a junction. Reader position must belong to the same graph.
  if not choice:
   for radius in range(1,8):
    if choice:break
    for face,nx,nz in [('north',0,-1),('south',0,1),('west',-1,0),('east',1,0)]:
     for shift in (0,-1,1,-2,2,-3,3):
      q=(site[0]-nx*radius+(shift if nz else 0),site[1]+1,site[2]-nz*radius+(shift if nx else 0));back=(q[0]-nx,q[1],q[2]-nz)
      if protected(q) or block(q).split('[')[0] not in empty or block(back).split('[')[0] not in backing:continue
      if any(sum((q[k]-old[k])**2 for k in range(3))<9 for old in used):continue
      read=nearest((q[0]+nx*2,site[1],q[2]+nz*2),1.5)
      if read is None or not np.isfinite(distances[:,read]).all() or not clear_ray(np.array(coords[read,[2,0,1]]+LO)+[.5,1.62,.5],np.array(q)+[.5,.5,.5]):continue
      choice=q,face,nx,nz;compact=True;break
     if choice:break
  # Open halls receive a suspended panel only where rods meet a measured
  # structural ceiling; nothing is mounted in free space.
  if not choice:
   for shift in (0,-2,2,-4,4):
    if choice:break
    for face,nx,nz in [('north',0,-1),('south',0,1),('west',-1,0),('east',1,0)]:
     q=(site[0]+(shift if nz else 0),site[1]+2,site[2]+(shift if nx else 0))
     front=[(q[0]+(u if nz else 0),q[1]+h,q[2]+(u if nx else 0)) for u in (-1,0,1) for h in (0,1)]
     if any(protected(t) or block(t).split('[')[0] not in empty for t in front):continue
     rods=[]
     for u in (-1,1):
      x,z=q[0]+(u if nz else 0),q[2]+(u if nx else 0);line=[]
      for y in range(q[1]+2,min(q[1]+14,HI[1])):
       b=block((x,y,z)).split('[')[0]
       if b in backing:break
       if b not in AIR|{'minecraft:light'}:line=[];break
       line.append((x,y,z))
      else:line=[]
      if not line:rods=[];break
      rods+=line
     if not rods:continue
     read=nearest((q[0]+nx*3,site[1],q[2]+nz*3),1.5)
     if read is None or not np.isfinite(distances[:,read]).all() or not clear_ray(np.array(coords[read,[2,0,1]]+LO)+[.5,1.62,.5],np.array(q)+[.5,.5,.5]):continue
     support=rods;choice=q,face,nx,nz;break
  if not choice:held.append(dict(site=requested,reason='no verified wall or structural ceiling mount'));continue
  q,face,nx,nz=choice;texts=[];destinations=[]
  at=read;site=tuple(map(int,coords[at,[2,0,1]]+LO))
  for gi,(title,_) in enumerate(goals):
   steps=[at];cursor=at
   while len(steps)<18 and cursor!=gids[gi]:
    cursor=int(predecessors[gi,cursor])
    if cursor<0:break
    steps.append(cursor)
   dst=coords[steps[min(5,len(steps)-1)],[2,0,1]]+LO;delta=dst-np.array(site);right=delta[0]*nz-delta[2]*nx;forward=-delta[0]*nx-delta[2]*nz
   direction='右转 →' if right>abs(forward)*.65 and right>0 else '← 左转' if -right>abs(forward)*.65 and right<0 else '向前' if forward>0 else '转身沿廊'
   if abs(delta[1])>2:direction='乘直梯上行' if delta[1]>0 else '乘直梯下行'
   texts.append(f'{direction} · {title}');destinations.append(dict(name=title,next=dst.tolist(),distance=round(float(distances[gi,at]),1)))
  state=f'projectseele:{"nerv_direction_panel" if compact else "station_departure_board"}[facing={face},wayfinding=true]';p.match((*q,*q),block(q),state,'r23/three_destination_junction_sign')
  for pole in support:p.match((*pole,*pole),block(pole),'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]','r23/measured_ceiling_suspension')
  tag=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2]),'Wayfinding':nbtlib.Byte(1),'Station':nbtlib.String('NERV 总部 · '+str(site[1])+' 层'),'Route':nbtlib.String('金字塔通行导向'),'PlatformCentre':nbtlib.Long(0)})
  for i,t in enumerate(texts):tag['Row'+str(i)]=nbtlib.String(t)
  p.block_entities[q]=tag;used.append(q);placed.append(dict(site=site,requested=requested,position=q,facing=face,compact=compact,suspension=support,rows=texts,destinations=destinations))
 p.meta.update(boards=placed,held=held,shared_boards=covered,walkable_nodes=n,registered_operable_doors=door_ports,native_lift_landings=[dict(y=y,node=(coords[i,[2,0,1]]+LO).tolist()) for y,i in landings],goals=[dict(name=label,node=(coords[i,[2,0,1]]+LO).tolist()) for (label,_),i in zip(goals,gids)])
 p.save_plan('measured_pyramid_junctions')
 if apply:p.apply('measured_pyramid_junctions')
 (OUT/'junctions.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
 print('Measured graph',n,'signs',len(placed),'held',len(held),'operable doors',len(door_ports));print(json.dumps(held,ensure_ascii=False))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--output',type=Path);args=ap.parse_args();main(args.apply,args.output)
