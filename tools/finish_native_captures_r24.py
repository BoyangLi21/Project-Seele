"""Sequential final native captures; each game exits before the next starts."""
from pathlib import Path
import json,os,shutil,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r24';V=ART/'validation';WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def run(mode,extra=()):
    began=time.time();log=V/(mode+'_final_capture.log');print('Starting',mode,flush=True)
    with log.open('w',encoding='utf8') as output:
        subprocess.run([sys.executable,str(ROOT/'tools/launch_rendered_client_r17.py'),'--world',WORLD.name,'--review',mode,*extra],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,check=True)
    return began
def latest(pattern,began):
    choices=[p for p in ART.glob(pattern) if p.is_dir() and p.stat().st_mtime>=began-2]
    assert choices,pattern
    return max(choices,key=lambda p:p.stat().st_mtime)
def main():
    os.environ['PYTHONUTF8']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
    sequence={}
    began=run('r24-farview');folder=latest('far_native_*',began);rows=read(folder/'measurements.json')
    assert {r['view'] for r in rows}=={'city_far','geofront_pyramid','geofront_lake','command_interior','un_far'}
    assert all(r['render_chunks']==24 and not r['dh_loaded'] and not r['vehicle_rest_rejected'] and not r['vehicle_phantom_diagnostics']['rejected'] for r in rows)
    sequence['far_views']=str(folder);(V/'final_runtime_sequence.json').write_text(json.dumps(sequence,indent=2))
    began=run('r24-campaign',['--battle-clip',str(ART/'camera/first_battle_r24_candidate.json'),'--movie-only'])
    report=WORLD/'r24_campaign_review.json';result=read(report)
    assert report.stat().st_mtime>=began and result['passed'] and not result['error'] and result['stage']==90,result
    shutil.copy2(report,V/'final_camera_campaign_native_pass.json')
    folder=latest('native_campaign_*',began);capture=read(folder/'frames.json');assert not capture.get('write_failure') and len(capture['frames'])>=400
    output=ART/'media/final';target=output/'R24_TV_first_battle_native.mp4'
    if target.exists() and not target.with_name('R24_TV_first_battle_native_early.mp4').exists():shutil.copy2(target,target.with_name('R24_TV_first_battle_native_early.mp4'))
    subprocess.run([sys.executable,str(ROOT/'tools/export_first_battle_movie_r10.py'),str(folder),'--output-dir',str(output),'--name','R24_TV_first_battle_native','--landing-time','12.2'],cwd=ROOT,check=True)
    sequence['movie']=str(folder);(V/'final_runtime_sequence.json').write_text(json.dumps(sequence,indent=2))
    began=run('r24-worldtour');folder=latest('native_tour_*',began)
    assert all((folder/(name+'.png')).is_file() for name in ('glow_tokyo_bookshop_equipment','glow_pyramid_analysis'))
    sequence['glow_views']=str(folder);sequence['native_runs_completed']=True
    (V/'final_runtime_sequence.json').write_text(json.dumps(sequence,indent=2));print('Native runs finished; visual inspection still required',flush=True)
if __name__=='__main__':main()
