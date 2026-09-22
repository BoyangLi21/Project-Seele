"""Promote the verified private model pair, preserving the formal world's identities."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r30';WORLD=ROOT/'run/saves/SEELE_R30_WORLD';REVIEW=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def main(manual=False):
    baseline=read(ART/'baseline.json');stage=read(ART/'geometry_stage/staged.json');assert stage['geometry_staged']
    for name,sha in baseline['original_user_files'].items():assert digest(ROOT/name)==sha,name
    for name,sha in stage['protected_runtime_hashes'].items():assert digest(WORLD/name)==sha,('Formal runtime data changed',name)
    walk=read(ART/'walk_coverage_consolidated.json');assert walk['full_run_count']==9941 and all(r['status']=='pass' for r in walk['results'])
    assert all(r['status']=='pass' for r in read(ART/'final_access_pass33.json'))
    light=read(ART/'lighting_coverage_consolidated.json');assert light['samples']==3108 and light['dark_samples']==0 and light['command_circuit']
    for file in ['lcl_containment_native_pass.json','power_client_pass.json','terrain_coverage_consolidated.json','npc_shinji_sachiel_pass.json','npc_asuka_shamshel_pass.json']:
        proof=read(ART/file);assert proof.get('passed'),file
    combat=read(REVIEW/'r30_combat_visual.json');assert combat['passed']
    native_path=REVIEW/'r30_un_model_pass.json';native=read(native_path) if native_path.exists() else {'passed':False}
    if not manual:assert native['passed']
    source=ROOT/'run/resourcepacks/eva_un_r30_review/assets/projectseele';target=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';manifest=read(source/'eva/un_models_r30.json')
    backup=ART/'model_promotion'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True,exist_ok=True);receipts=[]
    files=[]
    for name,model in manifest['models'].items():
        core={'mesh':f'mesh/{name}.mesh.json','geo':f'geo/{name}.geo.json','animation':f'animations/{name}.animation.json','texture':f'textures/entity/{name}.png'}
        for key,path in core.items():assert digest(source/path)==model['sha256'][key];files.append(path)
        for path,sha in model['pbr'].items():assert digest(source/path)==sha;files.append(path)
    files.append('eva/un_models_r30.json')
    for relative in files:
        before=target/relative;old=digest(before) if before.exists() else None
        if before.exists():p=backup/'assets'/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(before,p)
        before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/relative,before);receipts.append({'file':relative,'before':old,'after':digest(before)})
    maps=ROOT/'run/projectseele-local-maps'
    for reviewed,installed in [('eva_body_r30_review.json','eva_body_r25.json'),('eva_dorsal_r30_review.json','eva_dorsal_r30.json')]:
        destination=maps/installed
        if destination.exists():shutil.copy2(destination,backup/installed)
        shutil.copy2(maps/reviewed,destination)
    body=read(maps/'eva_body_r25.json');assert '3' in body['rigs'] and '4' in body['rigs']
    # Provenance belongs to the world; original saved airframes and capsules remain.
    (WORLD/'un_models_r30.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    for name,sha in stage['protected_runtime_hashes'].items():assert digest(WORLD/name)==sha,name
    import build_server_ready_pack as package
    package.validate_private_eva_mesh_contracts()
    result={'installed':True,'verification_passed':bool(native['passed']),'acceptance_mode':'manual_by_user' if manual else 'native_verified','revision':'R30','world':WORLD.name,'protocol':34,'models':manifest['models'],'model_backup':str(backup),'registered_walk_routes':9941,'final_fixture_routes':33,'lighting_samples':3108,'runtime_lcl_containment':True,'original_runtime_data_preserved':True,'remote_server_progress':'Not supplied; this release is based on the local formal R29 save.','pending_manual_checks':['Final integrated UN pair driving, flight and recovery','Production dedicated-server startup'] if manual else []}
    (WORLD/'r30_ready.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');(backup/'receipt.json').write_text(json.dumps(receipts,indent=2));(ART/'model_promotion/installed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('R30 private models installed and formal world marked ready',flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--manual-acceptance',action='store_true');main(ap.parse_args().manual_acceptance)
