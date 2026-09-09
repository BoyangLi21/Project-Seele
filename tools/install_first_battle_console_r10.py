"""Install a reachable dispatch desk inside the already furnished operations briefing room."""
import json
import regional_voxels as vox
from scan_regional_completion import volume
from survey_world_art_r10 import OUT
if __name__=='__main__':
 p=vox.Painter();lo=(83,-435,273);hi=(86,-430,276);a,pal=volume(lo,hi)
 def old(pos):x,y,z=pos;return pal[a[y-lo[1],z-lo[2],x-lo[0]]]
 for pos,state in [((84,-434,274),'minecraft:smooth_quartz'),((84,-433,274),'projectseele:nerv_workstation[facing=south]')]:
  before=old(pos)
  if before not in {'minecraft:air','minecraft:cave_air'} and before!=state:raise RuntimeError((pos,before))
  p.match((*pos,*pos),before,state,'r10/briefing_dispatch')
 # The sign is mounted directly to the retained briefing display wall.
 assert old((85,-432,273))=='minecraft:black_concrete'
 p.sign(85,-432,274,['第3使徒迎撃','端末を右クリック','初号機 / UNIT-01','東北 迎撃大道'],'r10/briefing_dispatch','south')
 vox.OUT=OUT;p.apply('dispatch_console')
