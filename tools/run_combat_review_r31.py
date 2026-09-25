"""Launch only the isolated R31 combat review using already compiled launch metadata."""
from pathlib import Path
import argparse,json,subprocess,shutil,time,hashlib
from contextlib import contextmanager
from launch_rendered_client_r17 import run_prepared,java_environment

ROOT=Path(__file__).resolve().parents[1]
WORLD='SEELE_FIELD_R31_REVIEW'

def compiled_hash():
    base=ROOT/'build/classes/java/main/com/projectseele';digest=hashlib.sha256();files=sorted(base.rglob('*.class'))
    if not files:raise RuntimeError('Compile the current mod before a native review')
    for source in (ROOT/'src/main/java/com/projectseele').rglob('*.java'):
        target=base/source.relative_to(ROOT/'src/main/java/com/projectseele').with_suffix('.class')
        if target.is_file() and source.stat().st_mtime>target.stat().st_mtime+.001:
            raise RuntimeError('Source changed after compilation: '+source.relative_to(ROOT).as_posix())
    for p in files:digest.update(p.relative_to(base).as_posix().encode()+b'\0');digest.update(p.read_bytes())
    return digest.hexdigest()

@contextmanager
def temporary_motion(source):
    if source is None:yield;return
    base=(ROOT/'run/projectseele-local-maps').resolve();saved={}
    try:
        for name in [*(f'eva_gameplay_r32_{i}.json' for i in range(5)),'sachiel_gameplay_r32.json']:
            target=base/name;candidate=source/name
            if not candidate.is_file():raise FileNotFoundError(candidate)
            saved[target]=target.read_bytes() if target.exists() else None
            shutil.copyfile(candidate,target)
        yield
    finally:
        for target,original in saved.items():
            if target.parent!=base:raise RuntimeError('Motion restore escaped runtime asset directory')
            if original is None:target.unlink(missing_ok=True)
            else:target.write_bytes(original)

