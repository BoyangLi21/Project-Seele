"""Gate the final review, publish its spatial contract, restore human inventory."""
from pathlib import Path
import copy,datetime,hashlib,json,msvcrt,shutil
import nbtlib

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23'
WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';V=OUT/'validation'
def read(path):return json.loads(path.read_text(encoding='utf8'))
def main():
    required=['all_current_walks_pass.json','native_final_guard_results.json','final_lcl_containment.json','client_piano_pass.json','client_flight_pass.json']
    for name in required:assert read(V/name)['passed'],name
    un=read(V/'client_un_pass.json');assert not un['error'] and len(un['checks'])==2 and all(q['passed'] and q['attack_recover_reset_commands'] and q['wet_closed_restored'] for q in un['checks'])
    lifts=read(V/'client_lifts_all_pass.json');assert not lifts['error'] and len(lifts['trips'])==10 and all(q['passed'] for q in lifts['trips'])
    assert read(V/'lift_final_quality.json')['all_steady_frames_within_015']
    trains=read(V/'train_u1_pass.json')+read(V/'client_surface_trains_pass.json')
    assert {q['service'] for q in trains}=={'U1','S1','R1'} and all(q['nativePassengerRegistration'] and q['stoppedAtNextStation'] for q in trains)
    assert len(read(V/'client_tour_receipt.json'))==18
    assert read(V/'visual_review.json')['passed']
    for row in read(OUT/'models/staged_files.json'):
        path=ROOT/'run/resourcepacks/eva_access_r22_review'/row['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],row['path']
    assert read(OUT/'transit/road_clearance_audit.json')['passed']
    assert read(OUT/'readiness/native_pass.json')['passed']
    nav=read(OUT/'navigation_final/junctions.json');assert len(nav['boards'])==78 and not nav['held']
    walks=read(V/'final_walkway_audit.json');assert not walks['orphan_halves'] and walks['flat_handrails_removed']==0
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=OUT/('review_handoff_'+stamp);backup.mkdir()
    source=Path(read(OUT/'baseline.json')['backup'])/'world'
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        for path in [WORLD/'level.dat',*list((WORLD/'playerdata').glob('*.dat'))]:
            original=source/path.relative_to(WORLD)
            if not original.exists():continue
            saved=backup/path.relative_to(WORLD);saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved)
            nbt=nbtlib.load(path);old=nbtlib.load(original)
            p=nbt['Data'].get('Player') if path.name=='level.dat' else nbt
            q=old['Data'].get('Player') if path.name=='level.dat' else old
            if p is None or q is None:continue
            assert 'RootVehicle' not in p,'Finish dismounting before handing back the review'
            for key in ['Inventory','EnderItems','SelectedItemSlot','XpLevel','XpP','XpTotal','Score','Health','AbsorptionAmount','foodLevel','foodSaturationLevel','foodExhaustionLevel','foodTickTimer','abilities','playerGameType']:
                if key in q:p[key]=copy.deepcopy(q[key])
                else:p.pop(key,None)
            p['Pos']=nbtlib.List[nbtlib.Double]([-335.5,-466,739.5]);p['Motion']=nbtlib.List[nbtlib.Double]([0.,0.,0.]);p['Rotation']=nbtlib.List[nbtlib.Float]([0.,0.])
            p['Dimension']=nbtlib.String('projectseele:geofront');p['FallDistance']=nbtlib.Float(0);p['abilities']['flying']=nbtlib.Byte(0)
            nbt.save(path)
        shutil.copy2(V/'full_walk_cases.json',WORLD/'quality_walk_cases.json')
        shutil.copy2(OUT/'navigation_final/junctions.json',WORLD/'wayfinding_r23.json')
        contract=dict(revision='R23',current_walk_catalogue='quality_walk_cases.json',route_count=9005,
                      guidance='wayfinding_r23.json',named_goals=nav['goals'],native_openable_command_doors=nav['registered_operable_doors'],
                      public_command_door=[28,-406,272],exterior_button=[27,-405,270],
                      room_entries=read(OUT/'safety/guard_contract.json')['room_entries'],
                      widened_galleries=read(OUT/'gallery_width/contract.json')['galleries'],
                      stations=read(OUT/'stations/contract.json')['stations'],military_readiness='military_readiness_r23.json',
                      mechanical_exclusions='Lift shafts retain their native interlocked doors; closed-landing collision probes passed.',
                      native_rail_source='r23-platform-alignment2',native_rail_snapshot='native_transit_r23.json')
        (WORLD/'spatial_contract_r23.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf8')
    report=dict(passed=True,revision='R23',validated_world=str(WORLD),timestamp=stamp,
                routes=read(V/'all_current_walks_pass.json'),edge_probes=len(read(V/'native_final_guard_results.json')['checks']),
                lifts=10,trains=trains,un_models=2,liquid_containment=True,private_assets_sha_verified=True,
                review_player_inventory_restored_from=str(source),review_backup=str(backup),native_tour_screenshots=18)
    (OUT/'final_acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('R23 review accepted; ready for exact-cell Main installation')
if __name__=='__main__':main()
