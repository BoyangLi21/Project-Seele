"""Freeze the user's current R21 save before R22 access and transit changes."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil,subprocess
import nbtlib
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/access_r22'
SITES={'retire_entry_detour':[-308,-466,729],'new_station_connection':[-335,-466,739],'west_dead_end':[-28,-461,269],'south_fall_edge':[-6,-448,385],'west_fall_edge':[-29,-448,268],'playable_piano':[13,-389,355]}
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 if not (OUT/'baseline.json').exists():
  assert not REVIEW.exists(),'Do not overwrite an existing review world'
  rows=subprocess.check_output(['git','status','--porcelain','-uall','-z'],cwd=ROOT).decode().split('\0')
  dirty={r[3:]:hashlib.sha256((ROOT/r[3:]).read_bytes()).hexdigest() for r in rows if r and (ROOT/r[3:]).is_file() and r[3:]!='tools/start_access_r22.py'}
  backup=ROOT/'backups'/('SEELE_R22_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
  with (WORLD/'session.lock').open('r+b') as lock:
   msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
   shutil.copytree(WORLD,backup/'world',ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
   shutil.copytree(WORLD,REVIEW,ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
   shutil.copytree(ROOT/'run/resourcepacks/eva_real_model',backup/'eva_real_model')
  (REVIEW/'session.lock').write_bytes(b'\0')
  level=nbtlib.load(REVIEW/'level.dat');level['Data']['LevelName']=nbtlib.String('SEELE R22 access and transit review');level.save(REVIEW/'level.dat')
  (OUT/'baseline.json').write_text(json.dumps(dict(world=str(WORLD),review=str(REVIEW),backup=str(backup),preexisting_dirty_files=dirty,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()),indent=2))
 (OUT/'reported_sites.json').write_text(json.dumps(SITES,indent=2))
 print('R22 cold baseline and one review copy ready',flush=True)
if __name__=='__main__':main()