@contextmanager
def temporary_options(path,separator,changes):
    path=Path(path); existed=path.exists(); lines=path.read_text(encoding='utf8').splitlines() if existed else []
    original={k:next((line for line in lines if line.partition(separator)[0]==k),None) for k in changes}
    output=[line for line in lines if line.partition(separator)[0] not in changes]
    output.extend(k+separator+str(v) for k,v in changes.items());path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('\n'.join(output)+'\n',encoding='utf8')
    try:yield
    finally:
        current=path.read_text(encoding='utf8').splitlines()
        current=[line for line in current if line.partition(separator)[0] not in changes]
        current.extend(line for line in original.values() if line is not None)
        path.write_text('\n'.join(current)+'\n',encoding='utf8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepared-file',type=Path,default=ROOT/'.Codex/client-launch-r17.json');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--video',action='store_true');ap.add_argument('--normal-attacks',action='store_true');ap.add_argument('--duel',action='store_true');ap.add_argument('--variant',type=int,choices=range(5),default=1)
    ap.add_argument('--body-physics-profiles',type=Path)
    ap.add_argument('--asset-overlay',type=Path,action='append',default=[]);ap.add_argument('--city-shaders',action='store_true');ap.add_argument('--awakening',action='store_true');ap.add_argument('--mouth-only',action='store_true')
    ap.add_argument('--recovery-only',action='store_true')
    ap.add_argument('--shutdown',action='store_true')
    ap.add_argument('--gameplay-motion-directory',type=Path);ap.add_argument('--side-view',action='store_true');ap.add_argument('--early-air',action='store_true');ap.add_argument('--exchange-only',action='store_true');ap.add_argument('--capture-audio',type=Path);ap.add_argument('--field-energy',type=float,default=0);ap.add_argument('--berserk',action='store_true');a=ap.parse_args()
    world=ROOT/'run/saves'/WORLD
    if not (world/'level.dat').is_file():raise FileNotFoundError('Create the disposable '+WORLD+' copy before this fixture; it never edits a formal world.')
    source=json.loads(a.prepared_file.read_text(encoding='utf8'));command=source['command']
    if Path(source['workingDirectory']).resolve()!=(ROOT/'run').resolve():raise ValueError('Unexpected Minecraft working directory')
    command=[c for c in command if not c.startswith(('-Dprojectseele.regionalBuild=','-Dprojectseele.bodyPoseReview=','-Dprojectseele.dorsalPoseReview=','-Dprojectseele.combatVideo=','-Dprojectseele.combatNormals=','-Dprojectseele.combatVariant=','-Dprojectseele.combatDuel=','-Dprojectseele.combatSideView=','-Dprojectseele.combatEarlyAir='))]
    command.insert(1,'-Dprojectseele.regionalBuild=r31-combat')
    command.insert(1,'-Dprojectseele.combatVariant='+str(a.variant))
    if a.body_physics_profiles:
        profile=a.body_physics_profiles.resolve()
        if not profile.is_file():raise FileNotFoundError(profile)
        command=[c for c in command if not c.startswith('-Dprojectseele.bodyPhysicsProfiles=')]
        command.insert(1,'-Dprojectseele.bodyPhysicsProfiles='+str(profile))
    if a.exchange_only:command.insert(1,'-Dprojectseele.combatExchange=true')
    if a.recovery_only:command.insert(1,'-Dprojectseele.combatRecovery=true')
    if a.shutdown:command.insert(1,'-Dprojectseele.combatWreck=true');command.insert(1,'-Dprojectseele.combatRecovery=true')
    if a.berserk:command.insert(1,'-Dprojectseele.combatBerserk=true')
    if a.mouth_only:a.awakening=True;command.insert(1,'-Dprojectseele.combatMouth=true')
    if a.awakening:command.insert(1,'-Dprojectseele.combatAwakening=true');command.insert(1,'-Dprojectseele.combatExchange=true')
    if a.city_shaders:command.insert(1,'-Dprojectseele.r37MaterialAudit=true')
    command.insert(1,'-Dprojectseele.combatFieldEnergy='+str(a.field_energy))
    if a.capture_audio:
        audio=a.capture_audio.resolve()
        if audio.exists():raise FileExistsError('Audio capture must use a new output: '+str(audio))
    if a.early_air:command.insert(1,'-Dprojectseele.combatEarlyAir=true')
    if a.side_view:command.insert(1,'-Dprojectseele.combatSideView=true')
    if a.duel:command.insert(1,'-Dprojectseele.combatDuel=true')
    if a.normal_attacks or a.duel:command.insert(1,'-Dprojectseele.combatNormals=true')
    if a.video:command.insert(1,'-Dprojectseele.combatVideo=true')
    if '--quickPlaySingleplayer' in command:command[command.index('--quickPlaySingleplayer')+1]=WORLD
    else:command.extend(['--quickPlaySingleplayer',WORLD])
    source['command']=command;launch=ROOT/'.Codex/client-r31-combat.json';launch.write_text(json.dumps(source),encoding='utf8')
    if a.prepare_only:print('Prepared '+str(launch));return 0
    guard=subprocess.run(['powershell','-NoProfile','-Command',
        "@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main|client-.*[.]args|GradleDaemon|GradleWrapperMain' }).Count"],capture_output=True,text=True,check=True)
    if int(guard.stdout.strip() or '0')!=0:raise RuntimeError('Minecraft or Gradle is still running; finish compilation and stop the daemon before the isolated review.')
    options=ROOT/'run/options.txt';lines=options.read_text(encoding='utf8').splitlines()
    packs=json.loads(next((line.partition(':')[2] for line in lines if line.startswith('resourcePacks:')),'[]'))
    packs=[p for p in packs if 'rotrblocks' not in p.lower() and 'patrix' not in p.lower() and p not in ('file/eva_un_r30_review','file/eva_un_r31_review')]
    if 'file/eva_real_model' not in packs:packs.append('file/eva_real_model')
    if (ROOT/'run/resourcepacks/eva_roar_r34/pack.mcmeta').is_file() and 'file/eva_roar_r34' not in packs:packs.append('file/eva_roar_r34')
    review_options={'renderDistance':'8','resourcePacks':json.dumps(packs,ensure_ascii=False)}
    if a.capture_audio:review_options.update(soundCategory_master='0.8',soundCategory_music='0.0',soundDevice='')
    if a.video:review_options['lang']='zh_cn'
    paths={p.name:p for p in (a.gameplay_motion_directory or ROOT/'run/projectseele-local-maps').glob('*gameplay_r32*.json')}
    body=a.body_physics_profiles or ROOT/'run/projectseele-local-maps/articulated_bodies_r35.json'
    if body.is_file():paths['articulated_bodies_r35.json']=body
    hashes={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()};implementation=compiled_hash();began=time.time()
    from contextlib import ExitStack
    render_hashes={}
    with ExitStack() as stack:
        base=(ROOT/'run/resourcepacks/eva_real_model').resolve();saved={}
        def restore_assets():
            for p,b in saved.items():
                if b is None:p.unlink(missing_ok=True)
                else:p.write_bytes(b)
        stack.callback(restore_assets)
        for overlay in a.asset_overlay:
            for p in overlay.resolve().rglob('*'):
                if not p.is_file():continue
                relative=p.relative_to(overlay.resolve());target=(base/relative).resolve()
                if not target.is_relative_to(base) or relative.parts[0] not in ('assets','texture.properties'):raise ValueError('Invalid asset overlay')
                if target not in saved:saved[target]=target.read_bytes() if target.exists() else None
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);render_hashes[relative.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        stack.enter_context(temporary_options(options,':',review_options))
        shader_settings={'enableShaders':'false'}
        if a.city_shaders:
            shader='ComplementaryUnbound_r5.3_SEELE_LCL.zip';shader_settings={'enableShaders':'true','shaderPack':shader}
            stack.enter_context(temporary_options(ROOT/'run/shaderpacks'/(shader+'.txt'),'=',{'RP_MODE':'3','SHADOW_QUALITY':'2','shadowDistance':'160.0','BLOCK_REFLECT_QUALITY':'2','ENTITY_SHADOWS_DEFINE':'1','NORMAL_MAP_STRENGTH':'70','CLOUD_STYLE_DEFINE':'0'}))
        with temporary_options(ROOT/'run/config/oculus.properties','=',shader_settings):
            from record_combat_pcm_r34 import capture
            with temporary_motion(a.gameplay_motion_directory),capture(a.capture_audio,start_log=ROOT/'run/logs/latest.log'):code=run_prepared(launch,java_environment()[1])
    print('Combat review evidence: '+str(world/'Review'))
    candidates=[p for p in (world/'Review').glob('r3*_*.json') if p.name.startswith(('r31_combat_','r32_normal_')) and p.stat().st_mtime>=began]
    if candidates:
        proof=json.loads(max(candidates,key=lambda p:p.stat().st_mtime).read_text());proof['inputs_sha256']=hashes;proof['implementation_sha256']=implementation;proof['render_inputs_sha256']=render_hashes;proof['city_shaders']=a.city_shaders
        media=(ROOT/'run'/proof['media']).resolve();(media/'server_evidence.json').write_text(json.dumps(proof,indent=2))
        print('Server evidence:',media/'server_evidence.json')
        if code==0 and not proof.get('passed'):print('Native review failed:',proof.get('error',''),proof.get('cases',[]));code=2
    elif code==0:print('No current native result was written');code=2
    return code

if __name__=='__main__':raise SystemExit(main())
