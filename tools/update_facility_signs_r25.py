"""Arrow-only signs follow the measured R25 route graph and reachable readers."""
from pathlib import Path
import argparse,copy,gzip,json,math
import nbtlib,numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/signs';DIR={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}
def main(apply=False,refresh_only=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
 with gzip.open(WORLD/'nerv_routes_r24.json.gz','rt',encoding='utf8') as f:graph=json.load(f)
 nodes=np.asarray(graph['nodes'],dtype=np.int32);tree=cKDTree(nodes[:,:3]);goals=[('指挥室',0),('机库',1),('总部车站',2)]
 def near(point,radius=2):
  ids=tree.query_ball_point(point,radius);ids=[i for i in ids if abs(nodes[i,1]-point[1])<.55]
  return min(ids,key=lambda i:sum((nodes[i,:3]-point)**2)) if ids else None
 def arrows(node,face):
  nx,nz=DIR[face];texts=[]
  for title,g in goals:
   cursor=node
   for _ in range(6):
    step=int(nodes[cursor,3+g])
    if step==cursor:break
    cursor=step
   dx,dy,dz=nodes[cursor,:3]-nodes[node,:3];right=dx*nz-dz*nx;forward=-dx*nx-dz*nz
   arrow='→' if right>abs(forward)*.65 and right>0 else '←' if -right>abs(forward)*.65 and right<0 else '↑' if forward>=0 else '↶'
   if abs(dy)>2:arrow='↑ 电梯' if dy>0 else '↓ 电梯'
   texts.append(arrow+'  '+title)
  return texts
 tags=list(iter_block_entities(WORLD,v.DIM,(-80,-574,-300),(190,-334,545)));updated=[];new=[];held=[];occupied=[]
 for q,original in tags:
  if str(original.get('id',''))!='projectseele:station_departure_board' or not int(original.get('Wayfinding',0)) or 'MapRows' in original:continue
  state=read_box(WORLD,v.DIM,q,q)[q];t=copy.deepcopy(original);changed=False
  if '金字塔' in str(t.get('Route','')) and 'facing=' in state:
   face=state.split('facing=')[1].split(',')[0].split(']')[0];nx,nz=DIR[face]
   candidates=[near(np.array([q[0]+nx*2,Y,q[2]+nz*2]),3) for Y in range(q[1]-3,q[1]+1)]
   node=next((i for i in candidates if i is not None),None)
   if node is not None:
    for i,line in enumerate(arrows(node,face)):t['Row'+str(i)]=nbtlib.String(line)
    changed=True
  for key in ('Row0','Row1','Row2'):
   old=str(t.get(key,''));s=old
   for a,b in [('右转 →','→'),('← 左转','←'),('向前','↑'),('转身沿廊','↶'),('左转','←'),('右转','→')]:s=s.replace(a,b)
   if s!=old:t[key]=nbtlib.String(s);changed=True
  if changed and t!=original:p.update_block_entity(q,state,original,t,'r25/current_graph_arrow_signs');updated.append(q)
  occupied.append(q)
 # Both sides of every new stair link plus both new lift lobbies.
 connections=json.loads((ROOT/'artifacts/facility_r25/command_links/contract.json').read_text())['connections'];sites=[]
 for r in connections:
  sites.extend([(r['id']+'/gallery',r['start']),(r['id']+'/command',r['end'])])
 sites.extend([('east_lift/'+str(y),(73.5,y,260.5)) for y in (-448,-434,-420,-406,-392)])
 sites.extend([('observation_lift/'+str(y),(-28.5,y,-284.5)) for y in (-394,-367)])
 if refresh_only:sites=[]
 backing={'projectseele:nerv_wall_panel','projectseele:nerv_wall_datum','projectseele:nerv_structural_panel','projectseele:clear_glass','minecraft:light_gray_stained_glass','minecraft:gray_concrete','minecraft:black_concrete','minecraft:smooth_stone','minecraft:smooth_quartz'}
 for label,point in sites:
  sx,sy,sz=map(math.floor,point);cells=read_box(WORLD,v.DIM,(sx-8,sy-2,sz-8),(sx+8,sy+5,sz+8));choice=None
  for radius in range(1,6):
   for face,(nx,nz) in DIR.items():
    for shift in (0,-1,1,-2,2,-3,3):
     q=(sx-nx*radius+(shift if nz else 0),sy+1,sz-nz*radius+(shift if nx else 0));back=(q[0]-nx,q[1],q[2]-nz)
     if cells.get(q,'UNKNOWN').split('[')[0] not in AIR or cells.get(back,'UNKNOWN').split('[')[0] not in backing:continue
     if any(sum((q[k]-old[k])**2 for k in range(3))<4 for old in occupied):continue
     reader=np.array([q[0]+nx*2,sy,q[2]+nz*2]);node=near(reader,1)
     if node is None:continue
     if any(cells.get((int(reader[0]),sy+h,int(reader[2])),'UNKNOWN').split('[')[0] not in AIR|{'minecraft:light'} for h in (0,1)):continue
     choice=(q,face,node,reader.tolist());break
    if choice:break
   if choice:break
  if not choice:held.append(dict(site=label,point=point));continue
  q,face,node,reader=choice;state=f'projectseele:nerv_direction_panel[facing={face},wayfinding=true]';p.match((*q,*q),cells[q],state,'r25/reachable_new_junction_sign')
  tag=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2]),'Wayfinding':nbtlib.Byte(1),'Station':nbtlib.String(str(sy)+' 层'),'Route':nbtlib.String('金字塔通行导向'),'PlatformCentre':nbtlib.Long(0)})
  rows=arrows(node,face)
  for i,line in enumerate(rows):tag['Row'+str(i)]=nbtlib.String(line)
  p.block_entities[q]=tag;occupied.append(q);new.append(dict(site=label,position=q,facing=face,rows=rows,reader=reader))
 name='refreshed_arrow_wayfinding' if refresh_only else 'reachable_arrow_wayfinding'
 p.meta.update(updated=updated,new_boards=new,held=held,graph_nodes=len(nodes),walk_nodes=[]);p.save_plan(name)
 if apply:p.apply(name)
 (OUT/('refresh_contract.json' if refresh_only else 'contract.json')).write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Updated',len(updated),'new',len(new),'held',held)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--refresh-only',action='store_true');args=ap.parse_args();main(args.apply,args.refresh_only)
