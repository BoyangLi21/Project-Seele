"""Preserve the full stair well after the level-corridor unions are finished."""
from pathlib import Path
import json
import regional_voxels as v
from query_blocks import read_box
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R21_REVIEW';OUT=ROOT/'artifacts/world_repair_r21/details'
def main():
 v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();o='r21/six_riser_well';wall='projectseele:nerv_structural_panel'
 def b(box,state):p.fill(*box,state,o,'owned')
 for x in (109,115):b((x,-449,248,x,-437,255),wall)
 b((109,-436,248,115,-436,255),wall)
 for i in range(6):
  y=-448+i;z=254-i;b((110,-449,z,114,y-1,z),wall);b((110,y,z,114,y,z),'minecraft:smooth_quartz_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]');b((110,y+1,z,114,-437,z),'minecraft:air')
 b((110,-443,247,114,-443,248),'projectseele:nerv_floor_panel');b((110,-442,247,114,-437,248),'minecraft:air')
 b((110,-449,255,114,-449,256),'projectseele:nerv_floor_panel');b((110,-448,255,114,-444,256),'minecraft:air')
 # Invisible installation receipts are not geometry residue. Retain them so
 # an older maintenance path cannot interpret retirement as unbuilt terrain.
 base=json.loads((OUT.parent/'baseline.json').read_text());cold=Path(base['backup'])/'world'
 a=read_box(cold,v.DIM,(146,-448,254),(164,-448,257));c=read_box(WORLD,v.DIM,(146,-448,254),(164,-448,257));n=0
 for q,s in a.items():
  if s=='minecraft:structure_void' and c[q]!=s:p.match((*q,*q),c[q],s,'r21/preserve_construction_receipts');n+=1
 p.meta.update(vertical_connection=dict(lower=[112,-448,255],upper=[112,-442,247],risers=6,full_headroom=True),construction_receipts_restored=n)
 p.apply('stair_void_and_authority_receipts')
if __name__=='__main__':main()
