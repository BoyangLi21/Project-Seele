"""Freeze the working save for full-height components and current fixture inventory."""
import json,msvcrt,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23/global';WORLD=ROOT/'run/saves/SEELE_R22_REVIEW'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 tasks={'components':"import scan_world_components_r19 as s;s.WORLD=w;s.main(o/'components')",'fixtures':"import inventory_world_r19 as s;s.WORLD=w;s.OUT=o/'inventory';s.main();import retire_floating_labels_r19 as t;t.vox.WORLD=w;t.OUT=o/'labels';t.survey()"}
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);jobs=[];logs=[]
  for name,body in tasks.items():
   log=(OUT/(name+'.log')).open('w',encoding='utf8');logs.append(log);code="import sys;from pathlib import Path;sys.path.insert(0,'tools');w=Path('D:/eva/run/saves/SEELE_R22_REVIEW');o=Path('D:/eva/artifacts/facility_r23/global');"+body
   jobs.append((name,subprocess.Popen([sys.executable,'-u','-c',code],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUTF8':'1','OPENBLAS_NUM_THREADS':'1'})))
  errors=[name for name,job in jobs if job.wait()!=0]
  for log in logs:log.close()
  if errors:raise RuntimeError(errors)
  inventory=json.loads((OUT/'inventory/world_objects.json').read_text(encoding='utf8'));parts=inventory['objects']['escalators'];dest=OUT/'walkways';dest.mkdir(exist_ok=True)
  snapshot=dict(scan=dict(full_chunks=inventory['full_chunks'],sections=inventory['sections'],complete=True,source='new full-height R23 scan; no old walkway cache'),steps=[[*q['pos'],q['state']] for q in parts if 'escalator_step' in q['state']],sides=[[*q['pos'],q['state']] for q in parts if 'escalator_side' in q['state']]);(dest/'native_cells.json').write_text(json.dumps(snapshot,separators=(',',':')))
 import audit_moving_walks_r23 as walks
 walks.OUT=dest;walks.main(False)
 print('R23 frozen whole-save scans complete',flush=True)
if __name__=='__main__':main()
