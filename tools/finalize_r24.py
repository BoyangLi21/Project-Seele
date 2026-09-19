"""Gate the final R24 installation on actual evidence, not successful process exits."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r24';V=ART/'validation'
def read(path):return json.loads(path.read_text(encoding='utf8'))
def main():
    required=['floor_native126645_pass.json','extended_navigation_native_pass.json','whip_native_pass.json',
              'cold_campaign_roundtrip_pass.json','clean_public_client_pass.json','skylight_native_final_pass.json','nbt_patch/result.json',
              'far_view_pass.json','visual_review.json','post_cleanup_readback.json','final_build_pass.json',
              'sbw_native_wake_pass.json','vehicle_rest_equivalence_final.json','vehicle_rest_repeat_equality.json',
              'vehicle_phantom_equivalence.json','natural_resolution_native_pass.json','glow_visual_pass.json',
              'soft_cross_visual_pass.json','final_camera_campaign_native_pass.json']
    for name in required:assert read(V/name)['passed'],name
    staff=read(V/'staff_native_pass.json');assert not staff['error'] and staff['phase']==10
    assert all(value for value in staff['checks'].values() if isinstance(value,bool))
    expected=read(V/'final_full_walk_cases.json');walks=read(V/'final_full_native_walk_results.json')
    assert len(expected)==len(walks)==9485 and {r['id'] for r in expected}=={r['id'] for r in walks}
    assert all(r['status']=='pass' for r in walks)
    assert read(ART/'global/final_lcl_containment.json')['passed']
    escalators=read(ART/'global/walkways/audit.json');assert not escalators['orphan_halves'] and escalators['flat_handrails_removed']==0
    residues=read(ART/'residue/classification.json');assert residues['removed_cells']==216 and not residues['unclassified']
    assert residues['rail_envelope_conflicts']==residues['plot_conflicts']==0
    assert len(read(V/'final_scene_tour_receipt.json'))==23
    camera=read(ART/'camera/visual_acceptance.json');assert camera['passed'] and camera['actors_and_timing_unchanged']
    clip=Path(camera['candidate']);clip=clip if clip.is_absolute() else ROOT/clip
    assert hashlib.sha256(clip.read_bytes()).hexdigest()==camera['sha256']
    for name,sha in read(ART/'baseline.json')['original_user_files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    report=dict(passed=True,revision='R24',world='SEELE_R24_TV_REVIEW',human_acceptance_pending=True,whole_current_native_routes=len(walks),floor_points=126645,
                full_height_chunks=51500,full_height_sections=3193000,old_world_residue_removed=216,private_test_terrain_not_promoted=34,
                npc_real_button_cycle=True,campaign_separate_jvm_restart=True,wet_cells_contained=5,nbt_only_sign_updates=78,
                camera_sha256=camera['sha256'],native_scene_views=23,protected_user_files=14,required_reports=required,
                limits=['Only Sachiel and Shamshel are playable in the ordered TV campaign; later chapters are not completed.',
                        'Fixed-view performance measurements do not establish smoothness over the entire F2 flight.',
                        'UN military-base fixed-view performance remains limited: median 62.61 ms and p95 159.82 ms on this laptop; no 30 FPS guarantee.',
                        'Private maps/models remain separate from public source; third-party distribution permissions are not automatically granted.'])
    (ART/'final_acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('R24 checks passed; exact-delta Main installation enabled')
if __name__=='__main__':main()
