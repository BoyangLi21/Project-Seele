"""Install the accepted R20 plans without copying review players or entities."""
import argparse,datetime,json,msvcrt,shutil
from collections import defaultdict
from pathlib import Path
import nbtlib
import regional_voxels as v
from transplant_s22_authority import read_region,parse_chunk,build_region
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=v.ROOT;OUT=ROOT/'artifacts/world_rebuild_r20';REVIEW=ROOT/'run/saves/SEELE_R20_REVIEW'
PLANS=[
 'factory/civil_factory','galleries/connected_gallery_junctions',
 'transit/civil/viaduct_stations_and_streets','transit/civil/circulation_handoffs',
 'transit/airport_revision/safe_airport_connections','transit/airport_revision/complete_shed_relocation',
 'factory/gallery_and_observer_finish','global_cleanup/verified_residue',
 'transit/civil/continuous_platform_aisles','transit/civil/supported_signs_and_interchanges',
 'un01_hangar/reserved_hangar_shell','circulation_ports/final_ports',
 'transit/grade_finish/six_metre_road_clearance','road_actual/clear_roadways_and_station_kerbs',
 'coast/sea_level_connections','transit/final_envelopes/final_static_clearance',
 'legacy_connections/retained_destinations','legacy_connections/cage_and_arrival_handoffs',
 'road_actual/continuous_asphalt_finish','road_actual/restore_extension_formation',
 'visual_finish/coherent_finishes_and_furniture',
 'visual_finish/static_guideway_markers',
 'final_cleanup/final_residue_and_label_supports',
]
def region(path):return read_region(path) if path.exists() and path.stat().st_size>=8192 else (bytes(4096),[None]*1024)
def full(blob):return bool(blob) and str(parse_chunk(blob).get('Status','')).removeprefix('minecraft:')=='full'
def required_chunks():
    wanted=set()
    for plan in PLANS:wanted.update(map(tuple,json.loads((OUT/plan/'chunks.json').read_text())))
    for rail in json.loads((OUT/'transit/flight_samples11.json').read_text()):
        for xx,_,zz in rail['points'][::2]:
            x,z=round(xx),round(zz)
            wanted.update((cx,cz) for cx in range((x-18)//16,(x+18)//16+1) for cz in range((z-18)//16,(z+18)//16+1))
    return wanted
def generated_terrain(apply=False):
    baseline=json.loads((OUT/'baseline.json').read_text());cold=Path(baseline['backup'])/'world';relative=Path('dimensions/projectseele/geofront/region');groups=defaultdict(list)
    for x,z in required_chunks():groups[x//32,z//32].append((x,z))
    report=[];backup=OUT/'main_generation_before'
    if apply:backup.mkdir(exist_ok=True)
    locks=[]
    try:
        for world in (v.WORLD,REVIEW):
            lock=(world/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);locks.append(lock)
        assert nbtlib.load(v.WORLD/'level.dat')['Data']['WorldGenSettings']['seed']==nbtlib.load(REVIEW/'level.dat')['Data']['WorldGenSettings']['seed']
        for (rx,rz),coords in sorted(groups.items()):
            name=f'r.{rx}.{rz}.mca';target=v.WORLD/relative/name;stamps,current=region(target);source=None;original=None;modified=[]
            for x,z in coords:
                slot=(z%32)*32+x%32
                if full(current[slot]):continue
                if source is None:source=region(REVIEW/relative/name)[1];original=region(cold/relative/name)[1]
                assert current[slot]==original[slot],('User modified an unfinished main chunk',x,z)
                assert full(source[slot]),('Required review chunk is not FULL',x,z)
                current[slot]=source[slot];modified.append([x,z])
            if modified:
                report.append(dict(region=name,chunks=modified))
                if apply:
                    if target.exists():shutil.copy2(target,backup/name)
                    else:(backup/(name+'.previously_absent')).write_text('')
                    atomic_replace(target,build_region(stamps,current))
        result=dict(applied=apply,only_previously_unfinished_chunks=True,no_entity_or_player_files_copied=True,regions=report,chunks=sum(len(q['chunks']) for q in report))
        (OUT/('main_generated_terrain_install.json' if apply else 'main_generated_terrain_plan.json')).write_text(json.dumps(result,indent=2));print('Required new FULL terrain chunks',result['chunks'],flush=True)
    finally:
        for lock in locks:lock.close()
def main(apply=False):
    if not apply:generated_terrain();return
    proof=json.loads((OUT/'transit/physical_acceptance.json').read_text());assert proof['passed']
    journal_path=OUT/'main_install_journal.json';journal=json.loads(journal_path.read_text()) if journal_path.exists() else {'started':datetime.datetime.now().isoformat(),'completed':[]}
    def step(name,action):
        if name in journal['completed']:return
        print('MAIN INSTALL',name,flush=True);action();journal['completed'].append(name);atomic_replace(journal_path,json.dumps(journal,indent=2).encode())
    from preflight_main_r20 import main as preflight
    from apply_r19_plan import main as plan_apply
    from install_factory_runtime_r20 import main as factory
    from install_un01_annex_r20 import main as annex
    from install_transit_r20 import main as transit
    from install_metadata_r20 import main as metadata
    step('cold_preflight',preflight);step('missing_terrain',lambda:generated_terrain(True))
    for plan in PLANS:step(plan,lambda plan=plan:plan_apply(plan,artifact_root=OUT))
    step('fleet_runtime',lambda:factory(v.WORLD));step('un01_empty_annex',lambda:annex(v.WORLD));step('native_transit',lambda:transit(v.WORLD,ROOT/'.Codex/r20-transit-built11'));step('world_metadata',lambda:metadata(v.WORLD))
    journal['installed']=True;journal['finished']=datetime.datetime.now().isoformat();atomic_replace(journal_path,json.dumps(journal,indent=2).encode());print('R20 main save installation complete',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply-main',action='store_true');main(p.parse_args().apply_main)
