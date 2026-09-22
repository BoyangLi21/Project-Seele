"""Bind the actual Blender execution and Lux source bytes into the offline bundle."""
from pathlib import Path
import argparse,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r30';MODELS=ART/'models'

def main(session):
    export=MODELS/'export';run=json.loads((export/'execution_local.json').read_text())
    evidence={'schema':'lux3d.scene-execution/v1','kind':'external-tool','toolName':'exec_command','callId':session,'recordRef':'exec_command:session:'+session,'executedAt':run['startedAt'],'exportSha256':run['scene_sha256'],'sources':[]}
    for unit,attempt in [('00','r30-1'),('01','r30-2')]:
        source=ART/'lux3d'/('un'+unit)/'source.glb'
        evidence['sources'].append({'itemId':'un'+unit,'attemptId':attempt,'artifactId':attempt+':glb','sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    assert hashlib.sha256((export/'scene.glb').read_bytes()).hexdigest()==evidence['exportSha256']
    (export/'scene_execution.json').write_text(json.dumps(evidence,indent=2))
    spec_path=MODELS/'delivery_spec.json';spec=json.loads(spec_path.read_text());spec['scene']={'status':'ready','artifactPath':'export/scene.glb','evidencePath':'export/scene_execution.json'};spec_path.write_text(json.dumps(spec,ensure_ascii=False,indent=2))
    skill=Path.home()/'.codex/plugins/cache/lux3d/aholo-lux3d/0.1.1/skills/lux3d';python=Path.home()/'.cache/aholo-lux3d/python-3.14/Scripts/python.exe'
    for name in ('EVA-UN-00.glb','EVA-UN-01.glb','scene.glb'):
        result=subprocess.run([str(python),str(skill/'core/runtime/artifact_delivery.py'),'inspect',str(export/name),'--format','glb'],capture_output=True,text=True,encoding='utf8',check=True)
        (export/(name+'.inspection.json')).write_text(result.stdout)
    subprocess.run([str(python),str(skill/'core/runtime/delivery_bundle.py'),'prepare','--spec',str(spec_path),'--output-dir',str(MODELS/'delivery'),'--locale','zh-CN'],check=True)
    from optimize_un_preview_r30 import main as optimize
    optimize()

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--export-session',required=True);main(ap.parse_args().export_session)
