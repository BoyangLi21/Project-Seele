"""Install the staged native MTR database after measured geometry has been written."""
from pathlib import Path
from datetime import datetime
import hashlib,json,msvcrt,shutil
from regional_voxels import ROOT,WORLD,OUT

source=ROOT/'.Codex/world-expansion/mtr-staging2/projectseele/geofront'
destination=WORLD/'mtr/projectseele/geofront'
lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
receipts=list((OUT/'geometry_all').glob('applied_*/receipt.json'))
if not receipts or not json.loads(receipts[-1].read_text(encoding='utf-8'))['verified']:raise RuntimeError('Verified regional geometry required')
if any(file.is_file() for file in (destination/'rails').rglob('*')):raise RuntimeError('Existing installed railway must not be replaced')
backup=OUT/('mtr_install_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
if destination.exists():shutil.copytree(destination,backup/'before')
manifest=[]
for file in source.rglob('*'):
    if not file.is_file():continue
    relative=file.relative_to(source);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(file,target);digest=hashlib.sha256(file.read_bytes()).hexdigest()
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('MTR install readback '+str(relative))
    manifest.append(dict(file=str(relative),sha256=digest))
(backup/'receipt.json').write_text(json.dumps(dict(files=manifest,source=str(source),verified=True),indent=2),encoding='utf-8')
for file in (WORLD/'regional_plan.json',OUT/'regional_plan.json'):
    data=json.loads(file.read_text(encoding='utf-8'));data['geometry_ready']=True;data['main_lift']['exit']='north';data['mtr_installed']=True;data['native_rail_count']=98
    file.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('NATIVE MTR INSTALLED',len(manifest),'verified files',flush=True)
