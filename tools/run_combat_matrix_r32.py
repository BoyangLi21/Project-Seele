"""Sequential native actor checks; preserve fresh reports and their exact motion inputs."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/combat_sortie_r32'
CASES={
    'duel':(['--duel','--variant','1'],'r32_normal_','duel_anatomical_pass.json'),
    'un00':(['--normal-attacks','--variant','3'],'r32_normal_','un00_motion_pass.json'),
    'un01':(['--normal-attacks','--variant','4'],'r32_normal_','un01_motion_pass.json'),
    'jump':(['--variant','1'],'r31_combat_','jump_final_pass.json'),
    'jump_early':(['--variant','1','--early-air'],'r31_combat_','jump_early_pass.json'),
}

def main():
    p=argparse.ArgumentParser();p.add_argument('cases',nargs='*',choices=list(CASES));p.add_argument('--driver-view',action='store_true');a=p.parse_args()
    profiles=OUT/'gameplay_sources'
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in profiles.glob('*gameplay_r32*.json')}
    for case in a.cases or CASES:
        args,prefix,report=CASES[case];started=time.time()
        command=[sys.executable,str(ROOT/'tools/run_combat_review_r31.py'),'--video',*(() if a.driver_view else ('--side-view',)),'--gameplay-motion-directory',str(profiles),*args]
        print('Starting native',case,flush=True)
        with (OUT/('matrix_'+case+'.log')).open('w',encoding='utf8') as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        folder=ROOT/'run/saves/SEELE_FIELD_R31_REVIEW/Review'
        path=max(folder.glob(prefix+'*.json'),key=lambda f:f.stat().st_mtime)
        if path.stat().st_mtime<started:raise RuntimeError('No fresh native report: '+case)
        data=json.loads(path.read_text(encoding='utf8'))
        if not data.get('passed'):raise RuntimeError(case+': '+str(data.get('error'))+' '+str(data.get('cases')))
        data['motion_inputs_sha256']=hashes;data['diagnostic_side_camera']=not a.driver_view
        (OUT/report).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
        print('Native PASS',case,data.get('media'),flush=True)

if __name__=='__main__':main()
