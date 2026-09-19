"""Retire only the exact actor created by failed R24 test1, absent from its frozen baseline."""
from pathlib import Path
import json,uuid,shutil,datetime,msvcrt
from verify_main_r20 import entities
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';BASE=ROOT/'backups/SEELE_R24_20260919_003327/world'
TARGET=uuid.UUID('0d3198ab-66d2-4075-abac-10a89f910cbd')
def key(tag):return uuid.UUID(''.join(f'{int(i)&0xffffffff:08x}' for i in tag['UUID']))
def main():
    out=ROOT/'artifacts/facility_r24/review_actor_cleanup'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        assert all(key(e)!=TARGET for e in entities(BASE).values())
        before=entities(WORLD);removed=[]
        for path in (WORLD/'dimensions/projectseele/geofront/entities').glob('r.*.*.mca'):
            if path.stat().st_size<8192:continue
            stamps,blobs=read_region(path);dirty=False
            for slot,blob in enumerate(blobs):
                if not blob:continue
                data=parse_chunk(blob);found=[e for e in data.get('Entities',[]) if key(e)==TARGET]
                if not found:continue
                assert len(found)==1 and str(found[0]['id'])=='projectseele:sachiel' and 'seele_first_battle_mission' in list(map(str,found[0].get('Tags',[])))
                if not dirty:shutil.copy2(path,out/path.name)
                removed.append(found[0].snbt());data['Entities'][:]=[e for e in data['Entities'] if key(e)!=TARGET];blobs[slot]=chunk_blob(data);dirty=True
            if dirty:atomic_replace(path,build_region(stamps,blobs))
        after=entities(WORLD);expected={k for k,e in before.items() if key(e)!=TARGET};assert set(after)==expected
        for k in expected:assert before[k].snbt()==after[k].snbt()
        (out/'receipt.json').write_text(json.dumps(dict(target=str(TARGET),removed=len(removed),other_entity_ids_preserved=len(after),original_entities=removed,source='campaign_native_run1.log original R10 MISSION Angel deployed UUID'),indent=2),encoding='utf8');print('Retired failed-review actor:',len(removed),'preserved other identities:',len(after))
if __name__=='__main__':main()
