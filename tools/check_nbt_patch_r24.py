"""Exercise an NBT-only edit and a rejected stale edit in an isolated one-region fixture."""
from pathlib import Path
import copy,datetime,hashlib,json,shutil,nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;BASE=ROOT/'backups/SEELE_R24_20260919_003327/world';OUT=ROOT/'artifacts/facility_r24/validation/nbt_patch'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    home=OUT/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');world=home/'fixture';world.mkdir(parents=True)
    row=json.loads((ROOT/'artifacts/facility_r23/navigation_final/junctions.json').read_text(encoding='utf8'))['boards'][0];pos=tuple(row['position'])
    relative=Path('dimensions/projectseele/geofront/region')/f'r.{pos[0]//512}.{pos[2]//512}.mca';target=world/relative;target.parent.mkdir(parents=True);shutil.copy2(BASE/relative,target)
    (world/'session.lock').write_bytes(b'\xe2\x98\x83');v.WORLD=world;v.OUT=home/'journal'
    state=read_box(world,v.DIM,pos,pos)[pos];before=dict(iter_block_entities(world,v.DIM,pos,pos))[pos];after=copy.deepcopy(before);after['Station']=nbtlib.String('NBT fixture only')
    painter=v.Painter();painter.update_block_entity(pos,state,before,after,'isolated_nbt_test');receipt=painter.apply('positive')
    assert receipt['counts']['cells']==0 and receipt['counts']['block_entities']==1
    assert read_box(world,v.DIM,pos,pos)[pos]==state
    assert dict(iter_block_entities(world,v.DIM,pos,pos))[pos].snbt()==after.snbt()
    oldhash=digest(target);painter=v.Painter();painter.update_block_entity(pos,state,before,after,'stale_nbt_test');rejected=False
    try:painter.apply('stale')
    except RuntimeError as error:
        assert 'NBT precondition changed' in str(error),str(error);rejected=True
    assert rejected and digest(target)==oldhash
    result=dict(passed=True,zero_voxel_edit=True,one_tag_changed=True,stale_tag_rejected=True,rejected_file_unchanged=True,fixture=str(world))
    (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
