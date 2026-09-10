"""Second visual pass after the first native photographs of the new roof room."""
import json,math
import regional_voxels as vox
from refine_architecture_r14 import Measured,OUT,FLOOR
def main():
 vox.OUT=OUT;p=vox.Painter();m=Measured(p,(4,-390,278),(52,-383,363));o='r14/reception_details'
 # The imported piano has a bright blue backing. Refinish that backing while
 # retaining the keys, shutters, pedals and the moved lectern's book.
 for y in range(-390,-386):
  for z in range(353,361):
   for x in range(10,15):
    pos=x,y,z
    if m.old(pos)=='minecraft:blue_concrete':m.put(pos,'minecraft:black_concrete',o+'/piano_finish')
 for x0,z0,x1,z1 in [(6,285,21,299),(34,285,49,299),(34,342,49,360)]:
  m.box((x0,-389,z0),(x1,-389,z1),'minecraft:gray_carpet',o+'/seating_rug',True)
 # Clusters stay out of both main axes; planters make the large waiting bays legible.
 for x,z in [(22,298),(33,298),(22,334),(33,334),(8,337),(48,319)]:
  m.box((x,-389,z),(x+1,-389,z+2),'minecraft:polished_blackstone',o+'/planter',True)
  m.box((x,-388,z),(x+1,-388,z+2),'minecraft:oak_leaves[distance=1,persistent=true,waterlogged=false]',o+'/planter',True)
 for x in range(25,32):
  m.put((x,-389,326),'projectseele:nerv_storage_panel[facing=south]',o+'/reception_desk',True)
  m.put((x,-388,326),'minecraft:smooth_quartz_slab[type=top,waterlogged=false]',o+'/reception_desk',True)
 m.put((28,-387,326),'projectseele:nerv_workstation[facing=south]',o+'/desk_terminal',True)
 for row in range(4):
  for col in range(12):m.put((22+col,-385-row,363),f'projectseele:nerv_briefing_tile[part={row*12+col}]',o+'/status_wall')
 m.flush();p.meta.update(visual_basis='Native r14 roof photos; piano backing and empty centre',protected_aisles='north-south X28 and east gallery Z340');p.apply('reception_details')
 # Front three-quarter instrument view, rather than photographing its back.
 path=vox.WORLD/'r07_photo_views.json';views=json.loads(path.read_text())
 for view in views:
  if view['file']=='r14_roof_piano.png':
   pos=[18,-388,362];target=[12,-388,357];dx,dy,dz=target[0]-pos[0],target[1]-pos[1]-1.62,target[2]-pos[2];view.update(position=pos,yaw=math.degrees(math.atan2(-dx,dz)),pitch=math.degrees(math.atan2(-dy,math.hypot(dx,dz))))
 path.write_text(json.dumps(views,indent=2))
 states=set(json.loads((vox.WORLD/'regional_states.json').read_text()));states.update(o.state for o in p.ops);(vox.WORLD/'regional_states.json').write_text(json.dumps(sorted(states),indent=2))
if __name__=='__main__':main()
