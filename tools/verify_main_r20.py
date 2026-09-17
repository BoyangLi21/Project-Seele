"""Verify installed identities, preserved interiors, and complete route metadata."""
import hashlib,json
from pathlib import Path
import nbtlib,numpy as np
from query_blocks import iter_selected_sections
from transplant_s22_authority import read_region,parse_chunk
from regional_voxels import ROOT,WORLD,DIM
OUT=ROOT/'artifacts/world_rebuild_r20'
def entities(world):
    result={}
    def visit(e):
        uid=tuple(map(int,e.get('UUID',[])))
        if uid:assert uid not in result;result[uid]=e
        for child in e.get('Passengers',[]):visit(child)
    for p in (world/'dimensions/projectseele/geofront/entities').glob('r.*.*.mca'):
        if p.stat().st_size<8192:continue
        for blob in read_region(p)[1]:
            if blob:
                for e in parse_chunk(blob).get('Entities',[]):visit(e)
    return result
def compare_box(before,after,lo,hi):
    selected={(x,z):set(range(lo[1]//16,hi[1]//16+1)) for x in range(lo[0]//16,hi[0]//16+1) for z in range(lo[2]//16,hi[2]//16+1)}
    old={(x,z,y):(p,i.reshape(16,16,16)) for x,z,y,p,i in iter_selected_sections(before,DIM,selected)};cells=0
    for x,z,y,p,i in iter_selected_sections(after,DIM,selected):
        palette,a=old[x,z,y];b=i.reshape(16,16,16);sl=np.s_[max(0,lo[1]-y*16):min(16,hi[1]-y*16+1),max(0,lo[2]-z*16):min(16,hi[2]-z*16+1),max(0,lo[0]-x*16):min(16,hi[0]-x*16+1)]
        assert np.array_equal(np.asarray(palette)[a[sl]],np.asarray(p)[b[sl]]),('Protected command interior changed',x,y,z);cells+=a[sl].size
    return cells
def windows(world):
    selected={(x,z):set(range(-30,-19)) for x in range(-12,13) for z in range(12,29)};count=0
    for x,z,y,p,a in iter_selected_sections(world,DIM,selected,skip_unfinished=True):
        for i,s in enumerate(p):
            if s.startswith('projectseele:one_way_glass') and 'pyramid=true' in s:count+=int(np.count_nonzero(a==i))
    return count
def main():
    baseline=json.loads((OUT/'baseline.json').read_text());cold=Path(baseline['backup'])/'world';journal=json.loads((OUT/'main_install_journal.json').read_text());assert journal['installed']
    for name,digest in baseline['preexisting_dirty_files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    a=entities(cold);b=entities(WORLD);removed={uid:e for uid,e in a.items() if uid not in b};assert all(str(e['id'])=='minecraft:text_display' and 'projectseele_r03_wayfinding' in map(str,e.get('Tags',[])) for e in removed.values());assert len(removed)==124
    af=nbtlib.load(cold/'data/projectseele_eva_fleet.dat')['data']['Fleet'];bf=nbtlib.load(WORLD/'data/projectseele_eva_fleet.dat')['data']['Fleet'];assert len(af)==len(bf)==3
    for old,new in zip(af,bf):
        for key in ['Canonical','EntryPlug']:assert list(old[key])==list(new[key]);assert tuple(map(int,new[key])) in b
        assert str(new['Phase'])=='PARKED' and int(new['Carrier'])==-240
    old_roster=json.loads((cold/'nerv_staff_r15.json').read_text(encoding='utf8'))['stations'];roster=json.loads((WORLD/'nerv_staff_r15.json').read_text(encoding='utf8'))['stations'];assert {s['id'] for s in old_roster}<={s['id'] for s in roster}
    protected=compare_box(cold,WORLD,(6,-445,262),(52,-388,365));window_before=windows(cold);window_after=windows(WORLD);assert window_before==window_after==2344
    cases=json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));assert len(cases)==8831
    assert json.loads((WORLD/'un01_annex_r20.json').read_text())['spawn_airframe'] is False
    report=dict(passed=True,main=str(WORLD),cold_entities=len(a),retained_entities=len(b),only_retired_wayfinding_entities_removed=len(removed),fleet_and_plug_identities_preserved=True,original_staff_stations=len(old_roster),current_staff_stations=len(roster),protected_command_cells_identical=protected,pyramid_one_way_windows=window_after,walk_catalogue=len(cases),user_files_preserved=len(baseline['preexisting_dirty_files']),un01_airframe_not_spawned=True)
    (OUT/'main_verification.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
