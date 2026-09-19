"""Four physical interchange signs point along the existing two escalator links."""
from pathlib import Path
import json,math,nbtlib
import regional_voxels as v
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/transfer_signs'
def main():
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();placed=[];held=[]
 links=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['transfer_links']
 for link in links:
  path=link['path'];sx,sy,sz=map(math.floor,path[0]);up=path[-1][1]>path[0][1]
  target=('R1' if up else 'S1') if 'hakone' in link['id'] else ('S1' if up else 'R1')
  station='新箱根中央' if 'hakone' in link['id'] else '湾岸防卫区'
  a=read_box(WORLD,v.DIM,(sx-9,sy-1,sz-9),(sx+9,sy+5,sz+9));choice=None
  for distance in range(1,7):
   for face,nx,nz in [('north',0,-1),('south',0,1),('east',1,0),('west',-1,0)]:
    for side in (0,1,-1,2,-2,3,-3):
     q=(sx-nx*distance+(side if nz else 0),sy+1,sz-nz*distance+(side if nx else 0));back=(q[0]-nx,q[1],q[2]-nz);r=(q[0]+nx*2,sy,q[2]+nz*2)
     if a.get(q,'?').split('[')[0] not in AIR or a.get(back,'?').split('[')[0] not in {'projectseele:clear_glass','projectseele:nerv_wall_panel','projectseele:nerv_structural_panel','minecraft:light_gray_concrete','minecraft:gray_concrete','minecraft:gray_stained_glass','minecraft:light_gray_stained_glass'}:continue
     if a.get((r[0],sy-1,r[2]),'?').split('[')[0] in AIR|{'?','minecraft:water'} or any(a.get((r[0],sy+h,r[2]),'?').split('[')[0] not in AIR for h in (0,1)):continue
     choice=(q,face,nx,nz,r);break
    if choice:break
   if choice:break
  if choice is None:held.append(link['id']);continue
  q,face,nx,nz,reader=choice;dx=path[min(5,len(path)-1)][0]-path[0][0];dz=path[min(5,len(path)-1)][2]-path[0][2];right=dx*nz-dz*nx;forward=-dx*nx-dz*nz
  arrow='→' if right>abs(forward) else '←' if -right>abs(forward) else '↑' if forward>=0 else '↶'
  state=f'projectseele:nerv_direction_panel[facing={face},wayfinding=true]';p.match((*q,*q),a[q],state,'r25/explicit_interchange_escalator_direction')
  rows=[arrow+'  换乘 '+target,('↑ 上层站台' if up else '↓ 下层站台'),'双向联络扶梯'];tag=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2]),'Wayfinding':nbtlib.Byte(1),'Station':nbtlib.String(station),'Route':nbtlib.String('S1 ↔ R1'),'PlatformCentre':nbtlib.Long(0)})
  for i,line in enumerate(rows):tag['Row'+str(i)]=nbtlib.String(line)
  p.block_entities[q]=tag;placed.append(dict(id=link['id'],position=q,facing=face,reader=reader,rows=rows))
 assert not held,held
 p.meta.update(boards=placed,walk_nodes=[]);p.apply('physical_interchange_arrows')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Transfer direction signs',len(placed))
if __name__=='__main__':main()
