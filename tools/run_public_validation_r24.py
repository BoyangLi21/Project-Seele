"""Build and boot the clean source snapshot using only pinned public dependencies."""
from pathlib import Path
import json,os,shutil,subprocess,sys,time
from bootstrap_dev_dependencies_r24 import FILES,sha
from launch_rendered_client_r17 import java_environment

ROOT=Path(__file__).resolve().parents[1];V=ROOT/'artifacts/facility_r24/validation'
def main():
    manifest=json.loads((ROOT/'artifacts/facility_r24/release/clean_build_snapshot.json').read_text(encoding='utf8'));source=Path(manifest['source'])
    assert source.is_relative_to(ROOT/'.Codex') and not (source/'run/resourcepacks/eva_real_model').exists()
    for name,_,algorithm,expected in FILES:
        cached=ROOT/'.Codex/local-mods'/name;assert sha(cached,algorithm)==expected
        target=source/'.Codex/local-mods'/name;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert sha(target,algorithm)==expected
        else:shutil.copy2(cached,target)
    java,env=java_environment();env['PYTHONUTF8']='1';began=time.time()
    with (V/'final_public_build.log').open('w',encoding='utf8') as log:
        subprocess.run([str(source/'gradlew.bat'),'--no-daemon','build','writeClientLaunchR17','-PregionalBuild=r24-public-smoke','-PclientHeap=4G'],cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('Public snapshot build passed',source,flush=True)
    with (V/'final_public_client.log').open('w',encoding='utf8') as log:
        subprocess.run([sys.executable,str(source/'tools/launch_rendered_client_r17.py'),'--prepared-file',str(source/'.Codex/client-launch-r17.json')],cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    report=source/'artifacts/public_smoke_r24.json';assert report.stat().st_mtime>=began
    data=json.loads(report.read_text());assert data['passed'] and data['private_pack_absent'] and data['no_world_opened']
    assert all(data[name] for name in ('moving_elevators_loaded','geckolib_loaded','mtr_loaded'))
    data['source_snapshot']=str(source);data['pinned_public_dependencies']=len(FILES)
    (V/'clean_public_client_pass.json').write_text(json.dumps(data,indent=2));print('Public-only native client passed',data,flush=True)
if __name__=='__main__':main()
