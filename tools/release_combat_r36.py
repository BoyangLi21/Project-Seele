"""Install or package the reviewed R36 runtime, excluding all save data."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess,zipfile
from check_runtime_r36 import check
from build_server_ready_pack import newest_project_jar
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/combat_direction_r36'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def files():
 result={p.name:p for p in (ART/'profiles').glob('*.json')};result['articulated_bodies_r35.json']=ROOT/'artifacts/combat_rebuild_r35/jbullet/articulated_bodies_r35.json';return result
def guard():
 r=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main|client-.*[.]args|GradleDaemon' }).Count"],capture_output=True,text=True,check=True)
 if int(r.stdout.strip() or '0'):raise RuntimeError('Close Minecraft and Gradle before installing')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');ap.add_argument('--package',action='store_true');args=ap.parse_args();paths=files();check(ART/'profiles')
 hashes={n:sha(p) for n,p in paths.items()};proof=json.loads((ART/'acceptance.json').read_text())
 if not proof.get('native_passed') or proof['inputs_sha256']!=hashes:raise ValueError('Current native evidence is missing')
 baseline=json.loads((ROOT/'artifacts/facility_r31/baseline.json').read_text(encoding='utf-8-sig'))
 for n,h in baseline['original_user_files'].items():
  if sha(ROOT/n)!=h:raise ValueError('Owner file modified: '+n)
 if args.install:
  guard();backup=ART/('runtime_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir();rows=[]
  for n,p in paths.items():
   target=ROOT/'run/projectseele-local-maps'/n;old=sha(target) if target.exists() else None
   if target.exists():shutil.copy2(target,backup/n)
   shutil.copy2(p,target);rows.append(dict(file=n,before=old,after=sha(target)))
  (ART/'installed.json').write_text(json.dumps(dict(revision=36,protocol=41,world_modified=False,backup=str(backup),files=rows),indent=2));check()
 if args.package:
  from run_combat_review_r31 import compiled_hash
  if proof.get('implementation_sha256')!=compiled_hash():raise ValueError('Native implementation proof is stale')
  public=newest_project_jar();out=ROOT/'artifacts/r36_runtime_update';out.mkdir(parents=True,exist_ok=True)
  physics=json.loads((ART/'packaged_physics/thin_floor.json').read_text())
  if not physics.get('passed') or physics.get('mod_sha256')!=sha(public):raise ValueError('Packaged physics evidence is stale')
  runtime=out/'projectseele-0.1.0.jar';private=ROOT/'run/resourcepacks/eva_real_model/assets';replace={'assets/'+p.relative_to(private).as_posix():p for p in private.rglob('*') if p.is_file()}
  with zipfile.ZipFile(public) as src,zipfile.ZipFile(runtime,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
   for entry in src.infolist():
    if entry.filename not in replace:dst.writestr(entry,src.read(entry.filename))
   for n,p in replace.items():dst.write(p,n)
  receipt=dict(revision=36,protocol=41,source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),public_mod_sha256=sha(public),private_mod_sha256=sha(runtime),inputs_sha256=hashes,preserved_owner_inputs=baseline['original_user_files'],world_files_included=False,community_roar_included=False,visual_acceptance='human review pending')
  archive=out/'Project_SEELE_R36_Runtime_Update.zip'
  with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   z.write(runtime,'mods/'+runtime.name)
   for n,p in paths.items():z.write(p,'projectseele-local-maps/'+n)
   for n in ['jbullet-1.0.3-sources.jar','stack-alloc-sources.jar','vecmath-sources.jar']:z.write(ROOT/'artifacts/combat_rebuild_r35/jbullet'/n,'third_party_sources/'+n)
   z.write(ROOT/'docs/ASSETS.md','素材来源与许可.md');z.write(ROOT/'docs/COMBAT_DIRECTION_R36.md','本轮说明.md')
   z.writestr('安装说明.txt','适用于现有 R31/R35 完整实例。关闭游戏与服务器，将 mods 与 projectseele-local-maps 放进对应实例目录，覆盖同名文件；保留原有的其他模组及本地数据。mods 仅保留一个 Project SEELE JAR。客户端与服务端必须同时更新到协议 41。此包不含存档，保留已有材质和光影。R35 社区吼声试用包不随包分发。\n')
   z.writestr('R36_UPDATE.json',json.dumps(receipt,ensure_ascii=False,indent=2))
  receipt.update(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size);(out/'RELEASE.json').write_text(json.dumps(receipt,indent=2));print(archive)
if __name__=='__main__':main()
