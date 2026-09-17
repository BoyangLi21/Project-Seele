"""Independent frozen-world identity, transport, glazing and layout checks."""
from pathlib import Path
import json,hashlib
import numpy as np
from query_blocks import AIR,iter_block_entities
import scan_regional_completion as scan
from transplant_s22_authority import read_region,parse_chunk

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r19'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def actors(world):
    result={}
    for path in (world/'dimensions/projectseele/geofront/entities').glob('r.*.*.mca'):
        if path.stat().st_size==0:continue
        _,chunks=read_region(path)
        for blob in chunks:
            if blob is None:continue
            for e in parse_chunk(blob).get('Entities',[]):
                key=tuple(map(int,e['UUID']));assert key not in result;result[key]=hashlib.sha256(e.snbt().encode()).hexdigest()
    return result
def tree_hashes(folder):return {str(p.relative_to(folder)):digest(p) for p in folder.rglob('*') if p.is_file()}
def main():
    baseline=json.loads((OUT/'baseline.json').read_text());world=Path(baseline['world']);backup=Path(baseline['backup']);checks={}
    for file,expected in baseline['user_files'].items():assert digest(ROOT/file)==expected,file
    checks['original_user_resource_hashes_unchanged']=len(baseline['user_files'])
    before,after=actors(backup),actors(world);removed=set(before)-set(after);added=set(after)-set(before)
    assert len(removed)==9 and not added;assert all(before[k]==after[k] for k in after)
    checks['entities']={'unchanged':len(after),'retired_exact_wayfinding_entities':len(removed),'new_entities':0}
    for relative in ('mtr','playerdata','advancements','stats'):
        assert tree_hashes(backup/relative)==tree_hashes(world/relative),relative
        checks[relative+'_unchanged']=True
    for relative in ('data/projectseele_eva_fleet.dat','dimensions/projectseele/geofront/data/projectseele_military_r07.dat','dimensions/projectseele/geofront/data/projectseele_staff_r15.dat'):
        assert digest(world/relative)==digest(backup/relative),relative
    checks['fleet_military_staff_saved_data_unchanged']=True
    scan.WORLD=world;a,p=scan.volume((6,-329,303),(54,-315,351));panes=int(np.array([s.startswith('projectseele:one_way_glass') and 'pyramid=true' in s for s in p])[a].sum())
    entities=sum(str(t['id'])=='projectseele:one_way_glass' for _,t in iter_block_entities(world,'projectseele:geofront',(6,-329,303),(54,-315,351)))
    assert panes==entities==2344;checks['one_way_window_blocks_and_entities']=panes
    def structural(s):return s.split('[')[0] not in AIR|{'minecraft:light'} and not any(word in s for word in ('_button[','_sign['))
    lo=(-2,-444,244);hi=(60,-389,366);scan.WORLD=backup;b,bp=scan.volume(lo,hi);scan.WORLD=world;a,ap=scan.volume(lo,hi)
    old=np.array([structural(s) for s in bp])[b];new=np.array([structural(s) for s in ap])[a]
    changed={(int(x+lo[0]),int(y+lo[1]),int(z+lo[2])) for y,z,x in np.argwhere(old!=new)}
    allowed={(29,-403,256),(30,-403,256)}|{(x,-403,257) for x in (26,27,29,30)}
    assert changed==allowed,changed
    checks['main_command_layout']={'preserved':True,'only_occupancy_changes':'Six explicitly repaired escalator landing/fence cells','cells':sorted(changed)}
    old=dict(iter_block_entities(backup,'projectseele:geofront',(12,-388,356),(12,-388,356)));new=dict(iter_block_entities(world,'projectseele:geofront',(12,-388,356),(12,-388,356)))
    assert old and all(old[k].snbt()==new[k].snbt() for k in old);checks['piano_book_preserved']=True
    (OUT/'preservation.json').write_text(json.dumps({'passed':True,'world':str(world),'checks':checks},indent=2));print(checks)

if __name__=='__main__':main()
