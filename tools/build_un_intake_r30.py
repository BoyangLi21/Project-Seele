"""Author the requested UN intake platforms against measured terrain and cage ports."""
from pathlib import Path
import json,argparse
import regional_voxels as v
from query_blocks import read_box,AIR

WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/un_intake'

def main(apply=False):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();receipt=[];retained=[]
    for serial,cx in enumerate([6442,6282]):
        lo=(cx-29,45,-6130);hi=(cx+29,82,-6082)
        cells=read_box(WORLD,v.DIM,lo,hi);desired={}
        # Existing door apron is at Y=77. Stay north of the road at Z=-6080.
        for x in range(cx-27,cx+28):
            for z in range(-6130,-6082):
                for y in [75,76]:
                    desired[x,y,z]='projectseele:nerv_structural_panel' if y==75 else 'minecraft:light_gray_concrete'
                if abs(x-cx)>=26 or z==-6083:
                    desired[x,76,z]='minecraft:yellow_concrete' if (x+z)%6<3 else 'minecraft:black_concrete'
                elif abs(x-cx) in [17,18]:desired[x,76,z]='minecraft:white_concrete'
                elif abs(x-cx)==0 and z%9<4:desired[x,76,z]='minecraft:yellow_concrete'
                for y in range(77,80):
                    old=cells[x,y,z]
                    if old not in AIR and v.natural(old):desired[x,y,z]='minecraft:air'
        # Piers extend down to the surveyed ground, not to an arbitrary Y plane.
        for px in [cx-24,cx,cx+24]:
            for pz in [-6128,-6116,-6104,-6092,-6085]:
                for x in range(px-1,px+2):
                    for z in range(pz-1,pz+2):
                        ground=max((y for y in range(45,75) if cells[x,y,z] not in AIR and v.natural(cells[x,y,z])),default=0)
                        assert ground>=45,(x,z,'unknown foundation')
                        for y in range(ground+1,75):desired[x,y,z]='projectseele:nerv_structural_panel'
        for x in [cx-27,cx+27]:
            for z in range(-6129,-6082):
                desired[x,77,z]='minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]'
        for x in range(cx-26,cx+27):
            desired[x,77,-6083]='minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]'
        for x in [cx-25,cx+25]:
            for z in [-6125,-6113,-6101,-6087]:
                desired[x,77,z]='projectseele:nerv_ceiling_light[hanging=false,lit=true]'
        for q,state in desired.items():
            old=cells[q]
            if old==state:continue
            # Preserve all previous constructed entry-apron flooring and furniture.
            if old not in AIR and not v.natural(old):
                if q[1]<=76:continue
                if 'iron_bars' in state or 'ceiling_light' in state:
                    retained.append({'pos':q,'state':old,'proposed':state});continue
                raise RuntimeError(('conflicting construction',q,old,state))
            p.match((*q,*q),old,state,'r30/un_intake_apron')
        receipt.append({'serial':serial,'eva_foot':[cx+.5,78.6,-6101.5],'deck_floor':77,'bounds':[lo,hi],'lane_port':[cx,77,-6130],'road_protected_z_min':-6081})
        for x in [cx-21,cx+21]:
            p.meta['walk_nodes'].append({'start':[x+.5,77,-6128.5],'end':[x+.5,77,-6086.5],'id':f'un_intake_{serial}_{x}'})
    p.meta['landmarks']=receipt;p.meta['retained_existing_edge']=retained;p.save_plan('un_intake_platforms')
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'ports.json').write_text(json.dumps(receipt,indent=2))
    if apply:p.apply('un_intake_platforms')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
