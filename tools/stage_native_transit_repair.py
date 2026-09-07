"""Copy the cold current MTR database before bounded native graph changes."""
import json,hashlib,shutil,msvcrt
from datetime import datetime
from pathlib import Path
from regional_voxels import WORLD,ROOT
from quality_structures import OUT,OLD,load

def hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}

def stage():
    source=WORLD/'mtr';target=ROOT/'.Codex/world-quality'/('mtr-native-repair-'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    before=hashes(source);shutil.copytree(source,target)
    if before!=hashes(source) or before!=hashes(target):raise RuntimeError('Cold native transit copy changed')
    inventory=load(OLD/'transit2/native_transit_receipt.json');s1=next(x for x in inventory['lines'] if x['line']=='S1');hakone=next(x['native_id'] for x in inventory['stations'] if x['key']=='hakone_central')
    plan=load(OUT/'estate_transit_draft.json');splice=load(OUT/'airport_rail_splice.json');plan['rails']+=splice['additions'];plan['retire_rails']=splice['retire']
    plan['regenerate_depots']=[dict(line='S1',depot_id=s1['depot_id'],siding_id=s1['siding_id'])]
    for station in plan['stations']:
        if station['id']=='S2_hakone':station['existing_id']=hakone
    plan_file=OUT/'native_transit_repair_plan.json';plan_file.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest=dict(source=str(source),stage=str(target),source_hashes=before,plan=str(plan_file),expected_rails=112,expected_routes=8)
    (OUT/'native_transit_repair_stage.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Cold MTR copy',target,'files',len(before),'expected rails112/routes8',flush=True)

if __name__=='__main__':stage()
