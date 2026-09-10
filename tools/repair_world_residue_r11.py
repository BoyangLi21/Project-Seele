"""Retire detached natural fragments verified in 3D; preserve imported ship detail and connected geology."""
import json
from collections import deque
import regional_voxels as vox
from query_blocks import read_box,AIR
OUT=vox.ROOT/'artifacts/world_motion_r11/map'
def main():
 data=json.loads((OUT/'whole_world_census.json').read_text());p=vox.Painter();seen=set();decisions=[]
 for item in data['natural_residue_candidates']:
  pos=tuple(item['pos']);x,y,z=pos
  if pos in seen:continue
  if 1428<=x<=1510 and 325<=z<=570:
   decisions.append(dict(item,decision='preserved',detail='Repeated authored detail on the two imported destroyers'));continue
  lo=(x-5,y-5,z-5);hi=(x+5,y+5,z+5);cells=read_box(vox.WORLD,vox.DIM,lo,hi);component=set();q=deque([pos])
  while q:
   at=q.popleft()
   if at in component or cells.get(at,'UNKNOWN') in AIR or at not in cells:continue
   component.add(at)
   for dx in (-1,0,1):
    for dy in (-1,0,1):
     for dz in (-1,0,1):
      if dx or dy or dz:q.append((at[0]+dx,at[1]+dy,at[2]+dz))
  seen.update(component)
  detached=0<len(component)<=8 and all(cells[k] in ['minecraft:stone','minecraft:dirt','minecraft:gravel','minecraft:sand'] for k in component) and all(all(lo[i]<k[i]<hi[i] for i in range(3)) for k in component)
  if detached:
   for k in sorted(component):p.match((*k,*k),cells[k],'minecraft:air','r11/global_scan/detached_natural_fragment')
   decisions.append(dict(item,decision='retired',component=sorted(component)))
  else:decisions.append(dict(item,decision='preserved',detail='Connected structure or geology extends beyond the isolated six-neighbour observation',component_size=len(component)))
 p.meta['decisions']=decisions;vox.OUT=OUT;p.apply('detached_fragments')
 (OUT/'residue_decisions.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2),encoding='utf8');print('Retired',len(p.ops),'verified isolated cells')
if __name__=='__main__':main()
