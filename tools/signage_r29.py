"""Route-facing signs from native train paths and measured floor/lift navigation."""
from pathlib import Path
from collections import defaultdict,Counter
import copy,gzip,json,math
import nbtlib,numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R29_REVIEW';ART=ROOT/'artifacts/facility_r29';OUT=ART/'signage'
FLOORS={-461:'B1 交通接驳层',-448:'1F 总部门厅',-434:'2F 勤务联络层',-420:'3F 科研联络层',-406:'4F 作战指挥室',-392:'5F 指挥室上层',-378:'6F 上部办公层',-364:'7F 上部观察层',-566:'终极教条前厅',-423:'科研联络层',-419:'科研联络层',-409:'作战指挥室',-442:'机库交通层',-394:'机库登机层',-370:'机库观察层',-367:'三机观察廊'}
DIR={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}

def main(refresh=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();occupied=set();created=[];updated=[];held=[];walks=[]
 native=json.loads((WORLD/'native_transit_r26.json').read_text());platforms={q['id']:q for q in native['platforms']};routes=[r for r in native['routes'] if r['transportMode']=='TRAIN']
 def centre(q):return np.array([(q['position1'][k]+q['position2'][k])/2 for k in ('x','y','z')])
 def station(pid):
  c=centre(platforms[pid]);matches=[]
  for s in native['stations']:
   if all(min(s['position1'][k],s['position2'][k])<=n<=max(s['position1'][k],s['position2'][k]) for k,n in zip(('x','y','z'),c)):
    matches.append((math.prod(abs(s['position1'][k]-s['position2'][k])+1 for k in ('x','y','z')),s['name'].split('|')[0]))
  assert matches,pid;return min(matches)[1]
 route_for={q['platformId']:r for r in routes for q in r['routePlatformData']};names={pid:station(pid) for pid in route_for}
 def outbound(pid):
  route=route_for[pid];seq=[q['platformId'] for q in route['routePlatformData']];i=seq.index(pid);following=(i+1)%len(seq)
  while names[seq[following]]==names[pid]:following=(following+1)%len(seq)
  order=list(dict.fromkeys(names[k] for k in seq));nxt=names[seq[following]]
  if order.index(nxt)<order.index(names[pid]):order.reverse()
  vector=None
  for depot in native['depots']:
   if route['id'] not in depot['routeIds']:continue
   path=depot['path']
   for j,leg in enumerate(path):
    if leg.get('savedRailBaseId')!=pid:continue
    for skip in range(1,len(path)+1):
     following_leg=path[(j+skip)%len(path)];a=following_leg['startPosition'];b=following_leg['endPosition'];dx,dz=b['x']-a['x'],b['z']-a['z']
     if dx or dz:vector=(dx,dz);break
    if vector:break
   if vector:break
  assert vector is not None,('No real departure path',pid)
  return route['routeNumber'],nxt,order,vector
 def diagram(pid,face):
  line,nxt,order,(dx,dz)=outbound(pid);nx,nz=DIR[face];right=dx*nz-dz*nx;forward=-dx*nx-dz*nz
  arrow='→' if right>abs(forward) else '←' if -right>abs(forward) else '↑' if forward>=0 else '↓'
  rows=['行车方向 '+arrow+'  下一站 '+nxt]+[('● '+s+'  本站') if s==names[pid] else '│ '+s for s in order]+['末站折返 · 每分钟一班']
  return line,rows
 with gzip.open(WORLD/'nerv_routes_r24.json.gz','rt',encoding='utf8') as stream:graph=json.load(stream)
 nodes=np.asarray(graph['nodes'],dtype=np.int32);tree=cKDTree(nodes[:,:3]);goals={q['id']:i for i,q in enumerate(graph['goals'])}
 def nearest(point,radius=4):
  ids=tree.query_ball_point(point,radius);ids=[i for i in ids if abs(nodes[i,1]-point[1])<.55]
  return min(ids,key=lambda i:np.linalg.norm(nodes[i,:3]-point)) if ids else None
 def guidance(point,face):
  node=nearest(np.asarray(point));assert node is not None,point;nx,nz=DIR[face];out=[]
  for label,key in [('指挥室','command'),('机库','hangars'),('总部车站','station')]:
   goal=goals[key];cursor=node;first=node;lift=None
   for count in range(2500):
    nxt=int(nodes[cursor,3+goal])
    if nxt==cursor:break
    if count<5:first=nxt
    if abs(nodes[nxt,1]-nodes[cursor,1])>2:lift=int(nodes[nxt,1]);break
    cursor=nxt
   dx,dy,dz=nodes[first,:3]-nodes[node,:3];right=dx*nz-dz*nx;forward=-dx*nx-dz*nz
   arrow='→' if right>abs(forward)*.65 else '←' if -right>abs(forward)*.65 else '↑' if forward>=0 else '↶'
   if abs(dy)>2:arrow='↑' if dy>0 else '↓'
   out.append(arrow+' '+('直梯 '+FLOORS.get(lift,'目标楼层')+' → ' if lift is not None else '')+label)
  return out
 shapes=json.loads((WORLD/'native_collision_shapes.json').read_text())
 def support(state):
  if state.split('[')[0] in AIR or any(s in state for s in ('water','lcl','door','barrier','sign','chair','stool','escalator_side')):return False
  return any(b[0]<=.3 and b[3]>=.7 and b[2]<=.3 and b[5]>=.7 and b[4]>=.9 for b in shapes.get(state,[[0,0,0,1,1,1]]))
 empty=AIR|{'minecraft:light'}
 def place(point,title,station_text,rowmaker,preferred=None,pid=None,compact=False):
  x,y,z=map(int,np.floor(point));lo=(x-9,y-2,z-9);hi=(x+9,y+13,z+9);cells=read_box(WORLD,v.DIM,lo,hi);tags=dict(iter_block_entities(WORLD,v.DIM,lo,hi));choice=None
  def st(q):return cells.get(q,'UNKNOWN')
  faces=[preferred]+[d for d in DIR if d!=preferred] if preferred else list(DIR)
  for distance in range(1,9):
   if choice:break
   for face in faces:
    nx,nz=DIR[face]
    for shift in (0,-2,2,-4,4):
     q=(x-nx*distance+(shift if nz else 0),y+2,z-nz*distance+(shift if nx else 0));width=(0,) if compact else (-1,0,1)
     front=[(q[0]+(u if nz else 0),q[1]+h,q[2]+(u if nx else 0)) for u in width for h in (0,1)]
     if any(pos in occupied or pos in tags or st(pos).split('[')[0] not in empty for pos in front):continue
     reader=(q[0]+nx*2,y,q[2]+nz*2)
     if not support(st((reader[0],y-1,reader[2]))) or any(st((reader[0],y+h,reader[2])).split('[')[0] not in empty for h in (0,1)):continue
     if compact and nearest(reader,1.5) is None:continue
     back=[(X-nx,Y,Z-nz) for X,Y,Z in front];rods=[]
     if not all(support(st(pos)) for pos in back):
      if compact:continue
      good=True
      for u in (-1,1):
       X,Z=q[0]+(u if nz else 0),q[2]+(u if nx else 0);rod=[]
       for Y in range(q[1]+2,y+13):
        state=st((X,Y,Z))
        if support(state):break
        if state.split('[')[0] not in empty:good=False;break
        rod.append((X,Y,Z))
       else:good=False
       if not good:break
       rods+=rod
      if not good:continue
     choice=q,face,reader,front,rods;break
    if choice:break
  if choice is None:held.append(dict(title=title,point=point));return
  q,face,reader,front,rods=choice;state=f'projectseele:{"nerv_direction_panel" if compact else "station_departure_board"}[facing={face},wayfinding=true]';p.match((*q,*q),st(q),state,'r26/visible_supported_sign')
  for pos in rods:p.match((*pos,*pos),st(pos),'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]','r26/sign_ceiling_support')
  tag=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2]),'Wayfinding':nbtlib.Byte(1),'Route':nbtlib.String(title),'Station':nbtlib.String(station_text),'PlatformCentre':nbtlib.Long(0)})
  rows=rowmaker(reader,face)
  if pid is not None:tag['NativePlatformId']=nbtlib.Long(pid);tag['MapRows']=nbtlib.List[nbtlib.String]([nbtlib.String(t) for t in rows])
  else:
   for i,t in enumerate(rows[:3]):tag['Row'+str(i)]=nbtlib.String(t)
  p.block_entities[q]=tag;occupied.update(front+rods);created.append(dict(position=q,facing=face,reader=reader,title=title,rows=rows,platform=pid))
  walks.append(dict(id='r26/sign/'+str(len(created)),path=[[reader[0]+.5,y,reader[2]+.5],[reader[0]+.5,y,reader[2]+.5]],readingBoard=list(q),readingWayfinding=pid is None))
 # Correct both original route maps and live departure-board platform identities.
 alltags={}
 for pid in route_for:
  c=centre(platforms[pid]);x,y,z=map(int,c);length=int(max(abs(platforms[pid]['position1'][k]-platforms[pid]['position2'][k]) for k in ('x','z'))/2)+28
  alltags.update(iter_block_entities(WORLD,v.DIM,(x-length,y-35,z-length),(x+length,y+10,z+length)))
 for q,old in alltags.items():
  if str(old.get('id',''))!='projectseele:station_departure_board':continue
  pid=int(old.get('NativePlatformId',-1))
  if pid not in route_for:continue
  candidates=[k for k in route_for if names[k]==names[pid] and route_for[k]['routeNumber']==route_for[pid]['routeNumber']]
  wanted=min(candidates,key=lambda k:np.linalg.norm((centre(platforms[k])-q)*[1,.1,1]))
  state=read_box(WORLD,v.DIM,q,q)[q];face=state.split('facing=')[1].split(',')[0].split(']')[0];tag=copy.deepcopy(old);tag['NativePlatformId']=nbtlib.Long(wanted)
  if 'MapRows' in tag:
   line,rows=diagram(wanted,face);tag['MapRows']=nbtlib.List[nbtlib.String]([nbtlib.String(s) for s in rows]);tag['Route']=nbtlib.String(line+' 全线站序 / 行车方向')
  if tag!=old:p.update_block_entity(q,state,old,tag,'r26/native_platform_direction');updated.append(dict(position=q,old_platform=pid,platform=wanted))
 # Each physical platform gets another readable diagram near its centre.
 for pid in ([] if refresh else route_for):
  c=centre(platforms[pid]);x,y,z=map(int,c);horizontal=platforms[pid]['position1']['x']!=platforms[pid]['position2']['x']
  for side in (-1,1):
   point=[x,y+1,z+side*7] if horizontal else [x+side*7,y+1,z]
   before=len(created);line=route_for[pid]['routeNumber'];place(point,line+' 全线站序 / 行车方向',names[pid],lambda _,face,k=pid:diagram(k,face)[1],pid=pid)
   if len(created)>before:break
 # Refresh all retained pyramid direction panels, then cover room exits and lift mouths.
 for q,old in iter_block_entities(WORLD,v.DIM,(-80,-474,230),(158,-355,475)):
  if str(old.get('id',''))!='projectseele:station_departure_board' or '金字塔' not in str(old.get('Route','')):continue
  state=read_box(WORLD,v.DIM,q,q)[q];face=state.split('facing=')[1].split(',')[0].split(']')[0];nx,nz=DIR[face];node=None
  for Y in range(q[1]-5,q[1]+1):
   node=nearest((q[0]+nx*2,Y,q[2]+nz*2),3)
   if node is not None:break
  if node is None:continue
  tag=copy.deepcopy(old);rows=guidance(nodes[node,:3],face);tag['Station']=nbtlib.String(FLOORS.get(int(nodes[node,1]),'设施联络层'))
  for i,line in enumerate(rows):tag['Row'+str(i)]=nbtlib.String(line)
  if tag!=old:p.update_block_entity(q,state,old,tag,'r26/floor_lift_wayfinding');updated.append(dict(position=q,kind='floor_lift'))
 rooms=json.loads((WORLD/'spatial_contract_r23.json').read_text())['room_entries'];sites=[]
 for room in rooms:
  x,y,z=room['entry'];X,xx,Z,zz=room['bounds'];face='west' if x==xx else 'east' if x==X else 'north' if z==zz else 'south';nx,nz=DIR[face];sites.append(([x-nx*3,y,z-nz*3],face,room['id']))
 for y in (-461,-448,-434,-420,-406,-392,-378,-364):sites.append(([66,y,309],'north','本层直梯'))
 for y in (-434,-420,-406,-392):
  for x in (-4,76):sites.extend([([x,y,283],None,'联络路口'),([x,y,371],None,'联络路口')])
 for point,face,label in ([] if refresh else sites):
  node=nearest(np.asarray(point),6)
  if node is None:held.append(dict(title=label,point=point));continue
  place(nodes[node,:3].tolist(),'金字塔 · 楼层导引',FLOORS.get(int(nodes[node,1]),'设施联络层'),guidance,face,compact=True)
 for point in ([] if refresh else ([30,-461,476],[30,-466,476],[30,-466,451],[30,-466,509])):
  node=nearest(np.asarray(point),7)
  if node is not None:place(nodes[node,:3].tolist(),'NERV TOKYO-3','总部交通枢纽',guidance)
 p.meta.update(created=created,updated=updated,held=held,walk_nodes=walks,native_source='native_transit_r26.json / depot path after the real platform stop')
 p.apply('refresh_floor_lift_signs' if refresh else 'native_direction_and_floor_lift_signs');(OUT/('refresh_contract.json' if refresh else 'contract.json')).write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
 print('New signs',len(created),'corrected',len(updated),'unplaced candidates',len(held),flush=True)
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--refresh-only',action='store_true');main(parser.parse_args().refresh_only)
