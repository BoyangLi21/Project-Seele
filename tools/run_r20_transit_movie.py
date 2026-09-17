"""Record natural native boarding and riding in the isolated R20 review world."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    a=argparse.ArgumentParser();a.add_argument('service',choices=['port','flight']);q=a.parse_args();mode='r20-port-boarding' if q.service=='port' else 'r20-flight-riding'
    command=[sys.executable,str(ROOT/'tools/launch_rendered_client_r17.py'),'--world','SEELE_R20_REVIEW','--heap','6G','--review',mode,'--native-capture','--prepare-only']
    subprocess.run(command,cwd=ROOT,check=True)
    d=json.loads((ROOT/'.Codex/client-launch-r17.json').read_text(encoding='utf8'));d['command'].insert(1,'-Dprojectseele.tvTransitCapture=true');launch=ROOT/f'.Codex/r20-{q.service}-movie-launch.json';launch.write_text(json.dumps(d,ensure_ascii=False),encoding='utf8')
    subprocess.run([sys.executable,str(ROOT/'tools/launch_rendered_client_r17.py'),'--prepared-file',str(launch)],cwd=ROOT,check=True)
if __name__=='__main__':main()
