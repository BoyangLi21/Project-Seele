"""Freeze the user's current local R30 save, keeping test runtime state isolated."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r31';SOURCE=ROOT/'run/saves/SEELE_R30_WORLD';REVIEW=ROOT/'run/saves/SEELE_FIELD_R31_REVIEW'
def main():
    ART.mkdir(parents=True,exist_ok=True)
    if (ART/'baseline.json').exists():print('R31 baseline already recorded');return
    assert not REVIEW.exists()
    original=json.loads((ROOT/'artifacts/facility_r30/baseline.json').read_text())['original_user_files'];original={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in original}
    extra='tools/java/TransitSnapshotR20.class'
    if (ROOT/extra).exists():original[extra]=hashlib.sha256((ROOT/extra).read_bytes()).hexdigest()
    stamp=datetime.datetime.now().astimezone();backup=ROOT/'backups'/('SEELE_R31_'+stamp.strftime('%Y%m%d_%H%M%S'))/'world'
    with (SOURCE/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        shutil.copytree(SOURCE,backup,ignore=shutil.ignore_patterns('session.lock','*.lock'))
        shutil.copytree(SOURCE,REVIEW,ignore=shutil.ignore_patterns('session.lock','*.lock'))
    report={'revision':'R31','created':stamp.isoformat(),'source_world':str(SOURCE),'review_world':str(REVIEW),'backup':str(backup),'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'original_user_files':original,'authority':'User confirmed current R30 local save; latest gameplay preserved. Only exact map receipts may return from review.'}
    (ART/'baseline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('Current R30 backed up; R31 isolated world ready',flush=True)
if __name__=='__main__':main()
