"""Freeze the installed, player-tested R24 before the requested R25 repairs."""
from pathlib import Path
import datetime, hashlib, json, msvcrt, shutil, subprocess
import nbtlib

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts/facility_r25'
MAIN = ROOT / 'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
REVIEW = ROOT / 'run/saves/SEELE_R25_REVIEW'

def main():
    ART.mkdir(parents=True, exist_ok=True)
    if (ART / 'baseline.json').exists():
        print('Existing R25 baseline retained'); return
    assert not REVIEW.exists()
    assert json.loads((MAIN / 'r24_ready.json').read_text())['ready']
    protected = json.loads((ROOT / 'artifacts/facility_r24/baseline.json').read_text())['original_user_files']
    for name, sha in protected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, name
    backup = ROOT / 'backups' / ('SEELE_R25_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    with (MAIN / 'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        shutil.copytree(MAIN, backup / 'world', ignore=shutil.ignore_patterns('session.lock'))
        (backup / 'world/session.lock').write_bytes('\u2603'.encode())
        shutil.copytree(backup / 'world', REVIEW)
    level = nbtlib.load(REVIEW / 'level.dat')
    level['Data']['LevelName'] = nbtlib.String('SEELE R25 circulation and communications review')
    level.save(REVIEW / 'level.dat')
    report = dict(revision='R25', world=str(REVIEW), authoritative=str(MAIN), backup=str(backup),
                  head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  original_user_files=protected,
                  authorization='2026-09-19 user coordinates, circulation, NPC roles/radio, pilot dispatch, EVA stance/audio/umbilical')
    (ART / 'baseline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('R25 frozen baseline and review ready', REVIEW, flush=True)

if __name__ == '__main__': main()
