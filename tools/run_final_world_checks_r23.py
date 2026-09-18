"""Final affected collision routes, perimeter pushes and cold liquid readback."""
from pathlib import Path
import datetime,json,os,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23/validation'
WORLD=ROOT/'run/saves/SEELE_R22_REVIEW'
def main():
    env={**os.environ,'PYTHONUTF8':'1','OPENBLAS_NUM_THREADS':'1','JAVA_HOME':str(Path.home()/'jdks/jdk-17.0.19+10')}
    env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
    subprocess.run([sys.executable,'tools/prepare_final_audits_r23.py','--install'],cwd=ROOT,env=env,check=True)
    for mode,result,destination in [('r23-collision','quality_native_walk_results.json','native_final_walk_results.json'),('r23-edges','r23_edge_physics.json','native_final_guard_results.json')]:
        start=datetime.datetime.now().timestamp()
        with (OUT/(mode+'_final.log')).open('w',encoding='utf8') as log:
            subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','runServer','-PregionalBuild='+mode,'-PreviewServerWorld='+WORLD.name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        p=WORLD/result;assert p.exists() and p.stat().st_mtime>=start
        data=json.loads(p.read_text(encoding='utf8'));shutil.copy2(p,OUT/destination)
        if mode=='r23-collision':
            assert len(data)==len(json.loads((OUT/'final_walk_cases.json').read_text(encoding='utf8')))
            bad=[q for q in data if q['status']!='pass'];assert not bad,bad
        else:assert data['passed'],[q for q in data['checks'] if not q['passed']]
        print('Native final check passed',mode,flush=True)
    for script in ('check_containment_final_r23.py','refresh_walkway_inventory_r23.py'):
        subprocess.run([sys.executable,'tools/'+script],cwd=ROOT,env=env,check=True)
    latest={}
    for name in ('native_full_walk_results.json','native_recheck2_results.json','native_final_walk_results.json'):
        latest.update({q['id']:q for q in json.loads((OUT/name).read_text(encoding='utf8'))})
    cases=json.loads((OUT/'full_walk_cases.json').read_text(encoding='utf8'))
    missing=[q['id'] for q in cases if q['id'] not in latest or latest[q['id']]['status']!='pass'];assert not missing,missing
    report=dict(passed=True,current_cases=len(cases),final_affected_cases=len(json.loads((OUT/'native_final_walk_results.json').read_text())),
                retired_cases=len(json.loads((OUT/'retired_routes.json').read_text(encoding='utf8'))),
                source_reports=['native_full_walk_results.json','native_recheck2_results.json','native_final_walk_results.json'])
    (OUT/'all_current_walks_pass.json').write_text(json.dumps(report,indent=2))
    print('All current route IDs passed',len(cases),flush=True)
if __name__=='__main__':main()
