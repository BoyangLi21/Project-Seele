"""Seal the reviewed R35 runtime, leaving every user world outside the archive."""
from pathlib import Path
import datetime,hashlib,json,subprocess,zipfile
from build_server_ready_pack import newest_project_jar
from install_combat_r35 import inputs,sha
from check_runtime_r35 import check
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/combat_rebuild_r35';OUT=ROOT/'artifacts/r35_runtime_update'

def main():
    proof=json.loads((ART/'acceptance.json').read_text());paths=inputs();hashes={n:sha(p) for n,p in paths.items()}
    if not proof.get('native_passed') or proof['inputs_sha256']!=hashes:raise ValueError('Unreviewed motion or physical profiles')
    check(ART/'profiles',paths['articulated_bodies_r35.json'])
    public=newest_project_jar();physics=json.loads((ART/'packaged_physics/result.json').read_text())
    if not physics.get('passed') or physics['mod_sha256']!=sha(public):raise ValueError('Packaged physics check is stale')
    baseline=json.loads((ROOT/'artifacts/facility_r31/baseline.json').read_text(encoding='utf-8-sig'))
    for n,h in baseline['original_user_files'].items():
        if sha(ROOT/n)!=h:raise ValueError('Owner file changed: '+n)
    OUT.mkdir(parents=True,exist_ok=True);private=ROOT/'run/resourcepacks/eva_real_model/assets';runtime=OUT/'projectseele-0.1.0.jar'
    replacements={'assets/'+p.relative_to(private).as_posix():p for p in private.rglob('*') if p.is_file()}
    with zipfile.ZipFile(public) as source,zipfile.ZipFile(runtime,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as target:
        for entry in source.infolist():
            if entry.filename not in replacements:target.writestr(entry,source.read(entry.filename))
        for name,path in replacements.items():target.write(path,name)
    shader=ROOT/'run/shaderpacks/ComplementaryUnbound_r5.3_SEELE_LCL.zip'
    if not shader.is_file():raise FileNotFoundError(shader)
    receipt={'revision':'R35','protocol':39,'created':datetime.datetime.now().astimezone().isoformat(),'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'public_mod_sha256':sha(public),'private_runtime_sha256':sha(runtime),'inputs_sha256':hashes,'acceptance_sha256':sha(ART/'acceptance.json'),'world_files_included':False,'existing_community_roar_included':False}
    guide='关闭游戏和服务器，将 mods 和 projectseele-local-maps 覆盖到各自游戏目录。客户端与服务端都要更新到协议 39，mods 内只保留一份 Project SEELE。\n\nshaderpacks 中附 LCL 兼容版光影；开启光影时请选择 ComplementaryUnbound_r5.3_SEELE_LCL。本机源码入口 start_eva_test_r35.bat --city-shaders 会自动选用它。\n\n存档、其他模组、现有材质和用户设置均不在更新范围。社区吼声音频只沿用本机已有试用资源，不随此更新包分发。\n\n'+(ROOT/'docs/COMBAT_REBUILD_R35.md').read_text(encoding='utf8')
    archive=OUT/'Project_SEELE_R35_Runtime_Update.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as target:
        target.write(runtime,'mods/'+runtime.name)
        for name,path in paths.items():target.write(path,'projectseele-local-maps/'+name)
        target.write(shader,'shaderpacks/'+shader.name)
        for name in ['jbullet-1.0.3-sources.jar','stack-alloc-sources.jar','vecmath-sources.jar']:target.write(ART/'jbullet'/name,'third_party_sources/'+name)
        target.write(ROOT/'docs/ASSETS.md','素材来源与许可.md');target.writestr('安装与操作说明.txt',guide);target.writestr('R35_UPDATE.json',json.dumps(receipt,ensure_ascii=False,indent=2))
    receipt.update(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size);(OUT/'RELEASE.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(archive)
if __name__=='__main__':main()
