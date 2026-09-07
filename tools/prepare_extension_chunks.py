"""Bound construction generation to measured native rails and planned surfaces."""
import argparse,json,math
from quality_structures import OUT,OLD,load
from regional_voxels import WORLD

def prepare(install=False):
    plan=load(OUT/'extension_plan.json');chunks=set()
    def box(x0,z0,x1,z1):
        for x in range(math.floor(x0/16),math.floor(x1/16)+1):
            for z in range(math.floor(z0/16),math.floor(z1/16)+1):chunks.add((x,z))
    x0,x1,z0,z1=plan['estate']['bounds'];box(x0-64,z0-64,x1+64,z1+64)
    for road in plan['roads']:
        for a,b in zip(road['points'],road['points'][1:]):box(min(a[0],b[0])-40,min(a[2],b[2])-40,max(a[0],b[0])+40,max(a[2],b[2])+40)
    for rail in load(OUT/'estate_transit_draft/track_samples.json'):
        for x,y,z in rail['points'][::8]:box(x-14,z-14,x+14,z+14)
    for b in plan['transit']['platforms']:
        x,y,z=b['center'];box(x-b['length']//2-20,z-24,x+b['length']//2+20,z+24)
    envelope=dict(chunks=sorted(chunks),estate=plan['estate']['bounds'],rails=10,source='native MTR RailMath + explicit road and estate bounds')
    (OUT/'extension_envelope.json').write_text(json.dumps(envelope,indent=2),encoding='utf-8')
    if install:
        target=WORLD/'regional_plan.json';master=load(target);master['extra_chunks']=sorted(chunks);master['extension_generation']='kirisato_r02';target.write_text(json.dumps(master,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Extension FULL chunk envelope',len(chunks),'installed',install)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');args=ap.parse_args();prepare(args.install)
