"""Run maintenance/lighting checks only in the frozen R39 review save."""
from pathlib import Path
import argparse,json
from contextlib import ExitStack
from release_combat_r36 import guard
from run_combat_review_r31 import temporary_options,compiled_hash
from launch_rendered_client_r17 import run_prepared,java_environment
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['transport','lighting']);p.add_argument('--shader');p.add_argument('--resume-return',action='store_true');a=p.parse_args();guard();compiled_hash()
    d=json.loads((ROOT/'.Codex/client-launch-r17.json').read_text());cmd=[x for x in d['command'] if not x.startswith('-Dprojectseele.regionalBuild=')]
    cmd.insert(1,'-Dprojectseele.regionalBuild='+('r39-transport' if a.mode=='transport' else 'r39-lighting-photos'))
    if a.resume_return:cmd.insert(1,'-Dprojectseele.r39ResumeReturn=true')
    if '--quickPlaySingleplayer' in cmd:cmd[cmd.index('--quickPlaySingleplayer')+1]='SEELE_FIELD_R39_REVIEW'
    else:cmd+=['--quickPlaySingleplayer','SEELE_FIELD_R39_REVIEW']
    d['command']=cmd;path=ROOT/'.Codex/client-r39-maintenance.json';path.write_text(json.dumps(d))
    with ExitStack() as stack:
        stack.enter_context(temporary_options(ROOT/'run/options.txt',':',{'renderDistance':'10' if a.mode=='lighting' else '6','pauseOnLostFocus':'false'}))
        settings={'enableShaders':'true' if a.mode=='lighting' else 'false'}
        if a.shader:settings['shaderPack']=a.shader
        stack.enter_context(temporary_options(ROOT/'run/config/oculus.properties','=',settings))
        result=run_prepared(path,java_environment()[1])
    if a.mode=='transport':
        report=ROOT/'artifacts/transport_return_r39/native.json'
        if not report.exists() or not json.loads(report.read_text()).get('passed'):return 2
    return result
if __name__=='__main__':raise SystemExit(main())
