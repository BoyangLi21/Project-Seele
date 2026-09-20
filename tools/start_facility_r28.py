"""Cold baseline for the user's R28 field corrections and deployment refresh."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil,subprocess
import nbtlib
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r28'
MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW'

def main():
    ART.mkdir(parents=True,exist_ok=True)
    if (ART/'baseline.json').exists():print('Existing R28 baseline retained');return
    assert not REVIEW.exists() and (MAIN/'r27_ready.json').exists()
    original=json.loads((ROOT/'artifacts/facility_r27/baseline.json').read_text())['original_user_files']
    for name,sha in original.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    backup=ROOT/'backups'/('SEELE_FIELD_R28_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    with (MAIN/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        shutil.copytree(MAIN,backup/'world',ignore=shutil.ignore_patterns('session.lock'))
        (backup/'world/session.lock').write_bytes('\u2603'.encode());shutil.copytree(backup/'world',REVIEW)
    data=nbtlib.load(REVIEW/'level.dat');data['Data']['LevelName']=nbtlib.String('SEELE R28 field corrections');data.save(REVIEW/'level.dat')
    report=dict(revision='R28',authoritative=str(MAIN),world=str(REVIEW),backup=str(backup),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),original_user_files=original,
      tasks=['Right fingers on all EVA variants','Carrier physical contacts and charging connector; handoff to relocated surface pylons','Reported shaft gaps; divider rear removal Z -53 through -33 with shaft width retained','Five times initial launch rate; unchanged surface arrival','NTW-20 rifle report and larger impact smoke','Pyramid corridor/wayfinding and named elevator stops','Reported 190/197 east tunnel; full-world obsolete transit audit','NERV airport rail station and continuous road approach','Provided Fuyutsuki skin and persistent command chair seating','Native validation and three matching deployment archives'])
    (ART/'baseline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('R28 cold baseline ready',REVIEW)
if __name__=='__main__':main()
