"""Append only the fourteen new P1 objects; never overwrite existing MTR runtime."""
from pathlib import Path
import json,hashlib,shutil,msvcrt
from datetime import datetime
from regional_voxels import WORLD,ROOT
from apply_s20_approved_semantic_repairs import atomic_replace
OUT=ROOT/'artifacts/world_expansion_r07'
def hashes(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def main():
    native=json.loads((OUT/'port_native_transit/native_transit_receipt.json').read_text(encoding='utf8'))
    clear=json.loads((OUT/'port_clearance/transit_clearance.json').read_text(encoding='utf8'))
    assert native['passed'] and native['existing_identities_preserved'] and clear['passed']==clear['rails']==7
    source=(WORLD/'mtr').resolve();stage=ROOT/'.Codex/r07-mtr-staging'
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    before=hashes(source);staged=hashes(stage);added=sorted(set(staged)-set(before))
    expected={'rails':7,'platforms':2,'stations':2,'routes':1,'depots':1,'sidings':1}
    from collections import Counter
    assert Counter(Path(n).parts[2] for n in added)==expected,(added,expected)
    for n in added:
        assert n.startswith('projectseele/geofront/') and (source/n).resolve().is_relative_to(source)
    backup=OUT/('port_transit_install_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir();shutil.copytree(source,backup/'before')
    try:
        for n in added:
            target=source/n;target.parent.mkdir(parents=True,exist_ok=True);atomic_replace(target,(stage/n).read_bytes())
        after=hashes(source)
        assert all(after[n]==v for n,v in before.items()) and all(after[n]==staged[n] for n in added)
    except Exception:
        for n in added:
            target=source/n
            if target.exists():target.unlink()
        raise
    report=dict(passed=True,added=added,old_files_unchanged=len(before),before_hashes=before,new_hashes={n:after[n] for n in added})
    (backup/'receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (OUT/'port_transit_install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('Verified P1 install:',len(added),'new files;',len(before),'old files unchanged')
if __name__=='__main__':main()
