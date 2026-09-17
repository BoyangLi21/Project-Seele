"""Promote only the reviewed UN resources; never replace other EVA assets."""
from pathlib import Path
from contextlib import ExitStack
import json,hashlib,shutil,msvcrt,datetime

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r19';CAND=OUT/'un00_local/runtime_candidate/assets/projectseele';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';PUBLIC=ROOT/'src/main/resources/assets/projectseele'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,data):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.r19-writing');tmp.write_bytes(data);tmp.replace(p)
def main():
    audit=json.loads((OUT/'un00_local/runtime_geometry_audit.json').read_text());assert audit['passed'] and audit['triangles']==139806
    mechanics=json.loads((OUT/'un_mechanics_pass/result.json').read_text());assert mechanics['error']=='' and len(mechanics['checks'])==14 and all(mechanics['checks'].values())
    terrain=json.loads((OUT/'un_terrain_pass/result.json').read_text());assert terrain['error']=='' and len(terrain['cases'])==10 and all(r['passed'] for r in terrain['cases'])
    witness=[json.loads(p.read_text()) for p in (OUT/'un00_local').glob('native_pose_*.json')];assert witness and all(r['passed'] for r in witness)
    baseline=json.loads((OUT/'baseline.json').read_text());assert all(digest(ROOT/p)==h for p,h in baseline['user_files'].items())
    backup=OUT/'un00_local'/('installed_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));changes=[]
    with ExitStack() as stack:
        for lock in (ROOT/'run/saves').glob('*/session.lock'):
            handle=stack.enter_context(lock.open('r+b'));msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        for relative in ('mesh/eva_prototype.mesh.json','geo/eva_prototype.geo.json','animations/eva_prototype.animation.json','textures/entity/eva_prototype.png','textures/entity/eva_prototype_eyes.png'):
            source=CAND/relative;target=PACK/relative;saved=backup/'pack'/relative;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);atomic(target,source.read_bytes());assert digest(target)==digest(source);changes.append({'file':str(target),'sha256':digest(target)})
            # Captured animation remains private; only project-authored body,
            # rig and material resources are mirrored into public source.
            if not relative.startswith('animations/'):
                target=PUBLIC/relative;saved=backup/'public'/relative;saved.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():shutil.copy2(target,saved)
                atomic(target,source.read_bytes())
    assert all(digest(ROOT/p)==h for p,h in baseline['user_files'].items())
    (OUT/'un00_local/installation.json').write_text(json.dumps({'status':'installed','geometry_and_materials':changes,'backup':str(backup),'original_three_evas_untouched':True,'main_world_entity_identity_unchanged':True},indent=2));print('EVA-UN-00 installed',backup)
if __name__=='__main__':main()
