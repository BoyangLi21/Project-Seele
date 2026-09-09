"""Preserve the catalog, retire superseded ship routes, and stage an R08 native audit."""
import json,shutil,argparse,msvcrt
from pathlib import Path
from regional_voxels import WORLD,ROOT
OUT=ROOT/'artifacts/world_refinement_r08'
def load(p):return json.loads(p.read_text(encoding='utf8'))
def main(restore=False,only_structure=False,only_workshops=False):
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    current=OUT/'audit_catalog';current.mkdir(exist_ok=True);pending=current/'pending.json'
    if restore:
        if not pending.exists():raise RuntimeError('No staged R08 audit')
        for name in ('quality_walk_cases.json','regional_states.json'):shutil.copy2(current/name,WORLD/name)
        pending.unlink();print('Restored updated catalog');return
    if pending.exists():raise RuntimeError('Restore prior stage first')
    for name in ('quality_walk_cases.json','regional_states.json'):
        if not (current/('baseline_'+name)).exists():shutil.copy2(WORLD/name,current/('baseline_'+name))
    original=load(current/'baseline_quality_walk_cases.json');retired=[c for c in original if c['id'].startswith('r07/fleet/')]
    additions=[]
    for name in ('port_walk_cases.json','port_detail_walk_cases.json','base_detail_walk_cases.json','structure_walk_cases.json'):
        if (OUT/name).exists():additions+=load(OUT/name)
    # Retain old circulation tests for the rooms/roads touched this round, and key underground links.
    native=[c for c in original if c['id'].startswith('r07/') and not c['id'].startswith('r07/fleet/')]
    native+=additions
    ids=set();native=[c for c in native if not (c['id'] in ids or ids.add(c['id']))]
    if only_structure:native=[c for c in native if c['id'].startswith('r08/structure/')]
    if only_workshops:native=[c for c in native if ('air_shelter_' in c['id'] or 'vehicle_shop' in c['id'] or 'workshop_walk' in c['id'])]
    catalog=[c for c in original if c not in retired]+additions
    if len({c['id'] for c in catalog})!=len(catalog):raise RuntimeError('Duplicate catalog IDs')
    states=set(load(current/'baseline_regional_states.json'))
    for path in OUT.glob('*/states.json'):states.update(load(path))
    for path in (current/'quality_walk_cases.json',):path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
    (current/'regional_states.json').write_text(json.dumps(sorted(states)),encoding='utf8')
    (WORLD/'quality_walk_cases.json').write_text(json.dumps(native,ensure_ascii=False,indent=2),encoding='utf8');shutil.copy2(current/'regional_states.json',WORLD/'regional_states.json')
    pending.write_text(json.dumps(dict(cases=len(native),catalog=len(catalog),retired=len(retired),added=len(additions)),indent=2),encoding='utf8')
    (OUT/'retired_ship_routes.json').write_text(json.dumps(retired,ensure_ascii=False,indent=2),encoding='utf8');print(pending.read_text())
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--restore',action='store_true');ap.add_argument('--only-structure',action='store_true');ap.add_argument('--only-workshops',action='store_true');args=ap.parse_args();main(args.restore,args.only_structure,args.only_workshops)
