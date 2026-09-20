"""Move obstructed junction panels onto the public side of their measured walls."""
from pathlib import Path
import copy,json,math
import numpy as np,nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
ROOT=v.ROOT;ART=ROOT/'artifacts/facility_r26';WORLD=ROOT/'run/saves/SEELE_R26_REVIEW';OUT=ART/'sign_sightlines';DIR={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}

def main():
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();data=json.loads((ART/'signage/contract.json').read_text());results=json.loads((WORLD/'quality_native_walk_results.json').read_text());ids={q['id'] for q in results if q['status']=='station_diagram_obstructed'};occupied=set();moves=[]
 for index,row in enumerate(data['created'],1):
  if 'r26/sign/'+str(index) not in ids or row['platform'] is not None:continue
  oldq=tuple(row['position']);sx,y,sz=row['reader'];cells=read_box(WORLD,v.DIM,(sx-9,y-1,sz-9),(sx+9,y+5,sz+9));tags=dict(iter_block_entities(WORLD,v.DIM,(sx-9,y,sz-9),(sx+9,y+4,sz+9)));tag=tags[oldq];choice=None;candidates=[]
  def at(q):return cells.get(q,'UNKNOWN')
  for x in range(sx-7,sx+8):
   for z in range(sz-7,sz+8):
    q=(x,y+2,z)
    if q in tags or q in occupied or at(q).split('[')[0] not in AIR:continue
    for face,(nx,nz) in DIR.items():
     back=(x-nx,y+2,z-nz);reader=(x+nx*2,y,z+nz*2)
     if at(back).split('[')[0] in AIR or any(k in at(back) for k in ('door','button','sign','chair','stool','barrier','UNKNOWN')):continue
     if at((reader[0],y-1,reader[2])).split('[')[0] in AIR or any(at((reader[0],y+j,reader[2])).split('[')[0] not in AIR|{'minecraft:light'} for j in (0,1)):continue
     eye=np.array(reader)+[.5,1.62,.5];target=np.array(q)+[.5-.4*nx,.5,.5-.4*nz];clear=True
     for t in np.linspace(0,1,32):
      cell=tuple(np.floor(eye*(1-t)+target*t).astype(int))
      if cell==q:continue
      if at(cell).split('[')[0] not in AIR|{'minecraft:light'}:clear=False;break
     if clear:candidates.append((np.linalg.norm(np.array(reader)-[sx,y,sz])+.1*np.linalg.norm(np.array(q)-oldq),q,face,reader))
  assert candidates,('No readable wall face',row)
  _,q,face,reader=min(candidates);old=at(oldq);p.match((*oldq,*oldq),old,'minecraft:air','r26/remove_obscured_junction_panel');newstate='projectseele:nerv_direction_panel[facing='+face+',wayfinding=true]';p.match((*q,*q),at(q),newstate,'r26/public_side_junction_panel');newtag=copy.deepcopy(tag)
  for key,value in zip(('x','y','z'),q):newtag[key]=nbtlib.Int(value)
  p.block_entities[q]=newtag;occupied.add(q);row['position']=list(q);row['reader']=list(reader);row['facing']=face
  for case in data['walk_nodes']:
   if case['id']=='r26/sign/'+str(index):case['readingBoard']=list(q);case['path']=[[reader[0]+.5,y,reader[2]+.5]]*2
  moves.append(dict(id=index,before=oldq,after=q,reader=reader))
 p.meta.update(moves=moves);p.apply('public_side_readable_panels');(ART/'signage/contract.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'contract.json').write_text(json.dumps(p.meta,indent=2));print('Relocated unreadable junction panels',len(moves))
if __name__=='__main__':main()
