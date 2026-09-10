"""Attach UN insignia to measured exterior faces and update existing base signage."""
import json,copy,sys
from pathlib import Path
import numpy as np
import nbtlib
import regional_voxels as vox
from query_blocks import iter_block_entities,read_box,AIR
from scan_regional_completion import volume
ROOT=vox.ROOT;OUT=ROOT/'artifacts/world_motion_r11/un';OUT.mkdir(exist_ok=True)
def rectangle(mask):
 best=(0,None);h=np.zeros(mask.shape[1],int)
 for row in range(mask.shape[0]):
  h=np.where(mask[row],h+1,0);stack=[]
  for c in range(len(h)+1):
   height=int(h[c]) if c<len(h) else 0;start=c
   while stack and stack[-1][1]>height:
    start,hh=stack.pop();width=c-start
    if hh>=3 and width>=4 and hh*width>best[0]:best=(hh*width,(start,row-hh+1,width,hh))
   if height and (not stack or stack[-1][1]<height):stack.append((start,height))
 return best
def surfaces_ship(cx):
 lo=(cx-13,63,388);hi=(cx+13,92,546);a,pal=volume(lo,hi);solid=np.array([s not in AIR and not any(k in s for k in ['stairs','slab','fence','wall','bars','pane','glass','trapdoor','chain','sign','button','torch','water','ladder','rail']) for s in pal])[a];empty=np.array([s in AIR for s in pal])[a];out=[]
 for sign in [-1,1]:
  choices=[]
  for x in range(cx+sign*3,cx+sign*12,sign):
   ix=x-lo[0];mask=solid[:,:,ix]&empty[:,:,ix+sign];score,rect=rectangle(mask)
   if rect:choices.append((score,x,rect))
  if not choices:raise RuntimeError('No continuous ship face '+str((cx,sign)))
  _,x,(z,y,w,h)=max(choices,key=lambda r:r[0]);size=min(3.4,h-.35,w-.35);pos=[x+(1.012 if sign>0 else -.012),lo[1]+y+h/2,lo[2]+z+w/2]
  out.append(dict(id=f'ship/{cx}/{sign}',position=pos,width=size,height=size,yaw=90 if sign>0 else -90,support=[x,lo[1]+y+h//2,lo[2]+z+w//2],kind='paint'))
 return out
def main():
 p=vox.Painter();plates=[]
 # These measured wall bands sit above the doors and below the roof.
 for name,z,x0,x1,y0,y1,want in [('operations',-6544,6388,6424,80,86,4),('eva_un_hangar',-6136,6462,6479,103,133,8),('air_support',-5984,6620,6638,80,82,2.5)]:
  a,pal=volume((x0,y0,z),(x1,y1,z+1));solid=np.array([s not in AIR and 'glass' not in s and 'sign' not in s for s in pal])[a[:,0,:]];empty=np.array([s in AIR for s in pal])[a[:,1,:]];score,r=rectangle(solid&empty)
  if not r:raise RuntimeError('No supported facade for '+name)
  x,y,w,h=r;size=min(want,w-.3,h-.3);plates.append(dict(id=name,position=[x0+x+w/2,y0+y+h/2,z+1.012],width=size,height=size,yaw=0,support=[x0+x+w//2,y0+y+h//2,z]))
 for cx in [1444,1494]:plates+=surfaces_ship(cx)
 for lo,hi in [((6320,70,-6704),(6880,166,-5950)),((1220,62,320),(1510,100,570))]:
  for pos,be in iter_block_entities(vox.WORLD,vox.DIM,lo,hi):
   if str(be.get('id','')) not in ['minecraft:sign','minecraft:hanging_sign']:continue
   data=copy.deepcopy(be);changed=False
   for face in ['front_text','back_text']:
    if face not in data:continue
    messages=data[face]['messages'];new=[]
    for message in messages:
     text=str(message);fixed=text.replace('NERV / UN','UNITED NATIONS').replace('NERV','UN').replace('UNNAMED','EVA-UN').replace('未命名 EVA 试验机','EVA-UN')
     if fixed!=text:changed=True
     new.append(nbtlib.String(fixed))
    data[face]['messages']=nbtlib.List[nbtlib.String](new)
   if not changed:continue
   before=read_box(vox.WORLD,vox.DIM,pos,pos)[pos]
   if 'oak_wall_sign' not in before:continue
   after=before.replace('minecraft:oak_wall_sign','minecraft:dark_oak_wall_sign')
   if after==before:after=before.replace('minecraft:dark_oak_wall_sign','minecraft:oak_wall_sign')
   p.match((*pos,*pos),before,after,'r11/un_identity/sign');p.block_entities[pos]=data
   for face in ['front_text','back_text']:
    if face in data:data[face]['color']=nbtlib.String('white' if 'dark_oak' in after else 'black')
 p.meta['insignia']=plates;vox.OUT=OUT;p.apply('facility_signs')
 config=dict(world='SEELE_TV_WORLD_PREVIEW_20260906',dimension=vox.DIM,plates=plates);(ROOT/'run/projectseele-local-maps/un_markings_r11.json').write_text(json.dumps(config,indent=2),encoding='utf8');(OUT/'fixed_insignia.json').write_text(json.dumps(config,indent=2),encoding='utf8');print('UN exterior insignia',len(plates),'signs',len(p.block_entities))
if __name__=='__main__':main()
