"""Stage, verify and seal the three matching private R27 deployment archives."""
from pathlib import Path
import argparse,datetime,hashlib,json,msvcrt,shutil,subprocess,zipfile
import build_server_ready_pack as base
ROOT=base.ROOT;OUT=ROOT/'artifacts/server-ready-r27';STAGE=OUT/'stage'

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf8',newline='\n')

def stage():
    assert not STAGE.exists(),'Keep earlier stage intact; inspect or use seal after production verification'
    assert json.loads((ROOT/'artifacts/facility_r27/promotion/installed.json').read_text())['installed']
    base.validate_private_eva_mesh_contracts()
    guide=(ROOT/'docs/PRIVATE_SERVER_DEPLOYMENT_CN.md').read_text(encoding='utf8')
    server,client,world=(STAGE/q for q in ('server','client','world'))
    base.build_server(server,guide);base.build_client(client,guide)
    lock=(ROOT/'run/saves'/base.WORLD_NAME/'session.lock').open('r+b')
    try:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        base.build_world(world)
    finally:lock.close()
    # Preserve directory content and timestamps; never copy host credentials,
    # account preferences, command history or remote server addresses.
    scripts=ROOT/'tools/deployment_r27'
    for folder in (server,client):base.copy_file(scripts/'Setup.ps1',folder/'Setup.ps1')
    for folder in (server,client):
        for name in ('MANUAL_ACCEPTANCE_R23.md','MANUAL_ACCEPTANCE_R24.md','MANUAL_ACCEPTANCE_R26.md'):
            base.copy_file(ROOT/'docs'/name,folder/name)
    for name in ('Start-Server.bat','start-server.sh','install-server.sh'):base.copy_file(scripts/name,server/name)
    base.copy_file(ROOT/'tools/forge_runtime_r25.json',server/'forge-runtime.json')
    base.copy_file(ROOT/'tools/realistic_pack_r25.json',client/'realistic-pack.json')
    write(server/'Install-Server.bat','@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File Setup.ps1 -Kind Server\r\npause\r\n')
    write(client/'Install-Textures.bat','@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File Setup.ps1 -Kind Client\r\npause\r\n')
    # A distribution is not the operator's agreement to a third-party EULA.
    write(server/'eula.txt','# Review https://aka.ms/MinecraftEULA before setting true.\neula=false\n')
    options=client/'options.txt';write(options,options.read_text(encoding='utf8')+'lang:zh_cn\n')
    # JVM/properties are UTF-8 without BOM: Java argfiles treat a BOM as a flag.
    write(server/'user_jvm_args.txt',base.jvm_args());write(server/'server.properties',base.server_properties())
    for root in (server,client):
        for spec in root.glob('projectseele-local-maps/*worldtour.json'):spec.unlink()
    manifest={'revision':'R27','created':datetime.datetime.now().astimezone().isoformat(),'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'world':base.WORLD_NAME,'mod_sha256':base.sha256(next((server/'mods').glob('projectseele-*.jar'))),'world_marker_sha256':base.sha256(world/'r27_ready.json')}
    assert manifest['mod_sha256']==base.sha256(next((client/'mods').glob('projectseele-*.jar'))),'The two private JARs differ'
    for root in (server,client,world):write(root/'R27_BATCH.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    for root,kind in ((server,'server-files'),(client,'client-pack')):base.write_manifest(root,kind)
    write(OUT/'batch.json',json.dumps(manifest,indent=2))
    print('R27 staged at',STAGE,flush=True)

def seal():
    proof=json.loads((OUT/'production_check.json').read_text(encoding='utf8'))
    assert proof['passed'],'Production Forge startup did not pass'
    server,client,world=(STAGE/q for q in ('server','client','world'))
    # Production testing uses a separate root; the distributable stage stays cold.
    assert (server/'eula.txt').read_text(encoding='utf8').strip().endswith('eula=false')
    assert not (server/'libraries').exists()
    assert not list(client.glob('resourcepacks/rotrblocks*.zip')),'Do not redistribute the restricted texture archive'
    jars=[next((root/'mods').glob('projectseele-*.jar')) for root in (server,client)]
    assert base.sha256(jars[0])==base.sha256(jars[1])==proof['mod_sha256']
    batch=json.loads((OUT/'batch.json').read_text(encoding='utf8'))
    batch['source_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for root in (server,client,world):write(root/'R27_BATCH.json',json.dumps(batch,ensure_ascii=False,indent=2))
    for root,kind in ((server,'server-files'),(client,'client-pack')):base.write_manifest(root,kind)
    write(OUT/'batch.json',json.dumps(batch,indent=2))
    paths=[OUT/'Project_SEELE_R27_Server.zip',OUT/'Project_SEELE_R27_World.zip',OUT/'Project_SEELE_R27_Client.zip']
    for root,path in zip((server,world,client),paths):base.zip_tree(root,path)
    base.validate_outputs(*paths)
    # Every cold world file must match its ZIP byte-for-byte, including MTR,
    # dimension metadata, NPC identities and Moving Elevators capabilities.
    with zipfile.ZipFile(paths[1]) as archive:
        for path in world.rglob('*'):
            if path.is_file():assert hashlib.sha256(archive.read(path.relative_to(world).as_posix())).hexdigest()==base.sha256(path)
    rows=[{'file':p.name,'bytes':p.stat().st_size,'sha256':base.sha256(p)} for p in paths]
    write(OUT/'SHA256SUMS.txt','\n'.join(f"{q['sha256']}  {q['file']}" for q in rows)+'\n')
    write(OUT/'RELEASE.json',json.dumps({'revision':'R27','files':rows,'production_test':proof},ensure_ascii=False,indent=2))
    base.copy_file(ROOT/'docs/PRIVATE_SERVER_DEPLOYMENT_CN.md',OUT/'部署说明.md')
    print(json.dumps(rows,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=('stage','seal'));a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    (stage if a.action=='stage' else seal)()
