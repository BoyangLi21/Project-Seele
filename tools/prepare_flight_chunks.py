"""Prepare full native chunks around airborne routes to avoid generation during fast flight."""
import argparse,json,math,msvcrt
from quality_structures import OUT,load
from regional_voxels import WORLD
from pathlib import Path

def prepare(install=False,samples=None):
    chunks=set()
    source=Path(samples) if samples else OUT/'native_flight_samples.json'
    for segment in load(source):
        if max(p[1] for p in segment['points'])<=90:continue
        for x,y,z in segment['points']:
            cx,cz=math.floor(x/16),math.floor(z/16)
            for dx in range(-8,9):
                for dz in range(-8,9):chunks.add((cx+dx,cz+dz))
    plan=dict(chunks=sorted(chunks),radius_chunks=8,source=str(source))
    (OUT/'flight_chunk_plan.json').write_text(json.dumps(plan),encoding='utf-8')
    if install:
        with (WORLD/'session.lock').open('r+b') as lock:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            target=WORLD/'regional_plan.json';master=load(target)
            (OUT/'flight_chunk_master_before.json').write_text(json.dumps(master,ensure_ascii=False,indent=2),encoding='utf-8')
            master['extra_chunks']=plan['chunks'];master['extension_generation']='flight_corridor_r02'
            target.write_text(json.dumps(master,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Native flight corridor chunks',len(chunks),'installed',install,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');ap.add_argument('--samples');args=ap.parse_args();prepare(args.install,args.samples)
