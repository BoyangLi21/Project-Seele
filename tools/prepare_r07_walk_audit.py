"""Stage the bounded native R07 audit while preserving the whole-world catalog."""
import json, shutil, argparse, msvcrt
from pathlib import Path
from regional_voxels import WORLD

OUT=Path(__file__).resolve().parents[1]/'artifacts/world_expansion_r07'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--restore',action='store_true');args=parser.parse_args()
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    current=OUT/'audit_catalog_current';pending=current/'pending.json'
    if args.restore:
        if not pending.exists():raise RuntimeError('No staged native audit to restore')
        for name in ('quality_walk_cases.json','regional_states.json'):shutil.copy2(current/name,WORLD/name)
        pending.unlink();print('Restored the catalog captured for this audit');return
    if pending.exists():raise RuntimeError('Restore the previous audit before staging another one')
    current.mkdir(exist_ok=True)
    for name in ('quality_walk_cases.json','regional_states.json'):shutil.copy2(WORLD/name,current/name)
    backup=OUT/'audit_catalog_before';backup.mkdir(exist_ok=True)
    for name in ('quality_walk_cases.json','regional_states.json'):
        if not (backup/name).exists():shutil.copy2(WORLD/name,backup/name)
    cases=[]
    for name in ('port','base','secret','fleet','road','transit','access','continuous','campus'):
        for case in json.loads((OUT/f'{name}_walk_cases.json').read_text(encoding='utf8')):
            if not case.get('runtime_only'):cases.append(case)
    if len({x['id'] for x in cases})!=len(cases):raise RuntimeError('Duplicate route IDs')
    states=set(json.loads((current/'regional_states.json').read_text(encoding='utf8')))
    for path in OUT.glob('*/states.json'):states.update(json.loads(path.read_text(encoding='utf8')))
    (WORLD/'quality_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
    (WORLD/'regional_states.json').write_text(json.dumps(sorted(states)),encoding='utf8')
    pending.write_text(json.dumps({'current_backup':str(current),'cases':len(cases)}),encoding='utf8')
    print('Staged',len(cases),'native R07 routes. After native review, run this script with --restore.')
if __name__=='__main__':main()
