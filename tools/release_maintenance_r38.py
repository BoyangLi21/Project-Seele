"""Ship R38 code and reviewed facility shader, preserving current save progress."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,zipfile
from release_combat_r36 import guard
from build_server_ready_pack import newest_project_jar
from run_combat_review_r31 import compiled_hash
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/combat_facility_r38';OUT=ROOT/'artifacts/r38_runtime_update'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');p.add_argument('--package',action='store_true');a=p.parse_args();guard()
    proof=json.loads((ART/'acceptance.json').read_text());baseline=json.loads((ART/'baseline.json').read_text())
    if not proof['passed'] or proof['implementation_sha256']!=compiled_hash():raise ValueError('Current native verification is incomplete')
    for n,h in baseline['original_user_files'].items():
        if sha(ROOT/n)!=h:raise ValueError('Owner input changed '+n)
    for n,h in baseline['world_files'].items():
        if sha(ROOT/'run/saves/SEELE_R31_WORLD'/n)!=h:raise ValueError('Formal save changed '+n)
    shader=ART/'shaders/ComplementaryUnbound_r5.3_SEELE_R38.zip';shader_hash=sha(shader)
    if shader_hash!=proof['shader_sha256']:raise ValueError('Shader differs from the reviewed build')
    marker=dict(revision=38,protocol=43,shader=dict(filename=shader.name,sha256=shader_hash),world_modified=False)
    marker_path=ART/'revision_r38.json';marker_path.write_text(json.dumps(marker,indent=2))
    if a.install:
        backup=ART/('runtime_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
        for relative,source in [(Path('projectseele-local-maps/revision_r38.json'),marker_path),(Path('shaderpacks')/shader.name,shader),(Path('shaderpacks')/(shader.name+'.txt'),shader.with_name(shader.name+'.txt'))]:
            target=ROOT/'run'/relative
            if target.exists():(backup/relative).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup/relative)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        config=ROOT/'run/config/oculus.properties';shutil.copy2(config,backup/'oculus.properties')
        lines=[line for line in config.read_text(encoding='utf8').splitlines() if line.partition('=')[0] not in ('enableShaders','shaderPack')]
        config.write_text('\n'.join(lines+['enableShaders=true','shaderPack='+shader.name])+'\n',encoding='utf8')
        (ART/'installed.json').write_text(json.dumps(dict(**marker,backup=str(backup)),indent=2))
    if a.package:
        OUT.mkdir(parents=True,exist_ok=True);public=newest_project_jar();runtime=OUT/'projectseele-0.1.0.jar'
        private=ROOT/'run/resourcepacks/eva_real_model/assets';assets={'assets/'+p.relative_to(private).as_posix():p for p in private.rglob('*') if p.is_file()}
        with zipfile.ZipFile(public) as src,zipfile.ZipFile(runtime,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
            for info in src.infolist():
                if info.filename not in assets:dst.writestr(info,src.read(info.filename))
            for name,path in assets.items():dst.write(path,name)
        archive=OUT/'Project_SEELE_R38_Runtime_Update.zip'
        receipt=dict(**marker,mod_sha256=sha(runtime),public_mod_sha256=sha(public),formal_world_preserved=True,community_roar_included=False)
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.write(runtime,'mods/'+runtime.name);z.write(marker_path,'projectseele-local-maps/'+marker_path.name)
            z.write(shader,'shaderpacks/'+shader.name);z.write(shader.with_name(shader.name+'.txt'),'shaderpacks/'+shader.name+'.txt')
            z.writestr('config/oculus.properties','enableShaders=true\nshaderPack='+shader.name+'\n')
            for n in ['jbullet-1.0.3-sources.jar','stack-alloc-sources.jar','vecmath-sources.jar']:z.write(ROOT/'artifacts/combat_rebuild_r35/jbullet'/n,'third_party_sources/'+n)
            z.write(ROOT/'docs/ASSETS.md','素材来源与许可.md');z.write(ROOT/'docs/COMBAT_RECOVERY_LIGHTING_R38.md','本轮说明.md')
            z.writestr('安装说明.txt','适用于现有 R37 实例。关闭游戏与服务器，将本包目录覆盖到 Minecraft 实例根目录，mods 内仅保留一个 Project SEELE JAR。客户端与服务端同时升级到协议 43；服务端不需要光影配置。此包不包含存档，保留当前进度及原有其他模组。NERV 运输机维护命令：/nerv transport force_recover；状态：/nerv transport status。光影选择 ComplementaryUnbound_r5.3_SEELE_R38.zip。\n')
            z.writestr('R38_UPDATE.json',json.dumps(receipt,ensure_ascii=False,indent=2))
        receipt.update(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size);(OUT/'RELEASE.json').write_text(json.dumps(receipt,indent=2));print(archive)
if __name__=='__main__':main()
