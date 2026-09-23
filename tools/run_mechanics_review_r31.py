"""Guarded original-UN mechanical review; never compiles, clones or edits a formal world."""
from pathlib import Path
import argparse,json,subprocess
from launch_rendered_client_r17 import run_prepared,java_environment
from run_combat_review_r31 import temporary_options

ROOT=Path(__file__).resolve().parents[1]
WORLD='SEELE_FIELD_R31_REVIEW'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepared-file',type=Path,default=ROOT/'.Codex/client-launch-r17.json');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--transport',action='store_true',help='Also run one original UN00 horizontal delivery; no long recovery loop.');ap.add_argument('--transport-only',action='store_true',help='Verify original UN00 identity and reset, then run only its normal horizontal delivery.')
    a=ap.parse_args();world=ROOT/'run/saves'/WORLD
    if not (world/'level.dat').is_file():raise FileNotFoundError(WORLD+' must already exist as an isolated copy')
    pack=ROOT/'run/resourcepacks/eva_un_r31_review'
    required=[pack/'pack.mcmeta',ROOT/'run/projectseele-local-maps/eva_body_r31_review.json',ROOT/'run/projectseele-local-maps/eva_dorsal_r31_review.json']
    for file in required:
        if not file.is_file():raise FileNotFoundError(file)
    source=json.loads(a.prepared_file.read_text(encoding='utf8'));command=source['command']
    if Path(source['workingDirectory']).resolve()!=(ROOT/'run').resolve():raise ValueError('Unexpected game working directory')
    properties={'regionalBuild':'r31-mechanics','mechanicsTransport':str(a.transport or a.transport_only).lower(),'mechanicsTransportOnly':str(a.transport_only).lower(),'bodyPoseReview':'projectseele-local-maps/eva_body_r31_review.json','dorsalPoseReview':'projectseele-local-maps/eva_dorsal_r31_review.json'}
    command=[arg for arg in command if not any(arg.startswith('-Dprojectseele.'+key+'=') for key in properties)]
    for key,value in properties.items():command.insert(1,'-Dprojectseele.'+key+'='+value)
    if '--quickPlaySingleplayer' in command:command[command.index('--quickPlaySingleplayer')+1]=WORLD
    else:command.extend(['--quickPlaySingleplayer',WORLD])
    source['command']=command;launch=ROOT/'.Codex/client-r31-mechanics.json';launch.write_text(json.dumps(source),encoding='utf8')
    if a.prepare_only:print('Prepared '+str(launch));return 0
    guard=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main' }).Count"],capture_output=True,text=True,check=True)
    if int(guard.stdout.strip() or '0')!=0:raise RuntimeError('A Minecraft JVM is running; this wrapper will not start another.')
    options=ROOT/'run/options.txt';lines=options.read_text(encoding='utf8').splitlines();packs=json.loads(next((line.partition(':')[2] for line in lines if line.startswith('resourcePacks:')),'[]'))
    packs=[p for p in packs if 'rotrblocks' not in p.lower() and 'patrix' not in p.lower() and p not in ('file/eva_un_r21_review','file/eva_un_r30_review','file/eva_un_r31_review')]
    if 'file/eva_real_model' not in packs:packs.append('file/eva_real_model')
    packs.append('file/eva_un_r31_review')
    with temporary_options(options,':',{'renderDistance':'8','resourcePacks':json.dumps(packs,ensure_ascii=False)}):
        with temporary_options(ROOT/'run/config/oculus.properties','=',{'enableShaders':'false'}):
            code=run_prepared(launch,java_environment()[1])
    print('Mechanical review report: '+str(world/'Review'));return code

if __name__=='__main__':raise SystemExit(main())
