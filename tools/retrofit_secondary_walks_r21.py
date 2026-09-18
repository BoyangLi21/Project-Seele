"""High-ceiling galleries are indoors even when the roof is above 12 m."""
from pathlib import Path
import json
import regional_voxels as v
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R21_REVIEW';OUT=ROOT/'artifacts/world_repair_r21/global_walkways'
def main():
 v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();rows=[]
 selected={'r03/continuous/pyramid_to_cage_wait','r03/continuous/cage_gallery_-12','hq/lobby/cross','nerv/arrival_spine','r04/terminal_dogma/west','r04/terminal_dogma/east','r04/terminal_dogma/rear','r09/dogma/restored_front_gallery','r07/secret/continuous_staff_to_plug','r20/gallery/lower_spine'}
 survey=json.loads((OUT.parent/'global_corridor_sections.json').read_text(encoding='utf8'))['segments'];seen=set()
 for r in survey:
  if r['id'] not in selected or r['status']=='enclosed_corridor':continue
  x,y,z=r['start'];X,Y,Z=r['end'];axis=r['axis'];f=y-1
  if y==-394:continue # retained cage mechanisms need the full MTR lanes already in place
  if y==-442:continue # platform edge, not a through corridor
  bounds=((min(x,X)-3,f,min(z,Z)-3),(max(x,X)+3,f+3,max(z,Z)+3));data=read_box(WORLD,v.DIM,*bounds);count=0
  for n in range(6,r['length']-5):
   if n%36<6:continue
   a=x+(n if axis=='x' else 0);c=z+(n if axis=='z' else 0);pair=[]
   for side in (-1,1):
    xx=a+(side if axis=='z' else 0);zz=c+(side if axis=='x' else 0);pos=(xx,f,zz);old=data[pos]
    clear=all(data[xx,yy,zz].split('[')[0] in AIR|{'minecraft:light'} for yy in (f+1,f+2))
    if not clear or not any(k in old for k in ('floor','concrete','smooth_stone','polished_deepslate','moving_walk')):break
    direction=('north' if side<0 else 'south') if axis=='z' else ('east' if side<0 else 'west');pair.append((pos,old,f'projectseele:nerv_moving_walk[facing={direction}]'))
   if len(pair)!=2:continue
   for pos,old,new in pair:
    if pos in seen:continue
    seen.add(pos);p.match((*pos,*pos),old,new,'r21/high_ceiling_paired_walk');count+=1
  rows.append(dict(id=r['id'],start=r['start'],end=r['end'],cells=count,classification='Named enclosed chamber or industrial gallery; roof height is not outdoor exposure'))
 p.meta.update(corridors=rows,unique_cells=len(seen));p.apply('high_ceiling_galleries');print(rows)
if __name__=='__main__':main()
