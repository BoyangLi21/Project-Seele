"""Assemble this owner's local PCL backup; no downloads or public redistribution."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,zipfile

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'artifacts/server-ready-r29'
OUT=ROOT/'artifacts/pcl-local-r29'
WORLD='SEELE_TV_WORLD_PREVIEW_20260906'

def sha(path,algorithm='sha256'):
    h=hashlib.new(algorithm)
    with path.open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--personal-local',action='store_true',required=True);ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    verified=json.loads((RELEASE/'RELEASE.json').read_text())
    assert verified['production_test']['passed']
    for row in verified['files']:
        assert sha(RELEASE/row['file'])==row['sha256'],row['file']
    client=RELEASE/'stage/client';server=RELEASE/'stage/server';world=RELEASE/'stage/world'
    shader=next(q for q in json.loads((ROOT/'tools/city_shaders_r29.json').read_text()) if q['project']=='complementary-unbound')
    texture=json.loads((ROOT/'tools/realistic_pack_r25.json').read_text())
    shader_path=ROOT/'run/shaderpacks'/shader['filename'];texture_path=ROOT/'run/resourcepacks'/texture['filename']
    for path,spec in ((shader_path,shader),(texture_path,texture)):assert sha(path,'sha512')==spec['sha512'],path
    files={};data={}
    def tree(folder,prefix):
        for p in sorted(folder.rglob('*')):
            if p.is_file():files[prefix+p.relative_to(folder).as_posix()]=p
    tree(client,'overrides/');tree(world,'overrides/saves/'+WORLD+'/');tree(server,'server/')
    # Root metadata belongs to the launcher format, not our file-hash manifest.
    files.pop('overrides/manifest.json',None)
    files['overrides/Install-Visuals.ps1']=ROOT/'tools/deployment_r29/Install-Visuals.ps1'
    files['overrides/Setup.ps1']=ROOT/'tools/deployment_r29/Setup.ps1'
    files['server/Setup.ps1']=ROOT/'tools/deployment_r29/Setup.ps1'
    files['overrides/shaderpacks/'+shader['filename']]=shader_path
    files['overrides/shaderpacks/'+shader['filename']+'.txt']=ROOT/'run/shaderpacks'/(shader['filename']+'.txt')
    files['overrides/resourcepacks/'+texture['filename']]=texture_path
    data['manifest.json']=json.dumps({'minecraft':{'version':'1.20.1','modLoaders':[{'id':'forge-47.4.10','primary':True}]},'manifestType':'minecraftModpack','manifestVersion':1,'name':'Project SEELE R29','version':'R29-PCL-Local','author':'Project SEELE','files':[],'overrides':'overrides'},ensure_ascii=False,indent=2).encode()
    options={}
    for line in (client/'options.txt').read_text(encoding='utf8').splitlines():
        key,sep,value=line.partition(':')
        if sep:options[key]=value
    options.update({'lang':'zh_cn','resourcePacks':json.dumps(['vanilla','mod_resources','file/'+texture['filename'],'file/eva_real_model'],separators=(',',':')),'incompatibleResourcePacks':json.dumps(['file/'+texture['filename']]),'renderDistance':'16','simulationDistance':'8'})
    data['overrides/options.txt']=('\n'.join(k+':'+v for k,v in options.items())+'\n').encode()
    data['overrides/config/oculus.properties']=('enableShaders=true\nshaderPack='+shader['filename']+'\n').encode()
    data['overrides/PCL/Setup.ini']=b'VersionArgumentIndieV2:True\n'
    intro='''Project SEELE R29 — 本机完整整合包\n\n1. 不要先解压到 PCL 启动器目录。把本 ZIP 直接拖入 PCL 窗口，确认安装一个新版本，例如 SEELE-R29。\n2. 选择新安装的 SEELE-R29 启动，使用 Java 17。单人游戏选择 SEELE_TV_WORLD_PREVIEW_20260906 对应的 TV 存档。\n3. 19 个模组、EVA 模型、完整 R29 存档、rotrBLOCKS 128x 和 Complementary Unbound r5.3 均已包含。无需再运行 Install-Textures 或 Install-Visuals，也无需重下这些素材。\n4. PCL 若发现 Minecraft 1.20.1 / Forge 47.4.10 运行库缺失，会补齐基础运行库；这部分不等于重复下载上述模组与素材。\n5. 光影已开启。想关闭，在视频设置的光影包界面选择关闭。密集基地负载高时可降低视距。\n6. 原有 1.20.1-forge-47.4.18 和其中 New World 等旧存档保留。不要把客户端文件覆盖进旧实例。\n\n服务器也在这个 ZIP 的 server 目录中。仅部署服务器时解压 server，把 overrides/saves/SEELE_TV_WORLD_PREVIEW_20260906 复制到 server/SEELE_TV_WORLD_PREVIEW_20260906，再按 server/PRIVATE_SERVER_DEPLOYMENT_CN.md 操作。\n\n这是用户已有资源在同一电脑上的个人打包副本，不是可公开上传的发行包。账号、登录令牌、服务器地址、聊天记录及旧实例的个人存档未打入。\n\n视觉资源署名：Complementary Unbound r5.3 — Complementary Development，https://www.complementary.dev/；rotrBLOCKS V87 128x — illystray，https://illystray.com/。原文件未修改。维护者负责本整合的兼容性。\n'''
    data['先读我.txt']=intro.encode('utf8');data['overrides/R29_PCL使用说明.txt']=intro.encode('utf8')
    for name in data:files.pop(name,None)
    forbidden=('session.lock','servers.dat','servers.dat_old','usercache.json','usernamecache.json','launcher_accounts.json','LatestLaunch.bat')
    # User caches in the authoritative world are part of the world only;
    # do not pull client accounts, logs or command lines into this archive.
    for name in list(files):
        if Path(name).name in forbidden and '/saves/' not in name:files.pop(name)
        assert not name.startswith(('/', '\\')) and '..' not in Path(name).parts
    assert len([n for n in files if n.startswith('overrides/mods/') and n.endswith('.jar')])==19
    dst=OUT/'Project_SEELE_R29_PCL_AllInOne.zip'
    with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,path in sorted(files.items()):z.write(path,name)
        for name,payload in sorted(data.items()):z.writestr(name,payload)
    with zipfile.ZipFile(dst) as z:
        assert z.testzip() is None
        assert json.loads(z.read('manifest.json'))['files']==[]
        for prefix,folder in [('overrides/saves/'+WORLD+'/',world),('overrides/mods/',client/'mods'),('server/mods/',server/'mods')]:
            for path in folder.rglob('*'):
                if path.is_file():assert hashlib.sha256(z.read(prefix+path.relative_to(folder).as_posix())).hexdigest()==sha(path)
        for name,spec in [('overrides/shaderpacks/'+shader['filename'],shader),('overrides/resourcepacks/'+texture['filename'],texture)]:
            assert hashlib.sha512(z.read(name)).hexdigest()==spec['sha512']
    report={'file':str(dst),'bytes':dst.stat().st_size,'sha256':sha(dst),'scope':'Owner-local archive; not a public distributable','client_mods':19,'server_mods':15,'world':WORLD,'shader_enabled':True,'downloads_during_packaging':0,'minecraft':'1.20.1','forge':'47.4.10','runtime_downloads':'PCL may fetch missing base game/Forge libraries; all mods/world/models/textures/shaders are already included','source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    (OUT/'VERIFIED.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'SHA256SUMS.txt').write_text(report['sha256']+'  '+dst.name+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
