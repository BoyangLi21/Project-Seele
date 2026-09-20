"""Install only S1's changed native objects; preserve every other train and flight."""
from pathlib import Path
import json,msvcrt,shutil
from stage_native_transit_repair import hashes
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/airport';STAGE=ROOT/'.Codex/r28-native-airport'

def main():
    r=json.loads((OUT/'airport_native_receipt.json').read_text());assert r['passed']
    before=json.loads((OUT/'source_hashes.json').read_text());after=hashes(STAGE)
    hx=lambda n:f'{n&((1<<64)-1):016X}'
    names={*r['retired_rails'],*r['new_rails'],*[hx(i) for i in r['new_platforms']],*[hx(r[k]) for k in ('route','station','depot','siding')]}
    names.update(hx(i) for i in r['cadence_platforms'])
    delta=[k for k in sorted(set(before)|set(after)) if Path(k).name in names and before.get(k)!=after.get(k)]
    assert 14<=len(delta)<=24,(len(delta),delta)
    assert json.loads((OUT/'cadence_S1.json').read_text())['passed']
    target=WORLD/'mtr';backup=OUT/'native_install_before';backup.mkdir(exist_ok=True)
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);current=hashes(target)
        for key in delta:assert current.get(key)==before.get(key),('Railway changed since staging',key)
        for key in delta:
            q=(target/key).resolve();assert q.is_relative_to(target.resolve())
            if q.exists():b=backup/key;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(q,b)
            if key in after:q.parent.mkdir(parents=True,exist_ok=True);atomic_replace(q,(STAGE/key).read_bytes())
            elif q.is_file():q.unlink()
        now=hashes(target);assert all(now.get(k)==v for k,v in current.items() if k not in delta)
        for name in ('native_transit_r28.json','native_transit_r26.json'):shutil.copy2(OUT/'native_final.json',WORLD/name)
    (OUT/'native_install.json').write_text(json.dumps(dict(installed=True,delta=delta,before={k:before.get(k) for k in delta},after={k:after.get(k) for k in delta},other_services_preserved=True),indent=2))
    print('Installed',len(delta),'S1 native objects; other services unchanged',flush=True)

if __name__=='__main__':main()
