"""Resolve the final scan's 32 natural remnants and three control-label backings."""
import gzip,json,math
import numpy as np
from scipy.spatial.transform import Rotation
import regional_voxels as v
from query_blocks import read_box,AIR,iter_block_entities
OUT=v.ROOT/'artifacts/world_rebuild_r20/final_cleanup';REVIEW=v.ROOT/'run/saves/SEELE_R20_REVIEW'
def main():
    OUT.mkdir(exist_ok=True);v.OUT=OUT;p=v.Painter();root=OUT.parent
    scan=json.loads((root/'global_components_final/contact_classification.json').read_text())
    with gzip.open(root/'global_components_final/isolated_soil_points.json.gz','rt') as f:soil=json.load(f)
    assert len(soil)==32 and not scan['cells_by_class'].get('isolated_vegetation',0)
    for row in soil:
        q=tuple(row['pos']);assert read_box(REVIEW,v.DIM,q,q)[q]==row['state'];p.match((*q,*q),row['state'],'minecraft:air','r20/final_isolated_natural_remnant')
    members=json.loads((REVIEW/'r08_native_details.json').read_text())['members'];retained=[]
    for row in scan['groups']:
        if row['kind']!='isolated_structure':continue
        lo,hi=np.asarray(row['lo']),np.asarray(row['hi']);reason=None
        if row['cells']==920 and row['lo']==[19,-443,313]:reason='Original command display/light volume, explicitly preserved'
        elif row['cells']==782:
            z=370 if lo[2]<400 else 510;legs=[m for m in members if m['key'].startswith(f'crane/{z}/leg/')];assert len(legs)==4
            for m in legs:
                a=np.asarray(m['position']);b=a+Rotation.from_quat(m['rotation']).apply([0,0,m['scale'][2]]);assert np.all(b>=lo) and np.all(b<=hi+1)
                foot=tuple(map(math.floor,a));assert read_box(REVIEW,v.DIM,foot,foot)[foot]=='minecraft:yellow_terracotta'
            reason='Deck supported by four continuous modelled steel crane legs verified at real quay foundations'
        elif row['cells']==24:
            z=int(lo[2]);assert any(m['key']==f'crane/{z}/hoist/0' for m in members);reason='Crane hook suspended from the modelled hoist'
        elif row['cells']==15 and set(row['states'])=={'minecraft:structure_void'}:reason='Invisible noncolliding construction markers'
        assert reason,('Unresolved isolated structure',row)
        retained.append(dict(lo=row['lo'],hi=row['hi'],cells=row['cells'],reason=reason))
    inventory=json.loads((root/'inventory_final/world_objects.json').read_text(encoding='utf8'));labels=[q for q in inventory['objects']['signs'] if q['unsupported']];assert len(labels)==3
    for row in labels:
        q=tuple(row['pos']);assert q[0] in (6234,6238,6246) and q[1:]==(80,-6141)
        backing=(q[0],80,-6140);assert read_box(REVIEW,v.DIM,backing,backing)[backing] in {'minecraft:gray_stained_glass','projectseele:nerv_wall_panel'}
        p.match((*q,*q),row['state'],row['state'].replace('facing=south','facing=north'),'r20/control_label_faces_existing_fixed_wall')
    p.meta.update(removed_natural_cells=32,corrected_labels=labels,retained=retained,unclassified_isolated_structures=0,unsupported_natural_after_patch=0,full_scan_regions=136,full_scan_chunks=39445,incremental_proof='Deleting isolated components cannot detach a different component; three label facings now use the existing fixed control wall')
    p.save_plan('final_residue_and_label_supports')
if __name__=='__main__':main()
