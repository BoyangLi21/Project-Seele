"""Finish installation and delivery once the current full-flight proof exists."""
import hashlib,json,msvcrt,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW'
def run(name,*args):
 print('START',name,flush=True);subprocess.run([sys.executable,'tools/'+name,*args],cwd=ROOT,check=True)
def main():
 deadline=time.monotonic()+7200
 while True:
  assert time.monotonic()<deadline,'The current full-flight proof did not arrive'
  try:
   evidence=json.loads((OUT/'native_flight_source.json').read_text());report=json.loads((OUT/'native_flight_pass.json').read_text())
   ready=evidence['passed'] and report['passed'] and report['oppositeAirportStop'] and all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in evidence['sha256'].items())
   with (WORLD/'session.lock').open('r+b') as lock:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
   if ready:break
  except (OSError,json.JSONDecodeError):pass
  time.sleep(5)
 run('install_un_pair_r21.py')
 run('verify_preservation_r21.py')
 run('verify_preservation_r21.py','--world',WORLD.name)
 run('final_map_acceptance_r21.py')
 # The new shared client clock also governs trains. Reuse the unchanged P1
 # geometry in its original disposable native-transit review world.
 train_world=ROOT/'run/saves/SEELE_R20_REVIEW';started=time.time()
 with (OUT/'native_port_clock.log').open('w') as log:
  subprocess.run([sys.executable,'tools/launch_rendered_client_r17.py','--world',train_world.name,'--review','r20-port-boarding','--native-capture'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
 train_path=train_world/'r20_port_metrics.json';assert train_path.stat().st_mtime>=started,'No fresh train result'
 train=json.loads(train_path.read_text());assert train['passed'] and train['nativePassengerRegistration'] and train['travel']>500,train
 (OUT/'native_port_clock_pass.json').write_text(json.dumps(dict(world=train_world.name,metrics=train,clock_sources=evidence['sha256']),indent=2))
 import encode_review_movies_r20 as video
 video.OUT=OUT/'media';folder=sorted((OUT/'transit').glob('native_movie_r21-flight-riding_*'))[-1]
 video.main(folder,'flight','R21_NERV_UN_flight',OUT/'native_flight_pass.json')
 run('publish_acceptance_r21.py')
 run('install_navigation_markers_r21.py','--apply')
 subprocess.run([str(ROOT/'start_eva_test_r21.bat'),'--check'],cwd=ROOT,check=True)
 env=dict(os.environ);env['JAVA_HOME']=str(Path.home()/'jdks/jdk-17.0.19+10');env['PATH']=env['JAVA_HOME']+'/bin;'+env['PATH']
 with (OUT/'final_build.log').open('w') as log:
  subprocess.run([str(ROOT/'gradlew.bat'),'--no-daemon','build'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('R21 INSTALLED, VERIFIED AND BUILT',flush=True)
if __name__=='__main__':main()
