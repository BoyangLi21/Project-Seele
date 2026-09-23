"""Launch only the isolated R31 combat review using already compiled launch metadata."""
from pathlib import Path
import argparse,json,subprocess
from contextlib import contextmanager
from launch_rendered_client_r17 import run_prepared,java_environment

ROOT=Path(__file__).resolve().parents[1]
WORLD='SEELE_FIELD_R31_REVIEW'

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
    ap=argparse.ArgumentParser();ap.add_argument('--prepared-file',type=Path,default=ROOT/'.Codex/client-launch-r17.json');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--video',action='store_true');ap.add_argument('--normal-attacks',action='store_true');ap.add_argument('--variant',type=int,choices=range(5),default=1);a=ap.parse_args()
    world=ROOT/'run/saves'/WORLD
    if not (world/'level.dat').is_file():raise FileNotFoundError('Create the disposable '+WORLD+' copy before this fixture; it never edits a formal world.')
    source=json.loads(a.prepared_file.read_text(encoding='utf8'));command=source['command']
    if Path(source['workingDirectory']).resolve()!=(ROOT/'run').resolve():raise ValueError('Unexpected Minecraft working directory')
    command=[c for c in command if not c.startswith(('-Dprojectseele.regionalBuild=','-Dprojectseele.bodyPoseReview=','-Dprojectseele.dorsalPoseReview=','-Dprojectseele.combatVideo=','-Dprojectseele.combatNormals=','-Dprojectseele.combatVariant='))]
    command.insert(1,'-Dprojectseele.regionalBuild=r31-combat')
    command.insert(1,'-Dprojectseele.combatVariant='+str(a.variant))
    if a.normal_attacks:command.insert(1,'-Dprojectseele.combatNormals=true')
    if a.video:command.insert(1,'-Dprojectseele.combatVideo=true')
    if '--quickPlaySingleplayer' in command:command[command.index('--quickPlaySingleplayer')+1]=WORLD
    else:command.extend(['--quickPlaySingleplayer',WORLD])
    source['command']=command;launch=ROOT/'.Codex/client-r31-combat.json';launch.write_text(json.dumps(source),encoding='utf8')
    if a.prepare_only:print('Prepared '+str(launch));return 0
    guard=subprocess.run(['powershell','-NoProfile','-Command',
        "@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main|client-.*[.]args' }).Count"],capture_output=True,text=True,check=True)
    if int(guard.stdout.strip() or '0')!=0:raise RuntimeError('A Minecraft JVM is already running; finish it before the isolated review.')
    options=ROOT/'run/options.txt';lines=options.read_text(encoding='utf8').splitlines()
    packs=json.loads(next((line.partition(':')[2] for line in lines if line.startswith('resourcePacks:')),'[]'))
    packs=[p for p in packs if 'rotrblocks' not in p.lower() and 'patrix' not in p.lower() and p not in ('file/eva_un_r30_review','file/eva_un_r31_review')]
    if 'file/eva_real_model' not in packs:packs.append('file/eva_real_model')
    review_options={'renderDistance':'8','resourcePacks':json.dumps(packs,ensure_ascii=False)}
    if a.video:review_options['lang']='zh_cn'
    with temporary_options(options,':',review_options):
        with temporary_options(ROOT/'run/config/oculus.properties','=',{'enableShaders':'false'}):
            code=run_prepared(launch,java_environment()[1])
    print('Combat review evidence: '+str(world/'Review'))
    return code

if __name__=='__main__':raise SystemExit(main())
