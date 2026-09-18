"""Sequential actual-client reviews with fresh result gates and preserved old evidence."""
from pathlib import Path
import argparse,datetime,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/validation'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('checks',nargs='+',choices=['lifts','lifts_all','un','trains','surface_trains','flight','tour','piano']);args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 modes={'lifts':('r22-lifts','r20_lift_review.json'),'lifts_all':('r22-lifts-all','r20_lift_review.json'),'un':('r22-un-base','un_base_r22_review.json'),'trains':('r22-train-riding','r23_train_ride_metrics.json'),'flight':('r22-flight-riding','r21_flight_metrics.json'),'tour':('r22-worldtour',None),'piano':('r22-prepare','r22_piano_review.json')}
 modes['surface_trains']=('r22-surface-trains','r23_train_ride_metrics.json')
 for kind in args.checks:
  mode,result=modes[kind];prior=OUT/'prior'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');prior.mkdir(parents=True)
  if (OUT/('client_'+kind+'.log')).exists():shutil.copy2(OUT/('client_'+kind+'.log'),prior/('client_'+kind+'.log'))
  for name in [result,'regional_transit_riding_failure.txt','regional_stop_requested']:
   if name and (WORLD/name).exists():shutil.move(str(WORLD/name),str(prior/name))
  start=datetime.datetime.now().timestamp()
  with (OUT/('client_'+kind+'.log')).open('w',encoding='utf8') as log:
   code=subprocess.call([sys.executable,'tools/launch_rendered_client_r17.py','--world',WORLD.name,'--heap','6G','--review',mode,'--native-capture'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUTF8':'1','OPENBLAS_NUM_THREADS':'1'})
  assert code==0,('Actual client process failed',kind,code)
  if result:
   p=WORLD/result;assert p.exists() and p.stat().st_mtime>=start,('No new native result',kind);data=json.loads(p.read_text(encoding='utf8'))
   if kind in ('lifts','lifts_all'):assert not data['error'] and len(data['trips'])==(10 if kind=='lifts_all' else 8) and all(q['passed'] for q in data['trips']),data
   elif kind=='un':assert not data['error'] and len(data['checks'])==2 and all(q['passed'] and q['attack_recover_reset_commands'] and q['wet_closed_restored'] for q in data['checks']),data
   elif kind=='trains':assert len(data)==3 and {q['service'] for q in data}=={'U1','S1','R1'} and all(q['nativePassengerRegistration'] and q['stoppedAtNextStation'] for q in data),data
   elif kind=='surface_trains':assert len(data)==2 and {q['service'] for q in data}=={'S1','R1'} and all(q['nativePassengerRegistration'] and q['stoppedAtNextStation'] for q in data),data
   elif kind=='flight':assert data['passed'] and data['oppositeAirportStop'] and data['nativePassengerRegistration'],data
   elif kind=='piano':assert data['passed'],data
   shutil.copy2(p,OUT/('client_'+kind+'_pass.json'))
  else:
   tours=[p for p in (ROOT/'artifacts/facility_r23').glob('native_tour_*/receipt.json') if p.stat().st_mtime>=start];assert len(tours)==1
   data=json.loads(tours[0].read_text());expected=json.loads((ROOT/'run/projectseele-local-maps/r23_worldtour.json').read_text());assert len(data)==len(expected);shutil.copy2(tours[0],OUT/'client_tour_receipt.json')
  print('Actual client review passed',kind,flush=True)
if __name__=='__main__':main()
