"""Sequential real-client reviews, with explicit per-stage result gates."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys,datetime,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('checks',nargs='+',choices=['lifts','factory','flight-riding','flight-un-boarding','worldtour']);a=ap.parse_args()
 for mode in a.checks:
  stop=WORLD/'regional_stop_requested'
  if stop.exists():
   saved=OUT/'prior_test_results'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');saved.mkdir(parents=True,exist_ok=True);shutil.move(str(stop),saved/stop.name)
  results={'lifts':['r20_lift_review.json'],'factory':['r20_factory_pass.json','r20_factory_failure.txt','r21_sound_events.json'],'flight-riding':['r21_flight_metrics.json'],'flight-un-boarding':['r21_un_boarding_metrics.json'],'worldtour':[]}[mode]
  for name in results:
   p=WORLD/name
   if p.exists():
    dest=OUT/'prior_test_results'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');dest.mkdir(parents=True,exist_ok=True);shutil.move(str(p),dest/name)
  with (OUT/('native_'+mode+'.log')).open('w',encoding='utf8') as log:
   result=subprocess.call([sys.executable,'tools/launch_rendered_client_r17.py','--world',WORLD.name,'--heap','6G','--review','r21-'+mode,'--native-capture'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  assert result==0,('Native client process failed',mode,result)
  if mode=='lifts':
   report=json.loads((WORLD/'r20_lift_review.json').read_text());assert not report['error'] and len(report['trips'])==4 and all(x['passed'] for x in report['trips']),report
   shutil.copy2(WORLD/'r20_lift_review.json',OUT/'native_lift_pass.json')
  elif mode=='factory':
   assert not (WORLD/'r20_factory_failure.txt').exists(),(WORLD/'r20_factory_failure.txt').read_text()
   report=json.loads((WORLD/'r20_factory_pass.json').read_text());assert report
   shutil.copy2(WORLD/'r20_factory_pass.json',OUT/'native_factory_pass.json');shutil.copy2(WORLD/'r21_sound_events.json',OUT/'native_sound_events.json')
  elif mode=='flight-riding':
   report=json.loads((WORLD/'r21_flight_metrics.json').read_text());assert report['passed'] and report['oppositeAirportStop'] and report['nativePassengerRegistration'],report
   shutil.copy2(WORLD/'r21_flight_metrics.json',OUT/'native_flight_pass.json')
   sources=['src/main/java/com/projectseele/client/AircraftCorrectionR21.java','src/main/java/com/projectseele/client/AircraftRenderClockR21.java','src/main/java/com/projectseele/client/AircraftCorrectionAccess.java','src/main/java/com/projectseele/mixin/client/AircraftPositionSmoothingMixin.java','src/main/java/com/projectseele/mixin/client/AircraftCorrectionBudgetMixin.java','src/main/java/com/projectseele/mixin/client/MtrFrameClockR21Mixin.java','src/main/java/com/projectseele/client/visual/RegionalTransitRidingChecks.java']
   (OUT/'native_flight_source.json').write_text(json.dumps(dict(passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}),indent=2))
  elif mode=='flight-un-boarding':
   report=json.loads((WORLD/'r21_un_boarding_metrics.json').read_text());assert report['passed'] and report['nativePassengerRegistration'] and report['boardingOnly'],report
   shutil.copy2(WORLD/'r21_un_boarding_metrics.json',OUT/'native_un_boarding_pass.json')
  print('R21 NATIVE COMPLETE',mode,flush=True)
if __name__=='__main__':main()
