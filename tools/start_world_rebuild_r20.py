"""Cold snapshot and explicit scope for the user's R20 reconstruction request."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
OUT=ROOT/'artifacts/world_rebuild_r20'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'baseline.json').exists():print('R20 baseline already present');return
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=ROOT/'backups'/('SEELE_R20_'+stamp)
    status=subprocess.check_output(['git','status','--porcelain','-uall','-z'],cwd=ROOT).decode().split('\0')
    owned=[r[3:] for r in status if r and (ROOT/r[3:]).is_file() and r[3:]!='tools/start_world_rebuild_r20.py']
    before={name:sha(ROOT/name) for name in owned}
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        shutil.copytree(WORLD,backup/'world',ignore=shutil.ignore_patterns('session.lock'))
        shutil.copytree(ROOT/'run/resourcepacks/eva_real_model',backup/'resourcepack')
        for name in owned:
            dest=backup/'user_files'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    assert all(sha(ROOT/name)==h for name,h in before.items())
    (OUT/'baseline.json').write_text(json.dumps({'world':str(WORLD),'backup':str(backup),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'preexisting_dirty_files':before,'created_at':datetime.datetime.now().astimezone().isoformat()},indent=2),encoding='utf8')
    refs=OUT/'references';refs.mkdir(exist_ok=True)
    source=Path('C:/Users/liboy/OneDrive/文档/xwechat_files/wxid_afzx30m2xeso12_550e/temp/RWTemp/2026-09/9e20f478899dc29eb19741386f9343c8/be2c7678a38d0c593b5f9f3a7efbd8cf.jpg')
    shutil.copy2(source,refs/'un01_user_reference.jpg')
    for name in ('reference_public.mp4','reference_mechanisms.jpg','reference_overview.jpg'):shutil.copy2(ROOT/'artifacts/world_repair_r19/references'/name,refs/name)
    print('R20 cold snapshot',backup,'preexisting user files',len(before),flush=True)

if __name__=='__main__':main()
