"""Measured forest groups and planted urban edges. No facility, track, road, or unknown cell is editable."""
import argparse,json,math,random
from collections import Counter
import numpy as np
from scipy.ndimage import maximum_filter,minimum_filter,distance_transform_edt
import regional_voxels as vox
from scan_regional_completion import volume
from survey_world_art_r10 import BOXES,OUT
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
GROUND={'minecraft:grass_block[snowy=false]','minecraft:dirt','minecraft:coarse_dirt','minecraft:podzol[snowy=false]','minecraft:rooted_dirt'}
PLANTS={'minecraft:grass','minecraft:fern','minecraft:dandelion','minecraft:poppy'}
def build(name):
 p=vox.Painter();lo,hi=BOXES[name];a,pal=volume(lo,hi,allow_unknown=True);data=np.load(OUT/(name+'.npz'));g=data['ground'];known=data['known'];eng=data['engineered'];water=data['water'];veg=data['vegetation']
 urban=not name.startswith('geofront');safe=known&(water<g)&(eng<g)&(veg<=g)&(g>lo[1])&(g<hi[1]-18)
 engineered=eng>=g;edge=distance_transform_edt(~engineered);lake=distance_transform_edt(water<g)
 safe &= minimum_filter(safe,size=13)>0;safe &= (maximum_filter(g,size=11)-minimum_filter(g,size=11))<(7 if urban else 5)
 safe &= edge>(10 if urban else 16)
 if urban:safe &= edge<70
 desired={};owners={};rng=random.Random(9910+sum(map(ord,name)));trees=[];shrubs=[]
 def get(pos):
  x,y,z=pos
  if not(lo[0]<=x<=hi[0] and lo[1]<=y<=hi[1] and lo[2]<=z<=hi[2]):return 'UNKNOWN'
  return pal[a[y-lo[1],z-lo[2],x-lo[0]]]
 def put(pos,state,owner,allowed):
  old=get(pos)
  if old in allowed and pos not in desired:desired[pos]=state;owners[pos]=owner
 locations=np.argwhere(safe);rng.shuffle(locations)
 target=330 if name=='geofront_west' else 180 if name=='geofront_south' else 110
 for iz,ix in locations:
  x,z=int(ix+lo[0]),int(iz+lo[2]);f=int(g[iz,ix]);h=9+rng.randrange(5);r=4+rng.randrange(2)
  if len(trees)>=target:break
  # Broad irregular groves alternate with open meadows, keeping the lake visible.
  density=(math.sin(x/87)+math.cos(z/71)+math.sin((x+z)/103))
  if not urban and density<-.7:continue
  if any((x-t[0])**2+(z-t[2])**2<13**2 for t in trees):continue
  if get((x,f,z)) not in GROUND:continue
  if any(get((x+dx,f+dy,z+dz)) not in AIR|PLANTS for dx in range(-r,r+1) for dz in range(-r,r+1) for dy in (max(1,h-4),h,h+3)):continue
  species='birch' if rng.random()<.16 else 'oak';owner=f'r10/{name}/grove/{len(trees):03d}'
  # Overlapping ellipsoids make branch-supported, asymmetric crowns.
  crown=[]
  for cy,rx,rz,ry,ox,oz in [(h-2,r,r-1,3,0,0),(h+1,r-1,r-1,3,rng.choice([-1,1]),rng.choice([-1,1]))]:
   for dy in range(-ry,ry+1):
    for dz in range(-rz,rz+1):
     for dx in range(-rx,rx+1):
      if (dx/rx)**2+(dz/rz)**2+(dy/ry)**2<=1+rng.uniform(-.09,.09):crown.append((x+dx+ox,f+cy+dy,z+dz+oz))
  for y in range(f+1,f+h+1):put((x,y,z),f'minecraft:{species}_log[axis=y]',owner,AIR|PLANTS)
  for side in (-1,1):
   for dx in range(1,4):put((x+side*dx,f+h-3+dx//2,z),f'minecraft:{species}_log[axis=x]',owner,AIR|PLANTS)
  for pos in crown:put(pos,f'minecraft:{species}_leaves[distance=1,persistent=true,waterlogged=false]',owner,AIR|PLANTS)
  trees.append((x,f,z,h,species))
 # Low scrub, fern and meadow flower groups occupy natural soil only, never paths.
 for iz,ix in locations[::7]:
  if len(shrubs)>target*12:break
  x,z=int(ix+lo[0]),int(iz+lo[2]);f=int(g[iz,ix]);pos=(x,f+1,z)
  if get((x,f,z)) not in GROUND or get(pos) not in AIR|PLANTS:continue
  v=math.sin(x/19)*math.cos(z/23);plant='minecraft:fern' if v<-.25 else 'minecraft:grass' if v<.7 else 'minecraft:azure_bluet'
  put(pos,plant,'r10/'+name+'/understory',AIR|PLANTS);shrubs.append(pos)
 for pos,new in sorted(desired.items()):p.match((*pos,*pos),get(pos),new,owners[pos])
 p.meta.update(trees=trees,understory=len(shrubs),unchanged_grade=True,source_bounds=[lo,hi],protected_clearance='10m urban / 16m GeoFront from all surveyed engineered columns; measured clear canopy')
 vox.OUT=OUT;return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('part',choices=[n for n in BOXES if n!='intercept_edge']);ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build(args.part);p.apply(args.part+'_landscape') if args.apply else p.save_plan(args.part+'_landscape')
