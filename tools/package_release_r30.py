"""Seal five matching personal deployment archives from the verified R30 world."""
from pathlib import Path
import argparse,datetime,hashlib,json,msvcrt,subprocess,zipfile
import build_server_ready_pack as base

ROOT=base.ROOT;OUT=ROOT/'artifacts/server-ready-r30';STAGE=OUT/'stage'
base.WORLD_NAME='SEELE_R30_WORLD'

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf8',newline='\n')

def visual_specs():
    shader=[x for x in json.loads((ROOT/'tools/city_shaders_r29.json').read_text()) if x['project']=='complementary-unbound']
    assert len(shader)==1
    texture=json.loads((ROOT/'tools/realistic_pack_r25.json').read_text())
    return texture,shader[0]

def stage(manual=False):
    assert not STAGE.exists(),'Keep the earlier stage intact; inspect it before retrying.'
    ready=json.loads((ROOT/'run/saves'/base.WORLD_NAME/'r30_ready.json').read_text())
    assert ready['installed'] and (ready['verification_passed'] or manual and ready.get('acceptance_mode')=='manual_by_user')
    base.validate_private_eva_mesh_contracts()
    guide=(ROOT/'docs/PRIVATE_SERVER_DEPLOYMENT_R30_CN.md').read_text(encoding='utf8')
    server,client,world,textures,shaders=(STAGE/q for q in ('server','client','world','textures','shaders'))
    base.build_server(server,guide,revision='R30');base.build_client(client,guide,revision='R30',city_shaders=True)
    lock=(ROOT/'run/saves'/base.WORLD_NAME/'session.lock').open('r+b')
    try:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);base.build_world(world)
    finally:lock.close()
    scripts=ROOT/'tools/deployment_r29'
    for folder in (server,client):
        base.copy_file(scripts/'Setup.ps1',folder/'Setup.ps1')
        for name in ('MANUAL_ACCEPTANCE_R30.md','FIRST_ACT_R30_CN.md','FIELD_REPAIR_R30.md','PRIVATE_SERVER_DEPLOYMENT_R30_CN.md','UN_MODELS_R30.md'):
            base.copy_file(ROOT/'docs'/name,folder/name)
    for name in ('Start-Server.bat','start-server.sh','install-server.sh'):base.copy_file(scripts/name,server/name)
    base.copy_file(ROOT/'tools/forge_runtime_r25.json',server/'forge-runtime.json')
    base.copy_file(ROOT/'tools/realistic_pack_r25.json',client/'realistic-pack.json')
    base.copy_file(ROOT/'tools/city_shaders_r29.json',client/'city-shaders.json')
    base.copy_file(scripts/'Install-Visuals.ps1',client/'Install-Visuals.ps1')
    for name,command in [('Install-Visuals','Install-Visuals.ps1'),('Install-Textures','Setup.ps1 -Kind Client')]:
        write(client/(name+'.bat'),'@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File '+command+'\r\npause\r\n')
    write(server/'Install-Server.bat','@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File Setup.ps1 -Kind Server\r\npause\r\n')
    write(server/'eula.txt','# Review https://aka.ms/MinecraftEULA before setting true.\neula=false\n')
    write(server/'user_jvm_args.txt',base.jvm_args());write(server/'server.properties',base.server_properties())
    options=client/'options.txt';write(options,options.read_text(encoding='utf8')+'lang:zh_cn\n')
    for folder in (server,client):
        for spec in folder.glob('projectseele-local-maps/*worldtour.json'):spec.unlink()
        for name in ('eva_body_r30_review.json','eva_dorsal_r30_review.json'):
            (folder/'projectseele-local-maps'/name).unlink(missing_ok=True)
    texture,shader=visual_specs()
    for spec,source,destination in [(texture,ROOT/'run/resourcepacks',textures/'resourcepacks'),(shader,ROOT/'run/shaderpacks',shaders/'shaderpacks')]:
        path=source/spec['filename'];assert hashlib.sha512(path.read_bytes()).hexdigest()==spec['sha512']
        base.copy_file(path,destination/spec['filename'])
        # Author archives remain byte-identical, including their own notices.
    base.copy_file(ROOT/'run/shaderpacks'/(shader['filename']+'.txt'),shaders/'shaderpacks'/(shader['filename']+'.txt'))
    write(shaders/'config/oculus.properties','enableShaders=true\nshaderPack='+shader['filename']+'\n')
    for folder,kind in [(textures,'材质'),(shaders,'光影')]:
        write(folder/'安装说明.txt',f'这是你已下载资源的私人本地备份。将本包解压到客户端的游戏目录，合并同名文件夹。\n'+('随后运行客户端中的 Install-Textures.bat。校验本地文件后直接启用，无需再次下载。' if kind=='材质' else '客户端已带 Oculus。启动后可在视频设置的光影菜单中启用或关闭。')+'\n请保留作者原包及说明。不要将私人整合包作为项目开源发布物。\n')
    manifest={'revision':'R30','acceptance_mode':ready.get('acceptance_mode','native_verified'),'created':datetime.datetime.now().astimezone().isoformat(),'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'world':base.WORLD_NAME,'mod_sha256':base.sha256(next((server/'mods').glob('projectseele-*.jar'))),'world_marker_sha256':base.sha256(world/'r30_ready.json'),'visuals':{'texture':texture['filename'],'shader':shader['filename']}}
    assert manifest['mod_sha256']==base.sha256(next((client/'mods').glob('projectseele-*.jar')))
    for folder in (server,client,world,textures,shaders):write(folder/'R30_BATCH.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    for folder,kind in ((server,'server-files'),(client,'client-pack'),(textures,'personal-textures'),(shaders,'personal-shaders')):base.write_manifest(folder,kind)
    write(OUT/'batch.json',json.dumps(manifest,ensure_ascii=False,indent=2));print('R30 five parts staged',flush=True)

def seal(manual=False):
    if manual:
        proof={'passed':None,'status':'not_run_user_requested_manual_acceptance','mod_sha256':base.sha256(next((STAGE/'server/mods').glob('projectseele-*.jar'))),'scope':'User requested packaging without further functional validation; final production-server and complete UN-pair acceptance remain manual.'}
        write(OUT/'manual_acceptance.json',json.dumps(proof,indent=2))
    else:
        proof=json.loads((OUT/'production_check.json').read_text());assert proof['passed']
    folders={name:STAGE/name.lower() for name in ('Server','Client','World','Textures','Shaders')}
    server,client=folders['Server'],folders['Client']
    assert (server/'eula.txt').read_text().strip().endswith('eula=false') and not (server/'libraries').exists()
    assert not list(client.glob('resourcepacks/rotrblocks*.zip')) and not list(client.glob('shaderpacks/*.zip'))
    assert all(base.sha256(next((folder/'mods').glob('projectseele-*.jar')))==proof['mod_sha256'] for folder in (server,client))
    batch=json.loads((OUT/'batch.json').read_text());batch['source_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for folder in folders.values():write(folder/'R30_BATCH.json',json.dumps(batch,ensure_ascii=False,indent=2))
    for name,kind in [('Server','server-files'),('Client','client-pack'),('Textures','personal-textures'),('Shaders','personal-shaders')]:base.write_manifest(folders[name],kind)
    write(OUT/'batch.json',json.dumps(batch,ensure_ascii=False,indent=2));rows=[]
    for name,folder in folders.items():
        target=OUT/f'Project_SEELE_R30_{name}.zip'
        if manual:
            with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
                for path in sorted(folder.rglob('*')):
                    if path.is_file():archive.write(path,path.relative_to(folder).as_posix())
        else:
            base.zip_tree(folder,target)
            with zipfile.ZipFile(target) as archive:
                assert archive.testzip() is None
                for path in folder.rglob('*'):
                    if path.is_file():assert hashlib.sha256(archive.read(path.relative_to(folder).as_posix())).hexdigest()==base.sha256(path)
        rows.append({'file':target.name,'bytes':target.stat().st_size,'sha256':base.sha256(target)})
        print(name+' archived',flush=True)
    if not manual:base.validate_outputs(OUT/'Project_SEELE_R30_Server.zip',OUT/'Project_SEELE_R30_World.zip',OUT/'Project_SEELE_R30_Client.zip',city_shaders=True)
    write(OUT/'SHA256SUMS.txt','\n'.join(f"{r['sha256']}  {r['file']}" for r in rows)+'\n')
    write(OUT/'RELEASE.json',json.dumps({'revision':'R30','files':rows,'production_test':proof},ensure_ascii=False,indent=2))
    base.copy_file(ROOT/'docs/PRIVATE_SERVER_DEPLOYMENT_R30_CN.md',OUT/'部署说明.md');print(json.dumps(rows,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=('stage','seal'));ap.add_argument('--personal-local',required=True,action='store_true');ap.add_argument('--manual-acceptance',action='store_true');args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);(stage if args.action=='stage' else seal)(args.manual_acceptance)
