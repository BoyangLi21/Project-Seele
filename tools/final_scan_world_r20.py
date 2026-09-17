"""Freeze the review save while independent final 3D and fixture scans run."""
import json,msvcrt,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_rebuild_r20';WORLD=ROOT/'run/saves/SEELE_R20_REVIEW'
def main():
    tasks={
        'components':"import scan_world_components_r19 as s;s.WORLD=w;s.main(o/'global_components_final')",
        'fixtures':"import inventory_world_r19 as s;s.WORLD=w;s.OUT=o/'inventory_final';s.main();import retire_floating_labels_r19 as t;t.vox.WORLD=w;t.OUT=o/'labels_final';t.survey()",
    }
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);jobs=[];logs=[]
        for name,body in tasks.items():
            log=(OUT/f'final_{name}_scan.log').open('w',encoding='utf8');logs.append(log)
            code="import sys;from pathlib import Path;sys.path.insert(0,'tools');w=Path('D:/eva/run/saves/SEELE_R20_REVIEW');o=Path('D:/eva/artifacts/world_rebuild_r20');"+body
            jobs.append((name,subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUTF8':'1','OPENBLAS_NUM_THREADS':'1'})))
        errors=[]
        for name,job in jobs:
            if job.wait()!=0:errors.append(name)
        for log in logs:log.close()
        assert not errors,errors
    print('Final frozen 3D, fixtures and display-backing scans finished')
if __name__=='__main__':main()
