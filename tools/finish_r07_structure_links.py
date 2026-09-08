"""Measured final structure links after the first R07 construction pass."""
import json
import numpy as np
import regional_voxels as vox
from scan_regional_completion import volume
from regional_architecture import stairs

OUT=vox.ROOT/'artifacts/world_expansion_r07';vox.OUT=OUT
p=vox.Painter();FLOOR='projectseele:nerv_floor_panel';DARK='minecraft:gray_concrete';AIR='minecraft:air';LIGHT='projectseele:nerv_strip_light'
def replace(box,state):
    a,pal=volume(box[:3],box[3:]);lo=box[:3]
    for y,z,x in np.ndindex(a.shape):
        old=pal[a[y,z,x]]
        if old!=state:
            pos=(int(x+lo[0]),int(y+lo[1]),int(z+lo[2]));p.match((*pos,*pos),old,state,'r07/final_structure_links')
# Keep the top return flight open while connecting the side gallery.
replace((6473,126,-6252,6486,126,-6251),AIR)
for x in (6419,6460):
    replace((x,126,-6252,x+5,126,-6233),FLOOR)
    pole=x if x==6419 else x+5
    for z in range(-6228,-6141,16):
        replace((x+2,134,z,x+2,134,z),AIR)
        replace((pole,77,z,pole,132,z),DARK)
        replace((min(pole,x+2),132,z,max(pole,x+2),132,z),DARK)
        replace((x+2,131,z,x+2,131,z),LIGHT)
# Put back the final stair where the too-wide link slab had covered it.
stairs(p,6482,-6255,121,5,'south','r07/restore_top_return_flight',3,'owned')
# High roof trusses stay above the experimental airframe and the personnel tower.
for z in range(-6276,-6145,24):
    p.fill(6385,155,z,6499,157,z+1,DARK,'r07/roof_truss','air')
    for x in (6385,6499):p.fill(x,77,z,x,159,z+1,DARK,'r07/roof_column','air')
p.apply('structure_links')
cases=json.loads((OUT/'secret_walk_cases.json').read_text(encoding='utf8'))
for case in cases:
    if case['id']=='r07/secret/gantry':case['path']=[[6480.5,127,-6249.5],[6462.5,127,-6249.5],[6462.5,127,-6217.5],[6442.5,127,-6217.5]]
    if case['id']=='r07/secret/gantry/return':case['path']=[[6442.5,127,-6217.5],[6462.5,127,-6217.5],[6462.5,127,-6249.5],[6480.5,127,-6249.5]]
    if '/secret/main_hangar/entry' in case['id']:case['runtime_only']='drain_and_open_gate'
(OUT/'secret_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
