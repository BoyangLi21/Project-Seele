"""Resolve the final full-world scan's remaining isolated components."""
import argparse,json,math
from itertools import product
import numpy as np
from scipy.spatial.transform import Rotation
import regional_voxels as vox
from query_blocks import read_box,AIR,iter_block_entities
from finish_fixture_supports_r19 import route_segments

OUT=vox.ROOT/'artifacts/world_repair_r19/global_components_final'

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();report=json.loads((OUT/'contact_classification.json').read_text());assert not report['cells_by_class'].get('isolated_soil',0) and not report['cells_by_class'].get('isolated_vegetation',0)
    starts,ends=route_segments();retired=[];retained=[];members=json.loads((vox.WORLD/'r08_native_details.json').read_text())['members']
    for r in report['groups']:
        if r['kind']!='isolated_structure':continue
        lo,hi=np.asarray(r['lo']),np.asarray(r['hi']);reason=None
        if r['cells']<=3:
            # Disconnected remnants of retired pavement and source-ship
            # rigging supports (the replacement cables are actual models).
            near=np.all(np.maximum(starts,ends)>=lo+[-.3,.49,-.3],axis=1)&np.all(np.minimum(starts,ends)<=hi+[1.3,1.02,1.3],axis=1)
            assert not np.any(near) and not list(iter_block_entities(vox.WORLD,vox.DIM,tuple(lo),tuple(hi)))
            b=read_box(vox.WORLD,vox.DIM,tuple(lo-1),tuple(hi+1));cells={q:s for q,s in b.items() if all(lo[i]<=q[i]<=hi[i] for i in range(3)) and s in r['states']};assert len(cells)==r['cells']
            for q,s in cells.items():
                for off in product((-1,0,1),repeat=3):
                    neighbour=tuple(a+d for a,d in zip(q,off))
                    if neighbour not in cells:assert b[neighbour].split('[')[0] in AIR|{'minecraft:light','minecraft:water'},(q,neighbour,b[neighbour])
                p.match((*q,*q),s,'minecraft:air','r19/final_isolated_paving_and_rigging_remnant')
            retired.append(dict(bounds=[r['lo'],r['hi']],cells=r['cells']));continue
        if r['cells']==920:
            assert r['lo']==[19,-443,313];reason='Original main-command green display/light assembly; user explicitly preserves this layout'
        elif r['cells']==782:
            z=370 if lo[2]<400 else 510;legs=[m for m in members if m['key'].startswith(f'crane/{z}/leg/')];assert len(legs)==4
            for m in legs:
                a=np.asarray(m['position']);b=a+Rotation.from_quat(m['rotation']).apply([0,0,m['scale'][2]])
                assert np.all(b>=lo) and np.all(b<=hi+1)
                foot=tuple(map(math.floor,a));assert read_box(vox.WORLD,vox.DIM,foot,foot)[foot]=='minecraft:yellow_terracotta'
            reason='Four continuous modeled steel legs connect the quay bogies to the machinery deck; all 84 member identities preserved'
        elif r['cells']==24:
            z=int(lo[2]);assert any(m['key']==f'crane/{z}/hoist/0' for m in members)
            reason='Crane hook hangs from the modeled hoist and jib; intentionally suspended machinery'
        elif r['cells']==15:
            assert set(r['states'])=={'minecraft:structure_void'};reason='Invisible noncolliding construction markers; not visible stray material'
        assert reason is not None,('Unclassified final component',r)
        retained.append(dict(bounds=[r['lo'],r['hi']],cells=r['cells'],reason=reason))
    assert sum(r['cells'] for r in retired)==14
    p.meta.update(final_full_scan_regions=84,final_full_scan_chunks=31962,retired=retired,retained=retained,
        unsupported_natural_components=0,unclassified_isolated_structures=0,unbuilt_boundaries_not_assumed_air=True)
    p.apply('final_fourteen_fragments') if apply else p.save_plan('final_fourteen_fragments')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
