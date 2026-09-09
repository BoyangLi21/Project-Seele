"""Replace the visibly domestic seating and activate briefing display surfaces, keeping their measured footprints."""
import json
import regional_voxels as vox
from scan_regional_completion import volume
from survey_world_art_r10 import OUT
if __name__=='__main__':
 rooms=json.loads((vox.ROOT/'artifacts/world_motion_r04/pyramid/places.json').read_text(encoding='utf8'))['rooms'];p=vox.Painter();count=0
 for r in rooms:
  x0,x1,z0,z1=r['bounds'];f=r['floor'];lo=(x0,f+1,z0);hi=(x1,f+5,z1);a,pal=volume(lo,hi)
  for y,z,x in __import__('numpy').argwhere(__import__('numpy').array(['chair[' in s for s in pal])[a]):
   before=pal[a[y,z,x]];facing=next((s.split('=')[1] for s in before.split('[')[1].rstrip(']').split(',') if s.startswith('facing=')),'north');pos=(int(x+lo[0]),int(y+lo[1]),int(z+lo[2]));p.match((*pos,*pos),before,f'projectseele:nerv_office_chair[facing={facing}]',r['id']+'/r10_chair');count+=1
  if r['purpose']=='BRIEFING':
   sx=(x0+x1)//2-5;back=r['entry'][2]==z0
   if back:
    for y in range(f+2,f+6):
     for x in range(x0+3,x1-2):
      pos=(x,y,z0+1);before=pal[a[y-lo[1],1,x-lo[0]]]
      if before=='minecraft:black_concrete':p.match((*pos,*pos),before,'projectseele:nerv_wall_panel',r['id']+'/retire_interrupted_screen')
   for row in range(4):
    for col in range(12):
     pos=sx+(11-col if back else col),f+5-row,z1 if back else z0+1;before=pal[a[pos[1]-lo[1],pos[2]-lo[2],pos[0]-lo[0]]]
     assert before in ({'projectseele:nerv_wall_panel','projectseele:nerv_wall_datum','minecraft:smooth_quartz','minecraft:light_gray_concrete'} if back else {'minecraft:black_concrete'}),(r['id'],pos,before)
     p.match((*pos,*pos),before,f'projectseele:nerv_briefing_tile[part={row*12+col}]',r['id']+'/tactical_display')
 p.meta.update(chairs=count,continuous_displays=3);vox.OUT=OUT;p.apply('room_furniture')
