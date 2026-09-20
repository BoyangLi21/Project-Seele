"""Recheck failed routes and every route touching post-full-audit corrections."""
from pathlib import Path
import json,math,time,subprocess,sys,os,shutil,argparse
import numpy as np
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r28';WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--last-failures',action='store_true');args=ap.parse_args()
    base=json.loads((ART/'validation/full_walk_cases.json').read_text());cases={q['id']:q for q in base};extra=[]
    for name in ('map_access','hakone_map'):
        extra+=json.loads((ART/name/'contract.json').read_text())['walk_nodes']
    cases.update({q['id']:q for q in extra});failed={q['id'] for q in json.loads((ART/'validation/failed_routes.json').read_text())};selected=failed|{q['id'] for q in extra}
    boxes=[]
    for root in ('retained_junctions','stair_heads','map_access','hakone_map'):
        for folder in (ART/root).glob('*/applied_*'):
            for path in (folder/'delta').glob('c.*.npz'):
                cx,cz=map(int,path.stem.split('.')[1:])
                with np.load(path) as d:
                    ids=d['offsets'].astype(int)+int(d['minimum'])*256
                    points=np.c_[cx*16+(ids&15),ids//256,cz*16+((ids//16)&15)]
                    boxes.append((points.min(0)-[3,3,3],points.max(0)+[3,3,3]))
    def intersects(a,b,low,high):
        delta=b-a;enter=0.;leave=1.
        for axis in range(3):
            if abs(delta[axis])<1e-8:
                if a[axis]<low[axis] or a[axis]>high[axis]:return False
            else:
                x,y=(low[axis]-a[axis])/delta[axis],(high[axis]-a[axis])/delta[axis];enter=max(enter,min(x,y));leave=min(leave,max(x,y))
        return enter<=leave
    for key,q in cases.items():
        pts=q.get('path') or [q['start'],q['end']]
        if any(intersects(np.asarray(a),np.asarray(b),lo,hi) for a,b in zip(pts,pts[1:]) for lo,hi in boxes):selected.add(key)
    if args.last_failures:
        last={q['id'] for q in json.loads((ART/'validation/recheck_failed.json').read_text())}
        selected=last|{'r28/map_approach/'+k for k in last}
    tests=[q for key,q in cases.items() if key in selected]
    out=ART/'validation';(out/'final_catalogue.json').write_text(json.dumps(list(cases.values()),ensure_ascii=False,indent=2),encoding='utf8');(out/'recheck_cases.json').write_text(json.dumps(tests,ensure_ascii=False,indent=2),encoding='utf8');shutil.copy2(out/'recheck_cases.json',WORLD/'r28_walk_cases.json')
    states=set(json.loads((WORLD/'regional_states.json').read_text()))
    for p in ART.rglob('states.json'):states.update(json.loads(p.read_text()))
    (WORLD/'regional_states.json').write_text(json.dumps(sorted(states)))
    print('Rechecking',len(tests),'of final',len(cases),'registered routes',flush=True);began=time.time()
    env={**os.environ,'PYTHONUTF8':'1','JAVA_HOME':str(Path.home()/'jdks/jdk-17.0.19+10')};env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
    with (out/'native_recheck.log').open('w',encoding='utf8') as log:subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','runServer','-PregionalBuild=r28-collision','-PreviewServerWorld='+WORLD.name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    path=WORLD/'quality_native_walk_results.json';assert path.stat().st_mtime>=began
    data=json.loads(path.read_text());assert len(data)==len(tests);shutil.copy2(path,out/'native_recheck_result.json')
    bad=[q for q in data if q['status']!='pass'];(out/'recheck_failed.json').write_text(json.dumps(bad,ensure_ascii=False,indent=2),encoding='utf8')
    print('Recheck failures',[(q['id'],q['status'],q.get('actual')) for q in bad],flush=True)
    assert not bad
    results={q['id']:q for q in json.loads((out/'native_full_result.json').read_text())};
    previous=out/'native_recheck_first_result.json'
    if previous.exists():results.update({q['id']:q for q in json.loads(previous.read_text())})
    results.update({q['id']:q for q in data});assert set(cases)<=set(results) and all(results[k]['status']=='pass' for k in cases)
    (out/'accepted_routes.json').write_text(json.dumps([results[k] for k in cases],ensure_ascii=False),encoding='utf8')
    shutil.copy2(out/'final_catalogue.json',WORLD/'r28_walk_cases.json')
    print('Accepted final routes',len(cases),flush=True)

if __name__=='__main__':main()
