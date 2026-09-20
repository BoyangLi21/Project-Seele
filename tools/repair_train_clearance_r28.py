"""Remove confirmed body intrusions and lower stepped ballast crowns to half slabs."""
from pathlib import Path
import json,shutil
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/train_repairs'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    source=OUT.parent/'train_shapes/report.json';data=json.loads(source.read_text());assert data['rails']==111
    shutil.copy2(source,OUT/'measured_before.json');kept=removed=0
    for row in data['items']:
        q=tuple(row['position']);old=read_box(WORLD,v.DIM,q,q)[q];assert old==row['state']
        assert not list(iter_block_entities(WORLD,v.DIM,q,q)),('Occupied rail intrusion',q)
        # The sampled track uses a continuous gradient. A full cube can
        # protrude by 0.1m into a bogie although its centre is below the rail.
        # Retain its support with a half slab instead of leaving a hole.
        slab=q[1]<row['rail'][1]-.52
        target='minecraft:smooth_stone_slab[type=bottom,waterlogged=false]' if slab else 'minecraft:air'
        p.match((*q,*q),old,target,'r28/verified_native_train_clearance');kept+=slab;removed+=not slab
    p.meta.update(rails=111,lowered_ballast_crowns=kept,body_intrusions_removed=removed,measured_source=str(source))
    p.apply('native_train_body_clearance')
    (OUT/'contract.json').write_text(json.dumps(p.meta,indent=2));print('Train clearance: half-slab supports',kept,'body obstructions removed',removed,flush=True)

if __name__=='__main__':main()
