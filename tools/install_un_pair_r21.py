"""Install exactly the reviewed private pair after all native base checks."""
import datetime,hashlib,json,msvcrt,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/un_models_r21';WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
def digest(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def main():
 for unit in ('00','01'):
  for test in ('mechanics','terrain','base'):
   report=json.loads((OUT/(test+'_un'+unit+'_pass.json')).read_text())
   if test=='base':assert report['passed'] and report['wet_closed_restored'] and report['driven_out_and_back']
   else:
    assert not report.get('error'),report.get('error')
    if test=='mechanics':assert len(report['checks'])==14 and all(v is True for v in report['checks'].values()),test
    else:assert len(report['cases'])==10 and all(r['passed'] for r in report['cases']),test
 assert json.loads((OUT/'boarding/native_acceptance.json').read_text())['passed']
 source=ROOT/'run/resourcepacks/eva_un_r21_review/assets/projectseele';target=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
 paths=[f'{folder}/{name}{suffix}' for name in ('eva_prototype','eva_un01') for folder,suffix in [('mesh','.mesh.json'),('geo','.geo.json'),('textures/entity','.png'),('textures/entity','_eyes.png'),('animations','.animation.json')]]
 staging=json.loads((OUT/'staging.json').read_text())
 for row in staging['records']:assert digest(source/'mesh'/(row['asset']+'.mesh.json'))==row['sha256']
 backup=OUT/'installation'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  rows=[]
  for rel in paths:
   old=target/rel;save=backup/rel
   if old.exists():save.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,save)
   old.parent.mkdir(parents=True,exist_ok=True);temp=old.with_name(old.name+'.r21-new');shutil.copy2(source/rel,temp);os.replace(temp,old)
   rows.append(dict(path=str(old),before=digest(save) if save.exists() else None,after=digest(old)))
  marker=WORLD/'un_models_r21.json'
  if marker.exists():shutil.copy2(marker,backup/marker.name)
  marker.write_text(json.dumps(dict(revision='R21',airframes=staging['records'],installation=str(backup)),indent=2))
 (backup/'receipt.json').write_text(json.dumps(dict(files=rows,backup=str(backup)),indent=2))
 env=dict(os.environ);env['JAVA_HOME']=str(Path.home()/'jdks/jdk-17.0.19+10');env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
 with (OUT/'main_commission.log').open('w') as log:
  subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','runServer','-PregionalBuild=r21-un-commission','-PreviewServerWorld='+WORLD.name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 report=json.loads((WORLD/'un_commission_r21.json').read_text());assert report['passed'] and len(report['units'])==2
 assert not (WORLD/'un_commission_r21_failure.txt').exists()
 zero=next(r for r in report['units'] if r['unit']=='EVA-UN-00');assert zero['airframe']=='aa222a1b-fb8b-4f62-8a60-0bfd20772115' and zero['plug']=='c331d78c-a22b-4892-afee-35390ee0df35'
 shutil.copy2(WORLD/'un_commission_r21.json',OUT/'main_commission.json')
 (OUT/'main_install.json').write_text(json.dumps(dict(installed=True,receipt=str(backup/'receipt.json'),commission=report),indent=2))
 print('Both private UN airframes installed and commissioned',flush=True)
if __name__=='__main__':main()
