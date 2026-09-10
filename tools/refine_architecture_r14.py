"""Measured R14 palette replacement, roof reception enclosure and lounge furnishing.

The accepted command module below Y=-390 is geometry-protected. Exact states and
block-entity NBT are backed up by Painter; the piano's lectern inventory moves intact.
"""
import argparse,json,copy
from pathlib import Path
import numpy as np
import nbtlib
import regional_voxels as vox
from scan_regional_completion import volume
from query_blocks import iter_block_entities
OUT=vox.ROOT/'artifacts/world_refinement_r14';AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
PANEL='projectseele:nerv_structural_panel';WALL='projectseele:nerv_wall_panel';FLOOR='projectseele:nerv_floor_panel';LIGHT='projectseele:nerv_strip_light'

def materials():
 p=vox.Painter();survey=json.loads((OUT/'reinforced_before.json').read_text())
 for item in survey['sections']:
  cx,cz=item['chunk'];sy=item['section'];p.match((cx*16,sy*16,cz*16,cx*16+15,sy*16+15,cz*16+15),item['state'],PANEL,'r14/materials/painted_structural_shell')
 p.meta.update(source='Measured actual TV save, including imported architecture',expected_old_material_cells=sum(survey['counts'].values()),geometry_unchanged=True,blast_properties_unchanged=True)
 return p

class Measured:
 def __init__(self,p,lo,hi):self.p=p;self.lo=lo;self.hi=hi;self.a,self.pal=volume(lo,hi);self.writes={};self.owners={}
 def old(self,pos):
  x,y,z=pos
  if not all(self.lo[k]<=pos[k]<=self.hi[k] for k in range(3)):raise ValueError(('unmeasured',pos))
  return self.pal[self.a[y-self.lo[1],z-self.lo[2],x-self.lo[0]]]
 def get(self,pos):return self.writes.get(pos,self.old(pos))
 def put(self,pos,state,owner,empty=False):
  old=self.get(pos)
  if empty and old.split('[')[0] not in AIR|{'minecraft:light'}:return
  self.writes[pos]=state;self.owners[pos]=owner
 def box(self,lo,hi,state,owner,empty=False):
  for y in range(lo[1],hi[1]+1):
   for z in range(lo[2],hi[2]+1):
    for x in range(lo[0],hi[0]+1):self.put((x,y,z),state,owner,empty)
 def flush(self):
  for pos,state in sorted(self.writes.items()):self.p.match((*pos,*pos),self.old(pos),state,self.owners[pos])

