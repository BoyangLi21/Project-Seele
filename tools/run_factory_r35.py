"""Observe one real fleet preparation, launch and return in the disposable world."""
from pathlib import Path
import json,subprocess,argparse,time,hashlib
from launch_rendered_client_r17 import run_prepared,java_environment
from run_combat_review_r31 import temporary_options
from record_combat_pcm_r34 import capture
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--capture-audio',type=Path);args=ap.parse_args()
    check=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main|client-.*[.]args|GradleDaemon|GradleWrapperMain' }).Count"],capture_output=True,text=True,check=True)
    if int(check.stdout.strip() or '0'):raise RuntimeError('Finish the current client/build first')
    data=json.loads((ROOT/'.Codex/client-launch-r17.json').read_text());command=[x for x in data['command'] if not x.startswith('-Dprojectseele.regionalBuild=')]
    world='SEELE_FACTORY_R35_REVIEW'
    if not (ROOT/'run/saves'/world/'level.dat').is_file():raise FileNotFoundError('Prepare the isolated factory copy first')
    command.insert(1,'-Dprojectseele.regionalBuild=r35-factory');command[command.index('--quickPlaySingleplayer')+1]=world;data['command']=command
    path=ROOT/'.Codex/client-factory-r35.json';path.write_text(json.dumps(data))
    began=time.time()
    with temporary_options(ROOT/'run/options.txt',':',{'renderDistance':'8','soundCategory_music':'0.0'}),temporary_options(ROOT/'run/config/oculus.properties','=',{'enableShaders':'false'}),capture(args.capture_audio):
        code=run_prepared(path,java_environment()[1])
    result=ROOT/'run/saves'/world/'Review/r35_factory_pass.json'
    if code or not result.is_file() or result.stat().st_mtime<began:raise RuntimeError('Factory did not complete this run; inspect the current native log')
    folders=[p for p in (ROOT/'artifacts/world_rebuild_r20/factory').glob('native_cycle_*') if (p/'frames.json').exists() and (p/'frames.json').stat().st_mtime>=began]
    media=max(folders,key=lambda p:(p/'frames.json').stat().st_mtime);frames=json.loads((media/'frames.json').read_text());sounds=frames.get('facility_sounds',{})
    if sounds.get('projectseele:facility_hydraulic_launch',0)<1:raise RuntimeError('Driver did not receive the hydraulic sound event')
    proof={'passed':True,'media':str(media),'trace_sha256':hashlib.sha256(result.read_bytes()).hexdigest(),'facility_sounds':sounds,'audio':str(args.capture_audio) if args.capture_audio else None,'scope':'Original fleet identity, full prepare/transfer/launch/recovery, native driver sound reception; separate visual inspection required.'}
    (ROOT/'artifacts/combat_rebuild_r35/facility/factory_pass.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof));return code
if __name__=='__main__':raise SystemExit(main())
