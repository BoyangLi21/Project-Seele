"""Cold baseline for the user's R26 field corrections and deployment refresh."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil,subprocess
import nbtlib
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r26'
MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_R26_REVIEW'

def main():
    ART.mkdir(parents=True,exist_ok=True)
    if (ART/'baseline.json').exists():print('Existing R26 baseline retained');return
    assert not REVIEW.exists() and (MAIN/'r25_ready.json').exists()
    original=json.loads((ROOT/'artifacts/facility_r25/baseline.json').read_text())['original_user_files']
    for name,sha in original.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    backup=ROOT/'backups'/('SEELE_R26_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    with (MAIN/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        shutil.copytree(MAIN,backup/'world',ignore=shutil.ignore_patterns('session.lock'))
        (backup/'world/session.lock').write_bytes('\u2603'.encode());shutil.copytree(backup/'world',REVIEW)
    data=nbtlib.load(REVIEW/'level.dat');data['Data']['LevelName']=nbtlib.String('SEELE R26 field corrections');data.save(REVIEW/'level.dat')
    report=dict(revision='R26',authoritative=str(MAIN),world=str(REVIEW),backup=str(backup),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),original_user_files=original,
      tasks=['Lower crane; remove upper cage crossbars; carrier rises during LCL drain','Continuous three-shaft exterior and reported gaps','Recess east lift; remove west platform; repair/remove overlapping old escalators','Actual rail direction and more station/wayfinding signs; every floor to its lift','Command seats and NPC routing; chat-only right click; phone pilot standby','Five-minute underground battery, surface-only cable and retained hatch support','Build and validate three replacement deployment packages'])
    (ART/'baseline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('R26 cold baseline ready',REVIEW)
if __name__=='__main__':main()
