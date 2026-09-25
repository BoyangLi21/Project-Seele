"""Install/package verified R37 candidates; never modify save data."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess,zipfile
from check_runtime_r37 import check
from build_server_ready_pack import newest_project_jar
from release_combat_r36 import guard
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/combat_beast_r37';OUT=ROOT/'artifacts/r37_runtime_update'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def payload():
    paths={Path('projectseele-local-maps')/p.name:p for p in (ART/'profiles').glob('*.json')}
    paths[Path('projectseele-local-maps/articulated_bodies_r35.json')]=ROOT/'run/projectseele-local-maps/articulated_bodies_r35.json'
    for folder in ['tv_jaw','materials']:
        for p in (ART/folder/'assets').rglob('*'):
            if p.is_file():paths[Path('resourcepacks/eva_real_model/assets')/p.relative_to(ART/folder/'assets')]=p
    return paths
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');ap.add_argument('--package',action='store_true');args=ap.parse_args()
    check(ART/'profiles',ART/'tv_jaw/assets');paths=payload();hashes={n.as_posix():sha(p) for n,p in paths.items()}
    proof=json.loads((ART/'acceptance.json').read_text());
    if not proof.get('native_passed') or proof['payload_sha256']!=hashes:raise ValueError('Native evidence does not match current assets')
    from run_combat_review_r31 import compiled_hash
    if compiled_hash()!=proof['implementation_sha256']:raise ValueError('Implementation changed since native review')
    baseline=json.loads((ROOT/'artifacts/facility_r31/baseline.json').read_text(encoding='utf-8-sig'))
    for n,h in baseline['original_user_files'].items():
        if sha(ROOT/n)!=h:raise ValueError('Owner file changed: '+n)
    guard()
    if args.install:
        backup=ART/('runtime_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir();rows=[]
        for n,p in paths.items():
            target=(ROOT/'run'/n).resolve();before=sha(target) if target.exists() else None
            if before==sha(p):continue
            if target.exists():(backup/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup/n)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);rows.append(dict(file=n.as_posix(),before=before,after=sha(target)))
        (ART/'installed.json').write_text(json.dumps(dict(revision=37,protocol=42,world_modified=False,backup=str(backup),files=rows),indent=2));check()
    if args.package:
        public=newest_project_jar();OUT.mkdir(parents=True,exist_ok=True);runtime=OUT/'projectseele-0.1.0.jar'
        private=ROOT/'run/resourcepacks/eva_real_model/assets';replace={'assets/'+p.relative_to(private).as_posix():p for p in private.rglob('*') if p.is_file()}
        with zipfile.ZipFile(public) as src,zipfile.ZipFile(runtime,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
            for entry in src.infolist():
                if entry.filename not in replace:dst.writestr(entry,src.read(entry.filename))
            for n,p in replace.items():dst.write(p,n)
        receipt=dict(revision=37,protocol=42,public_mod_sha256=sha(public),private_mod_sha256=sha(runtime),payload_sha256=hashes,world_files_included=False,official_reference_images_included=False,community_roar_included=False,visual_acceptance='human review pending')
        archive=OUT/'Project_SEELE_R37_Runtime_Update.zip'
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.write(runtime,'mods/'+runtime.name)
            for n,p in paths.items():z.write(p,n.as_posix())
            z.write(ROOT/'docs/BEAST_AWAKENING_R37.md','本轮说明.md');z.write(ROOT/'docs/ASSETS.md','素材来源与许可.md')
            z.writestr('安装说明.txt','关闭游戏和服务器，将本包解压到现有实例根目录，覆盖 mods、projectseele-local-maps 和 resourcepacks 中同名文件；mods 内仅保留一个 Project SEELE JAR。客户端与服务端须同时更新至协议 42。本包不包含存档。客户端的资源包更新不可省略，否则旧头部模型会覆盖新模型。光影使用现有 Complementary Unbound 5.3 SEELE LCL；材质模式 RP_MODE=3、ENTITY_SHADOWS_DEFINE=1、NORMAL_MAP_STRENGTH=70。\n')
            z.writestr('R37_UPDATE.json',json.dumps(receipt,ensure_ascii=False,indent=2))
        receipt.update(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size);(OUT/'RELEASE.json').write_text(json.dumps(receipt,indent=2));print(archive)
if __name__=='__main__':main()
