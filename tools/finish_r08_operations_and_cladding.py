"""Finish the operations-room console rhythm and cover exterior shaft identification bands."""
import numpy as np
import regional_voxels as v
from scan_regional_completion import volume
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT;p=v.Painter()
for x in range(6398,6471,12):
    for z in (-6611,-6598):p.fill(x-1,75,z,x+1,77,z+2,'minecraft:air','r08/operations/retire_wide_spacing','owned')
for x in range(6394,6473,6):
    for z in (-6615,-6606,-6596):
        p.fill(x-1,75,z,x+1,75,z,'minecraft:smooth_quartz','r08/operations/console','owned');p.put(x,76,z,'projectseele:nerv_workstation[facing=south]','r08/operations/console','owned')
        p.put(x,75,z+2,'another_furniture:dark_oak_chair[facing=north,tucked=false,variant=1,waterlogged=false]','r08/operations/chair','owned')
for cx in (-12,30,72):
    lo=(cx-18,-348,-54);hi=(cx+18,24,-18);a,pal=volume(lo,hi)
    sides=[(x,z,x+(1 if x<cx else -1),z) for x in (cx-18,cx+18) for z in range(-54,-17)]
    sides += [(x,z,x,z+(1 if z==-54 else -1)) for z in (-54,-18) for x in range(cx-17,cx+18)]
    for x,z,nx,nz in sides:
        for y in range(-348,25):
            old=pal[a[y-lo[1],z-lo[2],x-lo[0]]];inner=pal[a[y-lo[1],nz-lo[2],nx-lo[0]]]
            outer_colour=old.split('[')[0].endswith('_concrete') and old!='minecraft:black_concrete'
            exposed_band=old in ('minecraft:air','minecraft:cave_air','minecraft:void_air') and (inner.split('[')[0].endswith('_concrete') or inner=='minecraft:sea_lantern')
            if outer_colour or exposed_band:p.match((x,y,z,x,y,z),old,'minecraft:black_concrete','r08/shaft/exterior_band_cover')
p.apply('operations_and_cladding')
