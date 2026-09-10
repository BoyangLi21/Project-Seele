"""Bring the new connector ceiling down with its measured stairs after native visual review."""
import numpy as np
import regional_voxels as vox
from refine_architecture_r14 import Measured,OUT,PANEL,LIGHT
def main():
 vox.OUT=OUT;p=vox.Painter();m=Measured(p,(53,-395,338),(76,-384,342));original=np.load(OUT/'command_before.npz');a,pal,lo=original['blocks'],original['palette'],original['lo']
 for x in range(53,76):
  f=-390 if x<=58 else -390-(x-58) if x<=60 else -393;ceiling=f+4
  for z in range(338,343):
   if 58<=x<=60 and z in (339,340,341):
    m.put((x,f-1,z),'projectseele:nerv_floor_panel','r14/connector/stair_support')
    m.put((x,f,z),'minecraft:smooth_quartz_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]','r14/connector/stair_rise')
   for y in range(ceiling+1,-383):m.put((x,y,z),str(pal[a[y-lo[1],z-lo[2],x-lo[0]]]),'r14/connector/retire_tall_shell')
   m.put((x,ceiling,z),LIGHT if z==340 and x%5==0 else PANEL,'r14/connector/continuous_ceiling')
 # The taller existing gallery receives a solid fascia above the new doorway.
 for z in range(338,343):m.put((75,-388,z),PANEL,'r14/connector/end_fascia')
 m.flush();p.meta.update(ceiling_clearance='3m above each full stair tread',existing_upper_gallery_preserved=True);p.apply('gallery_ceiling')
 p=vox.Painter();m=Measured(p,(4,-390,278),(52,-382,363))
 for z in range(278,364):
  for x in range(4,53):
   if not(25<=x<=31 and 313<=z<=324):m.put((x,-390,z),'projectseele:nerv_floor_panel','r14/reception/continuous_floor')
 # Refinish the imported stone columns inside this new room, keeping their exact geometry.
 for y in range(-389,-381):
  for z in range(278,364):
   for x in range(4,53):
    pos=x,y,z
    if m.get(pos) in {'minecraft:polished_deepslate','minecraft:deepslate_bricks','minecraft:deepslate_tiles','minecraft:polished_blackstone_bricks'}:m.put(pos,'minecraft:black_concrete','r14/reception/painted_columns')
 m.flush();p.meta.update(floor_bounds=[4,-390,278,52,-390,363],shaft_sweep_preserved=True);p.apply('reception_floor')
if __name__=='__main__':main()
