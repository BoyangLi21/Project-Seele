"""Fit paired flush moving walks without widening the accepted command rooms."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import regional_voxels as v
import scan_regional_completion as scan
from query_blocks import AIR
ROOT=v.ROOT;OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW';ASSET=ROOT/'src/main/resources/assets/projectseele'
def assets():
 im=Image.new('RGB',(32,256));d=ImageDraw.Draw(im)
 for frame in range(8):
  y=frame*32;d.rectangle((0,y,31,y+31),fill='#3d484b')
  for z in range(32):
   if (z+frame)%4==0:d.line((3,y+z,28,y+z),fill='#879391')
  for x in (0,1,30,31):d.line((x,y,x,y+31),fill='#c6ac57')
  d.line((10,y+15,16,y+9,22,y+15),fill='#d9e2dd',width=2)
 im.save(ASSET/'textures/block/nerv_moving_walk.png')
 (ASSET/'textures/block/nerv_moving_walk.png.mcmeta').write_text(json.dumps({'animation':{'frametime':2,'interpolate':False}}))
 model={'parent':'minecraft:block/block','textures':{'particle':'projectseele:block/nerv_moving_walk','top':'projectseele:block/nerv_moving_walk','side':'projectseele:block/nerv_floor_panel'},'elements':[{'from':[0,0,0],'to':[16,15,16],'faces':{f:{'texture':'#top' if f=='up' else '#side'} for f in ['up','down','north','south','west','east']}}]}
 (ASSET/'models/block/nerv_moving_walk.json').write_text(json.dumps(model,indent=2))
 (ASSET/'blockstates/nerv_moving_walk.json').write_text(json.dumps({'variants':{f'facing={f}':{'model':'projectseele:block/nerv_moving_walk','y':yaw} for f,yaw in [('north',0),('east',90),('south',180),('west',270)]}},indent=2))
 for lang,label in [('zh_cn','NERV 平层自动步道'),('en_us','NERV Flat Moving Walk')]:
  p=ASSET/'lang'/f'{lang}.json';data=json.loads(p.read_text(encoding='utf8'));data['block.projectseele.nerv_moving_walk']=label;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main(apply=False):
 assets();scan.WORLD=WORLD;v.WORLD=WORLD;v.OUT=OUT/'global_walkways';p=v.Painter();report=[];cells={}
 rows=json.loads((OUT/'global_corridor_sections.json').read_text(encoding='utf8'))['segments']
 for r in rows:
  if r['status']!='enclosed_corridor':continue
  x,y,z=r['start'];X,Y,Z=r['end'];axis=r['axis'];f=y-1
  if 85<=x<=155 and -300<=z<=251 and -443<=f<=-368:continue # full-width MTR lanes installed by facility plan
  lo=(min(x,X)-3,f,min(z,Z)-3);hi=(max(x,X)+3,f+3,max(z,Z)+3);a,pal=scan.volume(lo,hi)
  width=min(r['minimum_half_width']);offset=1 if width<=2 else 2
  points=[]
  for n in range(5,r['length']-4):
   cx=x+(n if axis=='x' else 0);cz=z+(n if axis=='z' else 0)
   # Short plain landings at room doors/junctions and every 36 m let people
   # cross both directions without any forced drift into the doorway.
   if n%36 in range(0,6):continue
   for sign in (-1,1):
    xx=cx+(sign*offset if axis=='z' else 0);zz=cz+(sign*offset if axis=='x' else 0);q=(xx,f,zz)
    old=pal[a[f-lo[1],zz-lo[2],xx-lo[0]]];head=[pal[a[h-lo[1],zz-lo[2],xx-lo[0]]] for h in (f+1,f+2)]
    if any(s.split('[')[0] not in AIR|{'minecraft:light'} for s in head):continue
    if not any(k in old for k in ('floor','smooth_stone','polished_deepslate','concrete')):continue
    # Never place transport machinery into the accepted main command module.
    if 6<=xx<=52 and -445<=f<=-388 and 262<=zz<=365:continue
    facing=('north' if sign<0 else 'south') if axis=='z' else ('east' if sign<0 else 'west')
    state=f'projectseele:nerv_moving_walk[facing={facing}]'
    if q in cells and cells[q][1]!=state:raise RuntimeError(('Incompatible crossing',q))
    cells[q]=(old,state);points.append(q)
  report.append(dict(id=r['id'],from_pos=r['start'],to=r['end'],measured_half_width=r['minimum_half_width'],cells=len(points),kind='paired compact moving floors with static crossing landings'))
 for q,(old,new) in cells.items():p.match((*q,*q),old,new,'r21/compact_paired_walkways')
 p.meta.update(corridors=report,unique_cells=len(cells),unchanged_main_command=True)
 p.apply('paired_indoor_walkways') if apply else p.save_plan('paired_indoor_walkways')
 print('Fitted pairs',len(report),'unique moving floor cells',len(cells))
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
