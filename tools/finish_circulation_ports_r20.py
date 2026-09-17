"""Open explicit stair/gallery ports after their enclosing shells are finished."""
from pathlib import Path
import regional_voxels as v
from build_transit_civil_r20 import ff,AIR
OUT=v.ROOT/'artifacts/world_rebuild_r20/circulation_ports'
def main():
    OUT.mkdir(exist_ok=True);v.OUT=OUT;p=v.Painter()
    p.protect((89,-446,-56,99,-364,-48),'retained_compact_lift_shell',('owned',))
    # Restore the small outer-shell corner touched by the earlier connector
    # draft. These cells are outside the travelling car and contain no control.
    from query_blocks import read_box
    original=read_box(v.WORLD,v.DIM,(96,-394,-49),(99,-389,-48))
    review=read_box(v.ROOT/'run/saves/SEELE_R20_REVIEW',v.DIM,(96,-394,-49),(99,-389,-48))
    for q,state in original.items():
        if review[q]!=state:p.match((*q,*q),review[q],state,'r20/factory/restore_retained_lift_shell')
    for x,y,zs in [(-78,100,[-200,-168,-136]),(-1438,124,[640,672]),(56,-461,[490,522])]:
        for z in zs:
            for side in (-12,12):ff(p,(x-3,y+1,z+side-2,x-3,y+4,z+side+2),AIR,'r20/interchange/stair_port')
    ff(p,(96,-394,-264,102,-390,-261),AIR,'r20/factory/front_gallery_port')
    ff(p,(96,-389,-264,103,-389,-261),'projectseele:nerv_structural_panel','r20/factory/front_port_roof')
    ff(p,(96,-394,-49,102,-390,-46),AIR,'r20/factory/middle_lift_port')
    ff(p,(100,-394,-60,102,-390,-46),AIR,'r20/factory/compact_lift_east_bypass')
    ff(p,(100,-395,-60,102,-395,-46),'projectseele:nerv_floor_panel','r20/factory/compact_lift_bypass_floor')
    ff(p,(100,-389,-60,103,-389,-46),'projectseele:nerv_structural_panel','r20/factory/compact_lift_bypass_roof')
    ff(p,(104,-442,-49,110,-438,-46),AIR,'r20/factory/lower_lift_port')
    for state in ('minecraft:gray_concrete','minecraft:polished_deepslate'):
        p.match((6331,77,-6134,6333,80,-6104),state,AIR,'r20/un01/retire_old_apron_curb')
    p.meta.update(interchange_stair_ports=14,factory_gallery_ports=3,old_curb_removed=True,lift_bypass_uses_x101_5=True)
    p.save_plan('final_ports')
if __name__=='__main__':main()
