"""Close the measured exterior skin of the retained east lift interface."""
import json
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/skin_finish'

def main():
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();positions=set()
    for y in range(-449,-433):
        for z in range(265,282):positions.add((137,y,z))
        for x in range(128,138):
            for z in (265,281):positions.add((x,y,z))
    # Only the skirt outside the original seven-by-seven moving cabin gets a
    # cap. The shaft, controller and all vertical travel remain unobstructed.
    for x in range(128,138):
        for z in range(265,282):
            if not (127<=x<=133 and 269<=z<=277):positions.add((x,-433,z))
    blocks=read_box(WORLD,v.DIM,(127,-450,264),(138,-432,282));tags=dict(iter_block_entities(WORLD,v.DIM,(127,-450,264),(138,-432,282)))
    allowed={'minecraft:air','minecraft:gray_concrete','minecraft:black_concrete','minecraft:orange_concrete','minecraft:light_gray_concrete','minecraft:smooth_stone','minecraft:polished_deepslate','minecraft:polished_blackstone','projectseele:nerv_structural_panel','projectseele:nerv_floor_panel','projectseele:nerv_wall_panel','projectseele:nerv_machine_panel','projectseele:nerv_pyramid_panel'}
    for q in sorted(positions):
        old=blocks[q];assert q not in tags and not old.startswith(('movingelevators:','mtr:')),('Functional housing boundary',q,old)
        assert old in allowed,('Unclassified housing boundary',q,old)
        if old!='projectseele:nerv_pyramid_panel':p.match((*q,*q),old,'projectseele:nerv_pyramid_panel','r25/retained_lift_exterior_enclosure')
    p.meta.update(kept_cabin=dict(x=[127,133],z=[269,277],size=[7,6,7]),preserved_controller=[130,-442,269],purpose='Opaque continuous outer skirt around the retained lift; west interior access preserved',public_route_intersections=0)
    p.apply('retained_east_lift_skin');(OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':main()
