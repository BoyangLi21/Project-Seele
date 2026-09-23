"""Run one bounded native R30 review in its own server root and review world."""
from pathlib import Path
import argparse,subprocess,shutil
from launch_rendered_client_r17 import java_environment,run_prepared

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/combat_sortie_r32'

def main(mode,nerv_only=False):
    assert mode == 'r32-airlift'
    guard=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main|client-r32-sortie.args' }).Count"],capture_output=True,text=True,check=True)
    if int(guard.stdout.strip() or '0'):raise RuntimeError('A Minecraft JVM is running')
    host=ROOT/'.Codex/r32-native-server';host.mkdir(parents=True,exist_ok=True)
    # Reuse this owner's existing development EULA acceptance; do not distribute it.
    assert 'eula=true' in (ROOT/'run/eula.txt').read_text()
    shutil.copy2(ROOT/'run/eula.txt',host/'eula.txt')
    (host/'server.properties').write_text('server-ip=127.0.0.1\nserver-port=25571\nonline-mode=false\nview-distance=6\nsimulation-distance=6\nallow-flight=true\nmax-tick-time=180000\n',encoding='utf8')
    shutil.copytree(ROOT/'run/config',host/'config',dirs_exist_ok=True)
    shutil.copytree(ROOT/'run/projectseele-local-maps',host/'projectseele-local-maps',dirs_exist_ok=True)
    _,env=java_environment()
    cmd=[str(ROOT/'gradlew.bat'),'--no-daemon','writeServerLaunchR17','-PstrictHighDetail=true','-PoptimizedServer','-PregionalBuild='+mode,'-PreviewServerWorld=SEELE_R32_AIR_REVIEW','-PreviewServerDirectory=.Codex/r32-native-server']
    with (ART/(mode+'.log')).open('w',encoding='utf8') as log:
        subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        # Run config carries only the requested review property, not user credentials.
        import json,os
        spec=json.loads((ROOT/'.Codex/server-launch-r17.json').read_text(encoding='utf8'));child=dict(env);child.update(spec['environment'])
        command=[('-Xmx8G' if s.startswith('-Xmx') else s) for s in spec['command']];command.insert(1,'-XX:ActiveProcessorCount=4');command.insert(1,'-Dprojectseele.airReviewNervOnly='+str(nerv_only).lower());args=ROOT/'.Codex/r32-native-server.args'
        def quote(s):
            assert not any(c in s for c in '\r\n\0');return '"'+s.replace('\\','\\\\').replace('"','\\"')+'"'
        args.write_text('\n'.join(quote(s) for s in command[1:]),encoding='utf8')
        proc=subprocess.run([command[0],'@'+str(args)],cwd=spec['workingDirectory'],env=child,stdout=log,stderr=subprocess.STDOUT,timeout=14400 if mode=='r30-collision' else 3600)
        assert proc.returncode==0,proc.returncode
    text=(ART/(mode+'.log')).read_text(encoding='utf8',errors='replace')
    assert 'OutOfMemoryError' not in text and 'Exception in server tick loop' not in text,'Native server failed during execution or shutdown'
    report='r32_airlift_review.json'
    if report:
        outcome=json.loads((ROOT/'run/saves/SEELE_R32_AIR_REVIEW'/report).read_text())
        assert outcome.get('passed'),outcome.get('error',outcome)
    print('Native R32 server finished',mode,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode');ap.add_argument('--nerv-only',action='store_true');a=ap.parse_args();main(a.mode,a.nerv_only)
