"""TV cage bridge proportions and the entire transfer-hall finish, preserving authored routes."""
import argparse
import regional_voxels as v
from scan_regional_completion import volume
import numpy as np

OUT=v.ROOT/'artifacts/tv_facilities_r16';GREEN='projectseele:nerv_machine_panel';BLUE='projectseele:nerv_shaft_panel';EDGE='projectseele:nerv_machine_edge'

def main(apply=False):
 p=v.Painter();v.OUT=OUT/'map';lo=(-32,-445,-127);hi=(92,-350,-17);a,q=volume(lo,hi)
 def old(x,y,z):return q[int(a[y-lo[1],z-lo[2],x-lo[0]])]
 def put(x,y,z,new,owner):p.match((x,y,z,x,y,z),old(x,y,z),new,'r16/'+owner)
 # These are the measured front observation tongues. The ring keeps a full
 # rear crossing for the dummy and two two-block-wide side walkways.
 for cx in (-12,30,72):
  for z in range(-115,-107):
   for x in range(cx-5,cx+6):
    assert old(x,-395,z) in (GREEN,EDGE,'minecraft:sea_lantern','minecraft:polished_deepslate'),(x,z,old(x,-395,z))
    assert old(x,-394,z) in ('minecraft:air','minecraft:light[level=15,waterlogged=false]'),(x,z,old(x,-394,z))
    put(x,-395,z,'minecraft:air','cage/retire_oversized_tongue')
  for side in (-1,1):
   x=cx+side*6
   for z in range(-115,-107):
    put(x,-395,z,EDGE,'cage/ring_beam')
    put(x,-394,z,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]','cage/inner_guardrail')
  for z in (-116,-107):
   for x in range(cx-5,cx+6):
    put(x,-395,z,'projectseele:nerv_machine_hazard','cage/witness_band')
    put(x,-394,z,'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]','cage/inner_guardrail')
 # Material-only correction of the old transfer floor, partitions and plant
 # galleries. Lodestones, barriers, lifts, windows and equipment are excluded.
 replacements={'minecraft:polished_deepslate':GREEN,'minecraft:polished_blackstone_bricks':BLUE,'minecraft:deepslate_bricks':BLUE,'minecraft:deepslate_tiles':BLUE,'minecraft:gray_concrete':GREEN,'minecraft:orange_concrete':GREEN,'minecraft:purple_concrete':GREEN,'minecraft:red_concrete':GREEN}
 for z in range(-68,-16):
  for y in range(-444,-349):
   for x in range(-32,93):
    s=old(x,y,z)
    if s in replacements:put(x,y,z,'projectseele:nerv_floor_panel' if y<=-443 else replacements[s],'transfer/finish')
 # Rear bridge colour is also maintained by personnelDeck at runtime.
 for cx in (-12,30,72):
  for z in range(-80,-70):
   for x in range(cx-18,cx+19):
    if not lo[0]<=x<=hi[0]:continue
    s=old(x,-395,z)
    if s in {'minecraft:smooth_stone','minecraft:purple_terracotta','minecraft:orange_terracotta','minecraft:red_terracotta'}:
     put(x,-395,z,EDGE if (x+z)%5==0 else GREEN,'cage/boarding_deck')
 p.meta.update(removed_tongue_cells=264,unchanged_dummy_crossing_z=-120,side_walkways_width=2,nose_walkway_width=3)
 p.apply('cage_architecture') if apply else p.save_plan('cage_architecture')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
