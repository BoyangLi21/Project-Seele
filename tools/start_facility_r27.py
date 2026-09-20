"""Cold baseline for the user's R27 field corrections and deployment refresh."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil,subprocess
import nbtlib
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r27'
MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_R27_REVIEW'

def main():
    ART.mkdir(parents=True,exist_ok=True)
    if (ART/'baseline.json').exists():print('Existing R27 baseline retained');return
    assert not REVIEW.exists() and (MAIN/'r26_ready.json').exists()
    original=json.loads((ROOT/'artifacts/facility_r26/baseline.json').read_text())['original_user_files']
    for name,sha in original.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    backup=ROOT/'backups'/('SEELE_R27_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    with (MAIN/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        shutil.copytree(MAIN,backup/'world',ignore=shutil.ignore_patterns('session.lock'))
        (backup/'world/session.lock').write_bytes('\u2603'.encode());shutil.copytree(backup/'world',REVIEW)
    data=nbtlib.load(REVIEW/'level.dat');data['Data']['LevelName']=nbtlib.String('SEELE R27 field corrections');data.save(REVIEW/'level.dat')
    report=dict(revision='R27',authoritative=str(MAIN),world=str(REVIEW),backup=str(backup),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),original_user_files=original,
      tasks=['Move Fuyutsuki to commander dais; native city controls','Chest-height F5 in hangar and silo','Three verified matching deployment archives'])
    (ART/'baseline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('R27 cold baseline ready',REVIEW)
if __name__=='__main__':main()
