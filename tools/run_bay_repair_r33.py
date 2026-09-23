"""Observe a complete 120-second repair in the disposable integrated world."""
from pathlib import Path
import json,subprocess,time
from launch_rendered_client_r17 import run_prepared,java_environment
from run_combat_review_r31 import temporary_options
ROOT=Path(__file__).resolve().parents[1]

def main(serial=-1,visual=False):
    pending=ROOT/'.Codex/r33_render_build_pending'
    until=time.monotonic()+900
    while pending.exists():
        if time.monotonic()>until:raise RuntimeError('Pending renderer build was not completed')
        time.sleep(1)
    check=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main|client-.*[.]args' }).Count"],capture_output=True,text=True,check=True)
    if int(check.stdout.strip() or '0'):raise RuntimeError('Minecraft is already running')
    spec=json.loads((ROOT/'.Codex/client-launch-r17.json').read_text())
    command=[s for s in spec['command'] if not s.startswith('-Dprojectseele.regionalBuild=')]
    command.insert(1,'-Dprojectseele.regionalBuild=r33-repair');command.insert(1,'-Dprojectseele.bayRepairSerial='+str(serial))
    command.insert(1,'-Dprojectseele.bayRepairVisual='+str(visual).lower())
    command[command.index('--quickPlaySingleplayer')+1]='SEELE_FIELD_R31_REVIEW';spec['command']=command
    target=ROOT/'.Codex/client-r33-repair.json';target.write_text(json.dumps(spec))
    with temporary_options(ROOT/'run/options.txt',':',{'renderDistance':'6','fov':'0.625'}):
        with temporary_options(ROOT/'run/config/oculus.properties','=',{'enableShaders':'false'}):
            code=run_prepared(target,java_environment()[1])
    result=json.loads((ROOT/('run/saves/SEELE_FIELD_R31_REVIEW/Review/r33_repair_'+('nerv' if serial<0 else 'un'+str(serial))+('_visual' if visual else '')+'.json')).read_text())
    assert code==0 and result['passed'],result
    print('Visual observation:' if visual else 'Original EVA repaired, full duration:',result['duration_ticks'])
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--serial',type=int,default=-1,choices=[-1,0,1]);p.add_argument('--visual-only',action='store_true');a=p.parse_args();main(a.serial,a.visual_only)
