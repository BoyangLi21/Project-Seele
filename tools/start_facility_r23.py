"""Freeze the post-human-inspection R22 world; retain this same working save."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'baseline.json').exists():print('R23 baseline already exists');return
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=ROOT/'backups'/('SEELE_R23_'+stamp)
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  shutil.copytree(WORLD,backup/'world',ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
  shutil.copytree(ROOT/'run/resourcepacks/eva_access_r22_review',backup/'review_assets')
  status=subprocess.check_output(['git','status','--porcelain','-z','-uall'],cwd=ROOT).decode().split('\0');files={}
  for row in status:
   if not row:continue
   relative=row[3:];source=ROOT/relative
   if source.is_file():
    dest=backup/'workspace'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);files[relative]=hashlib.sha256(source.read_bytes()).hexdigest()
  old=json.loads((ROOT/'artifacts/access_r22/baseline.json').read_text())
  (OUT/'baseline.json').write_text(json.dumps(dict(world=str(WORLD),backup=str(backup),starting_workspace=files,original_user_files=old['preexisting_dirty_files'],source='post-user manual inspection, not original R21',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()),indent=2))
 print('R23 post-inspection cold backup ready',backup,flush=True)
if __name__=='__main__':main()
