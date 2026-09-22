"""Reuse already compiled client launch metadata for a guarded R30 native review."""
from pathlib import Path
import argparse,json
from launch_rendered_client_r17 import run_prepared,java_environment

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('r30-terrain-focus','r30-power-client','r30-un-models'));a=ap.parse_args()
    source=ROOT/'.Codex/client-launch-r17.json';spec=json.loads(source.read_text(encoding='utf8'));cmd=spec['command']
    assert any(s.startswith('-Dprojectseele.regionalBuild=r30-') for s in cmd)
    assert cmd[cmd.index('--quickPlaySingleplayer')+1]==('SEELE_FIELD_R30_REVIEW' if a.mode=='r30-un-models' else 'SEELE_TERRAIN_R30_REVIEW')
    for i,s in enumerate(cmd):
        if s.startswith('-Dprojectseele.regionalBuild='):cmd[i]='-Dprojectseele.regionalBuild='+a.mode
    launch=ROOT/'.Codex'/('client-'+a.mode+'.json');launch.write_text(json.dumps(spec),encoding='utf8')
    # Block texture quality does not affect this isolated motion fixture. Keep
    # the real high-detail EVA resources, and restore the user's pack choices.
    option=ROOT/'run/options.txt';lines=option.read_text(encoding='utf8').splitlines();original={}
    for i,line in enumerate(lines):
        key,_,value=line.partition(':')
        if key=='resourcePacks' and a.mode!='r30-un-models':
            original[key]=line;packs=json.loads(value);lines[i]=key+':'+json.dumps([p for p in packs if 'rotrblocks' not in p])
        elif key=='renderDistance':original[key]=line;lines[i]='renderDistance:8'
    option.write_text('\n'.join(lines)+'\n',encoding='utf8')
    try:code=run_prepared(launch,java_environment()[1])
    finally:
        current=option.read_text(encoding='utf8').splitlines();option.write_text('\n'.join(original.get(s.partition(':')[0],s) for s in current)+'\n',encoding='utf8')
    assert code==0,code

if __name__=='__main__':main()
