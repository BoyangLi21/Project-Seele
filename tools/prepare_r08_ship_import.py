"""Cache the two selected author builds and survey their destination via query_blocks."""
from pathlib import Path
import sys,json,importlib.util
from collections import Counter
import numpy as np
import scan_regional_completion as scan
from query_blocks import iter_block_entities,AIR
import regional_voxels as vox

OUT=vox.ROOT/'artifacts/world_refinement_r08/ships'
SOURCE=vox.ROOT/'external-assets/work/ships/nekoseal_division6/Destroyer Division 6'
SPECS=[dict(id='dd6_01',lo=(-565,96,-473),hi=(-320,158,-443),destination=(1444,330)),dict(id='dd6_02',lo=(-234,96,-7),hi=(11,158,23),destination=(1494,330))]

def main():
    OUT.mkdir(parents=True,exist_ok=True);report=[]
    previous=(scan.WORLD,scan.DIM);scan.WORLD=SOURCE;scan.DIM='minecraft:overworld'
    for s in SPECS:
        a,p=scan.volume(s['lo'],s['hi']);np.savez_compressed(OUT/(s['id']+'_source.npz'),blocks=a,palette=np.array(p),lo=s['lo'],hi=s['hi'])
        valid=np.array([q.split('[')[0] not in AIR|{'minecraft:water','minecraft:barrier','minecraft:seagrass','minecraft:kelp','minecraft:kelp_plant'} for q in p])[a]
        xyz=np.argwhere(valid)[:,[2,0,1]]+np.array(s['lo']);lo=xyz.min(0);hi=xyz.max(0)
        barriers=np.argwhere(np.array([q.startswith('minecraft:barrier') for q in p])[a]);heights=Counter((barriers[:,0]+s['lo'][1]).tolist())
        print(s['id'],'bounds',lo.tolist(),hi.tolist(),'solid',int(valid.sum()),'barriers',dict(heights),flush=True)
        report.append(dict(**s,actual_bounds=[lo.tolist(),hi.tolist()],solid=int(valid.sum()),barrier_heights=dict(heights)))
        # Native signs are inspected for ship identity, without importing commands/entities.
        signs=[]
        for entry in iter_block_entities(SOURCE,'minecraft:overworld',s['lo'],s['hi']):signs.append(str(entry))
        (OUT/(s['id']+'_signs.json')).write_text(json.dumps(signs,ensure_ascii=False,indent=2),encoding='utf8')
    scan.WORLD,scan.DIM=previous
    lo=(1400,40,312);hi=(1536,125,600);a,p=scan.volume(lo,hi);np.savez_compressed(OUT/'berth_before.npz',blocks=a,palette=np.array(p),lo=lo,hi=hi)
    (OUT/'selected.json').write_text(json.dumps(report,indent=2),encoding='utf8')

if __name__=='__main__':main()
