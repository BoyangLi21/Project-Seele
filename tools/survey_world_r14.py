"""R14 measured material census and command-floor volumes; no world writes."""
import json,time
from collections import Counter
from pathlib import Path
import numpy as np
from regional_voxels import ROOT,WORLD,DIM
from query_blocks import iter_selected_sections,dimension_dir
from inspect_map_assets import iter_chunks
from scan_regional_completion import volume

OUT=ROOT/'artifacts/world_refinement_r14'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 selected={};directory=dimension_dir(WORLD,DIM)
 regions=[tuple(map(int,p.stem.split('.')[1:])) for p in (directory/'region').glob('r.*.*.mca')]
 bounds=(min(x for x,z in regions)*32,max(x for x,z in regions)*32+31,min(z for x,z in regions)*32,max(z for x,z in regions)*32+31)
 for cx,cz,chunk in iter_chunks(directory,bounds):
  if str(chunk.get('Status','')).removeprefix('minecraft:')!='full':continue
  # Metadata only selects sections. All actual block reads use query_blocks.
  sy={int(s['Y']) for s in chunk.get('sections',[]) if any('reinforced_deep' in str(p['Name']) for p in s.get('block_states',{}).get('palette',[]))}
  if sy:selected[cx,cz]=sy
 found=[];counts=Counter();started=time.monotonic()
 for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected):
  for i,s in enumerate(pal):
   if 'reinforced_deep' not in s:continue
   positions=np.argwhere(idx.reshape(16,16,16)==i)
   if not len(positions):continue
   counts[s]+=len(positions);found.append(dict(chunk=[cx,cz],section=sy,state=s,count=len(positions)))
 report=dict(world=str(WORLD),counts=dict(counts),sections=found,seconds=time.monotonic()-started)
 (OUT/'reinforced_before.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print('Reinforced material',dict(counts),'sections',len(found),flush=True)
 for name,lo,hi in [('command',(-12,-449,240),(85,-379,380)),('crown',(0,-398,290),(60,-299,360))]:
  a,pal=volume(lo,hi);np.savez_compressed(OUT/(name+'_before.npz'),blocks=a,palette=pal,lo=lo,hi=hi)
  print(name,'blocks',a.size,'palette',len(pal),flush=True)
if __name__=='__main__':main()
