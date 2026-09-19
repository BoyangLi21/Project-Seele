"""Retire the unused buffer spur west of the U2 platform, with native graph checks."""
from pathlib import Path
import json,shutil,subprocess,msvcrt
from stage_native_transit_repair import hashes
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/transit';STAGE=ROOT/'.Codex/r25-native-transit'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 data=json.loads((WORLD/'native_transit_r23.json').read_text(encoding='utf8'))
 for depot in data['depot_paths']:
  for segment in depot['path']:
   assert not any(segment[k]=={'x':94,'y':-443,'z':-40} for k in ('startPosition','endPosition')),('Spur is in an active service',depot['name'])
 if not STAGE.exists():
  with (WORLD/'session.lock').open('r+b') as lock:
   msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);before=hashes(WORLD/'mtr');shutil.copytree(WORLD/'mtr',STAGE)
   assert before==hashes(STAGE);(OUT/'source_hashes.json').write_text(json.dumps(before,indent=2))
 plan={'rails':[],'stations':[],'lines':[],'retire_rails':[{'from':[94,-443,-40],'to':[118,-443,-40],'from_angle':'E','to_angle':'W'}]}
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2))
 java=Path.home()/'jdks/jdk-17.0.19+10/bin';classes=ROOT/'.Codex/r25-java';classes.mkdir(exist_ok=True)
 libs=Path.home()/'.gradle/caches/modules-2/files-2.1/org.apache.logging.log4j';cp=';'.join(map(str,[ROOT/'.Codex/local-mods/MTR-forge-4.0.5+1.20.1.jar']+sorted(libs.glob('*/2.19.0/*/*.jar'))))
 subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(classes),str(ROOT/'tools/java/RegionalTransitAuthor.java'),str(ROOT/'tools/java/TransitSnapshotR20.java')],check=True)
 with (OUT/'native.log').open('w',encoding='utf8') as log:
  subprocess.run([str(java/'java.exe'),'-Dfile.encoding=UTF-8','-cp',cp+';'+str(classes),'RegionalTransitAuthor',str(OUT/'plan.json'),str(STAGE),str(OUT/'built'),'--append'],check=True,stdout=log,stderr=subprocess.STDOUT)
  subprocess.run([str(java/'java.exe'),'-Dfile.encoding=UTF-8','-cp',cp+';'+str(classes),'TransitSnapshotR20',str(STAGE),str(OUT/'native_final.json')],check=True,stdout=log,stderr=subprocess.STDOUT)
 result=json.loads((OUT/'built/native_transit_receipt.json').read_text(encoding='utf8'));assert result['passed'] and len(result['retired_rails'])==1
 after=hashes(STAGE);before=json.loads((OUT/'source_hashes.json').read_text());delta=sorted(k for k in set(after)|set(before) if after.get(k)!=before.get(k))
 # Saving the native simulator may touch timings; installation is bounded to
 # its one retired rail file, never the running train or schedule records.
 deleted=[k for k in delta if k not in after];assert len(deleted)==1 and '/rails/' in '/'+deleted[0],delta
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);target=(WORLD/'mtr'/deleted[0]).resolve();assert target.is_relative_to((WORLD/'mtr').resolve())
  assert hashes(WORLD/'mtr')[deleted[0]]==before[deleted[0]]
  backup=OUT/'before'/deleted[0];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup);target.unlink()
  shutil.copy2(OUT/'native_final.json',WORLD/'native_transit_r25.json')
 (OUT/'installed_review.json').write_text(json.dumps({'retired_file':deleted[0],'old_sha':before[deleted[0]],'active_service_path_uses_spur':False,'other_native_files_preserved':True},indent=2))
 print('Retired one unused U2 spur; active platform and all service identities retained')
if __name__=='__main__':main()
