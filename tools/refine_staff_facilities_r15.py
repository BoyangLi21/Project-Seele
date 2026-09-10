"""Measured material-only interior unification and understory in existing landscape zones."""
import argparse,json,math
import numpy as np
from scipy.ndimage import distance_transform_edt,maximum_filter,minimum_filter
import regional_voxels as vox
from scan_regional_completion import volume
from survey_world_art_r10 import BOXES
OUT=vox.ROOT/'artifacts/staff_world_r15/map'
MATERIALS={
 'minecraft:cobblestone':'projectseele:nerv_wall_panel',
 'minecraft:mossy_cobblestone':'projectseele:nerv_wall_panel',
 'minecraft:stone_bricks':'projectseele:nerv_wall_panel',
 'minecraft:cracked_stone_bricks':'projectseele:nerv_wall_panel',
 'minecraft:polished_deepslate':'projectseele:nerv_structural_panel',
 'minecraft:deepslate_tiles':'projectseele:nerv_structural_panel',
 'minecraft:deepslate_bricks':'projectseele:nerv_structural_panel',
 'minecraft:cobbled_deepslate':'projectseele:nerv_structural_panel'}
def interiors():
 p=vox.Painter();boxes=[('preserved_command_layout',(2,-449,244),(52,-391,366))]
 for file in ['artifacts/world_motion_r04/pyramid/places.json','artifacts/world_expansion_20260907/geometry_all/places.json']:
  for r in json.loads((vox.ROOT/file).read_text(encoding='utf8'))['rooms']:
   if r['floor']<0:
    x0,x1,z0,z1=r['bounds'];f=r['floor'];boxes.append((r['id'],(x0,f,z0),(x1,min(f+6,-320),z1)))
 desired={};stats=[]
 for name,lo,hi in boxes:
  if hi[1]<lo[1]:continue
  a,pal=volume(lo,hi);count=0
  for index,old in enumerate(pal):
   if old not in MATERIALS:continue
   for y,z,x in np.argwhere(a==index):
    pos=(int(x+lo[0]),int(y+lo[1]),int(z+lo[2]));desired[pos]=(old,MATERIALS[old],name);count+=1
  stats.append(dict(room=name,material_cells=count))
 for pos,(old,new,room) in desired.items():p.match((*pos,*pos),old,new,'r15/interior/'+room)
 p.meta.update(rooms=stats,layout_unchanged=True,block_entities_untouched=True,material_mapping=MATERIALS);return p
def landscape(name):
 lo,hi=BOXES[name];a,pal=volume(lo,hi,allow_unknown=True);p=vox.Painter();base=[s.split('[')[0] for s in pal]
 soil=np.array([s in {'minecraft:grass_block','minecraft:dirt','minecraft:coarse_dirt','minecraft:podzol','minecraft:rooted_dirt'} for s in base]);earth=np.array([s in {'minecraft:stone','minecraft:gravel','minecraft:sand','minecraft:clay'} for s in base])|soil
 water=np.array([s=='minecraft:water' for s in base]);trees=np.array([s.endswith(('_log','_leaves')) for s in base]);empty=np.array([s in {'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:light','minecraft:grass','minecraft:fern','minecraft:tall_grass','minecraft:large_fern','minecraft:dandelion','minecraft:poppy','minecraft:azure_bluet'} for s in base]);y=np.arange(lo[1],hi[1]+1)[:,None,None]
 def top(mask):return np.max(np.where(mask[a],y,lo[1]-1),axis=0)
 ground=top(earth);canopy=top(trees);built=top(~(earth|water|trees|empty))>=ground;wet=top(water);known=~np.array([s=='UNKNOWN' for s in pal])[a].any(0)
 safe=known&(ground>lo[1])&(ground<hi[1]-3)&(wet<ground)&(distance_transform_edt(~built)>12)&(maximum_filter(ground,5)-minimum_filter(ground,5)<4)
 def old(x,f,z):return pal[a[f-lo[1],z-lo[2],x-lo[0]]]
 count=0;plants=0
 for iz,ix in np.argwhere(safe):
  x,z=int(ix+lo[0]),int(iz+lo[2]);f=int(ground[iz,ix]);floor=old(x,f,z);above=old(x,f+1,z);value=(x*73856093^z*19349663)&65535;patch=math.sin(x/11)*math.cos(z/13)
  if canopy[iz,ix]>f+3 and value%5<2 and patch>.25 and floor.startswith(('minecraft:grass_block','minecraft:dirt')) and above in {'minecraft:air','minecraft:fern','minecraft:grass'}:
   new='minecraft:podzol[snowy=false]' if value%3 else 'minecraft:coarse_dirt';p.match((x,f,z,x,f,z),floor,new,'r15/'+name+'/leaf_litter');count+=1
  if value%83==0 and patch<-.4 and floor.startswith(('minecraft:grass_block','minecraft:dirt','minecraft:podzol')) and above=='minecraft:air':
   p.match((x,f+1,z,x,f+1,z),above,'minecraft:fern' if canopy[iz,ix]>f else 'minecraft:azure_bluet','r15/'+name+'/groundcover');plants+=1
 p.meta.update(existing_landscape=name,leaf_litter=count,groundcover=plants,clearance_from_structures=12,grades_unchanged=True);return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('part',choices=['interiors']+[s for s in BOXES if s!='intercept_edge']);ap.add_argument('--apply',action='store_true');args=ap.parse_args();vox.OUT=OUT;p=interiors() if args.part=='interiors' else landscape(args.part);p.apply(args.part) if args.apply else p.save_plan(args.part)
