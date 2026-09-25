"""Five complete owner-local archives, with a PCL-importable client and pinned visuals."""
from pathlib import Path
import argparse,datetime,json,hashlib,shutil,subprocess,zipfile,msvcrt
import build_server_ready_pack as base
ROOT=base.ROOT;OUT=ROOT/'artifacts/server-ready-r39';STAGE=OUT/'stage'
WORLD='SEELE_R31_WORLD';base.WORLD_NAME=WORLD

def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf8')
def data(p,obj):write(p,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jar(folder):
    files=list((folder/'mods').glob('projectseele-*.jar'));assert len(files)==1;return files[0]
def stage():
    from release_combat_r36 import guard
    from check_runtime_r39 import check
    guard();check()
    assert not STAGE.exists(),'Do not overwrite an existing release batch'
    baseline=read(ROOT/'artifacts/facility_r31/baseline.json')
    for name,digest in baseline['original_user_files'].items():assert base.sha256(ROOT/name)==digest,name
    # The ordinary save, never the transport/lighting fixture.
    frozen=read(ROOT/'artifacts/transport_return_r39/baseline.json')
    current=ROOT/'run/saves'/WORLD
    for name,row in frozen['files'].items():
        p=current/name;assert p.stat().st_size==row['size'] and p.stat().st_mtime_ns==row['mtime'],name
    guide=(ROOT/'docs/TRANSPORT_RETURN_R39.md').read_text(encoding='utf8')
    server,client,world,textures,shaders=(STAGE/n for n in ('server','client','world','textures','shaders'))
    with zipfile.ZipFile(base.newest_project_jar()) as z:
        assert b"\x01\x00\x0244" in z.read("com/projectseele/network/SeeleNetwork.class"),"Wrong runtime protocol"
    base.validate_private_eva_mesh_contracts()
    base.build_server(server,guide,revision='R39');base.build_client(client,guide,revision='R39',city_shaders=True)
    with (current/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        base.build_world(world)
    shader=read(ROOT/'run/projectseele-local-maps/revision_r39.json')['shader']
    texture=read(ROOT/'tools/realistic_pack_r25.json')
    for folder,kind,spec in ((textures,'resourcepacks',texture),(shaders,'shaderpacks',shader)):
        source=ROOT/'run'/kind/spec['filename'];assert source.is_file()
        if 'sha512' in spec:assert hashlib.sha512(source.read_bytes()).hexdigest()==spec['sha512']
        else:assert base.sha256(source)==spec['sha256']
        base.copy_file(source,folder/kind/source.name);base.copy_file(source,client/kind/source.name)
        if kind=='shaderpacks':
            for target in (folder,client):
                base.copy_file(source.with_name(source.name+'.txt'),target/kind/(source.name+'.txt'))
                write(target/'config/oculus.properties','enableShaders=true\nshaderPack='+source.name+'\n')
        write(folder/'安装说明.txt','合并到 PCL 对应版本的独立游戏目录。客户端包已内置同一份资源，此包用于单独备份或更新。\n')
    # Copy only deployment files; account caches, logs and review fixtures stay out.
    for folder in (server,client):
        base.copy_file(ROOT/'docs/TRANSPORT_RETURN_R39.md',folder/'R39使用说明.md')
        base.copy_file(ROOT/'docs/FIRST_ACT_R31_CN.md',folder/'第一幕流程.md')
        base.copy_file(ROOT/'docs/ASSETS.md',folder/'素材来源.md')
        for name in ['jbullet-1.0.3-sources.jar','stack-alloc-sources.jar','vecmath-sources.jar']:
            base.copy_file(ROOT/'artifacts/combat_rebuild_r35/jbullet'/name,folder/'third_party_sources'/name)
        local=folder/'projectseele-local-maps'
        for p in list(local.glob('*worldtour.json'))+list(local.glob('*_review.json')):p.unlink()
    runtime=ROOT/'.Codex/server-pack-cache/runtime-r25/libraries'
    base.copy_tree(runtime,server/'libraries')
    write(server/'eula.txt','# Review https://aka.ms/MinecraftEULA before setting true.\neula=false\n')
    write(server/'Start-Server.bat','@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\nif not exist "'+WORLD+'\\level.dat" (echo Import the World ZIP into '+WORLD+' first. & pause & exit /b 1)\r\nset "SEELE_JAVA=java"\r\nif defined JAVA_HOME set "SEELE_JAVA=%JAVA_HOME%\\bin\\java.exe"\r\n"%SEELE_JAVA%" @user_jvm_args.txt @libraries/net/minecraftforge/forge/1.20.1-47.4.10/win_args.txt nogui\r\npause\r\n')
    write(server/'start-server.sh','#!/usr/bin/env sh\ncd "$(dirname "$0")" || exit 1\nexec "${JAVA_HOME:+$JAVA_HOME/bin/}java" @user_jvm_args.txt @libraries/net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt nogui\n')
    # No installer can silently select the obsolete, darker shader.
    write(client/'Enable-Visuals.ps1',"$ErrorActionPreference = 'Stop'\n$cfg = Join-Path $PSScriptRoot 'config\\oculus.properties'\n[IO.File]::WriteAllText($cfg, \"enableShaders=true`nshaderPack="+shader['filename']+"`n\", [Text.UTF8Encoding]::new($false))\nWrite-Host 'R39 installed shader enabled; no downloads.'\n")
    write(client/'Enable-Visuals.bat','@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File Enable-Visuals.ps1\r\npause\r\n')
    opts={line.partition(':')[0]:line.partition(':')[2] for line in (client/'options.txt').read_text().splitlines() if ':' in line}
    opts.update(lang='zh_cn',renderDistance='16',simulationDistance='8',gamma='1.0',resourcePacks=json.dumps(['vanilla','mod_resources','file/'+texture['filename'],'file/eva_real_model']),incompatibleResourcePacks=json.dumps(['file/'+texture['filename']]))
    write(client/'options.txt',''.join(k+':'+v+'\n' for k,v in opts.items()))
    write(client/'PCL/Setup.ini','VersionArgumentIndieV2:True\n')
    hashes={p.name:base.sha256(p) for p in (ROOT/'run/projectseele-local-maps').glob('*.json')}
    batch=dict(revision='R39',protocol=44,created=datetime.datetime.now().astimezone().isoformat(),world=WORLD,
        mod_sha256=base.sha256(jar(server)),runtime_profiles=hashes,shader=shader,texture=texture['filename'],world_original_progress=True)
    assert batch['mod_sha256']==base.sha256(jar(client))
    for folder in (server,client,world,textures,shaders):data(folder/'R39_BATCH.json',batch)
    data(OUT/'batch.json',batch);print('Five full R39 stages ready',flush=True)

def seal():
    from release_combat_r36 import guard
    guard();proof=read(OUT/'production_check.json');assert proof['passed']
    native=read(ROOT/'artifacts/transport_return_r39/native.json');assert native['passed']
    batch=read(OUT/'batch.json');assert proof['mod_sha256']==batch['mod_sha256']
    batch['source_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    rows=[]
    for kind in ('Client','Server','World','Shaders','Textures'):
        folder=STAGE/kind.lower();data(folder/'R39_BATCH.json',batch)
        if kind!='World':base.write_manifest(folder,'r39-'+kind.lower())
        target=OUT/f'Project_SEELE_R39_{kind}.zip';assert not target.exists()
        with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            prefix='overrides/' if kind=='Client' else ''
            for path in sorted(folder.rglob('*')):
                if path.is_file():z.write(path,prefix+path.relative_to(folder).as_posix())
            if kind=='Client':
                manifest=dict(minecraft=dict(version='1.20.1',modLoaders=[dict(id='forge-47.4.10',primary=True)]),manifestType='minecraftModpack',manifestVersion=1,name='Project SEELE R39',version='R39',author='Project SEELE',files=[],overrides='overrides')
                z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
                for p in sorted((STAGE/'world').rglob('*')):
                    if p.is_file():z.write(p,'overrides/saves/'+WORLD+'/'+p.relative_to(STAGE/'world').as_posix())
                z.writestr('先读我.txt','直接将本 ZIP 拖入 PCL 安装新实例。模组、模型、存档、材质、光影已全部内置；只可能补下载缺失的 Minecraft/Forge 基础运行库。Java 17，建议分配 6–8 GB 内存。\n')
        with zipfile.ZipFile(target) as z:assert z.testzip() is None
        rows.append(dict(file=target.name,bytes=target.stat().st_size,sha256=base.sha256(target)));print(kind+' ZIP ready',flush=True)
    data(OUT/'RELEASE.json',dict(**batch,files=rows,native=native,server_validation=proof,visual_acceptance='Manual in-game acceptance remains with the user'))
    write(OUT/'SHA256SUMS.txt',''.join(row['sha256']+'  '+row['file']+'\n' for row in rows))
    base.copy_file(ROOT/'docs/TRANSPORT_RETURN_R39.md',OUT/'安装与验收.md')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','seal']);a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    stage() if a.action=='stage' else seal()
