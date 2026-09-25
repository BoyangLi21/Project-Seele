"""Run maintenance/lighting checks only in the frozen R38 review save."""
from pathlib import Path
import argparse,json
from contextlib import ExitStack
from release_combat_r36 import guard
from run_combat_review_r31 import temporary_options,compiled_hash
from launch_rendered_client_r17 import run_prepared,java_environment
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['recovery','lighting']);p.add_argument('--shader');p.add_argument('--live-cargo',action='store_true');a=p.parse_args();guard();compiled_hash()
    d=json.loads((ROOT/'.Codex/client-launch-r17.json').read_text());cmd=[x for x in d['command'] if not x.startswith('-Dprojectseele.regionalBuild=')]
    cmd.insert(1,'-Dprojectseele.regionalBuild='+('r38-recovery' if a.mode=='recovery' else 'r38-lighting-photos'))
    if a.live_cargo:cmd.insert(1,'-Dprojectseele.r38LiveCargo=true')
    if '--quickPlaySingleplayer' in cmd:cmd[cmd.index('--quickPlaySingleplayer')+1]='SEELE_FIELD_R38_REVIEW'
    else:cmd+=['--quickPlaySingleplayer','SEELE_FIELD_R38_REVIEW']
    d['command']=cmd;path=ROOT/'.Codex/client-r38-maintenance.json';path.write_text(json.dumps(d))
    with ExitStack() as stack:
        stack.enter_context(temporary_options(ROOT/'run/options.txt',':',{'renderDistance':'10','pauseOnLostFocus':'false'}))
        settings={'enableShaders':'true' if a.mode=='lighting' else 'false'}
        if a.shader:settings['shaderPack']=a.shader
        stack.enter_context(temporary_options(ROOT/'run/config/oculus.properties','=',settings))
        result=run_prepared(path,java_environment()[1])
    if a.mode=='recovery':
        report=ROOT/'artifacts/combat_facility_r38'/('force_recovery_cargo.json' if a.live_cargo else 'force_recovery.json')
        if not report.exists() or not json.loads(report.read_text()).get('passed'):return 2
    return result
if __name__=='__main__':raise SystemExit(main())
