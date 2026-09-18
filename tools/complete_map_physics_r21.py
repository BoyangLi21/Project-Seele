"""Finish full-catalogue audit, rerun corrected seams, then real passengers."""
from pathlib import Path
import json,msvcrt,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW'
def run(script,*args):subprocess.run([sys.executable,'tools/'+script,*args],cwd=ROOT,check=True)
def main():
 deadline=time.monotonic()+2400
 while True:
  assert time.monotonic()<deadline,'Full route audit did not finish'
  try:
   report=json.loads((WORLD/'quality_native_walk_results.json').read_text())
   rows=report if isinstance(report,list) else report.get('results',[])
   if len(rows)!=8861:time.sleep(3);continue
   with (WORLD/'session.lock').open('r+b') as lock:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
   break
  except (OSError,json.JSONDecodeError):time.sleep(3)
 shutil.copy2(WORLD/'quality_native_walk_results.json',OUT/'full_native_walk_first.json')
 cases=json.loads((WORLD/'quality_walk_cases.json').read_text());assert len(cases)==8861
 (OUT/'full_walk_catalogue.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
 bad=[r for r in rows if r['status']!='pass'];print('Full native audit',len(rows),'cases, failures',[(r['id'],r['status']) for r in bad],flush=True)
 assert all('base/taxi_cross_-6080' in r['id'] or 'base/cross_-6080' in r['id'] for r in bad),'New failure needs inspection before continuing'
 if bad:
  run('finish_un_crossing_r21.py');ids={r['id'] for r in bad}
  (WORLD/'quality_walk_cases.json').write_text(json.dumps([c for c in cases if c['id'] in ids]))
  env=dict(os.environ);env['JAVA_HOME']=str(Path.home()/'jdks/jdk-17.0.19+10');env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
  with (OUT/'native_crossing_retry.log').open('w') as log:
   subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','runServer','-PstrictHighDetail=true','-PregionalBuild=r21-collision','-PreviewServerWorld='+WORLD.name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  final=json.loads((WORLD/'quality_native_walk_results.json').read_text());final=final if isinstance(final,list) else final['results']
  assert len(final)==len(bad) and all(r['status']=='pass' for r in final),final
  (OUT/'crossing_retry_pass.json').write_text(json.dumps(final,indent=2))
  replacement={r['id']:r for r in final};rows=[replacement.get(r['id'],r) for r in rows]
 (WORLD/'quality_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'full_native_walk_final.json').write_text(json.dumps(dict(passed=True,total=len(rows),rerun_after_measured_fix=len(bad),results=rows),indent=2))
 run('freeze_geometry_r21.py')
 run('run_native_checks_r21.py','lifts','factory','flight-riding','worldtour')
if __name__=='__main__':main()
