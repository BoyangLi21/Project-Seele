"""Repair the observed upper-shaft obstruction and four unsupported wall signs."""
import copy
import nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
def main():
 v.WORLD=v.ROOT/'run/saves/SEELE_R21_REVIEW';v.OUT=v.ROOT/'artifacts/world_repair_r21/details';p=v.Painter()
 # Actual survival passenger damage was inWall at Y=71.05. The shallow
 # foyer foundation had left one complete solid layer across the old shaft.
 for q,s in read_box(v.WORLD,v.DIM,(127,72,270),(133,72,276)).items():
  assert s=='projectseele:nerv_structural_panel',(q,s)
  p.match((*q,*q),s,'minecraft:air','r21/clear_upper_native_cabin_sweep')
 for old,new,facing,back in [((124,77,268),(124,77,266),'south',(124,77,265)),((537,88,26),(511,80,26),'north',(511,80,27)),((637,88,26),(611,80,26),'north',(611,80,27))]:
  before=read_box(v.WORLD,v.DIM,old,old)[old];assert before.startswith('minecraft:oak_wall_sign[')
  assert read_box(v.WORLD,v.DIM,new,new)[new].split('[')[0] in AIR
  assert read_box(v.WORLD,v.DIM,back,back)[back].split('[')[0] not in AIR
  tag=copy.deepcopy(dict(iter_block_entities(v.WORLD,v.DIM,old,old))[old])
  for k,value in zip(('x','y','z'),new):tag[k]=nbtlib.Int(value)
  p.match((*old,*old),before,'minecraft:air','r21/remount_sign_on_existing_wall')
  p.put(*new,f'minecraft:oak_wall_sign[facing={facing},waterlogged=false]','r21/remount_sign_on_existing_wall','owned');p.block_entities[new]=tag
 # Continuous lintel above a five-metre-clear pedestrian terminal opening.
 for q,s in read_box(v.WORLD,v.DIM,(385,78,38),(390,78,38)).items():
  assert s.split('[')[0] in AIR
  p.match((*q,*q),s,'projectseele:nerv_structural_panel','r21/terminal_sign_lintel')
 p.meta.update(native_collision_source='r20_lift_review.json: inWall, Y=71.05, known structural layer at Y=72',shaft_cells=49,unsupported_signs_fixed=4)
 p.apply('upper_shaft_and_supported_wayfinding')
if __name__=='__main__':main()
