"""Close measured gaps around the authored pyramid rooms and circulation core."""
import argparse,json
import numpy as np
import regional_voxels as vox
from audit_pyramid_envelope_r06 import OUT,LO,HI,coords
from scan_regional_completion import volume

def main(apply=False):
    data=np.load(OUT/'pyramid_envelope.npz');before=data['blocks'];palette=data['palette']
    current,current_palette=volume(LO,HI);mask=data['floor']|data['wall']|data['ceiling']
    if not np.array_equal(np.asarray(current_palette)[current[mask]],palette[before[mask]]):
        raise RuntimeError('Pyramid changed since the enclosure survey')
    vox.OUT=OUT;p=vox.Painter();counts={}
    for kind,state in [('floor','minecraft:smooth_stone'),('wall','minecraft:light_gray_concrete'),('ceiling','minecraft:polished_deepslate')]:
        points=coords(data[kind]);counts[kind]=len(points)
        for x,y,z in points:
            old=str(palette[before[y-LO[1],z-LO[2],x-LO[0]]])
            target='minecraft:sea_lantern' if old.startswith('minecraft:light[') else state
            p.match((x,y,z,x,y,z),old,target,'r06/pyramid/envelope/'+kind)
    p.meta.update(source='R04 named spaces and retained native route ports',survey='pyramid_envelope.npz',counts=counts,
                  causes=['two missing wall courses between staircase storeys','open connector ceilings and sides','missing support below wall edges'])
    receipt=p.apply('pyramid_enclosure') if apply else p.save_plan('pyramid_enclosure')
    if apply:
        after,pal=volume(LO,HI)
        for name in ['floor','wall','ceiling']:
            if any(str(s).split('[')[0] in ('minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:light') for s in np.asarray(pal)[after[data[name]]]):
                raise RuntimeError('An enclosure gap remains in the applied mask')
        (OUT/'pyramid_enclosure_verified.json').write_text(json.dumps(dict(counts=counts,verified=True),indent=2))
        print('Enclosure gaps closed',counts,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args();main(args.apply)
