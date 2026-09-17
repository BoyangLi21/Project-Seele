"""Verify the main save is still the cold baseline plus the recorded 87 lift cells."""
import hashlib,json
from pathlib import Path
import numpy as np
from query_blocks import iter_selected_sections
from transplant_s22_authority import read_region,parse_chunk
from regional_voxels import ROOT,WORLD,DIM
OUT=ROOT/'artifacts/world_rebuild_r20'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    baseline=json.loads((OUT/'baseline.json').read_text());backup=Path(baseline['backup'])/'world'
    assert all(sha(ROOT/k)==v for k,v in baseline['preexisting_dirty_files'].items()),'Pre-existing user files changed'
    allowed={'dimensions/projectseele/geofront/region/r.0.-1.mca','dimensions/projectseele/geofront/region/r.0.0.mca'}
    before={p.relative_to(backup).as_posix():p for p in backup.rglob('*') if p.is_file()}
    after={p.relative_to(WORLD).as_posix():p for p in WORLD.rglob('*') if p.is_file() and p.name!='session.lock'}
    assert set(before)==set(after),('Unexpected main save files',set(before)^set(after))
    changed=[k for k in before if k not in allowed and sha(before[k])!=sha(after[k])]
    assert not changed,('Main save changed outside the lift patch',changed)
    deltas={};folder=OUT/'lifts/clear_owned_lift_sweeps/applied_20260917_113254_525264/delta'
    for p in folder.glob('c.*.*.npz'):
        _,x,z,_=p.name.split('.');d=np.load(p);rows=[]
        for i,old,new in zip(d['offsets'],d['before'],d['after']):
            i=int(i);rows.append(((i&15,int(d['minimum'])+(i>>8),(i>>4)&15),str(d['palette'][old]),str(d['palette'][new])))
        deltas[int(x),int(z)]=rows
    selected={q:set(range(-42,20)) for q in deltas}
    old={(x,z,y):(p,i) for x,z,y,p,i in iter_selected_sections(backup,DIM,selected)}
    for x,z,y,p,i in iter_selected_sections(WORLD,DIM,selected):
        pal,idx=old[x,z,y];expected=np.asarray(pal)[idx].copy();actual=np.asarray(p)[i]
        for (xx,yy,zz),was,now in deltas[x,z]:
            if yy//16!=y:continue
            offset=((yy&15)<<8)|(zz<<4)|xx;assert expected[offset]==was
            # Fixed-width unicode palettes may be too short for the new name.
            if len(now)>expected.dtype.itemsize//4:expected=expected.astype('<U'+str(len(now)))
            expected[offset]=now
        assert np.array_equal(expected,actual),('Main blocks differ from known lift changes',x,z,y)
    for relative in allowed:
        _,a=read_region(before[relative]);_,b=read_region(after[relative]);rx,rz=map(int,Path(relative).stem.split('.')[1:])
        for index,(old,new) in enumerate(zip(a,b)):
            cx,cz=rx*32+index%32,rz*32+index//32
            if (cx,cz) not in deltas:assert old==new,('Unexpected changed main chunk',cx,cz)
            else:
                oa,nb=parse_chunk(old),parse_chunk(new)
                assert oa.get('block_entities')==nb.get('block_entities'),'Lift repair changed block-entity identity'
    receipt=dict(passed=True,main=str(WORLD),cold_backup=str(backup),expected_lift_cells=sum(map(len,deltas.values())),files=len(before),preexisting_user_files=len(baseline['preexisting_dirty_files']))
    (OUT/'main_preflight.json').write_text(json.dumps(receipt,indent=2));print(receipt)
if __name__=='__main__':main()
