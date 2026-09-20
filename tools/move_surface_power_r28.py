"""Replace the three north-side reels with registered south-side sockets."""
from pathlib import Path
import json,nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/power'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();rows=[]
    for x in (-12,30,72):
        old=(x,81,-75);new=(x,81,3);state=read_box(WORLD,v.DIM,old,old)[old];assert state=='projectseele:umbilical_pylon'
        p.match((*old,*old),state,'minecraft:air','r28/retired_north_socket')
        box=(x-2,79,1,x+2,83,5);measured=read_box(WORLD,v.DIM,box[:3],box[3:]);assert not list(iter_block_entities(WORLD,v.DIM,box[:3],box[3:])),('Existing fixture at new socket',new)
        for q,s in measured.items():
            X,y,z=q
            target='projectseele:nerv_structural_panel' if y==79 else 'projectseele:nerv_machine_panel' if y==80 else 'minecraft:air'
            if q==new:target=state
            if s!=target:p.match((*q,*q),s,target,'r28/new_south_reel_pad')
        p.block_entities[new]=nbtlib.Compound({'id':nbtlib.String(state),'x':nbtlib.Int(x),'y':nbtlib.Int(81),'z':nbtlib.Int(3)})
        rows.append(dict(before=old,after=new))
    p.meta.update(reels=rows,relative_to_surface_hatch='south/rear, 39 metres from the centre',travelling_rack_supplies_underground=True)
    p.apply('surface_power_south_handoff')
    (OUT/'contract.json').write_text(json.dumps(p.meta,indent=2));(WORLD/'r28_surface_power.json').write_text(json.dumps(dict(reels=rows),indent=2))
    print('Replaced three north sockets with registered south-side reels',flush=True)

if __name__=='__main__':main()
