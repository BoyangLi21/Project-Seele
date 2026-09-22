"""Remove the five-block south lip omitted by the R20 cage relocation mask."""
import argparse,json
import regional_voxels as v
import scan_regional_completion as scan
import numpy as np

WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/retired_cage_lip'
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;scan.WORLD=WORLD;p=v.Painter()
    lo=(-40,-512,-150);hi=(104,-443,-146);a,pal=scan.volume(lo,hi,allow_unknown=True)
    states=['minecraft:polished_deepslate','minecraft:deepslate_bricks'];counts={s:int((a==pal.index(s)).sum()) for s in states if s in pal}
    assert counts.get(states[0],0)>600 and counts.get(states[1],0)>40000,counts
    # R20 copied/cleared Z=-145..-70. This isolated five-row lip precedes that
    # exact mask. The replacement incline's own posts at Z=-152/-151 remain.
    for s in states:p.match((*lo,*hi),s,'minecraft:air','r30/retired_original_cage_south_lip')
    p.meta.update(landmarks=[{'id':'retired_original_cage_south_lip','bounds':[lo,hi],'original_mask_source':'tools/plan_factory_r20.py SOURCE=(-40,-467,-145,104,-350,-70)','reason':'Five-row remnant outside the retired cage copy/clear mask; no registered public route uses it','preserve':'All new NERV material states, ramp trenches, perimeter columns at Z=-152/-151 and natural GeoFront ground'}],old_counts=counts)
    p.save_plan('retire_original_cage_lip')
    if apply:p.apply('retire_original_cage_lip')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
