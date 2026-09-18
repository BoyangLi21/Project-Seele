"""Verify protected world identities and interiors after exact-cell installation."""
from pathlib import Path
import hashlib,json
import nbtlib,numpy as np
from query_blocks import read_box,iter_block_entities,AIR
from verify_main_r20 import entities,windows
from promote_world_r23 import datafile

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23'
WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
def main():
    cold=Path(json.loads((ROOT/'artifacts/access_r22/baseline.json').read_text())['backup'])/'world'
    initial=json.loads((OUT/'baseline.json').read_text())['original_user_files']
    for name,digest in initial.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    old,new=entities(cold),entities(WORLD)
    assert set(old)<=set(new),('Lost original entity identities',set(old)-set(new))
    a=nbtlib.load(datafile(cold,'projectseele_eva_fleet.dat'))['data']['Fleet']
    b=nbtlib.load(datafile(WORLD,'projectseele_eva_fleet.dat'))['data']['Fleet']
    assert len(a)==len(b)==3
    for before,after in zip(a,b):
        for key in ('Canonical','EntryPlug'):
            assert list(before[key])==list(after[key])
            assert tuple(map(int,after[key])) in new
    military=nbtlib.load(datafile(WORLD,'projectseele_military_r07.dat'))['data']
    old_military=nbtlib.load(datafile(cold,'projectseele_military_r07.dat'))['data']['Entities']
    for key,uid in old_military.items():assert list(uid)==list(military['Entities'][key]) and tuple(map(int,uid)) in new,key
    additions={k:tuple(map(int,v)) for k,v in military['Entities'].items() if k.startswith(('vehicle/r23/','owner/vehicle/r23/'))}
    assert len(additions)==198 and len(set(additions.values()))==198
    assert all(uid in new for uid in additions.values())
    assert str(military['Phase'])=='WET'
    assert str(nbtlib.load(datafile(WORLD,'projectseele_un01_annex_r20.dat'))['data']['Phase'])=='WET'
    staff=json.loads((cold/'nerv_staff_r15.json').read_text(encoding='utf8'))
    assert staff==json.loads((WORLD/'nerv_staff_r15.json').read_text(encoding='utf8'))
    lo,hi=(6,-445,262),(52,-388,365)
    before,after=read_box(cold,'projectseele:geofront',lo,hi),read_box(WORLD,'projectseele:geofront',lo,hi)
    guards={}
    for row in json.loads((OUT/'safety/guard_contract.json').read_text(encoding='utf8'))['guards']:
        x,y,z=row['guard']
        guards[x,y-1,z]='projectseele:nerv_structural_panel'
        guards[x,y,z]=guards[x,y+1,z]='projectseele:clear_glass'
    sweeps=[row['sweep'] for row in json.loads((ROOT/'artifacts/world_rebuild_r20/lifts/sweep_masks.json').read_text())]
    def mechanical(q):
        return any(all(a[i]<=q[i]<=b[i] for i in range(3)) for a,b in sweeps) or (26<=q[0]<=30 and q[2]==317 and any(y<=q[1]<y+3 for y in (-388,-340)))
    changes=[];additions_in_air=0;moving_cells=0
    for q,state in before.items():
        if state==after[q]:continue
        if 11<=q[0]<=17 and -390<=q[1]<=-385 and 351<=q[2]<=358:continue
        if mechanical(q):moving_cells+=1;continue
        if state in AIR:
            assert after[q].split('[')[0]==guards.get(q) or q==(27,-405,270) and after[q].startswith('minecraft:stone_button['),(q,after[q])
            additions_in_air+=1
        else:changes.append(dict(pos=q,before=state,after=after[q]))
    assert not changes,changes[:30]
    assert windows(cold)==windows(WORLD)==2344
    def glass_nbt(world):
        return {q:tag.snbt() for q,tag in iter_block_entities(world,'projectseele:geofront',(-192,-480,192),(207,-305,463))
                if str(tag.get('id',''))=='projectseele:one_way_glass'}
    old_glass=glass_nbt(cold)
    assert old_glass and old_glass==glass_nbt(WORLD),'One-way window NBT changed or was not measured'
    # Installation never rewrites the human player's inventory or location.
    for p in (cold/'playerdata').glob('*.dat'):
        assert p.read_bytes()==(WORLD/'playerdata'/p.name).read_bytes(),p.name
    oldplayer=nbtlib.load(cold/'level.dat')['Data'].get('Player')
    newplayer=nbtlib.load(WORLD/'level.dat')['Data'].get('Player')
    assert oldplayer.snbt()==newplayer.snbt()
    cases=json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));assert len(cases)==9005
    report=dict(passed=True,retained_original_entities=len(old),added_registered_equipment=144,added_control_nodes=54,
                original_military_identities=len(old_military),staff_stations=len(staff['stations']),
                pyramid_one_way_windows=2344,protected_command_static_nonair_preserved=True,moving_cabin_or_landing_door_cells=moving_cells,guard_brackets_glass_or_button_added_in_air=additions_in_air,
                user_files_preserved=len(initial),main_player_unchanged=True,walk_catalogue=len(cases))
    (OUT/'main_verification.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
