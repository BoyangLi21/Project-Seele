"""Low-sill viewing glass, supported handrails and coherent wayfinding."""
import json
from pathlib import Path
import regional_voxels as v
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R21_REVIEW';OUT=ROOT/'artifacts/world_repair_r21/details'
def main():
 v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
 def b(box,state,owner):p.fill(*box,state,owner,'owned')
 # A high observation room needs a downward sight line, not merely glass
 # above eye level. Glazed sill/floor strips remain full collision blocks.
 for cx in (-12,30,72):
  for z in (-275,-226):
   b((cx-12,-368,z,cx+12,-363,z),'projectseele:clear_glass','r21/commander_downward_view')
  b((cx-4,-368,-225,cx+4,-368,-224),'projectseele:clear_glass','r21/observer_glazed_sill')
  b((cx-4,-367,-225,cx+4,-366,-224),'minecraft:air','r21/observer_crosswalk_landing')
  for dx in (-5,-3,3,5):
   b((cx+dx,-367,-277,cx+dx,-367,-277),'minecraft:air','r21/clear_window_approach')
   p.put(cx+dx,-367,-285,'projectseele:nerv_workstation[facing=south]','r21/observation_console','owned')
  for dx in (-4,4):
   p.put(cx+dx,-367,-279,'minecraft:air','r21/clear_window_approach','owned')
   p.put(cx+dx,-367,-283,'projectseele:nerv_office_chair[facing=north]','r21/observation_console','owned')
 # The access stair guard sits on a full edge curb rather than on the lower
 # half of a tread, which otherwise leaves a visible gap under the handrail.
 for x in range(325,380):
  f=80 if x<=330 else max(72,80-(x-330)//3)
  for z in (34,42):
   p.put(x,f,z,'projectseele:nerv_floor_panel','r21/airport_access_guard','owned')
   p.put(x,f+1,z,'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]','r21/airport_access_guard','owned')
 # Signs are wall-mounted at named junctions, never suspended over missing
 # platform tiles. Nearby MTR display boards continue to show real departures.
 signs=[(123,-440,239,['发射区 / 机库','双向自动步道','↑ 整备联络车站','↓ 金字塔内部'],'west'),
        (112,-391,-60,['机库中层','↑ 三机登机廊','↓ 电梯 / 发射车站',''],'west'),
        (112,-365,-220,['总指挥观察廊','← 零号 / 初号 / 二号','俯视窗在北侧',''],'west'),
        (35,-464,446,['NERV 总部站','U2 整备联络线','机库 / 发射区方向','由此进站'],'west')]
 for x,y,z,lines,facing in signs:
  support=(x+1,y,z) if facing=='west' else (x,y,z+1)
  p.put(*support,'projectseele:nerv_wall_panel','r21/supported_route_sign','owned');p.sign(x,y,z,lines,'r21/supported_route_sign',facing)
 p.meta.update(downward_sightlines=6,supported_wayfinding=len(signs),walk_nodes=[dict(id='r21/observer/window_unit01',path=[[30.5,-367,-281.5],[30.5,-367,-276.5]])])
 p.apply('observation_views_and_access_guards')
if __name__=='__main__':main()
