"""Sequential full registered-route and native edge verification on the isolated save."""
from pathlib import Path
import argparse,datetime,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r25';WORLD=ROOT/'run/saves/SEELE_R25_REVIEW'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--affected-only',action='store_true');args=ap.parse_args();out=ART/'validation';out.mkdir(parents=True,exist_ok=True)
 env={**os.environ,'PYTHONUTF8':'1','OPENBLAS_NUM_THREADS':'1','JAVA_HOME':str(Path.home()/'jdks/jdk-17.0.19+10')};env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
 subprocess.run([sys.executable,'tools/export_facility_navigation_r25.py'],cwd=ROOT,env=env,check=True)
 source=out/'affected_walk_cases.json' if args.affected_only else ART/'navigation/full_walk_cases.json';shutil.copy2(source,WORLD/'r25_walk_cases.json')
 guards=json.loads((WORLD/'r25_guard_cases.json').read_text(encoding='utf8'))
 legacy=ROOT/'artifacts/facility_r23/validation/final_guard_cases.json'
 if legacy.exists():
  for q in json.loads(legacy.read_text(encoding='utf8')):
   x,y,z=q['start']
   if 102<=x<=115 and -443<=y<=-437 and -291<=z<=-50:continue
   if q['id'] not in {a['id'] for a in guards}:guards.append(q)
 (WORLD/'r25_guard_cases.json').write_text(json.dumps(guards,ensure_ascii=False,indent=2),encoding='utf8')
 retired_path=ART/'guard_finish/retired_guards.json'
 if retired_path.exists():
  retired={q['id'] for q in json.loads(retired_path.read_text(encoding='utf8'))}
  guards=[q for q in guards if q['id'] not in retired]
  (WORLD/'r25_guard_cases.json').write_text(json.dumps(guards,ensure_ascii=False,indent=2),encoding='utf8')
 for mode,result,label in [('r25-collision','quality_native_walk_results.json','affected' if args.affected_only else 'full'),('r25-edges','r25_edge_physics.json','edges')]:
  began=datetime.datetime.now().timestamp()
  with (out/('native_'+label+'_final.log')).open('w',encoding='utf8') as log:
   subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','runServer','-PregionalBuild='+mode,'-PreviewServerWorld='+WORLD.name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  path=WORLD/result;assert path.exists() and path.stat().st_mtime>=began,('No fresh native result',mode)
  data=json.loads(path.read_text(encoding='utf8'));shutil.copy2(path,out/('native_'+label+'_result.json'))
  if mode=='r25-collision':
   bad=[{k:q[k] for k in ('id','status','actual')} for q in data if q['status']!='pass'];print('Native route results',len(data),'failures',bad,flush=True);assert not bad
  else:print('Native edge result',data['passed'],len(data['checks']),flush=True);assert data['passed'],[q for q in data['checks'] if not q['passed']]
 print('R25 world checks complete',flush=True)
if __name__=='__main__':main()
