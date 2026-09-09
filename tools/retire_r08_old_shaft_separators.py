"""Remove the two old inter-silo walls missed by R02's three +/-18 relocation boxes."""
import json
import numpy as np
import regional_voxels as v
from scan_regional_completion import volume
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT;p=v.Painter();counts={}
allowed={'minecraft:reinforced_deepslate','minecraft:orange_concrete','minecraft:purple_concrete','minecraft:red_concrete','minecraft:sea_lantern','minecraft:iron_block','minecraft:polished_basalt'}
for x0 in (7,49):
    lo=(x0,-349,207);hi=(x0+4,79,237);a,pal=volume(lo,hi);count=0
    for iy,iz,ix in np.argwhere(np.array([s.split('[')[0] in allowed for s in pal])[a]):
        x,y,z=ix+x0,iy-349,iz+207;old=pal[a[iy,iz,ix]]
        p.match((x,y,z,x,y,z),old,'minecraft:air' if y<=24 else 'minecraft:stone','r08/retire_old_inter_silo_wall');count+=1
    counts[str(x0)]=count
p.meta.update(provenance='tools/relocate_regional_eva.py BOXES left gaps X7..11 and49..53 between the three retired original launch shafts at Z203..237. Actual active shafts are at Z-53..-19.',retired_cells=counts,surface_y80_and_above_preserved=True,public_lift_preserved=True)
p.apply('old_shaft_separators')
(OUT/'facilities/old_shaft_cleanup.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
