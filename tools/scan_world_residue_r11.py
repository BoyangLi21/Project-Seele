"""Whole-save palette census and isolated natural-residue candidates from the frozen R11 checkpoint.

Chunk metadata selects FULL sections; all block values are read through query_blocks.
Candidates are observations, not blanket permission to erase engineered objects.
"""
import json,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from regional_voxels import ROOT,DIM
from query_blocks import iter_selected_sections,dimension_dir,read_box,AIR
from inspect_map_assets import iter_chunks
OUT=ROOT/'artifacts/world_motion_r11/map';OUT.mkdir(exist_ok=True)
WORLD=ROOT/'backups/SEELE_R11_20260909_234420/world'
NATURAL={'minecraft:stone','minecraft:dirt','minecraft:gravel','minecraft:sand','minecraft:coarse_dirt','minecraft:grass_block','minecraft:deepslate','minecraft:netherrack'}
def main():
 selected={};incomplete=0
 directory=dimension_dir(WORLD,DIM);regions=[tuple(map(int,p.stem.split('.')[1:])) for p in (directory/'region').glob('r.*.*.mca')]
 bounds=(min(x for x,z in regions)*32,max(x for x,z in regions)*32+31,min(z for x,z in regions)*32,max(z for x,z in regions)*32+31)
 for cx,cz,chunk in iter_chunks(directory,bounds):
  if str(chunk.get('Status','')).removeprefix('minecraft:')!='full':incomplete+=1;continue
  selected[cx,cz]={int(s['Y']) for s in chunk.get('sections',[])}
 print('Selected full chunks',len(selected),'incomplete',incomplete,flush=True)
 counts=Counter();sections=0;candidates=[];border=[];start=time.monotonic()
 for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected):
  freq=np.bincount(idx,minlength=len(pal));counts.update({s:int(freq[i]) for i,s in enumerate(pal) if freq[i]})
  sections+=1
  if sections%10000==0:print('sections',sections,'seconds',round(time.monotonic()-start,1),flush=True)
  nat=np.array([s.split('[')[0] in NATURAL for s in pal]);free=np.array([s in AIR for s in pal]);a=idx.reshape(16,16,16)
  if not nat.any() or not free.any():continue
  empty=np.pad(free[a],1,constant_values=True);mask=nat[a].copy()
  for dy,dz,dx in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:mask &= empty[1+dy:17+dy,1+dz:17+dz,1+dx:17+dx]
  for y,z,x in np.argwhere(mask):
   pos=(int(cx*16+x),int(sy*16+y),int(cz*16+z));item=dict(pos=pos,state=pal[a[y,z,x]],reason='natural-material cell with six air neighbours')
   if any(v in (0,15) for v in (x,y,z)):border.append(item)
   else:candidates.append(item)
 print('Border checks',len(border),flush=True)
 for d in border:
  x,y,z=d['pos'];cells=read_box(WORLD,DIM,(x-1,y-1,z-1),(x+1,y+1,z+1));neighbours=[(x+dx,y+dy,z+dz) for dx,dy,dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
  if all(cells.get(p) in AIR for p in neighbours):candidates.append(d)
 report=dict(world=str(WORLD),full_chunks=len(selected),unfinished_chunks_not_treated_as_air=incomplete,sections=sections,measured_cells=sum(counts.values()),non_air=sum(v for k,v in counts.items() if k not in AIR),natural_residue_candidates=candidates,seconds=time.monotonic()-start)
 (OUT/'whole_world_census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'block_counts.json').write_text(json.dumps(dict(counts.most_common()),ensure_ascii=False,indent=2),encoding='utf8')
 print('Complete',sections,'sections; candidates',len(candidates),flush=True)
if __name__=='__main__':main()
