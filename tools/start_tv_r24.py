"""Freeze installed R23 and create one isolated world for TV refinement."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil,subprocess
import nbtlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r24'
MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
REVIEW=ROOT/'run/saves/SEELE_R24_TV_REVIEW'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'baseline.json').exists():
        print('R24 baseline already exists; existing work was not replaced');return
    assert json.loads((MAIN/'r23_ready.json').read_text())['ready']
    assert not REVIEW.exists(),'Inspect an existing review before replacing it'
    protected=json.loads((ROOT/'artifacts/facility_r23/baseline.json').read_text())['original_user_files']
    for name,sha in protected.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=ROOT/'backups'/('SEELE_R24_'+stamp)
    with (MAIN/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        # Windows range locking also rejects a second handle reading the
        # lock file. It carries no world data and is recreated in the copies.
        shutil.copytree(MAIN,backup/'world',ignore=shutil.ignore_patterns('session.lock'))
        (backup/'world/session.lock').write_bytes('\u2603'.encode('utf8'))
        shutil.copytree(backup/'world',REVIEW)
        shutil.copytree(ROOT/'run/resourcepacks/eva_real_model',backup/'eva_real_model')
    pack=ROOT/'run/resourcepacks/eva_tv_r24_review';assert not pack.exists()
    shutil.copytree(backup/'eva_real_model',pack)
    (pack/'pack.mcmeta').write_text(json.dumps({'pack':{'pack_format':15,'description':'Private R24 TV refinement review'}}),encoding='utf8')
    level=nbtlib.load(REVIEW/'level.dat');level['Data']['LevelName']=nbtlib.String('SEELE R24 TV detail review');level.save(REVIEW/'level.dat')
    report=dict(revision='R24',world=str(REVIEW),authoritative=str(MAIN),backup=str(backup),private_pack=str(pack),
                head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                original_user_files=protected,source='Installed and commissioned R23; no old preview transplanted',
                authorization=json.loads((OUT/'authorization.json').read_text()))
    (OUT/'baseline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (REVIEW/'working_revision_r24.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('R24 frozen baseline and isolated review ready',REVIEW,flush=True)
if __name__=='__main__':main()
