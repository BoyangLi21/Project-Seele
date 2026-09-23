"""Sequential native reviews. A fresh report is mandatory for every case."""
from pathlib import Path
import argparse,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_foundation_r33'
CASES=['un00','un01','jump','repair_nerv','repair_un0','repair_un1']
def main(cases):
    for case in cases:
        start=time.time();print('Starting',case,flush=True)
        if case.startswith('repair_'):
            serial=-1 if case=='repair_nerv' else int(case[-1]);command=[sys.executable,'tools/run_bay_repair_r33.py','--serial',str(serial)];report='r33_'+case+'.json'
        else:
            command=[sys.executable,'tools/run_combat_review_r31.py','--video','--gameplay-motion-directory',str(OUT/'profiles')]
            if case!='jump':command+=['--normal-attacks','--variant',str(3 if case=='un00' else 4)]
            report='r31_combat_pass.json' if case=='jump' else 'r32_normal_pass.json'
        with (OUT/('final_'+case+'.log')).open('w',encoding='utf8') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        result=ROOT/'run/saves/SEELE_FIELD_R31_REVIEW/Review'/report
        if not result.is_file() or result.stat().st_mtime<start:raise RuntimeError('No fresh successful report for '+case)
        if not json.loads(result.read_text()).get('passed'):raise RuntimeError('Failed '+case)
        if case.startswith('repair_'):(OUT/(case+'.json')).write_bytes(result.read_bytes())
        else:
            label='jump_pass' if case=='jump' else case+'_motion_pass';collect=[sys.executable,'tools/collect_combat_foundation_proof_r33.py',label]
            collect+=['--jump'] if case=='jump' else ['--variant',str(3 if case=='un00' else 4)]
            subprocess.run(collect,cwd=ROOT,check=True)
        print('Passed',case,'elapsed_seconds',round(time.time()-start,1),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cases',nargs='*',choices=CASES);a=p.parse_args();main(a.cases or CASES)
