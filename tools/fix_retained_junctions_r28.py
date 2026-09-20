"""Restore measured internal portals caught by the full-world route regression."""
from pathlib import Path
import json
import regional_voxels as v
from query_blocks import read_box
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';ART=ROOT/'artifacts/facility_r28';OUT=ART/'retained_junctions'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    baseline=Path(json.loads((ART/'baseline.json').read_text())['backup'])/'world'
    def clear(lo,hi):
        for q,old in read_box(WORLD,v.DIM,lo,hi).items():
            if old!='minecraft:air':p.match((*q,*q),old,'minecraft:air','r28/retained_enclosed_personnel_port')
    # This passage opens into the existing sealed middle observer gallery,
    # not outdoors or into the retired lower blind hall.
    clear((96,-394,-55),(112,-389,-55))
    for z in (395,403):clear((87,-461,z),(91,-458,z))
    # Preserve the original science return stair, including its headroom.
    lo=(194,-469,539);hi=(198,-456,546)
    old=read_box(baseline,v.DIM,lo,hi);now=read_box(WORLD,v.DIM,lo,hi)
    for q,state in old.items():
        if state!=now[q]:p.match((*q,*q),now[q],state,'r28/retain_measured_south_return_stair')
    p.meta.update(portals=[[(96,-394,-55),(112,-389,-55)],[(87,-461,395),(91,-458,395)],[(87,-461,403),(91,-458,403)]],restored_original_stair=[lo,hi])
    p.apply('retained_gallery_spine_and_stair_ports')
    (OUT/'contract.json').write_text(json.dumps(p.meta,indent=2))
    print('Restored enclosed gallery door, headquarters through-junction and original science stair',flush=True)

if __name__=='__main__':main()
