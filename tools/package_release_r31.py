"""Stage/seal five R31 private deployment ZIPs; functional acceptance stays explicit."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import msvcrt
import subprocess
import zipfile
import build_server_ready_pack as base
from package_release_r30 import visual_specs

ROOT=base.ROOT;ART=ROOT/'artifacts/facility_r31';OUT=ROOT/'artifacts/server-ready-r31';STAGE=OUT/'stage'
base.WORLD_NAME='SEELE_R31_WORLD'
WORLD=ROOT/'run/saves'/base.WORLD_NAME
MOTIONS=('eva_combat_capture_r31.json','eva_combat_capture_r31_un00.json','eva_combat_capture_r31_un01.json')
GRIP_PROFILE='angel_grip_r31.json'
RECOVERY_PROFILE='eva_recovery_r31.json'
FULL_RUNTIME_COVERAGE=('combat','recovery','un_reset_capsules','air_transport','rendered_socket_alignment')
DOCS=('MANUAL_ACCEPTANCE_R31.md','FIRST_ACT_R31_CN.md','PRIVATE_SERVER_DEPLOYMENT_R31_CN.md',
      'UN_HANGARS_R31.md','DIALOGUE_AUDIO_R31.md','COMBAT_CAPTURE_R31.md',
      'COMBAT_AND_RECOVERY_R31.md','AIR_TRANSPORT_R31.md','UN_RESET_CAPSULE_R31.md',
      'EVA_RECOVERY_R31.md','UN_MODEL_CANDIDATES_R31.md','ANGEL_COMBAT_R31.md')

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf8',newline='\n')
def data(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def private_jar(folder):
    values=list((folder/'mods').glob('projectseele-*.jar'))
    assert len(values)==1,'Expected one private runtime JAR'
    return values[0]

def acceptance_status(report):
    """A transport pass is evidence for transport, never an implicit full release pass."""
    if report is None:
        return {'passed':None,'status':'not_run','scope':'No consolidated R31 runtime acceptance report supplied',
                'required_coverage':list(FULL_RUNTIME_COVERAGE),'missing_coverage':list(FULL_RUNTIME_COVERAGE)}
    summary=report if isinstance(report,dict) else {}
    coverage=summary.get('coverage',{})
    if not isinstance(coverage,dict):coverage={}
    def passed(name):
        value=coverage.get(name)
        return value is True or isinstance(value,dict) and value.get('passed') is True
    missing=[name for name in FULL_RUNTIME_COVERAGE if not passed(name)]
    full=summary.get('revision')=='R31' and summary.get('passed') is True and not missing
    return {'revision':'R31','passed':True if full else False if summary.get('passed') is False else None,
            'status':'passed_full_runtime_coverage' if full else 'partial_or_failed_runtime_evidence',
            'scope':'Combat, recovery, UN reset/capsules, air transport and rendered socket alignment; dedicated-server startup remains separate.' if full
                    else 'Partial evidence only. Transport/reset completion does not certify rendered capsule alignment or the full R31 experience.',
            'required_coverage':list(FULL_RUNTIME_COVERAGE),'missing_coverage':missing,'source_report':report}

def check_inputs(model_receipt):
    world=read(WORLD/'r31_world_stage.json')
    assert world['geometry_staged'] and world['all_original_progress_files_preserved']
    assert world['review_runtime_copied'] is False and world['review_overworld_copied'] is False
    rename=world['level_name_change']
    assert rename['allowed_property']=='Data.LevelName' and rename['after']=='Project SEELE R31' and rename['all_other_typed_nbt_equal']
    baseline=read(ART/'baseline.json')
    for name,digest in baseline['original_user_files'].items():assert base.sha256(ROOT/name)==digest,name
    marker=read(WORLD/'un_hangars_r31.json');assert marker['revision']==31
    assert all(h['new_pressure_width']==49 and h['new_outer_width']==133 for h in marker['hangars'])
    promotion=read(model_receipt);assert promotion.get('installed') is True,'R31 model promotion not complete'
    assets=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
    staging=read(ART/'models/staging.json')
    review_assets=Path(staging['pack'])/'assets/projectseele'
    review_contract=read(review_assets/'eva/un_models_r30.json')['models']
    for name in ('eva_prototype','eva_un01'):
        expected=promotion['models'][name]['mesh_sha256']
        assert expected==review_contract[name]['sha256']['mesh'],('Promotion is not the reviewed R31 model',name)
        assert base.sha256(assets/'mesh'/(name+'.mesh.json'))==expected,('R31 model was not installed',name)
        core={'mesh':f'mesh/{name}.mesh.json','geo':f'geo/{name}.geo.json','animation':f'animations/{name}.animation.json','texture':f'textures/entity/{name}.png'}
        for key,relative in core.items():assert base.sha256(assets/relative)==review_contract[name]['sha256'][key],('Incomplete model promotion',relative)
        for relative,digest in review_contract[name]['pbr'].items():assert base.sha256(assets/relative)==digest,('Incomplete PBR promotion',relative)
    # The production renderer intentionally retains its R30-named compatibility
    # contract. The R31 promotion receipt establishes the actual newer asset batch.
    base.validate_private_eva_mesh_contracts()
    body=read(ROOT/'run/projectseele-local-maps/eva_body_r25.json');bones=body['motion']['bones']
    review_body=read(Path(staging['body']));dorsal=read(ROOT/'run/projectseele-local-maps/eva_dorsal_r30.json');review_dorsal=read(Path(staging['dorsal']))
    for key,name in (('3','eva_prototype'),('4','eva_un01')):
        for group in ('rigs','rig_support','eye_positions','carrier_hulls'):
            if key in review_body.get(group,{}):assert body.get(group,{}).get(key)==review_body[group][key],('R31 model/CPU rig mismatch',group,key)
        assert dorsal['profiles'][name]==review_dorsal['profiles'][name],('R31 dorsal profile mismatch',name)
    motions={}
    for name in MOTIONS:
        path=ROOT/'run/projectseele-local-maps'/name;clip=read(path)
        assert clip['bones']==bones and all(k in clip['clips'] for k in ('r31_grapple_start','r31_shoulder_throw','r31_air_downstrike','r31_get_up'))
        motions[name]=base.sha256(path)
    grip_path=ROOT/'run/projectseele-local-maps'/GRIP_PROFILE;grip=read(grip_path)
    assert grip['schema']=='projectseele.angel_grip_surface_r31/v1'
    assert grip['space']=='GECKO_MODEL_BLOCKS' and grip['render_scale']==5
    for name in ('sachiel','shamshel'):
        profile=grip['profiles'][name]
        assert profile['mesh_sha256']==base.sha256(assets/'mesh'/(name+'.mesh.json')),('Angel contact profile was measured on another mesh',name)
        assert set(profile['anchors'])=={'left','right'}
    recovery_path=ROOT/'run/projectseele-local-maps'/RECOVERY_PROFILE;recovery=read(recovery_path)
    assert recovery['schema']=='projectseele.recovery-r31.v1' and recovery['bones']==bones
    assert set(recovery['models'])=={'0','1','2','3','4'},'Recovery profile must cover all five measured EVA rigs'
    for key,profile in recovery['models'].items():
        capture=MOTIONS[1] if key=='3' else MOTIONS[2] if key=='4' else MOTIONS[0]
        assert profile['source_sha256']==motions[capture],('Recovery motion is from another capture revision',key)
        rig_hash=hashlib.sha256(json.dumps(body['rigs'][key],sort_keys=True).encode()).hexdigest()
        assert profile['rig_sha256']==rig_hash,('Recovery support is from another rig',key)
        assert 2<=len(profile['frames'])<=600 and profile['support'] and len(profile['sole_l'])==3 and len(profile['anchor'])==3
    runtime_profiles={**motions,GRIP_PROFILE:base.sha256(grip_path),RECOVERY_PROFILE:base.sha256(recovery_path)}
    source=(ROOT/'src/main/java/com/projectseele/network/SeeleNetwork.java').read_text(encoding='utf8')
    assert 'PROTOCOL_VERSION = "35"' in source
    with zipfile.ZipFile(base.newest_project_jar()) as archive:
        network=archive.read('com/projectseele/network/SeeleNetwork.class')
        assert b'\x01\x00\x0235' in network,'Built JAR is not protocol 35; build the final sources first'
    return world,promotion,runtime_profiles

def stage(manual=False,model_receipt=None,verification_report=None):
    assert not STAGE.exists(),'Keep the earlier R31 stage intact; never merge deployment batches.'
    world,promotion,runtime_profiles=check_inputs(model_receipt or ART/'models/promotion.json')
    motions={name:runtime_profiles[name] for name in MOTIONS}
    verification=acceptance_status(read(verification_report) if verification_report else None)
    if not manual:assert verification.get('passed') is True,'Supply full R31 coverage including rendered_socket_alignment, or explicit --manual-acceptance'
    guide=(ROOT/'docs/PRIVATE_SERVER_DEPLOYMENT_R31_CN.md').read_text(encoding='utf8')
    server,client,world_part,textures,shaders=(STAGE/n for n in ('server','client','world','textures','shaders'))
    base.build_server(server,guide,revision='R31');base.build_client(client,guide,revision='R31',city_shaders=True)
    ready={'revision':'R31','protocol':35,'installed':True,'world':base.WORLD_NAME,'geometry_installed':True,
           'acceptance_mode':'manual_by_user' if manual else 'native_verified','verification_passed':verification.get('passed'),
           'verification':verification,'models_installed':True,'model_promotion_sha256':base.sha256(model_receipt or ART/'models/promotion.json'),
           'motion_sha256':motions,'runtime_profile_sha256':runtime_profiles,'model_staging_sha256':base.sha256(ART/'models/staging.json'),
           'source_backup':world['source_backup'],'original_progress_preserved':True,
           'pending_manual_checks':['Combat feel and all five machines','UN reset and capsule alignment','Horizontal occupied/disabled transport and restart','Dedicated-server deployment'] if manual else []}
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        data(WORLD/'r31_ready.json',ready)
        base.build_world(world_part)
    scripts=ROOT/'tools/deployment_r29'
    for folder in (server,client):
        base.copy_file(scripts/'Setup.ps1',folder/'Setup.ps1')
        for name in DOCS:base.copy_file(ROOT/'docs'/name,folder/name)
        local=folder/'projectseele-local-maps'
        for path in list(local.glob('*worldtour.json'))+list(local.glob('*_review.json')):path.unlink()
        for name,digest in runtime_profiles.items():assert base.sha256(local/name)==digest,('Missing matching runtime profile',name)
    for name in ('Start-Server.bat','start-server.sh','install-server.sh'):base.copy_file(scripts/name,server/name)
    base.copy_file(ROOT/'tools/forge_runtime_r25.json',server/'forge-runtime.json')
    base.copy_file(ROOT/'tools/realistic_pack_r25.json',client/'realistic-pack.json')
    base.copy_file(ROOT/'tools/city_shaders_r29.json',client/'city-shaders.json')
    base.copy_file(scripts/'Install-Visuals.ps1',client/'Install-Visuals.ps1')
    for name,command in [('Install-Visuals','Install-Visuals.ps1'),('Install-Textures','Setup.ps1 -Kind Client')]:
        write(client/(name+'.bat'),'@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File '+command+'\r\npause\r\n')
    write(server/'Install-Server.bat','@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File Setup.ps1 -Kind Server\r\npause\r\n')
    write(server/'eula.txt','# Review https://aka.ms/MinecraftEULA before setting true.\neula=false\n')
    write(server/'server.properties',base.server_properties());write(server/'user_jvm_args.txt',base.jvm_args())
    options=client/'options.txt';write(options,options.read_text(encoding='utf-8-sig')+'lang:zh_cn\nkey_key.projectseele.eva_grapple:key.keyboard.comma\n')
    texture,shader=visual_specs()
    for spec,source,destination in [(texture,ROOT/'run/resourcepacks',textures/'resourcepacks'),(shader,ROOT/'run/shaderpacks',shaders/'shaderpacks')]:
        path=source/spec['filename'];assert hashlib.sha512(path.read_bytes()).hexdigest()==spec['sha512']
        base.copy_file(path,destination/spec['filename'])
    base.copy_file(ROOT/'run/shaderpacks'/(shader['filename']+'.txt'),shaders/'shaderpacks'/(shader['filename']+'.txt'))
    write(shaders/'config/oculus.properties','enableShaders=true\nshaderPack='+shader['filename']+'\n')
    for folder,kind in ((textures,'材质'),(shaders,'光影')):
        write(folder/'安装说明.txt','这是已下载资源的私人本地备份。解压到 PCL 对应版本的独立游戏目录，合并同名文件夹。\n'+
              ('随后运行客户端包的 Install-Textures.bat，复用本地原包。' if kind=='材质' else '视频设置中选择 Complementary Unbound。客户端已含 Oculus。')+
              '\n保留作者原始 ZIP，不需要再下载一次。不要把它解压到 PCL 启动器程序目录。\n')
    mod_hash=base.sha256(private_jar(server));assert mod_hash==base.sha256(private_jar(client))
    batch={'revision':'R31','protocol':35,'created':datetime.datetime.now().astimezone().isoformat(),'source_head':head(),
           'world':base.WORLD_NAME,'mod_sha256':mod_hash,'world_marker_sha256':base.sha256(world_part/'r31_ready.json'),
           'model_mesh_sha256':{name:row['mesh_sha256'] for name,row in promotion['models'].items()},'motion_sha256':motions,
           'runtime_profile_sha256':runtime_profiles,'model_staging_sha256':base.sha256(ART/'models/staging.json'),
           'acceptance_mode':ready['acceptance_mode'],'functional_verification':verification,
           'visuals':{'texture':texture['filename'],'shader':shader['filename']}}
    for folder in (server,client,world_part,textures,shaders):data(folder/'R31_BATCH.json',batch)
    for folder,kind in ((server,'server-files'),(client,'client-pack'),(textures,'personal-textures'),(shaders,'personal-shaders')):base.write_manifest(folder,kind)
    data(OUT/'batch.json',batch);data(OUT/'acceptance_status.json',{'runtime':verification,'dedicated_server':{'passed':None,'status':'not_run_at_staging'}})
    print('R31 five parts staged; no new gameplay validation claimed')

def seal(manual=False):
    batch=read(OUT/'batch.json')
    if manual:
        proof={'passed':None,'status':'not_run_dedicated_server_manual_acceptance','mod_sha256':batch['mod_sha256'],
               'scope':'Final gameplay and dedicated-server checks remain manual; ZIP hashing is packaging integrity only.'}
        data(OUT/'manual_acceptance.json',proof)
    else:
        proof=read(OUT/'production_check.json');assert proof.get('passed') is True
    folders={name:STAGE/name.lower() for name in ('Server','Client','World','Textures','Shaders')}
    assert not any(OUT.glob('Project_SEELE_R31_*.zip')),'Existing R31 archives must not be overwritten'
    for name in ('Server','Client'):
        assert base.sha256(private_jar(folders[name]))==batch['mod_sha256']==proof['mod_sha256']
        for file,digest in batch['runtime_profile_sha256'].items():assert base.sha256(folders[name]/'projectseele-local-maps'/file)==digest
    assert (folders['Server']/'eula.txt').read_text().strip().endswith('eula=false')
    assert not list((folders['Client']/'shaderpacks').glob('*.zip')) and not list((folders['Client']/'resourcepacks').glob('rotrblocks*.zip'))
    assert base.sha256(folders['World']/'r31_ready.json')==batch['world_marker_sha256']
    batch['source_head']=head();batch['dedicated_server_verification']=proof
    for folder in folders.values():data(folder/'R31_BATCH.json',batch)
    for name,kind in [('Server','server-files'),('Client','client-pack'),('Textures','personal-textures'),('Shaders','personal-shaders')]:base.write_manifest(folders[name],kind)
    data(OUT/'batch.json',batch);rows=[]
    for name,folder in folders.items():
        target=OUT/f'Project_SEELE_R31_{name}.zip'
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for path in sorted(folder.rglob('*')):
                if path.is_file():archive.write(path,path.relative_to(folder).as_posix())
        if not manual:
            with zipfile.ZipFile(target) as archive:assert archive.testzip() is None
        rows.append({'file':target.name,'bytes':target.stat().st_size,'sha256':base.sha256(target)})
        print(name+' archived',flush=True)
    if not manual:base.validate_outputs(OUT/'Project_SEELE_R31_Server.zip',OUT/'Project_SEELE_R31_World.zip',OUT/'Project_SEELE_R31_Client.zip',city_shaders=True)
    write(OUT/'SHA256SUMS.txt','\n'.join(f"{row['sha256']}  {row['file']}" for row in rows)+'\n')
    data(OUT/'RELEASE.json',{'revision':'R31','protocol':35,'files':rows,'runtime_verification':batch['functional_verification'],'production_test':proof})
    base.copy_file(ROOT/'docs/PRIVATE_SERVER_DEPLOYMENT_R31_CN.md',OUT/'部署说明.md')
    print('R31 archives sealed; R30 archives and source save preserved')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=('stage','seal'));ap.add_argument('--personal-local',required=True,action='store_true');ap.add_argument('--manual-acceptance',action='store_true')
    ap.add_argument('--model-receipt',type=Path);ap.add_argument('--verification-report',type=Path);args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.action=='stage':stage(args.manual_acceptance,args.model_receipt,args.verification_report)
    else:seal(args.manual_acceptance)
