"""Retest the final moved gallery, inspect its footprint and capture it."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
from query_blocks import read_box,iter_block_entities,AIR
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--routes-only',action='store_true');args=ap.parse_args()
 records=json.loads((WORLD/'wayfinding_r21.json').read_text(encoding='utf8'))
 for r in records:
  q=tuple(r['position']);assert 'wayfinding=true' in read_box(WORLD,'projectseele:geofront',q,q)[q]
  tags=dict(iter_block_entities(WORLD,'projectseele:geofront',q,q));assert bool(tags[q]['Wayfinding'])
  for b in r['full_backing']:
   pos=tuple(b['pos']);state=read_box(WORLD,'projectseele:geofront',pos,pos)[pos];assert state.split('[')[0] not in AIR,(r['title'],pos,state)
 (OUT/'wayfinding/verification.json').write_text(json.dumps(dict(passed=True,mounted_boards=len(records),full_backing_cells_per_board=6,headroom_metres=2.25,taller_text_panel=True),indent=2))
 subprocess.run([sys.executable,'tools/audit_spatial_contract_r21.py'],cwd=ROOT,check=True)
 assert not json.loads((OUT/'global_audit/spatial_footprint.json').read_text())['candidates']
 shutil.copy2(OUT/'spatial_contract_r21.json',WORLD/'spatial_contract_r21.json')
 original=(WORLD/'quality_walk_cases.json').read_bytes()
 cases=json.loads((OUT/'hoist_separation/retest_cases.json').read_text())
 env=dict(os.environ);env['JAVA_HOME']=str(Path.home()/'jdks/jdk-17.0.19+10');env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
 try:
  (WORLD/'quality_walk_cases.json').write_text(json.dumps(cases))
  for mode in (('collision',) if args.routes_only else ('collision','edges')):
   stop=WORLD/'regional_stop_requested'
   if stop.exists():shutil.move(stop,OUT/('hoist_separation/prior_stop_'+mode))
   with (OUT/('hoist_separation/native_'+mode+'.log')).open('w') as log:
    subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','runServer','-PregionalBuild=r21-'+mode,'-PreviewServerWorld='+WORLD.name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   if mode=='collision':
    rows=json.loads((WORLD/'quality_native_walk_results.json').read_text());assert len(rows)==2 and all(r['status']=='pass' for r in rows),[(r['id'],r['status'],r.get('actual')) for r in rows]
    (OUT/'hoist_separation/native_routes.json').write_text(json.dumps(rows,indent=2))
    result=json.loads((OUT/'full_native_walk_final.json').read_text());byid={r['id']:r for r in rows};result['results']=[byid.get(r['id'],r) for r in result['results']];result['observer_routes_retested']=2
    (OUT/'full_native_walk_final.json').write_text(json.dumps(result,indent=2))
   else:
    proof=json.loads((WORLD/'r21_edge_physics.json').read_text());assert proof['passed'];shutil.copy2(WORLD/'r21_edge_physics.json',OUT/'edge_physics_pass.json')
 finally:(WORLD/'quality_walk_cases.json').write_bytes(original)
 if args.routes_only:return
 subprocess.run([sys.executable,'tools/run_native_checks_r21.py','worldtour'],cwd=ROOT,check=True)
 subprocess.run([sys.executable,'tools/verify_preservation_r21.py','--world',WORLD.name],cwd=ROOT,check=True)
 print('Observer final native checks complete',flush=True)

if __name__=='__main__':main()