def roof():
 p=vox.Painter();m=Measured(p,(0,-395,270),(79,-379,366));o='r14/roof_reception'
 # The existing slab supports the room. No write reaches the command-room volume below it.
 for pos in [(6,-390,280),(50,-390,340),(28,-390,333)]:
  assert m.old(pos).split('[')[0] not in AIR,(pos,m.old(pos))
 # Preserve the complete measured instrument, including every shutter state and its sheet music.
 delta=(-14,-1,-4);piano=[]
 for y in range(-389,-385):
  for z in range(357,365):
   for x in range(24,29):
    pos=x,y,z;state=m.old(pos)
    if state.split('[')[0] in AIR|{'minecraft:light'}:continue
    target=tuple(pos[k]+delta[k] for k in range(3));piano.append((pos,target,state));m.put(pos,'minecraft:air',o+'/retire_piano_footprint')
 for pos,target,state in piano:
  assert target[1]==-390 or m.old(target).split('[')[0] in AIR|{'minecraft:light'},(target,m.old(target))
  m.put(target,state,o+'/piano_corner')
 for _,tag in iter_block_entities(vox.WORLD,vox.DIM,(24,-389,357),(28,-386,364)):
  # query_blocks returns the original typed tag; preserve the book rather than recreating an empty lectern.
  entity=copy.deepcopy(tag);old=tuple(int(entity[k]) for k in ('x','y','z'));new=tuple(old[k]+delta[k] for k in range(3))
  for k,n in zip(('x','y','z'),new):entity[k]=nbtlib.Int(n)
  p.block_entities[new]=entity
 # Keep the centre of the lift and its approach untouched; give the room a continuous coffered ceiling.
 for z in range(278,364):
  for x in range(4,53):
   if not(25<=x<=31 and 313<=z<=324):
    if m.get((x,-390,z)).split('[')[0] not in AIR:m.put((x,-390,z),FLOOR,o+'/floor_finish')
   if 25<=x<=31 and 318<=z<=324:continue
   m.put((x,-381,z),PANEL,o+'/ceiling')
   if x in (12,20,36,44) and z%12 in (3,4,5,6):m.put((x,-382,z),LIGHT,o+'/ceiling_battens')
 # External walls follow the measured slab, stopping below the existing upper rooms at Y=-379.
 for y in range(-389,-381):
  for z in range(278,364):
   for x in (4,52):m.put((x,y,z),PANEL if y in (-389,-382) else WALL,o+'/walls')
  for x in range(4,53):
   for z in (278,363):m.put((x,y,z),PANEL if y in (-389,-382) else WALL,o+'/walls')
 # Supported north arrival remains open; a second, graded east link joins the named R04 gallery.
 for x in range(26,31):
  for y in range(-389,-385):m.put((x,y,278),'minecraft:air',o+'/north_door')
 for z in range(339,342):
  for y in range(-389,-385):m.put((52,y,z),'minecraft:air',o+'/east_door')
 for x in range(53,76):
  f=-390 if x<=57 else -390-(x-57) if x<=60 else -393
  for z in range(338,343):
   m.put((x,f-1,z),PANEL,o+'/gallery_support')
   m.put((x,f,z),f'minecraft:smooth_quartz_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]' if 58<=x<=60 and z in (339,340,341) else FLOOR,o+'/gallery_floor')
   for y in range(f+1,-384):m.put((x,y,z),WALL if z in (338,342) else 'minecraft:air',o+'/gallery_enclosure')
   m.put((x,-384,z),LIGHT if z==340 and x%5==0 else PANEL,o+'/gallery_ceiling')
 # Visible riser at the secure lift approach is a stair, not a full cube to jump onto.
 for x in range(26,31):m.put((x,-389,313),'minecraft:smooth_quartz_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]',o+'/lift_threshold')
 # Paired seating bays preserve a wide north/south spine and the cross route to the lift.
 for x0,z0 in [(8,288),(36,288),(36,345)]:
  for x in range(x0,x0+10):
   for z in (z0,z0+8):
    m.put((x,-389,z),'another_furniture:gray_sofa[facing='+('south' if z==z0 else 'north')+',type=single,waterlogged=false]',o+'/waiting_seats',True)
  m.box((x0+3,-389,z0+3),(x0+6,-389,z0+5),'minecraft:smooth_quartz_slab[type=top,waterlogged=false]',o+'/low_table',True)
  for x in (x0,x0+9):m.put((x,-389,z0+4),'minecraft:potted_bamboo',o+'/plants',True)
 for z in range(320,329):
  m.put((6,-389,z),'projectseele:nerv_storage_panel[facing=east]',o+'/service_storage',True)
  m.put((6,-388,z),'minecraft:smooth_quartz_slab[type=top,waterlogged=false]',o+'/service_counter',True)
 m.put((6,-387,322),'projectseele:nerv_workstation[facing=east]',o+'/service_terminal',True)
 m.put((6,-387,326),'minecraft:potted_fern',o+'/service_plant',True)
 # A restrained wall datum ties the reception to the rest of the facility.
 for z in range(281,360):
  for x in (4,52):
   if not(x==52 and 339<=z<=341):m.put((x,-387,z),'projectseele:nerv_wall_datum',o+'/datum')
 m.flush();p.meta.update(piano_blocks=len(piano),piano_offset=delta,main_command_layout_preserved=True,protected_lower_volume='All Y < -390',roof_room_bounds=[4,-390,278,52,-381,363],gallery_endpoints=[[50,-389,340],[76,-392,340]])
 p.meta['walk_nodes']=[dict(id=o+'/east',start=[49.5,-389,340.5],end=[76.5,-392,340.5]),dict(id=o+'/lift',start=[28.5,-389,305.5],end=[28.5,-388,315.5]),dict(id=o+'/spine',start=[28.5,-389,280.5],end=[28.5,-389,309.5]),dict(id=o+'/piano_aisle',start=[19.5,-389,337.5],end=[19.5,-389,358.5])]
 return p

def lounges():
 p=vox.Painter()
 for f in (-449,-462):
  m=Measured(p,(-67,f,295),(-34,f+9,322));o=f'r14/staff_lounge/{f}'
  # The two named existing staff rest rooms flank the command complex.
  for x0,z0 in [(-62,300),(-48,314)]:
   for x in range(x0,x0+8):
    m.put((x,f+1,z0),'another_furniture:gray_sofa[facing=south,type=single,waterlogged=false]',o+'/seats',True)
   m.box((x0+2,f+1,z0+2),(x0+5,f+1,z0+3),'minecraft:smooth_quartz_slab[type=top,waterlogged=false]',o+'/tables',True)
   for x in (x0,x0+7):m.put((x,f+1,z0+3),'minecraft:potted_fern',o+'/plants',True)
  for z in range(298,305):
   m.put((-66,f+1,z),'projectseele:nerv_storage_panel[facing=east]',o+'/pantry',True);m.put((-66,f+2,z),'minecraft:smooth_quartz_slab[type=top,waterlogged=false]',o+'/pantry',True)
  for x in range(-61,-38,7):
   m.put((x,f+7,307),LIGHT,o+'/pendants',True)
  m.flush();p.meta['rooms'].append(dict(id=o,bounds=[-67,-34,295,322],floor=f,entry=[-34,f+1,308]))
 return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('part',choices=['materials','roof','lounges']);ap.add_argument('--apply',action='store_true');args=ap.parse_args();vox.OUT=OUT;p=globals()[args.part]();p.apply(args.part) if args.apply else p.save_plan(args.part)
