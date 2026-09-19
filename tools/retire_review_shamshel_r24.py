"""Remove the two specifically identified failed-restart fixtures, not world Angels."""
from pathlib import Path
import datetime,json,msvcrt,shutil,uuid,copy
import nbtlib
from verify_main_r20 import entities
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';BASE=ROOT/'backups/SEELE_R24_20260919_003327/world'
TARGETS={uuid.UUID(s) for s in ('aa82ecd1-0906-4b46-933d-745860bb9d2e','a9ae79a9-12c8-4d7f-b9c1-37e865d633d4')}
EVA=uuid.UUID('8e75c216-f030-4627-82b5-8903cff26240')
def key(e):return uuid.UUID(''.join(f'{int(i)&0xffffffff:08x}' for i in e['UUID']))
def main():
    out=ROOT/'artifacts/facility_r24/review_actor_cleanup'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);baseline=entities(BASE);before=entities(WORLD)
        assert not TARGETS&{key(e) for e in baseline.values()}
        assert all(str(row['Phase'])=='PARKED' for row in nbtlib.load(WORLD/'data/projectseele_eva_fleet.dat')['data']['Fleet'])
        original=next(e for e in baseline.values() if key(e)==EVA);removed=[];saved={};restored=False
        try:
            for path in (WORLD/'dimensions/projectseele/geofront/entities').glob('r.*.*.mca'):
                if path.stat().st_size<8192:continue
                stamps,blobs=read_region(path);dirty=False
                for slot,blob in enumerate(blobs):
                    if not blob:continue
                    root=parse_chunk(blob);kept=[];changed=False
                    for entity in root.get('Entities',[]):
                        uid=key(entity)
                        if uid in TARGETS:
                            assert str(entity['id'])=='projectseele:shamshel' and 'seele_tv_shamshel_r24' in list(map(str,entity.get('Tags',[])))
                            removed.append(dict(uuid=str(uid),before=entity.snbt()));changed=True;continue
                        if uid==EVA:
                            assert float(entity['Pos'][1])==-442 and not any(str(e['id'])=='minecraft:player' for e in entity.get('Passengers',[]))
                            entity['Invulnerable']=copy.deepcopy(original.get('Invulnerable',nbtlib.Byte(0)));changed=True;restored=True
                        kept.append(entity)
                    if changed:root['Entities']=nbtlib.List[nbtlib.Compound](kept);blobs[slot]=chunk_blob(root);dirty=True
                if dirty:
                    shutil.copy2(path,out/path.name);saved[path]=out/path.name;atomic_replace(path,build_region(stamps,blobs))
            assert {uuid.UUID(r['uuid']) for r in removed}==TARGETS and restored
            after=entities(WORLD);expected={u for u,e in before.items() if key(e) not in TARGETS};assert set(after)==expected
            for u in expected:
                expected_tag=copy.deepcopy(before[u])
                if key(expected_tag)==EVA:expected_tag['Invulnerable']=copy.deepcopy(original.get('Invulnerable',nbtlib.Byte(0)))
                assert expected_tag.snbt()==after[u].snbt()
            report=dict(removed=removed,original_ids_preserved=len(after),original_eva_test_invulnerability_restored=True,source='Failed cold-resume fixtures native2/native3; their assertion occurred before review target cleanup ownership was assigned. Main was never modified.')
            (out/'receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('Retired two exact failed-review targets; all other actor data retained, original EVA invulnerability restored')
        except BaseException:
            for path,backup in saved.items():atomic_replace(path,backup.read_bytes())
            raise
if __name__=='__main__':main()
