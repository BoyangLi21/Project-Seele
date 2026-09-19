"""Run the existing native low-stance fixture with only the named candidate pose asset."""
from pathlib import Path
import argparse,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--rifle',action='store_true');parser.add_argument('--unit',type=int,choices=(0,1,2),default=1);args=parser.parse_args()
 candidate=ROOT/'artifacts/facility_r25/crouch/eva_body_r25.json';assert candidate.is_file()
 assert ' ' not in str(candidate),'Use the JVM argument-file launcher for spaced paths'
 env=dict(os.environ);env['PYTHONUTF8']='1';env['OPENBLAS_NUM_THREADS']='1'
 env['JAVA_TOOL_OPTIONS']=(env.get('JAVA_TOOL_OPTIONS','')+' -Dprojectseele.bodyPoseReview='+str(candidate.resolve())+' -Dprojectseele.reviewUnit='+str(args.unit)).strip()
 log=ROOT/'artifacts/facility_r25/validation'/((('rifle' if args.rifle else 'terrain')+'_candidate'+('' if args.unit==1 else '_unit'+str(args.unit)))+'.log')
 with log.open('w',encoding='utf8') as stream:
  subprocess.run([sys.executable,'tools/launch_rendered_client_r17.py','--world','SEELE_TERRAIN_R25_REVIEW','--heap','6G','--review','r25-rifle' if args.rifle else 'r25-terrain','--native-capture'],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
if __name__=='__main__':main()
