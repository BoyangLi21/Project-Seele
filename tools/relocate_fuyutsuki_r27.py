"""Move only the existing deputy's entity and roster post beside the authored city keys."""
from pathlib import Path
import argparse,copy,hashlib,json,msvcrt
import nbtlib
from query_blocks import read_box
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace
from verify_main_r20 import entities

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r27'
POS=(27,-406,277)

def install(world):
    out=ART/('promotion' if world.name=='SEELE_TV_WORLD_PREVIEW_20260906' else 'relocation')
    out.mkdir(parents=True,exist_ok=True)
    assert not (out/'installed.json').exists(),'Already relocated'
    blocks=read_box(world,'projectseele:geofront',(25,-407,276),(31,-404,278))
    assert blocks[27,-407,277]=='minecraft:white_concrete'
    assert all(blocks[27,y,277]=='minecraft:air' for y in (-406,-405))
    assert 'nerv_office_chair' in blocks[28,-406,277]
    assert 'warped_button' in blocks[26,-405,277] and 'crimson_button' in blocks[30,-405,277]
    with (world/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        original=entities(world)
        old=[(uid,e) for uid,e in original.items() if str(e.get('StaffId',''))=='fuyutsuki']
        assert len(old)==1
        uid,old=old[0];new=copy.deepcopy(old)
        assert list(map(int,old['Pos']))==[24,-389,349]
        new['Pos']=nbtlib.List[nbtlib.Double]([27.5,-406,277.5])
        new['Motion']=nbtlib.List[nbtlib.Double]([0,0,0])
        new['Rotation']=nbtlib.List[nbtlib.Float]([0,0])
        new['StaffStation']=nbtlib.Long(((27&0x3ffffff)<<38)|((277&0x3ffffff)<<12)|(-406&4095))
        new['StaffStationYaw']=nbtlib.Float(0)
        new['HadPendingStaffTask']=nbtlib.Byte(0)
        path=world/'dimensions/projectseele/geofront/entities/r.0.0.mca'
        timestamps,chunks=read_region(path)
        source=(24>>4)+((349>>4)*32);target=(27>>4)+((277>>4)*32)
        a,b=parse_chunk(chunks[source]),parse_chunk(chunks[target])
        found=[e for e in a['Entities'] if tuple(map(int,e.get('UUID',[])))==uid]
        assert len(found)==1
        a['Entities'].remove(found[0]);b['Entities'].append(new)
        chunks[source]=chunk_blob(a);chunks[target]=chunk_blob(b)
        rosterpath=world/'nerv_staff_r15.json';roster=json.loads(rosterpath.read_text(encoding='utf8'))
        post=next(s for s in roster['stations'] if s['id']=='fuyutsuki')
        post.update(feet=list(POS),yaw=0,room='supreme_command_city_console')
        (out/'entity_region_before.mca').write_bytes(path.read_bytes())
        (out/'nerv_staff_before.json').write_bytes(rosterpath.read_bytes())
        try:
            atomic_replace(path,build_region(timestamps,chunks))
            atomic_replace(rosterpath,json.dumps(roster,ensure_ascii=False,indent=2).encode('utf8'))
            after=entities(world)
            assert original.keys()==after.keys() and after[uid]==new
            assert all(e==after[k] for k,e in original.items() if k!=uid)
        except BaseException:
            atomic_replace(path,(out/'entity_region_before.mca').read_bytes())
            atomic_replace(rosterpath,(out/'nerv_staff_before.json').read_bytes());raise
    report=dict(installed=True,world=str(world),position=POS,uuid=uid,other_actors_unchanged=len(original)-1,blocks_changed=0)
    (out/'installed.json').write_text(json.dumps(report,indent=2))
    (world/'r27_ready.json').write_text(json.dumps(report,indent=2))
    print(report)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--main',action='store_true');args=p.parse_args()
    if args.main:
        proof=json.loads((ART/'acceptance.json').read_text());assert proof['passed']
    install(ROOT/'run/saves'/('SEELE_TV_WORLD_PREVIEW_20260906' if args.main else 'SEELE_R27_REVIEW'))
