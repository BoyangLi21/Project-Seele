"""Measured shore ecotones and quiet meadow detail outside protected engineered columns."""
import argparse,math,json
import numpy as np
from scipy.ndimage import distance_transform_edt,maximum_filter,minimum_filter
import regional_voxels as vox
from scan_regional_completion import volume
from survey_world_art_r10 import BOXES
OUT=vox.ROOT/'artifacts/world_refinement_r14'
def build(name):
 lo,hi=BOXES[name];a,pal=volume(lo,hi,allow_unknown=True);p=vox.Painter();base=[s.split('[')[0] for s in pal]
 earth=np.array([s in {'minecraft:grass_block','minecraft:dirt','minecraft:coarse_dirt','minecraft:podzol','minecraft:rooted_dirt','minecraft:gravel','minecraft:sand','minecraft:stone','minecraft:clay'} for s in base]);water=np.array([s=='minecraft:water' for s in base]);trees=np.array([s.endswith(('_log','_leaves')) for s in base]);empty=np.array([s in {'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:light','minecraft:grass','minecraft:fern','minecraft:tall_grass','minecraft:large_fern','minecraft:dandelion','minecraft:poppy','minecraft:azure_bluet'} for s in base]);natural=earth|water|trees|empty;y=np.arange(lo[1],hi[1]+1)[:,None,None]
 def top(mask):return np.max(np.where(mask[a],y,lo[1]-1),axis=0)
 ground=top(earth);wet=top(water);engineered=top(~natural);canopy=top(trees);known=~np.array([s=='UNKNOWN' for s in pal])[a].any(0)
 built=engineered>=ground;distance=distance_transform_edt(~built);lake=distance_transform_edt(wet<ground)
 safe=known&(ground>lo[1])&(ground<hi[1]-4)&(wet<ground)&(distance>8)&(maximum_filter(ground,5)-minimum_filter(ground,5)<5)
 changed=0;shore=0;understory=0
 def old(x,f,z):return pal[a[f-lo[1],z-lo[2],x-lo[0]]]
 for iz,ix in np.argwhere(safe):
  x,z=int(ix+lo[0]),int(iz+lo[2]);f=int(ground[iz,ix]);floor=old(x,f,z);above=old(x,f+1,z)
  value=(x*73856093^z*19349663)&65535
  if lake[iz,ix]<5 and floor.startswith(('minecraft:grass_block','minecraft:dirt','minecraft:sand')) and above.split('[')[0] in {'minecraft:air','minecraft:grass','minecraft:fern'}:
   material='minecraft:gravel' if value%7<3 else 'minecraft:coarse_dirt' if value%7<5 else 'minecraft:clay'
   p.match((x,f,z,x,f,z),floor,material,'r14/'+name+'/shore_transition');shore+=1
  elif value%29==0 and floor.startswith(('minecraft:grass_block','minecraft:dirt','minecraft:podzol')) and above=='minecraft:air':
   patch=math.sin(x/18)*math.cos(z/21)+math.sin((x+z)/38)
   plant='minecraft:fern' if canopy[iz,ix]>f or patch<.2 else 'minecraft:grass' if patch<1.2 else 'minecraft:azure_bluet'
   p.match((x,f+1,z,x,f+1,z),above,plant,'r14/'+name+'/meadow_understory');understory+=1
 p.meta.update(area=name,shore_cells=shore,understory_cells=understory,existing_grade_preserved=True,clearance_from_engineered_columns=8,unknown_columns_protected=True);return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('area',choices=[s for s in BOXES if s!='intercept_edge']);ap.add_argument('--apply',action='store_true');args=ap.parse_args();vox.OUT=OUT;p=build(args.area);p.apply('landscape_'+args.area) if args.apply else p.save_plan('landscape_'+args.area)
