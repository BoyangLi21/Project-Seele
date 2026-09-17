"""Physical caution caps identify the commissioned static guideway to clients."""
import math
import regional_voxels as v
from plan_factory_r20 import guide_y
OUT=v.ROOT/'artifacts/world_rebuild_r20/visual_finish'
def main():
    v.OUT=OUT;p=v.Painter();markers=[]
    for z in (-204,-140,-76):
        q=(9,math.floor(guide_y(z))+4,z);p.match((*q,*q),'projectseele:nerv_machine_panel','projectseele:nerv_machine_hazard','r20/static_guideway_identity');markers.append(q)
    p.meta.update(markers=markers,collision_shape_unchanged=True,scope='Existing machinery separator caps');p.save_plan('static_guideway_markers');print(markers)
if __name__=='__main__':main()
