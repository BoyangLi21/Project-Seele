"""Install only the verified private UN pair and three unchanged local skins."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,os,shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/facility_r23'
WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
SOURCE=ROOT/'run/resourcepacks/eva_access_r22_review'
TARGET=ROOT/'run/resourcepacks/eva_real_model'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert json.loads((OUT/'final_acceptance.json').read_text())['passed']
    assert json.loads((OUT/'promotion/installed.json').read_text())['installed']
    rows=json.loads((OUT/'models/staged_files.json').read_text())
    for row in json.loads((ROOT/'artifacts/access_r22/asset_stage.json').read_text(encoding='utf8'))['skins']:
        rows.append(dict(path=f"assets/projectseele/textures/entity/training_pilot_{row['role']}.png",sha256=row['sha256']))
    assert len(rows)==13
    for row in rows:assert digest(SOURCE/row['path'])==row['sha256'],row['path']
    backup=OUT/'asset_install'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True);saved=[];absent=[]
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            for row in rows:
                rel=Path(row['path']);dst=TARGET/rel
                if dst.exists():
                    old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,old);saved.append(rel)
                else:absent.append(rel)
                dst.parent.mkdir(parents=True,exist_ok=True)
                temp=dst.with_name(dst.name+'.r23-new');shutil.copy2(SOURCE/rel,temp);os.replace(temp,dst)
                assert digest(dst)==row['sha256']
            marker=WORLD/'un_models_r23.json'
            if marker.exists():shutil.copy2(marker,backup/marker.name)
            report=dict(installed=True,files=rows,backup=str(backup),private_only=True)
            marker.write_text(json.dumps(report,indent=2),encoding='utf8')
            (OUT/'asset_install/installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        except BaseException:
            for rel in saved:shutil.copy2(backup/rel,TARGET/rel)
            for rel in absent:
                dst=(TARGET/rel).resolve();assert dst.is_relative_to(TARGET.resolve())
                if dst.exists():dst.unlink()
            raise
    print('Installed 10 UN model resources and 3 private pilot skins')
if __name__=='__main__':main()
