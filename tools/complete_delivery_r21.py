"""Finish remaining native gates sequentially; stop immediately on real failures."""
from pathlib import Path
import json,msvcrt,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R21_REVIEW';OUT=ROOT/'artifacts/un_models_r21'
def run(name,*args):
 print('START',name,flush=True);subprocess.run([sys.executable,'tools/'+name,*args],cwd=ROOT,check=True)
def main():
 deadline=time.monotonic()+1800
 started=json.loads((OUT/'base_review_launch.json').read_text())['epoch']
 while True:
  assert time.monotonic()<deadline,'Real-base drive review did not finish'
  try:
   with (WORLD/'session.lock').open('r+b') as lock:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
   if (WORLD/'un_base_r21_review.json').stat().st_mtime<started:time.sleep(5);continue
   break
  except OSError:time.sleep(5)
 report=json.loads((WORLD/'un_base_r21_review.json').read_text());assert not report['error'],report
 assert report['checks'],report
 for row in report['checks']:(OUT/('base_un'+row['unit'][-2:]+'_pass.json')).write_text(json.dumps(row,indent=2))
 for unit in ('00','01'):assert json.loads((OUT/('base_un'+unit+'_pass.json')).read_text())['passed']
 run('verify_un_bays_r21.py')
 run('repair_un_boarding_bays_r21.py','--main')
 subprocess.run(['C:/Program Files/nodejs/node.exe','tools/verify_un_preview_r21.cjs'],cwd=ROOT,check=True)
 run('run_native_checks_r21.py','flight-riding')
 run('install_un_pair_r21.py')
 run('verify_preservation_r21.py')
 run('verify_preservation_r21.py','--world',WORLD.name)
 run('final_map_acceptance_r21.py')
 print('REMAINING R21 GATES PASSED',flush=True)
if __name__=='__main__':main()
