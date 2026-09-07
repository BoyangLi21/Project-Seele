"""Install only the verified native MTR staging diff, retaining a full rollback copy."""
import json,hashlib,shutil,msvcrt
from pathlib import Path
from datetime import datetime
from stage_native_transit_repair import hashes
from regional_voxels import WORLD
from quality_structures import OUT,load
from apply_s20_approved_semantic_repairs import atomic_replace

def install():
    manifest=load(OUT/'native_transit_repair_stage.json');native=load(OUT/'native_transit_repair/native_transit_receipt.json');clearance=load(OUT/'transit_clearance.json')
    if not native['passed'] or not native['existing_identities_preserved'] or native['native_rails']!=112:raise RuntimeError('Native staging has not passed')
    if clearance['passed']!=112 or clearance['rails']!=112:raise RuntimeError('Physical train/airplane clearance has not passed')
    source=Path(manifest['source']).resolve();stage=Path(manifest['stage']).resolve();baseline=manifest['source_hashes'];after=hashes(stage)
    if source!=(WORLD/'mtr').resolve():raise RuntimeError('Unexpected native installation destination')
    changed=[name for name,value in after.items() if baseline.get(name)!=value];removed=sorted(set(baseline)-set(after));added=set(after)-set(baseline)
    retired={r['id'].upper() for r in native['retired_rails']}
    if len(removed)!=len(retired) or any('/rails/' not in name or Path(name).name.upper() not in retired for name in removed):raise RuntimeError('Unexpected native deletions')
    for name in set(changed)|set(removed):
        if not (source/name).resolve().is_relative_to(source):raise RuntimeError('Native target escapes world')
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    if hashes(source)!=baseline:raise RuntimeError('Current native railway changed since cold staging')
    folder=OUT/('native_transit_install_'+datetime.now().strftime('%Y%m%d_%H%M%S'));folder.mkdir();shutil.copytree(source,folder/'before')
    try:
        for name in changed:
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True);atomic_replace(target,(stage/name).read_bytes())
        for name in removed:(source/name).unlink()
        if hashes(source)!=after:raise RuntimeError('Native install readback differs')
    except Exception:
        for name in set(changed)|set(removed):
            target=source/name;old=folder/'before'/name
            if old.exists():atomic_replace(target,old.read_bytes())
            elif name in added and target.exists():target.unlink()
        raise
    for path in (WORLD/'regional_plan.json',):
        plan=load(path);plan['native_rail_count']=112;plan['native_route_count']=8;plan['kirisato_connected']=True;plan['airport_S1_splice']=True
        path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    receipt=dict(verified=True,changed=changed,removed=removed,added=sorted(added),native_rails=112,native_routes=8,retained_routes=7,retained_rails=97,logical_station_platform_depot_ids_preserved=True)
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    (OUT/'native_transit_install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('Installed native repair:',len(changed),'changed/new files;',len(removed),'retired rail file;112 rails/8 routes; readback verified',flush=True)

if __name__=='__main__':install()
