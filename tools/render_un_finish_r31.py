"""Render the exact isolated R31 candidate and its copied R30 baseline with the same camera."""
import sys,argparse,runpy,shutil,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r31/models'
parser=argparse.ArgumentParser();parser.add_argument('--unit',choices=('00','01'),required=True);parser.add_argument('--with-baseline',action='store_true');a=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
def render(root,views,pose='rest'):
    sys.argv=[str(ROOT/'tools/render_un_r30.py'),'--','--unit',a.unit,'--asset-root',str(root),'--views',views,'--pose',pose];runpy.run_path(str(ROOT/'tools/render_un_r30.py'));gc.collect()
if a.with_baseline:
    before=ART/'baseline_review'/('un'+a.unit)/'runtime/assets/projectseele';shutil.copytree(ART/('un'+a.unit)/'baseline/assets/projectseele',before,dirs_exist_ok=True)
    render(ART/'baseline_review','front')
render(ART,'front,threequarter,rear,head,hand_r,dorsal')
render(ART,'hand_r','fist')
print('R31 actual geometry renders complete',a.unit,flush=True)
