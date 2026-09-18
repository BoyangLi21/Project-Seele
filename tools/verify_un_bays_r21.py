"""Native walking and guard attempts on the final UN boarding catwalks."""
import json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R21_REVIEW';OUT=ROOT/'artifacts/un_models_r21/boarding'

def main():
 original=(WORLD/'quality_walk_cases.json').read_bytes()
 cases=json.loads((OUT/'retest_cases.json').read_text())
 env=dict(os.environ);env['JAVA_HOME']=str(Path.home()/'jdks/jdk-17.0.19+10');env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
 try:
  (WORLD/'quality_walk_cases.json').write_text(json.dumps(cases))
  for mode in ('collision','un-edges'):
   with (OUT/('native_'+mode+'.log')).open('w') as log:
    subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','runServer','-PregionalBuild=r21-'+mode,'-PreviewServerWorld='+WORLD.name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   if mode=='collision':
    rows=json.loads((WORLD/'quality_native_walk_results.json').read_text());assert len(rows)==len(cases)==8 and all(r['status']=='pass' for r in rows),rows
    (OUT/'native_routes.json').write_text(json.dumps(rows,indent=2))
   else:
    edges=json.loads((WORLD/'r21_un_edge_physics.json').read_text());assert edges['passed'] and len(edges['checks'])==8,edges
    (OUT/'native_edges.json').write_text(json.dumps(edges,indent=2))
 finally:(WORLD/'quality_walk_cases.json').write_bytes(original)
 catalogue=json.loads(original);proof=ROOT/'artifacts/world_repair_r21/full_native_walk_final.json';full=json.loads(proof.read_text());byid={r['id']:r for r in full['results']};byid.update({r['id']:r for r in rows})
 assert set(byid)=={c['id'] for c in catalogue} and len(catalogue)==8865
 full['results']=[byid[c['id']] for c in catalogue];full['total']=len(catalogue);full['un_boarding_routes_retested']=8;proof.write_text(json.dumps(full,indent=2))
 (ROOT/'artifacts/world_repair_r21/full_walk_catalogue.json').write_bytes(original)
 (OUT/'native_acceptance.json').write_text(json.dumps(dict(passed=True,native_walks=len(rows),edge_attempts=len(edges['checks'])),indent=2))
 print('UN catwalks: eight native walks and eight guard attempts passed',flush=True)
if __name__=='__main__':main()
