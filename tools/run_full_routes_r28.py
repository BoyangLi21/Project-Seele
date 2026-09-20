"""Validate the full retained route catalogue and every R28 added path natively."""
from pathlib import Path
import json,os,subprocess,sys,time,shutil
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r28';WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW'

def main():
    env={**os.environ,'PYTHONUTF8':'1','OPENBLAS_NUM_THREADS':'1','JAVA_HOME':str(Path.home()/'jdks/jdk-17.0.19+10')};env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
    subprocess.run([sys.executable,'tools/prepare_checks_r28.py'],cwd=ROOT,env=env,check=True)
    cases=json.loads((ART/'navigation/full_walk_cases.json').read_text());extra=json.loads((ART/'validation/affected_walk_cases.json').read_text());cases=list({q['id']:q for q in cases+extra}.values())
    target=ART/'validation/full_walk_cases.json';target.write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8');shutil.copy2(target,WORLD/'r28_walk_cases.json')
    began=time.time()
    with (ART/'validation/native_full.log').open('w',encoding='utf8') as log:
        subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','runServer','-PregionalBuild=r28-collision','-PreviewServerWorld='+WORLD.name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    path=WORLD/'quality_native_walk_results.json';assert path.stat().st_mtime>=began,'No fresh native results'
    data=json.loads(path.read_text());assert len(data)==len(cases),(len(data),len(cases))
    shutil.copy2(path,ART/'validation/native_full_result.json');bad=[q for q in data if q['status']!='pass'];print('Full native routes',len(data),'failures',len(bad),flush=True)
    (ART/'validation/failed_routes.json').write_text(json.dumps(bad,ensure_ascii=False,indent=2),encoding='utf8')
    if bad:print([(q['id'],q['status'],q.get('actual')) for q in bad],flush=True)
    assert not bad

if __name__=='__main__':main()
