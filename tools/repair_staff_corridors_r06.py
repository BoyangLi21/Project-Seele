"""Restore measured envelopes and the original airport rail-transfer clearance."""
import argparse,json
import numpy as np
import regional_voxels as vox
from scan_regional_completion import volume
from audit_staff_corridors_r06 import OUT,AREAS

def main(apply=False):
    changes={};counts={}
    for area in AREAS:
        data=np.load(OUT/(area+'.npz'));lo=data['lo'];hi=data['hi'];pal=data['palette'];before=data['blocks']
        mask=data['floor']|data['wall']|data['ceiling']|data['soil'];actual,palette=volume(lo,hi)
        if not np.array_equal(np.asarray(palette)[actual[mask]],pal[before[mask]]):
            raise RuntimeError('Changed measured corridor: '+area)
        for kind,target in [('floor','projectseele:nerv_floor_panel'),('wall','projectseele:nerv_wall_panel'),
                            ('ceiling','minecraft:polished_deepslate'),('soil','minecraft:air')]:
            for y,z,x in np.argwhere(data[kind]):
                pos=(int(x+lo[0]),int(y+lo[1]),int(z+lo[2]));old=str(pal[before[y,z,x]])
                state='projectseele:nerv_strip_light' if old.startswith('minecraft:light[') else target
                entry=(old,state,kind)
                if pos in changes and changes[pos]!=entry:raise RuntimeError('Conflicting envelope '+str(pos))
                changes[pos]=entry
    vox.OUT=OUT;p=vox.Painter()
    for pos,(old,state,kind) in sorted(changes.items()):
        p.match((*pos,*pos),old,state,'r06/staff_enclosure/'+kind);counts[kind]=counts.get(kind,0)+1
    p.meta.update(counts=counts,source='R02/R03/R04 authored rooms, stair headroom and native route ports',
                  terrain='Clear only soil in the explicit original airport/bay rail_transfer air box')
    p.apply('repair') if apply else p.save_plan('repair')
    if apply:
        result=[]
        for area in AREAS:
            data=np.load(OUT/(area+'.npz'));lo=data['lo'];hi=data['hi'];actual,pal=volume(lo,hi)
            checked=0
            for pos,(_,state,_) in changes.items():
                if all(lo[i]<=pos[i]<=hi[i] for i in range(3)):
                    x,y,z=pos
                    if pal[actual[y-lo[1],z-lo[2],x-lo[0]]]!=state:raise RuntimeError(('Readback',pos,state))
                    checked+=1
            result.append(dict(area=area,checked=checked))
        (OUT/'verified.json').write_text(json.dumps(dict(counts=counts,readbacks=result),indent=2))
    print('Staff repairs',counts,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
