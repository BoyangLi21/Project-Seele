"""Cold full-height audit of the current R28 save, using canonical readers."""
from pathlib import Path
import json,msvcrt,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r28/global';WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    tasks={'components':"import scan_world_components_r19 as s;s.WORLD=w;s.main(o/'components')",
           'fixtures':"import inventory_world_r19 as s;s.WORLD=w;s.OUT=o/'inventory';s.main();import retire_floating_labels_r19 as t;t.vox.WORLD=w;t.OUT=o/'labels';t.survey()"}
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);jobs=[];logs=[]
        for name,body in tasks.items():
            log=(OUT/(name+'.log')).open('w',encoding='utf8');logs.append(log)
            code="import sys;from pathlib import Path;sys.path.insert(0,'tools');w=Path("+repr(str(WORLD))+");o=Path("+repr(str(OUT))+");"+body
            jobs.append((name,subprocess.Popen([sys.executable,'-u','-c',code],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUTF8':'1','OPENBLAS_NUM_THREADS':'1'})))
        errors=[name for name,job in jobs if job.wait()!=0]
        for log in logs:log.close()
        if errors:raise RuntimeError(errors)
        import classify_component_contacts_r19 as contacts
        contacts.WORLD=WORLD;contacts.OUT=OUT/'components';contacts.main()
        inventory=json.loads((OUT/'inventory/world_objects.json').read_text(encoding='utf8'));parts=inventory['objects']['escalators'];destination=OUT/'walkways';destination.mkdir(exist_ok=True)
        snapshot=dict(scan=dict(full_chunks=inventory['full_chunks'],sections=inventory['sections'],complete=True,source='Fresh R28 full-height save scan; includes surface and underground'),
                      steps=[[*q['pos'],q['state']] for q in parts if 'escalator_step' in q['state']],
                      sides=[[*q['pos'],q['state']] for q in parts if 'escalator_side' in q['state']])
        (destination/'native_cells.json').write_text(json.dumps(snapshot,separators=(',',':')),encoding='utf8')
        import audit_moving_walks_r23 as walks
        walks.WORLD=WORLD;walks.OUT=destination;walks.main(False)
    print('R28 current whole-height scan complete; candidates still require semantic classification',flush=True)
if __name__=='__main__':main()
